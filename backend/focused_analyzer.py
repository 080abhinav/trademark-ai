"""
Focused Analyzer — Per-Mark, Anti-Hallucination Trademark Analysis
===================================================================
Replaces rag_analyzer.py. Core philosophy:
  • ONE mark at a time, ONE issue at a time
  • LLM gets ~200-500 tokens of focused TMEP context (not thousands)
  • Prior marks processed INDIVIDUALLY — no collective feeding
  • Citations validated against our hardcoded 26 TMEP sections (all 13 DuPont factors)
  • Deterministic rules where possible, LLM only for nuanced judgment

THREE-TIER ARCHITECTURE:
  Tier 1: ML Similarity (Phonetic/Semantic/Visual via sentence-transformers)
  Tier 2: Deterministic Screening (9 strict rules)
  Tier 3: LLM (Groq/Gemini) for ambiguous/high-risk marks

WHY THIS WORKS:
  The old RAG pipeline retrieved 5+ TMEP sections per query and fed ALL
  prior marks at once. With ~120 prior marks from a 443-page report, the
  LLM saw >5000 tokens of conflicting data and hallucinated. Now, each
  LLM call sees ONE prior mark + ONE TMEP section = clear, focused answer.
"""

import os
import json
import asyncio
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from google import genai

from similarity_engine import engine as similarity_engine, ScreeningResult, SimilarityScores

from tmep_knowledge import (
    TMEP_SECTIONS,
    get_section,
    get_sections_by_category,
    get_confusion_sections,
    get_descriptiveness_sections,
    format_section_for_prompt,
    validate_citation,
    VALID_SECTIONS,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MarkComparisonResult:
    """Result of comparing ONE prior mark against the applied-for mark."""
    prior_mark_name: str
    prior_mark_goods: str
    prior_mark_classes: List[int]
    prior_mark_reg_number: str
    is_similar: bool
    is_related_goods: bool
    confusion_risk: str          # HIGH / MEDIUM / LOW
    reasoning: str               # 2-3 sentences
    key_factor: str              # Which DuPont factor is decisive
    tmep_section: str            # e.g. "1207.01"
    citation_text: str
    confidence: float            # 0.0 to 1.0
    name_contained: bool         # Does applied mark contain prior mark name?
    # 3-Tier Architecture metadata
    tier_resolved: str = ""      # "tier1_2" or "tier3" — which tier made the decision
    similarity_scores: Optional[Dict] = None  # Raw ML scores from Tier 1


@dataclass
class IssueResult:
    """Result of analyzing a single issue (descriptiveness, specimens, etc.)."""
    issue_type: str              # e.g. "descriptiveness", "specimen_deficiency"
    risk_level: str              # HIGH / MEDIUM / LOW
    title: str
    description: str
    tmep_section: str
    citation_text: str
    reasoning: str
    confidence: float
    recommendation: str


@dataclass
class FullAnalysisResult:
    """Complete analysis result with per-mark breakdown."""
    mark: str
    goods_services: str
    classes: List[int]
    # Per-mark confusion analysis (the KEY differentiator)
    per_mark_results: List[MarkComparisonResult]
    # Non-confusion issues
    other_issues: List[IssueResult]
    # Aggregated
    overall_confusion_risk: str  # HIGH / MEDIUM / LOW
    highest_risk_mark: Optional[str]
    total_prior_marks_analyzed: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int


# ---------------------------------------------------------------------------
# Focused Analyzer
# ---------------------------------------------------------------------------

class FocusedAnalyzer:
    """
    Anti-Hallucination Trademark Analyzer.

    Architecture:
    1. analyze_single_prior_mark() — ONE mark at a time with focused TMEP context
    2. analyze_descriptiveness() — uses only §1209 sections
    3. analyze_specimen_issues() — uses only §904 sections
    4. analyze_filing_issues() — uses only §806
    5. analyze_identification_issues() — uses only §1402
    6. run_full_analysis() — orchestrates everything, aggregates results
    """

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
    ):
        # Prefer Gemini (interviewer's choice) over Groq
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")
        self.groq_api_key = groq_api_key or os.environ.get("GROQ_API_KEY")

        if self.gemini_api_key and not self.groq_api_key:
            self.llm_provider = "gemini"
            self.model_name = "gemini-2.0-flash-lite"
            print(f"🔧 Focused Analyzer initialized (Gemini: {self.model_name})")
            print(f"   ⚡ Rate limits: 15 RPM, 1,000 RPD (free tier)")
        elif self.groq_api_key:
            self.llm_provider = "groq"
            self.model_name = "llama-3.1-8b-instant"
            print(f"🔧 Focused Analyzer initialized (Groq: {self.model_name})")
            print(f"   ⚡ Rate limits: 30 RPM (free tier — fallback)")
        else:
            self.llm_provider = None
            self.model_name = "none"
            print("⚠️ WARNING: No LLM API key set. Set GROQ_API_KEY or GEMINI_API_KEY.")

        print(f"   📚 TMEP Knowledge: {len(TMEP_SECTIONS)} sections loaded")
        print(f"   🛡️  Anti-hallucination: 3-Tier analysis, citation validation")

    # ------------------------------------------------------------------
    # Tier 3 (LLM) call (shared by all analysis methods)
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str, temperature: float = 0.0, max_tokens: int = 512) -> Optional[str]:
        """
        Call LLM via REST API. Supports Groq (primary) and Gemini (fallback).
        Groq uses OpenAI-compatible API format.
        Returns raw response text, or None on failure.
        """
        if self.llm_provider == "groq":
            return self._call_groq(prompt, temperature, max_tokens)
        elif self.llm_provider == "gemini":
            return self._call_gemini(prompt, temperature, max_tokens)
        else:
            print("   ⚠️  No LLM provider configured")
            return None

    def _call_groq(self, prompt: str, temperature: float = 0.0, max_tokens: int = 512) -> Optional[str]:
        """Call Groq API (OpenAI-compatible format). 30 RPM, 14,400 RPD free tier."""
        import time
        import urllib.request
        import urllib.error
        import json

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.groq_api_key}',
            'User-Agent': 'TrademarkRiskAssessment/3.0',
        }
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a USPTO trademark examining attorney. Follow instructions precisely and respond in the exact format requested."},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        max_retries = 5
        base_delay = 5.0

        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(data).encode('utf-8'),
                    headers=headers,
                    method='POST'
                )
                with urllib.request.urlopen(req) as response:
                    res_json = json.loads(response.read().decode('utf-8'))
                    choices = res_json.get('choices', [])
                    if not choices:
                        return None
                    text = choices[0].get('message', {}).get('content', '')
                    if not text:
                        return None
                    return self._clean_llm_output(text)

            except urllib.error.HTTPError as e:
                error_str = e.read().decode('utf-8')

                if e.code == 429 or e.code == 503:
                    if attempt < max_retries - 1:
                        sleep_time = base_delay * (2 ** attempt)
                        print(f"   ⚠️  Groq Rate Limit. Retrying in {sleep_time:.0f}s... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(sleep_time)
                        continue

                print(f"   ⚠️  Groq API error ({e.code}): {error_str[:200]}")
                return None
            except Exception as e:
                print(f"   ⚠️  Groq API Request failed: {e}")
                return None

        return None

    def _call_gemini(self, prompt: str, temperature: float = 0.0, max_tokens: int = 512) -> Optional[str]:
        """Call Gemini API (fallback). 15 RPM free tier."""
        import time
        import urllib.request
        import urllib.error
        import json

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.gemini_api_key}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }

        max_retries = 10
        base_delay = 15.0

        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
                with urllib.request.urlopen(req) as response:
                    res_json = json.loads(response.read().decode('utf-8'))
                    candidates = res_json.get('candidates', [])
                    if not candidates:
                        return None
                    parts = candidates[0].get('content', {}).get('parts', [])
                    text = ""
                    for p in parts:
                        if 'text' in p:
                            text = p['text']
                    if not text:
                        return None
                    return self._clean_llm_output(text)

            except urllib.error.HTTPError as e:
                error_str = e.read().decode('utf-8')

                if e.code == 429 or e.code == 503 or "quota" in error_str.lower() or "exhausted" in error_str.lower():
                    if attempt < max_retries - 1:
                        retry_match = re.search(r'"retryDelay":\s*"(\d+)s"', error_str)
                        sleep_time = int(retry_match.group(1)) + 1 if retry_match else base_delay * (2 ** attempt)
                        print(f"   ⚠️  Gemini Rate Limit. Retrying in {sleep_time:.0f}s... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(sleep_time)
                        continue

                print(f"   ⚠️  Gemini API error ({e.code}): {error_str[:200]}")
                return None
            except Exception as e:
                print(f"   ⚠️  Gemini API Request failed: {e}")
                return None

        return None

    @staticmethod
    def _clean_llm_output(text: str) -> str:
        """Strip leaked prompt questions and formatting artifacts from LLM output."""
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            # Skip lines that are echoed prompt questions (numbered items)
            if re.match(r'^\*\*\d+\.', stripped):  # **1. Could this mark...
                continue
            if re.match(r'^\d+\.\s+[A-Z]{2,}', stripped):  # 2. USE OF USPTO... / 1. IS THE...
                continue
            if re.match(r'^\d+\.\s+(Could|Will|Should|Is |For |If |Are |Does )', stripped):
                continue
            cleaned.append(line)
        return "\n".join(cleaned).strip()

    @staticmethod
    def _validate_citations(text: str) -> str:
        """
        Anti-hallucination guardrail: scans text for TMEP citations and 
        verifies they exist in our knowledge base. Flags fake citations.
        """
        # Find patterns like TMEP 1207.01(b) or § 1209.03
        pattern = r'(?:TMEP|§)\s*([\d\.]+(?:\([a-zA-Z0-9]+\))*)'
        matches = re.finditer(pattern, text)
        invalid_citations = []
        for match in matches:
            citation = match.group(1).strip()
            if not validate_citation(citation):
                invalid_citations.append(citation)
        
        if invalid_citations:
            deduped = list(dict.fromkeys(invalid_citations))
            text += f" [⚠️ WARNING: LLM cited unrecognized TMEP section(s): {', '.join(deduped)}. This may be a hallucination.]"
            
        return text

    @staticmethod
    def _normalize_ocr_text(text: str) -> str:
        """Fix common PDF/OCR text artifacts like mid-word spaces."""
        # Fix known OCR splits: 'ELECTROL YTES' -> 'ELECTROLYTES'
        text = re.sub(r'\b(\w+)\s+(\w+)\b', lambda m: m.group(0) if len(m.group(1)) > 3 or len(m.group(2)) > 3 else m.group(1) + m.group(2), text)
        # Specific known fixes for CompuMark PDFs
        text = text.replace('ELECTROL YTES', 'ELECTROLYTES')
        text = text.replace('electrol ytes', 'electrolytes')
        return text

    # Common English words relevant to trademark analysis
    _COMMON_WORDS = {
        # Basic English words that indicate the mark has meaning
        'the', 'a', 'an', 'and', 'or', 'for', 'of', 'to', 'in', 'on', 'at', 'by', 'is',
        'it', 'my', 'no', 'do', 'go', 'so', 'up', 'be', 'we', 'he', 'me', 'us',
        # Action/descriptive words common in marks
        'live', 'more', 'love', 'life', 'pure', 'power', 'strong', 'fresh', 'clean',
        'fast', 'best', 'good', 'well', 'free', 'new', 'max', 'pro', 'plus', 'ultra',
        'super', 'mega', 'bio', 'eco', 'green', 'blue', 'red', 'gold', 'silver',
        'smart', 'fit', 'slim', 'lean', 'vital', 'prime', 'elite', 'peak', 'edge',
        'rush', 'boost', 'burn', 'fuel', 'glow', 'flow', 'zen', 'calm', 'bold',
        # Product-related words
        'drink', 'drinks', 'energy', 'sport', 'sports', 'health', 'nutrition',
        'vitamin', 'protein', 'water', 'juice', 'tea', 'cola', 'soda', 'brew',
        'food', 'diet', 'body', 'mind', 'soul', 'spirit', 'natural', 'organic',
        'tear', 'pour', 'mix', 'shake', 'blend', 'drop', 'splash', 'fizz',
        # Common mark words
        'mark', 'brand', 'star', 'sun', 'moon', 'sky', 'sea', 'rock', 'fire',
        'ice', 'iron', 'steel', 'wolf', 'bear', 'lion', 'hawk', 'eagle', 'phoenix',
        'king', 'queen', 'royal', 'crown', 'shield', 'knight', 'ace', 'one',
    }

    def _check_if_fanciful(self, mark: str) -> bool:
        """
        Deterministic check: is this mark a coined/fanciful term?
        Returns True if the mark has NO recognizable English words.
        This prevents the LLM from hallucinating meaning for random strings.
        """
        # Split mark into words, lowercase
        words = re.findall(r'[a-zA-Z]+', mark.lower())
        if not words:
            return False  # No alpha chars — can't determine

        # Check if ANY word in the mark is a known English word
        for word in words:
            if word in self._COMMON_WORDS:
                return False  # Contains a real word — let LLM analyze
            # Also check if any 3+ letter substring is a common word
            # (handles cases like "LIVEMORE" containing "live" and "more")
            if len(word) >= 5:
                for cw in self._COMMON_WORDS:
                    if len(cw) >= 3 and cw in word:
                        return False  # Contains embedded word — let LLM analyze

        # No recognizable words found — mark is FANCIFUL
        return True

    # ------------------------------------------------------------------
    # 1. Per-mark confusion analysis (CORE anti-hallucination feature)
    # ------------------------------------------------------------------

    def analyze_single_prior_mark(
        self,
        mark: str,
        goods_services: str,
        classes: List[int],
        prior_mark: Dict,
        similarity_scores: Optional[Dict] = None,
        tier2_trigger: str = ""
    ) -> MarkComparisonResult:
        """
        Tier 3: Analyze ONE prior mark for likelihood of confusion using Gemini.
        Only called if the mark bypassed Tier 1/2 filters.
        """
        pm_name = prior_mark.get("name") or prior_mark.get("mark") or "Unknown"
        pm_goods = prior_mark.get("goods_services") or prior_mark.get("goods") or "Unknown"
        pm_classes = prior_mark.get("classes") or []
        pm_reg = prior_mark.get("registration") or prior_mark.get("registration_number") or ""

        mark_lower = mark.lower().strip()
        pm_lower = pm_name.lower().strip()
        name_contained = bool(pm_lower and (pm_lower in mark_lower or mark_lower in pm_lower))
        class_overlap = bool(set(classes) & set(pm_classes)) if classes and pm_classes else False

        # Build focused LLM prompt with CORRECT TMEP section based on escalation reason
        tmep_section_base = "1207.01(b)(i)"
        if tier2_trigger == "high_semantic_similarity":
            # Semantic similarity → foreign equivalents doctrine
            tmep_text = format_section_for_prompt("1207.01(b)(vi)", max_rules=5)
            tmep_section_base = "1207.01(b)(vi)"
        elif tier2_trigger == "dilution_risk":
            # Very high composite without class overlap → dilution
            tmep_text = format_section_for_prompt("1208", max_rules=5)
            tmep_section_base = "1208"
        elif tier2_trigger == "name_contained":
            # Mark contains prior mark entirely → containment doctrine
            tmep_text = format_section_for_prompt("1207.01(d)(i)", max_rules=5)
            tmep_section_base = "1207.01(d)(i)"
        elif tier2_trigger in ("high_phonetic_similarity", "visual_similarity_class_overlap"):
            # Phonetic or visual similarity → mark similarity analysis
            tmep_text = format_section_for_prompt("1207.01(b)(i)", max_rules=5)
            tmep_section_base = "1207.01(b)(i)"
        else:
            # Default: general mark similarity
            tmep_text = format_section_for_prompt("1207.01(b)(i)", max_rules=5)

        # Always add composite mark rules for multi-word marks
        if len(mark.split()) > 1 or len(pm_name.split()) > 1:
            tmep_text += "\n" + format_section_for_prompt("1207.01(d)", max_rules=4)

        # Always add trade channels + buyer sophistication (DuPont factors 3 & 4)
        tmep_text += "\n" + format_section_for_prompt("1207.01(b)(iii)", max_rules=3)
        tmep_text += "\n" + format_section_for_prompt("1207.01(b)(iv)", max_rules=3)

        prompt = f"""You are a USPTO trademark examining attorney. You must STRICTLY analyze whether this prior mark creates a likelihood of confusion with the applied-for mark under the DuPont factors framework (In re E.I. du Pont de Nemours & Co., 476 F.2d 1357, 177 USPQ 563).

APPLIED-FOR MARK: "{mark}"
GOODS/SERVICES: "{goods_services}"
CLASSES: {classes}

PRIOR MARK: "{pm_name}"
PRIOR GOODS/SERVICES: "{pm_goods}"
PRIOR CLASSES: {pm_classes}
REGISTRATION: {pm_reg}

RELEVANT TMEP GUIDANCE:
{tmep_text}

CRITICAL: Analyze ALL relevant DuPont factors including:
- Factor 1: Similarity of marks (sound, appearance, meaning, commercial impression)
- Factor 2: Relatedness of goods/services
- Factor 3: Similarity of trade channels
- Factor 4: Buyer sophistication (low-cost goods = less care = MORE confusion risk)

This is a LEGAL system — err on the side of finding confusion when evidence is ambiguous.

Answer ONLY in this exact format (nothing else):
SIMILAR: YES or NO
RELATED_GOODS: YES or NO
CONFUSION_RISK: HIGH or MEDIUM or LOW
REASONING: [2-3 sentences max, cite specific DuPont factors and TMEP sections]
KEY_FACTOR: [which factor is most important: mark_similarity, goods_relatedness, trade_channels, buyer_sophistication, composite_mark, name_containment, foreign_equivalent, or dilution]
"""

        # Call Gemini (Tier 3)
        llm_response = self._call_llm(prompt, max_tokens=256)

        if llm_response:
            parsed = self._parse_confusion_response(llm_response)
        else:
            parsed = None

        if parsed:
            confusion_risk = parsed["confusion_risk"]
            is_similar = parsed["is_similar"]
            key_factor = parsed["key_factor"]
            reasoning = parsed["reasoning"]
            confidence = 0.85 if confusion_risk == "HIGH" else 0.80
        else:
            # Deterministic fallback — use Tier 1+2 data (NEVER say "unable to analyze")
            if class_overlap and similarity_scores:
                comp = similarity_scores.get("composite", 0)
                confusion_risk = "HIGH" if comp > 0.60 else "MEDIUM"
                reasoning = (
                    f"Class overlap detected between classes {classes} and {pm_classes}. "
                    f"ML similarity scores: Phonetic={similarity_scores.get('phonetic', 0):.2f}, "
                    f"Semantic={similarity_scores.get('semantic', 0):.2f}, "
                    f"Visual={similarity_scores.get('visual', 0):.2f}. "
                    f"Per DuPont factor 2 (§1207.01(b)(ii)), goods in overlapping classes "
                    f"are presumed related, increasing confusion risk."
                )
            elif class_overlap:
                confusion_risk = "MEDIUM"
                reasoning = (
                    f"Class overlap detected between {classes} and {pm_classes}. "
                    f"Per §1207.01(b)(ii), related goods in the same classes increase confusion risk."
                )
            else:
                confusion_risk = "LOW"
                reasoning = (
                    f"No class overlap between {classes} and {pm_classes}. "
                    f"Goods are in different trade channels per §1207.01(b)(iii)."
                )
            is_similar = False
            key_factor = "goods_relatedness" if class_overlap else "no_overlap"
            confidence = 0.4

        if class_overlap and is_similar and confusion_risk == "MEDIUM":
            confusion_risk = "HIGH"
            confidence = min(confidence + 0.1, 1.0)

        section_data = get_section(tmep_section_base)

        return MarkComparisonResult(
            prior_mark_name=pm_name,
            prior_mark_goods=pm_goods,
            prior_mark_classes=pm_classes,
            prior_mark_reg_number=pm_reg,
            is_similar=is_similar,
            is_related_goods=class_overlap or (parsed["is_related_goods"] if parsed else False),
            confusion_risk=confusion_risk,
            reasoning=reasoning,
            key_factor=key_factor,
            tmep_section=tmep_section_base,
            citation_text=section_data["citation_text"] if section_data else "",
            confidence=confidence,
            name_contained=name_contained,
            tier_resolved="tier3",
            similarity_scores=similarity_scores,
        )

    def _parse_confusion_response(self, response: str) -> Optional[Dict]:
        """Parse the structured LLM response for confusion analysis."""
        try:
            lines = response.strip().split("\n")
            result = {
                "is_similar": False,
                "is_related_goods": False,
                "confusion_risk": "LOW",
                "reasoning": "",
                "key_factor": "unknown",
            }
            for line in lines:
                line = line.strip()
                if line.startswith("SIMILAR:"):
                    result["is_similar"] = "YES" in line.upper()
                elif line.startswith("RELATED_GOODS:"):
                    result["is_related_goods"] = "YES" in line.upper()
                elif line.startswith("CONFUSION_RISK:"):
                    risk = line.replace("CONFUSION_RISK:", "").strip().upper()
                    if risk in ("HIGH", "MEDIUM", "LOW"):
                        result["confusion_risk"] = risk
                elif line.startswith("REASONING:"):
                    result["reasoning"] = line.replace("REASONING:", "").strip()
                elif line.startswith("KEY_FACTOR:"):
                    result["key_factor"] = line.replace("KEY_FACTOR:", "").strip().lower()
            
            result["reasoning"] = self._validate_citations(result["reasoning"])
            return result
        except Exception:
            return None

    # ------------------------------------------------------------------
    # 2. Descriptiveness analysis
    # ------------------------------------------------------------------

    def analyze_descriptiveness(
        self, mark: str, goods_services: str
    ) -> IssueResult:
        """Analyze if the mark is descriptive of the goods/services."""
        
        # --- DETERMINISTIC PRE-CHECK: Detect fanciful/coined marks ---
        # If mark has no recognizable English words, it's FANCIFUL (strongest TM)
        # This prevents LLM from hallucinating meaning for random strings
        fanciful_result = self._check_if_fanciful(mark)
        if fanciful_result:
            section_data = get_section("1209.01(b)")
            return IssueResult(
                issue_type="descriptiveness",
                risk_level="LOW",
                title="Descriptiveness / Distinctiveness Analysis",
                description=(
                    f"Mark classified as FANCIFUL for these goods/services. "
                    f'The mark "{mark}" is a coined/invented term with no recognizable English meaning. '
                    f"Fanciful marks receive the STRONGEST trademark protection under the "
                    f"Abercrombie spectrum (Abercrombie & Fitch v. Hunting World, 1976). "
                    f"No descriptiveness concerns."
                ),
                tmep_section="1209.01(b)",
                citation_text=section_data["citation_text"] if section_data else "",
                reasoning=f'"{mark}" is a fanciful/coined mark with no dictionary meaning.',
                confidence=0.95,  # High confidence — deterministic check
                recommendation="Mark appears highly distinctive. No descriptiveness objections expected.",
            )
        
        # --- LLM-POWERED DESCRIPTIVENESS ANALYSIS ---
        tmep_text = format_section_for_prompt("1209.01(b)", max_rules=5)
        tmep_text += "\n" + format_section_for_prompt("1209.03", max_rules=4)

        prompt = f"""You are a USPTO trademark examiner. Determine if this mark is descriptive of the goods/services.

MARK: "{mark}"
GOODS/SERVICES: "{goods_services}"

RELEVANT TMEP GUIDANCE:
{tmep_text}

IMPORTANT: Do NOT classify a slogan or phrase as GENERIC. Generic means the mark IS the common name for the product (e.g., "ENERGY DRINK" for energy drinks). A phrase like "{mark}" is at most DESCRIPTIVE, never GENERIC.

Answer ONLY in this exact format (no extra text):
DESCRIPTIVE: YES or NO or BORDERLINE
RISK_LEVEL: HIGH or MEDIUM or LOW
REASONING: [2-3 sentences explaining why the mark is or is not descriptive of these specific goods]
CLASSIFICATION: DESCRIPTIVE or SUGGESTIVE or ARBITRARY or FANCIFUL
"""

        llm_response = self._call_llm(prompt, max_tokens=1024)
        section_data = get_section("1209.01(b)")

        if llm_response:
            parsed = self._parse_descriptiveness_response(llm_response)
            risk = parsed.get("risk_level", "MEDIUM")
            reasoning = parsed.get("reasoning", "Analysis performed.")
            confidence = 0.75
            classification = parsed.get("classification", "unknown")
            
            # --- ANTI-HALLUCINATION: Classification-Risk consistency check ---
            if classification in ("suggestive", "arbitrary", "fanciful") and risk == "HIGH":
                risk = "LOW"
                confidence = 0.6
                reasoning += " [Note: LLM classified mark as " + classification + " but rated HIGH risk — overridden to LOW since " + classification + " marks are registrable.]"
            elif classification in ("suggestive",) and risk == "MEDIUM":
                risk = "LOW"
            
            description = (
                f"Mark classified as {classification.upper()} for these goods/services. "
                f"{reasoning}"
            )
        else:
            # Deterministic fallback when LLM unavailable
            mark_words = set(w.lower() for w in re.split(r'[\s,]+', mark) if len(w) >= 3)
            goods_words = set(w.lower() for w in re.split(r'[\s,;]+', goods_services) if len(w) >= 3)
            descriptive_overlap = mark_words & goods_words
            is_phrase = len(mark_words) >= 3 or "," in mark
            
            if descriptive_overlap:
                risk = "HIGH"
                classification = "descriptive"
                reasoning = f'The mark "{mark}" contains words ({", ".join(descriptive_overlap)}) that directly describe the goods/services. Per TMEP §1209.01(b).'
            elif is_phrase:
                risk = "LOW"
                classification = "suggestive"
                reasoning = f'The mark "{mark}" is a multi-word phrase that suggests rather than describes the goods. Per Abercrombie & Fitch v. Hunting World (1976).'
            else:
                risk = "LOW"
                classification = "arbitrary"
                reasoning = f'The mark "{mark}" does not describe any quality of the goods/services. Per TMEP §1209.01(b).'
            confidence = 0.60
            description = f"Mark classified as {classification.upper()} for these goods/services. {reasoning}"

        return IssueResult(
            issue_type="descriptiveness",
            risk_level=risk,
            title="Descriptiveness / Distinctiveness Analysis",
            description=description,
            tmep_section="1209.01(b)",
            citation_text=section_data["citation_text"] if section_data else "",
            reasoning=reasoning,
            confidence=confidence,
            recommendation=(
                "Mark is likely descriptive. Options: (1) Argue the mark as a whole is SUGGESTIVE — "
                "the combination requires imagination to connect to the goods. "
                "(2) File on the Supplemental Register and upgrade after acquiring distinctiveness. "
                "(3) If 5+ years of continuous use exists, claim §2(f) acquired distinctiveness."
                if risk == "HIGH"
                else "Monitor for potential descriptiveness objections"
                if risk == "MEDIUM"
                else "Mark appears sufficiently distinctive"
            ),
        )

    def _parse_descriptiveness_response(self, response: str) -> Dict:
        result = {"risk_level": "MEDIUM", "reasoning": "", "classification": "unknown"}
        for line in response.strip().split("\n"):
            line = line.strip()
            if line.startswith("RISK_LEVEL:"):
                level = line.replace("RISK_LEVEL:", "").strip().upper()
                if level in ("HIGH", "MEDIUM", "LOW"):
                    result["risk_level"] = level
            elif line.startswith("REASONING:"):
                result["reasoning"] = line.replace("REASONING:", "").strip()
            elif line.startswith("CLASSIFICATION:"):
                result["classification"] = line.replace("CLASSIFICATION:", "").strip().lower()
        
        result["reasoning"] = self._validate_citations(result["reasoning"])
        return result

    # ------------------------------------------------------------------
    # 3. Specimen analysis
    # ------------------------------------------------------------------

    def analyze_specimen_issues(
        self, mark: str, goods_services: str, classes: List[int]
    ) -> IssueResult:
        """Analyze potential specimen issues with LLM-assisted depth."""
        section_data = get_section("904.03")
        specimen_text = format_section_for_prompt("904.03", max_rules=5)

        # --- LLM-POWERED SPECIMEN ANALYSIS ---
        prompt = f"""You are a USPTO trademark examiner evaluating specimen requirements.

MARK: "{mark}"
GOODS/SERVICES: "{goods_services}"
CLASSES: {classes}

RELEVANT TMEP GUIDANCE:
{specimen_text}

Write a unified analytical paragraph covering: whether this mark could be seen as a slogan rather than a source identifier, whether it might be refused as merely ornamental, and what specimen format is best.

IMPORTANT: Coined/fanciful marks (made-up words with no dictionary meaning) inherently function as source identifiers and are NOT slogans. Only common English phrases risk being seen as slogans.

Do NOT repeat these instructions. Output ONLY the analysis in this format:
RISK_LEVEL: HIGH or MEDIUM or LOW
REASONING: [3-4 sentences of unified analysis — do not use numbered lists or repeat the questions]
SPECIMEN_TYPE: [product_label or product_packaging or website_screenshot or hang_tag]
"""

        llm_response = self._call_llm(prompt, max_tokens=1024)

        if llm_response:
            parsed = self._parse_simple_response(llm_response)
            risk = parsed.get("risk_level", "MEDIUM")
            reasoning = parsed.get("reasoning") or "Specimen analysis performed."
            confidence = 0.75
        else:
            # Deterministic fallback
            is_phrase = len(mark.split()) > 2
            risk = "MEDIUM" if is_phrase else "LOW"
            reasoning = (
                f"The multi-word mark '{mark}' may appear as a slogan on packaging rather than "
                f"a source identifier. For classes {classes}, ensure the specimen shows the mark "
                f"prominently as a trademark on product labels or packaging, not merely as "
                f"informational or decorative text. Per TMEP §904.03."
            ) if is_phrase else (
                f"The mark '{mark}' should function as a source identifier on specimens. "
                f"Standard product labels or packaging showing the mark prominently are acceptable. "
                f"Per TMEP §904.03."
            )
            confidence = 0.60

        return IssueResult(
            issue_type="specimen_deficiency",
            risk_level=risk,
            title="Specimen Analysis",
            description=reasoning,
            tmep_section="904.03",
            citation_text=section_data["citation_text"] if section_data else "",
            reasoning=reasoning,
            confidence=confidence,
            recommendation=(
                "Ensure mark appears as a SOURCE IDENTIFIER on the specimen, not as a slogan or decorative text. "
                "Use product labels showing the mark prominently near the brand name area."
                if risk in ("HIGH", "MEDIUM")
                else "Standard specimen requirements should be met with product labels or packaging."
            ),
        )

    # ------------------------------------------------------------------
    # 4. Filing basis analysis
    # ------------------------------------------------------------------

    def analyze_filing_issues(
        self, mark: str, goods_services: str, filing_basis: str = "1(b)",
        has_confusion_risk: bool = False
    ) -> IssueResult:
        """Analyze filing basis issues with contextual depth."""
        section_data = get_section("806")
        tmep_text = format_section_for_prompt("806", max_rules=5)

        # --- LLM-POWERED FILING ANALYSIS ---
        prompt = f"""You are a USPTO trademark examiner evaluating filing basis issues.

MARK: "{mark}"
GOODS/SERVICES: "{goods_services}"
FILING BASIS: Section {filing_basis}
SIGNIFICANT PRIOR MARKS FOUND: {"YES — high confusion risk detected" if has_confusion_risk else "No major conflicts"}

RELEVANT TMEP GUIDANCE:
{tmep_text}

Write a unified analytical paragraph covering: whether the filing basis is appropriate, strategic implications of the confusion risk for ITU applications, and risks of partial refusal in multi-class filings.

IMPORTANT LEGAL CONTEXT: A §1(b) intent-to-use application is actually STRATEGICALLY APPROPRIATE when high confusion risk exists — it lets the applicant test the waters with the USPTO before investing in product manufacturing and packaging. Do NOT call §1(b) "inappropriate" when confusion risk is high.

Do NOT repeat these instructions. Output ONLY the analysis in this format:
RISK_LEVEL: HIGH or MEDIUM or LOW
REASONING: [3-4 sentences of unified analysis — do not use numbered lists or repeat the questions]
"""

        llm_response = self._call_llm(prompt, max_tokens=1024)

        if llm_response:
            parsed = self._parse_simple_response(llm_response)
            risk = parsed.get("risk_level", "LOW")
            reasoning = parsed.get("reasoning") or (
                f"Filing under §{filing_basis} basis. "
                f"{'Given the high confusion risk from identified prior marks, an intent-to-use strategy provides flexibility.' if has_confusion_risk else 'Standard filing basis requirements apply.'}"
            )
            confidence = 0.75
        else:
            # Deterministic fallback
            risk = "MEDIUM" if has_confusion_risk else "LOW"
            reasoning = (
                f"Application filed under §{filing_basis}. "
                f"{'Given the high confusion risk from prior marks, an intent-to-use application provides strategic flexibility — the applicant can abandon or amend before incurring specimen costs. However, the prior marks may necessitate Office Action responses before registration.' if has_confusion_risk else 'Standard filing basis requirements apply.'} "
                f"Per TMEP §806."
            )
            confidence = 0.65

        return IssueResult(
            issue_type="filing_basis_issue",
            risk_level=risk,
            title="Filing Basis & Strategy Analysis",
            description=reasoning,
            tmep_section="806",
            citation_text=section_data["citation_text"] if section_data else "",
            reasoning=reasoning,
            confidence=confidence,
            recommendation=(
                "Consider filing strategy adjustments — an ITU application allows flexibility but confusion risks may require costly Office Action responses."
                if risk in ("HIGH", "MEDIUM")
                else "Filing basis appears appropriate. Monitor for potential office actions."
            ),
        )

    # ------------------------------------------------------------------
    # 5. Identification of goods/services analysis
    # ------------------------------------------------------------------

    def analyze_identification_issues(
        self, mark: str, goods_services: str, classes: List[int]
    ) -> IssueResult:
        """Analyze identification of goods/services with thorough LLM evaluation."""
        section_data = get_section("1402.01")
        tmep_text = format_section_for_prompt("1402.01", max_rules=5)

        # --- LLM-POWERED IDENTIFICATION ANALYSIS ---
        prompt = f"""You are a USPTO trademark examiner. Evaluate if this identification of goods/services is acceptable.

MARK: "{mark}"
GOODS/SERVICES: "{goods_services}"
CLASSES: {classes}

RELEVANT TMEP GUIDANCE:
{tmep_text}

Evaluate whether the identification is specific enough (not overly broad), uses standard USPTO ID Manual language, has correctly assigned classes (Class 5 = dietary supplements; Class 32 = non-alcoholic beverages), and whether any terms need narrowing or amendment.

Do NOT repeat these instructions. Output ONLY the analysis in this format:
ACCEPTABLE: YES or NO or NEEDS_AMENDMENT
RISK_LEVEL: HIGH or MEDIUM or LOW
REASONING: [3-4 sentences of unified analysis — do not use numbered lists or repeat the questions]
"""

        llm_response = self._call_llm(prompt, max_tokens=1024)

        if llm_response:
            parsed = self._parse_simple_response(llm_response)
            risk = parsed.get("risk_level", "MEDIUM")
            reasoning = parsed.get("reasoning") or (
                f"The identification of goods/services for classes {classes} uses generally acceptable language."
            )
            confidence = 0.75
        else:
            risk = "MEDIUM"
            reasoning = (
                f"The identification '{goods_services}' should be verified against the USPTO ID Manual "
                f"for classes {classes}. Terms like 'energy drinks' and 'dietary supplements' are generally "
                f"acceptable, but the identification should use precise ID Manual language to avoid "
                f"office actions requiring amendment."
            )
            confidence = 0.50

        return IssueResult(
            issue_type="identification_issue",
            risk_level=risk,
            title="Identification of Goods/Services Analysis",
            description=reasoning,
            tmep_section="1402.01",
            citation_text=section_data["citation_text"] if section_data else "",
            reasoning=reasoning,
            confidence=confidence,
            recommendation=(
                "Amend identification to use precise USPTO ID Manual language. Verify class assignments match each listed good/service."
                if risk in ("HIGH", "MEDIUM")
                else "Identification appears acceptable. Verify against current ID Manual before filing."
            ),
        )

    def _parse_simple_response(self, response: str) -> Dict:
        result = {"risk_level": "LOW", "reasoning": ""}
        lines = response.strip().split("\n")
        keywords = {"RISK_LEVEL:", "REASONING:", "ACCEPTABLE:", "SPECIMEN_TYPE:", "DESCRIPTIVE:", "CLASSIFICATION:"}
        collecting_reasoning = False
        reasoning_parts = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("RISK_LEVEL:"):
                collecting_reasoning = False
                level = stripped.replace("RISK_LEVEL:", "").strip().upper()
                if level in ("HIGH", "MEDIUM", "LOW"):
                    result["risk_level"] = level
            elif stripped.startswith("REASONING:"):
                collecting_reasoning = True
                text = stripped.replace("REASONING:", "").strip()
                if text:
                    reasoning_parts.append(text)
            elif collecting_reasoning:
                # Continue capturing reasoning until we hit another keyword
                if any(stripped.startswith(kw) for kw in keywords):
                    collecting_reasoning = False
                elif stripped:
                    reasoning_parts.append(stripped)

        result["reasoning"] = " ".join(reasoning_parts)
        result["reasoning"] = self._validate_citations(result["reasoning"])
        return result

    # _prefilter_mark() REMOVED — consolidated into SimilarityEngine.run_tier2()

    # ------------------------------------------------------------------
    # 6. FULL ANALYSIS ORCHESTRATOR
    # ------------------------------------------------------------------

    async def run_full_analysis(
        self,
        mark: str,
        goods_services: str,
        classes: List[int],
        prior_marks: List[Dict],
    ) -> FullAnalysisResult:
        """
        Run complete trademark analysis with the 3-TIER PIPELINE.

        Tier 1: ML Similarity (Phonetic, Semantic, Visual) — transformer models
        Tier 2: Deterministic Screening — rule-based pass/fail
        Tier 3: Gemini LLM evaluation — only for ambiguous/high-risk marks
        """
        print(f"\n{'='*60}")
        print(f"   3-TIER PIPELINE — Analyzing: {mark}")
        print(f"   Goods: {goods_services}")
        print(f"   Classes: {classes}")
        print(f"   Prior marks to screen: {len(prior_marks)}")
        print(f"{'='*60}")

        tier3_llm_queue = []  # Marks that passed Tier 1+2 → need LLM
        per_mark_results: List[MarkComparisonResult] = []
        tier12_drops = 0

        # ===== TIER 1 + TIER 2: Screen all prior marks =====
        print(f"\n   [TIER 1] Running ML similarity (phonetic/semantic/visual)...")
        print(f"   [TIER 2] Applying deterministic screening rules...")

        for pm in prior_marks:
            pm_name = (pm.get("name") or pm.get("mark") or "Unknown").strip()
            pm_classes = pm.get("classes") or []

            # Run combined Tier 1 + Tier 2 screening
            screening: ScreeningResult = similarity_engine.run_full_screening(
                mark=mark,
                prior_mark_name=pm_name,
                classes=classes,
                pm_classes=pm_classes,
            )

            scores = screening.similarity_scores
            scores_dict = {
                "phonetic": scores.phonetic,
                "semantic": scores.semantic,
                "visual": scores.visual,
                "composite": scores.composite,
            }

            if screening.verdict == "PASS_TO_TIER3":
                # Mark is ambiguous → queue for LLM
                tier3_llm_queue.append((pm, scores_dict, screening.reason))
            elif screening.verdict == "DROP_HIGH":
                # ===== Obvious HIGH risk — deterministic classification =====
                # No LLM needed. Generate template reasoning from ML scores.
                tier12_drops += 1
                trigger = screening.reason
                section_key = "1207.01(d)(i)" if screening.name_contained else "1207.01(b)(i)"
                section_data = get_section(section_key)

                # Generate specific reasoning based on trigger type
                if trigger == "name_contained_class_overlap":
                    reasoning = (
                        f"The applied-for mark contains the prior mark \"{pm_name}\" "
                        f"(or vice versa), creating a strong presumption of likelihood of "
                        f"confusion under TMEP §1207.01(d)(i). The goods/services are in "
                        f"overlapping classes, which increases confusion risk under DuPont "
                        f"Factor 2. Phonetic: {scores.phonetic:.0%}, Semantic: {scores.semantic:.0%}, "
                        f"Visual: {scores.visual:.0%}, Composite: {scores.composite:.0%}."
                    )
                elif trigger == "very_high_composite_class_overlap":
                    reasoning = (
                        f"Extremely high overall similarity (Composite: {scores.composite:.0%}) "
                        f"with overlapping goods/services classes. The marks are similar in "
                        f"sound (Phonetic: {scores.phonetic:.0%}), meaning (Semantic: {scores.semantic:.0%}), "
                        f"and appearance (Visual: {scores.visual:.0%}), satisfying DuPont Factor 1. "
                        f"Class overlap satisfies DuPont Factor 2."
                    )
                elif trigger == "near_identical_phonetic":
                    reasoning = (
                        f"Near-identical phonetic similarity ({scores.phonetic:.0%}) indicates "
                        f"the marks sound substantially the same when spoken, a primary ground "
                        f"for refusal under TMEP §1207.01(b)(i). DuPont Factor 1 is strongly "
                        f"satisfied. Visual: {scores.visual:.0%}, Semantic: {scores.semantic:.0%}."
                    )
                else:  # near_identical_visual_class_overlap
                    reasoning = (
                        f"Near-identical visual similarity ({scores.visual:.0%}) with overlapping "
                        f"classes indicates the marks look substantially the same, creating "
                        f"confusion risk per DuPont Factor 1. Phonetic: {scores.phonetic:.0%}, "
                        f"Semantic: {scores.semantic:.0%}, Composite: {scores.composite:.0%}."
                    )

                per_mark_results.append(MarkComparisonResult(
                    prior_mark_name=pm_name,
                    prior_mark_goods=pm.get("goods_services", ""),
                    prior_mark_classes=pm_classes,
                    prior_mark_reg_number=pm.get("registration", ""),
                    is_similar=True,
                    is_related_goods=screening.class_overlap,
                    confusion_risk="HIGH",
                    reasoning=reasoning,
                    key_factor=trigger,
                    tmep_section=section_key,
                    citation_text=section_data["citation_text"] if section_data else "",
                    confidence=0.90,
                    name_contained=screening.name_contained,
                    tier_resolved="tier1_2",
                    similarity_scores=scores_dict,
                ))
            else:
                # Mark dropped at Tier 1/2 → deterministic LOW/MEDIUM
                tier12_drops += 1
                is_medium = screening.verdict == "DROP_MEDIUM"
                risk_level = "MEDIUM" if is_medium else "LOW"
                section_data = get_section("1207.01(b)(i)")

                per_mark_results.append(MarkComparisonResult(
                    prior_mark_name=pm_name,
                    prior_mark_goods=pm.get("goods_services", ""),
                    prior_mark_classes=pm_classes,
                    prior_mark_reg_number=pm.get("registration", ""),
                    is_similar=is_medium,
                    is_related_goods=screening.class_overlap,
                    confusion_risk=risk_level,
                    reasoning=(
                        f"Moderate similarity detected but below LLM threshold "
                        f"(Composite: {scores.composite:.2f}, Semantic: {scores.semantic:.2f})."
                        if is_medium else
                        f"Low similarity across all dimensions "
                        f"(Composite: {scores.composite:.2f}, Semantic: {scores.semantic:.2f})."
                    ),
                    key_factor="moderate_similarity" if is_medium else "no_similarity",
                    tmep_section="1207.01(b)(i)",
                    citation_text=section_data["citation_text"] if section_data else "",
                    confidence=0.85 if is_medium else 0.95,
                    name_contained=screening.name_contained,
                    tier_resolved="tier1_2",
                    similarity_scores=scores_dict,
                ))

        tier12_high = len([r for r in per_mark_results if r.confusion_risk == "HIGH"])
        total = len(prior_marks)
        print(f"\n   [TIER 1+2 RESULTS]")
        print(f"   ✅ {tier12_drops}/{total} marks filtered without LLM ({tier12_high} HIGH, {tier12_drops - tier12_high} MEDIUM/LOW)")
        print(f"   ➡️  {len(tier3_llm_queue)} marks promoted to Tier 3 (LLM)")

        # ===== TIER 3: LLM Evaluation (Groq or Gemini) =====
        if tier3_llm_queue:
            print(f"\n   [TIER 3] Engaging {self.llm_provider or 'LLM'} ({self.model_name}) for {len(tier3_llm_queue)} complex marks...")

            async def _analyze_mark_tier3(pm_data: Tuple) -> MarkComparisonResult:
                pm, scores, trigger = pm_data
                return await asyncio.to_thread(
                    self.analyze_single_prior_mark,
                    mark, goods_services, classes, pm, scores, trigger
                )

            # Gemini Flash-Lite: 15 RPM → 1 per 4s (use 5.0s for safety)
            # Groq: 30 RPM → 1 per 2s (use 3.5s for safety)
            delay = 5.0 if self.llm_provider == "gemini" else 3.5

            llm_results = []
            for pm_data in tier3_llm_queue:
                res = await _analyze_mark_tier3(pm_data)
                llm_results.append(res)
                await asyncio.sleep(delay)

            per_mark_results.extend(llm_results)

        # ===== AGGREGATION =====
        high_risk = [r for r in per_mark_results if r.confusion_risk == "HIGH"]
        med_risk = [r for r in per_mark_results if r.confusion_risk == "MEDIUM"]
        low_risk = [r for r in per_mark_results if r.confusion_risk == "LOW"]

        print(f"\n   [CONFUSION RESULTS] {len(high_risk)} HIGH, {len(med_risk)} MEDIUM, {len(low_risk)} LOW")

        # ===== OTHER ISSUES (Sequential — LLM calls) =====
        print(f"\n   [OTHER] Analyzing non-confusion issues...")
        has_high_risk = len(high_risk) > 0

        async def _run_other():
            other_delay = 2.5 if self.llm_provider == "groq" else 5.0
            desc_result = await asyncio.to_thread(self.analyze_descriptiveness, mark, goods_services)
            await asyncio.sleep(other_delay)

            spec_result = await asyncio.to_thread(self.analyze_specimen_issues, mark, goods_services, classes)
            await asyncio.sleep(other_delay)

            filing_result = await asyncio.to_thread(self.analyze_filing_issues, mark, goods_services, "1(b)", has_high_risk)
            await asyncio.sleep(other_delay)

            id_result = await asyncio.to_thread(self.analyze_identification_issues, mark, goods_services, classes)

            return desc_result, spec_result, filing_result, id_result

        desc_result, spec_result, filing_result, id_result = await _run_other()
        other_issues = [desc_result, spec_result, filing_result, id_result]

        print(f"   [OTHER] Done: {len(other_issues)} issues analyzed")

        # ===== AGGREGATE =====
        if high_risk:
            overall_confusion = "HIGH"
        elif med_risk:
            overall_confusion = "MEDIUM"
        else:
            overall_confusion = "LOW"

        highest_risk_mark = high_risk[0].prior_mark_name if high_risk else (
            med_risk[0].prior_mark_name if med_risk else None
        )

        # Sort: HIGH first, then MEDIUM, then LOW
        per_mark_results.sort(key=lambda r: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(r.confusion_risk, 3))

        result = FullAnalysisResult(
            mark=mark,
            goods_services=goods_services,
            classes=classes,
            per_mark_results=per_mark_results,
            other_issues=other_issues,
            overall_confusion_risk=overall_confusion,
            highest_risk_mark=highest_risk_mark,
            total_prior_marks_analyzed=len(per_mark_results),
            high_risk_count=len(high_risk),
            medium_risk_count=len(med_risk),
            low_risk_count=len(low_risk),
        )

        print(f"\n   {'='*60}")
        print(f"   ANALYSIS COMPLETE!")
        print(f"   Overall confusion risk: {overall_confusion}")
        print(f"   Tier 1+2 filtered: {tier12_drops}/{total} marks")
        print(f"   Tier 3 LLM calls: {len(tier3_llm_queue)}")
        if highest_risk_mark:
            print(f"   Highest risk: {highest_risk_mark}")
        print(f"   {'='*60}")

        return result


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def test_focused_analyzer():
    """Quick test of the focused analyzer."""
    print("🧪 TESTING FOCUSED ANALYZER")
    print("=" * 60)

    analyzer = FocusedAnalyzer()

    # Test single mark comparison
    print("\n--- Test: Single Prior Mark ---")
    result = analyzer.analyze_single_prior_mark(
        mark="TEAR, POUR, LIVE MORE",
        goods_services="Energy drinks, sports drinks",
        classes=[5, 32],
        prior_mark={
            "name": "POUR MORE",
            "goods_services": "Bottled water",
            "classes": [32],
            "registration": "1234567"
        }
    )
    print(f"  Prior mark: {result.prior_mark_name}")
    print(f"  Confusion risk: {result.confusion_risk}")
    print(f"  Name contained: {result.name_contained}")
    print(f"  Confidence: {result.confidence}")
    print(f"  TMEP §{result.tmep_section}")
    print(f"  Reasoning: {result.reasoning[:200]}")

    # Test descriptiveness
    print("\n--- Test: Descriptiveness ---")
    desc = analyzer.analyze_descriptiveness(
        mark="TEAR, POUR, LIVE MORE",
        goods_services="Energy drinks, dietary supplements"
    )
    print(f"  Risk: {desc.risk_level}")
    print(f"  TMEP §{desc.tmep_section}")
    print(f"  Reasoning: {desc.reasoning[:200]}")

    print("\n✅ Focused Analyzer Test Complete!")


if __name__ == "__main__":
    test_focused_analyzer()
