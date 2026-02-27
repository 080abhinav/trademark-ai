"""
Focused Analyzer — Per-Mark, Anti-Hallucination Trademark Analysis
===================================================================
Replaces rag_analyzer.py. Core philosophy:
  • ONE mark at a time, ONE issue at a time
  • LLM gets ~200-500 tokens of focused TMEP context (not thousands)
  • Prior marks processed INDIVIDUALLY — no collective feeding
  • Citations validated against our hardcoded 20 TMEP sections
  • Deterministic rules where possible, LLM only for nuanced judgment

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
import requests
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

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
        ollama_url: str = "http://localhost:11434/api/generate",
        model_name: str = "llama3.1:8b"
    ):
        self.ollama_url = ollama_url
        self.model_name = model_name
        print(f"🔧 Focused Analyzer initialized (model: {self.model_name})")
        print(f"   📚 TMEP Knowledge: {len(TMEP_SECTIONS)} sections loaded")
        print(f"   🛡️  Anti-hallucination: per-mark analysis, citation validation")

    # ------------------------------------------------------------------
    # LLM call (shared by all analysis methods)
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str, temperature: float = 0.0, max_tokens: int = 512) -> Optional[str]:
        """
        Call Ollama LLM with a focused prompt.
        max_tokens: 256 for short per-mark analyses, 1024 for full analyses.
        Returns raw response text, or None on failure.
        """
        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "temperature": temperature,
                    "seed": 42,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                    },
                },
                timeout=120,
            )
            if response.status_code == 200:
                raw = response.json().get("response", "")
                return self._clean_llm_output(raw)
            return None
        except Exception as e:
            print(f"   ⚠️  LLM error: {e}")
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
    ) -> MarkComparisonResult:
        """
        Analyze ONE prior mark for likelihood of confusion.

        This is the KEY anti-hallucination design:
        - LLM sees ONLY this one prior mark (not all 120)
        - LLM sees ONLY the relevant TMEP section (~200 tokens)
        - LLM output is structured and validated
        """
        pm_name = prior_mark.get("name") or prior_mark.get("mark") or "Unknown"
        pm_goods = prior_mark.get("goods_services") or prior_mark.get("goods") or "Unknown"
        pm_classes = prior_mark.get("classes") or []
        pm_reg = prior_mark.get("registration") or prior_mark.get("registration_number") or ""

        # --- Deterministic check: name containment ---
        mark_lower = mark.lower().strip()
        pm_lower = pm_name.lower().strip()
        name_contained = bool(pm_lower and (pm_lower in mark_lower or mark_lower in pm_lower))

        # --- Deterministic check: class overlap ---
        class_overlap = bool(set(classes) & set(pm_classes)) if classes and pm_classes else False

        # --- Build focused LLM prompt ---
        # Use §1207.01(b)(i) for mark similarity + §1207.01(d) if composite
        tmep_text = format_section_for_prompt("1207.01(b)(i)", max_rules=5)
        if len(mark.split()) > 1 or len(pm_name.split()) > 1:
            tmep_text += "\n" + format_section_for_prompt("1207.01(d)", max_rules=4)

        prompt = f"""You are a USPTO trademark examiner. Analyze if this prior mark creates a likelihood of confusion with the applied-for mark.

APPLIED-FOR MARK: "{mark}"
GOODS/SERVICES: "{goods_services}"
CLASSES: {classes}

PRIOR MARK: "{pm_name}"
PRIOR GOODS/SERVICES: "{pm_goods}"
PRIOR CLASSES: {pm_classes}
REGISTRATION: {pm_reg}

RELEVANT TMEP GUIDANCE:
{tmep_text}

Answer ONLY in this exact format (nothing else):
SIMILAR: YES or NO
RELATED_GOODS: YES or NO
CONFUSION_RISK: HIGH or MEDIUM or LOW
REASONING: [2-3 sentences max explaining why]
KEY_FACTOR: [which factor is most important: mark_similarity, goods_relatedness, trade_channels, composite_mark, or name_containment]
"""

        # --- Call LLM ---
        llm_response = self._call_llm(prompt, max_tokens=256)  # Per-mark: short response, fast

        # --- Parse response ---
        if llm_response:
            parsed = self._parse_confusion_response(llm_response)
        else:
            parsed = None

        # --- Apply deterministic overrides ---
        if name_contained:
            # If the applied mark literally contains the prior mark name,
            # this is almost certainly HIGH risk regardless of LLM opinion
            confusion_risk = "HIGH"
            is_similar = True
            key_factor = "name_containment"
            reasoning = (
                parsed["reasoning"] if parsed else
                f"The applied-for mark '{mark}' contains the prior mark '{pm_name}' "
                f"in its entirety, creating a strong likelihood of confusion per TMEP §1207.01(d)."
            )
            confidence = 0.95
        elif parsed:
            confusion_risk = parsed["confusion_risk"]
            is_similar = parsed["is_similar"]
            key_factor = parsed["key_factor"]
            reasoning = parsed["reasoning"]
            confidence = 0.75 if confusion_risk == "HIGH" else 0.70
        else:
            # LLM failed — use deterministic fallback
            confusion_risk = "MEDIUM" if class_overlap else "LOW"
            is_similar = False
            key_factor = "goods_relatedness" if class_overlap else "unknown"
            reasoning = (
                f"Unable to analyze via LLM. Class overlap detected between {classes} and {pm_classes}."
                if class_overlap else
                f"Unable to analyze via LLM. No class overlap detected."
            )
            confidence = 0.4

        # Boost risk if classes overlap AND LLM already found similarity
        if class_overlap and is_similar and confusion_risk == "MEDIUM":
            confusion_risk = "HIGH"
            confidence = min(confidence + 0.1, 1.0)

        tmep_section = "1207.01(d)" if name_contained else "1207.01(b)(i)"
        section_data = get_section(tmep_section)

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
            tmep_section=tmep_section,
            citation_text=section_data["citation_text"] if section_data else "",
            confidence=confidence,
            name_contained=name_contained,
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
            # If LLM says SUGGESTIVE/ARBITRARY/FANCIFUL but risk is HIGH, that's contradictory
            # Suggestive marks are registrable; only DESCRIPTIVE marks face §2(e)(1) refusal
            if classification in ("suggestive", "arbitrary", "fanciful") and risk == "HIGH":
                risk = "LOW"
                confidence = 0.6  # Lower confidence — LLM contradicted itself
                reasoning += " [Note: LLM classified mark as " + classification + " but rated HIGH risk — overridden to LOW since " + classification + " marks are registrable.]"
            elif classification in ("suggestive",) and risk == "MEDIUM":
                risk = "LOW"  # Suggestive marks are clearly registrable
            
            description = (
                f"Mark classified as {classification} for these goods/services. "
                f"{reasoning}"
            )
        else:
            risk = "MEDIUM"
            reasoning = "LLM unavailable. Manual review recommended for descriptiveness assessment."
            confidence = 0.3
            description = reasoning

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
            has_goods_class = any(c in [5, 32] for c in classes)
            risk = "MEDIUM" if len(mark.split()) > 2 else "LOW"
            reasoning = (
                f"The multi-word mark '{mark}' may appear as a slogan on packaging rather than "
                f"a source identifier. For classes {classes}, ensure the specimen shows the mark "
                f"prominently as a trademark on product labels or packaging, not merely as "
                f"informational or decorative text. Per TMEP §904.07(a)."
            )
            confidence = 0.6

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
                f"{'Given the high confusion risk from identified prior marks, an intent-to-use strategy provides flexibility to assess and respond to Office Actions before committing specimen costs. However, the applicant should be prepared for potential §2(d) refusals during prosecution.' if has_confusion_risk else 'Standard filing basis requirements apply. No significant strategic concerns identified.'}"
            )
            confidence = 0.75
        else:
            # Deterministic fallback with more nuance
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
                f"The identification of goods/services for classes {classes} uses generally acceptable language. "
                f"Terms like 'vitamins', 'supplements', 'dietary supplements' (Class 5) and 'energy drinks', "
                f"'sports drinks' (Class 32) align with standard USPTO ID Manual entries. "
                f"Minor amendments may be needed if exact ID Manual wording differs."
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
            confidence = 0.5

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

    # ------------------------------------------------------------------
    # DETERMINISTIC PRE-FILTER (speed optimization)
    # ------------------------------------------------------------------

    def _prefilter_mark(
        self,
        mark: str,
        classes: List[int],
        prior_mark: Dict,
    ) -> str:
        """
        Deterministic pre-filter: classify a prior mark WITHOUT calling LLM.
        
        Strategy:
        - Name containment (full) → HIGH
        - 2+ shared words → LLM_NEEDED (always)
        - 1 shared word + class overlap → LLM_NEEDED
        - 1 shared word, no class overlap → MEDIUM_DETERMINISTIC (skip LLM)
        - Compound word with 2+ mark words inside → LLM_NEEDED
        - No overlap → LOW

        Returns: "HIGH", "LLM_NEEDED", "MEDIUM_SKIP", or "LOW"
        """
        pm_name = (prior_mark.get("name") or prior_mark.get("mark") or "").strip()
        pm_classes = prior_mark.get("classes") or []
        if not pm_name or len(pm_name) < 2:
            return "LOW"

        mark_lower = mark.lower()
        pm_lower = pm_name.lower()

        import string
        mark_clean = mark_lower.translate(str.maketrans("", "", string.punctuation))
        pm_clean = pm_lower.translate(str.maketrans("", "", string.punctuation))

        mark_words = set(w for w in mark_clean.split() if len(w) >= 3)
        pm_words = set(w for w in pm_clean.split() if len(w) >= 3)

        stop_words = {"the", "and", "for", "its", "than", "when", "with", "from", "into", "your", "way", "out"}
        mark_words -= stop_words
        pm_words -= stop_words

        class_overlap = bool(set(classes) & set(pm_classes)) if classes and pm_classes else False

        # --- Rule 1: Full name containment → definitely HIGH ---
        if len(pm_lower) >= 3 and (pm_lower in mark_lower or mark_lower in pm_lower):
            return "HIGH"

        # --- Rule 2: Count EXACT shared words ---
        shared_words = mark_words & pm_words
        n_shared = len(shared_words)

        if n_shared >= 2:
            # 2+ shared words (e.g., "MORE TO POUR" shares MORE + POUR) → always LLM
            return "LLM_NEEDED"

        if n_shared == 1:
            if class_overlap:
                # 1 shared word + same class → likely confusing, needs LLM
                return "LLM_NEEDED"
            else:
                # 1 shared word but different class → probably not confusing
                # e.g., "LIBERAL TEARS" (class 25) vs our mark (class 5, 32)
                # Classify as MEDIUM deterministically — saves LLM call
                return "MEDIUM_SKIP"

        # --- Rule 3: Compound word check (LIVEMORE = LIVE+MORE) ---
        for pw in pm_words:
            if len(pw) >= 6:  # Only check longer words for compound potential
                mark_word_matches = [mw for mw in mark_words if mw in pw and len(mw) >= 3]
                if len(mark_word_matches) >= 2:
                    return "LLM_NEEDED"

        # --- Rule 4: Stem similarity (TEAR/TEARS, POUR/POURS, LIVE/LIVED) ---
        for mw in mark_words:
            for pw in pm_words:
                if len(mw) >= 4 and len(pw) >= 4:
                    # Very close stems — differ by ≤ 2 chars (TEAR/TEARS, POUR/POURS)
                    if pw.startswith(mw) and len(pw) - len(mw) <= 2:
                        if class_overlap:
                            return "LLM_NEEDED"
                        return "MEDIUM_SKIP"
                    if mw.startswith(pw) and len(mw) - len(pw) <= 2:
                        if class_overlap:
                            return "LLM_NEEDED"
                        return "MEDIUM_SKIP"

        # --- Rule 5: No meaningful overlap → LOW ---
        return "LOW"

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
        Run complete trademark analysis with SMART PRE-FILTERING.

        Pipeline:
        1. DETERMINISTIC pre-filter: classify marks without LLM (~90% of work)
        2. LLM analysis: only for marks with word overlap (~10% of marks)
        3. Descriptiveness, specimens, filing, identification checks
        4. Aggregate results
        """
        print(f"\n   Starting focused analysis for: {mark}")
        print(f"   Goods: {goods_services}")
        print(f"   Classes: {classes}")
        print(f"   Total prior marks: {len(prior_marks)}")

        # ------ Step 1: Deterministic pre-filtering ------
        llm_needed = []          # Marks that need LLM analysis
        deterministic_high = []  # Already classified HIGH
        deterministic_med = []   # Classified MEDIUM without LLM (1 shared word, no class overlap)
        deterministic_low = []   # Already classified LOW

        for pm in prior_marks:
            verdict = self._prefilter_mark(mark, classes, pm)
            if verdict == "HIGH":
                deterministic_high.append(pm)
            elif verdict == "LLM_NEEDED":
                llm_needed.append(pm)
            elif verdict == "MEDIUM_SKIP":
                deterministic_med.append(pm)
            else:
                deterministic_low.append(pm)

        total = len(prior_marks)
        skipped = len(deterministic_high) + len(deterministic_med) + len(deterministic_low)
        print(f"\n   [PRE-FILTER] HIGH: {len(deterministic_high)}, LLM: {len(llm_needed)}, MEDIUM(skip): {len(deterministic_med)}, LOW: {len(deterministic_low)}")
        print(f"   [SPEED] {skipped}/{total} marks classified without LLM. Only {len(llm_needed)} LLM calls needed.")

        # ------ Step 2a: Build results for deterministic HIGH marks ------
        per_mark_results: List[MarkComparisonResult] = []

        for pm in deterministic_high:
            pm_name = pm.get("name") or pm.get("mark") or "Unknown"
            pm_goods = pm.get("goods_services") or ""
            pm_classes = pm.get("classes") or []
            pm_reg = pm.get("registration") or ""
            section_data = get_section("1207.01(d)")

            per_mark_results.append(MarkComparisonResult(
                prior_mark_name=pm_name,
                prior_mark_goods=pm_goods,
                prior_mark_classes=pm_classes,
                prior_mark_reg_number=pm_reg,
                is_similar=True,
                is_related_goods=bool(set(classes) & set(pm_classes)),
                confusion_risk="HIGH",
                reasoning=f"The applied-for mark '{mark}' contains '{pm_name}' or vice versa, creating strong likelihood of confusion per TMEP 1207.01(d).",
                key_factor="name_containment",
                tmep_section="1207.01(d)",
                citation_text=section_data["citation_text"] if section_data else "",
                confidence=0.95,
                name_contained=True,
            ))

        # ------ Step 2b: LLM analysis for ambiguous marks (in parallel) ------
        if llm_needed:
            print(f"\n   [LLM] Analyzing {len(llm_needed)} marks that share words with '{mark}'...")

            async def _analyze_mark(pm: Dict) -> MarkComparisonResult:
                return await asyncio.to_thread(
                    self.analyze_single_prior_mark,
                    mark, goods_services, classes, pm
                )

            tasks = [_analyze_mark(pm) for pm in llm_needed]
            llm_results = await asyncio.gather(*tasks)
            per_mark_results.extend(llm_results)

        # ------ Step 2c: Build results for deterministic MEDIUM marks ------
        for pm in deterministic_med:
            pm_name = pm.get("name") or pm.get("mark") or "Unknown"
            pm_goods = pm.get("goods_services") or ""
            pm_classes = pm.get("classes") or []
            pm_reg = pm.get("registration") or ""
            section_data = get_section("1207.01(b)(ii)")

            per_mark_results.append(MarkComparisonResult(
                prior_mark_name=pm_name,
                prior_mark_goods=pm_goods,
                prior_mark_classes=pm_classes,
                prior_mark_reg_number=pm_reg,
                is_similar=False,
                is_related_goods=False,
                confusion_risk="MEDIUM",
                reasoning=f"Some textual similarity between '{mark}' and '{pm_name}' (shared words), but marks are in different classes ({classes} vs {pm_classes}), reducing confusion likelihood.",
                key_factor="partial_similarity_different_class",
                tmep_section="1207.01(b)(ii)",
                citation_text=section_data["citation_text"] if section_data else "",
                confidence=0.70,
                name_contained=False,
            ))

        # ------ Step 2d: Build results for deterministic LOW marks ------
        for pm in deterministic_low:
            pm_name = pm.get("name") or pm.get("mark") or "Unknown"
            pm_goods = pm.get("goods_services") or ""
            pm_classes = pm.get("classes") or []
            pm_reg = pm.get("registration") or ""
            section_data = get_section("1207.01(b)(i)")

            per_mark_results.append(MarkComparisonResult(
                prior_mark_name=pm_name,
                prior_mark_goods=pm_goods,
                prior_mark_classes=pm_classes,
                prior_mark_reg_number=pm_reg,
                is_similar=False,
                is_related_goods=False,
                confusion_risk="LOW",
                reasoning=f"No significant word overlap between '{mark}' and '{pm_name}'. Different marks in sound, appearance, and meaning.",
                key_factor="no_word_overlap",
                tmep_section="1207.01(b)(i)",
                citation_text=section_data["citation_text"] if section_data else "",
                confidence=0.85,
                name_contained=False,
            ))

        # Count results
        high_risk = [r for r in per_mark_results if r.confusion_risk == "HIGH"]
        med_risk = [r for r in per_mark_results if r.confusion_risk == "MEDIUM"]
        low_risk = [r for r in per_mark_results if r.confusion_risk == "LOW"]

        print(f"   [RESULTS] {len(high_risk)} HIGH, {len(med_risk)} MEDIUM, {len(low_risk)} LOW")

        # ------ Step 3: Other issues (in parallel) ------
        print(f"\n   [OTHER] Analyzing non-confusion issues...")
        has_high_risk = len(high_risk) > 0

        async def _run_other():
            desc_task = asyncio.to_thread(
                self.analyze_descriptiveness, mark, goods_services
            )
            spec_task = asyncio.to_thread(
                self.analyze_specimen_issues, mark, goods_services, classes
            )
            filing_task = asyncio.to_thread(
                self.analyze_filing_issues, mark, goods_services, "1(b)", has_high_risk
            )
            id_task = asyncio.to_thread(
                self.analyze_identification_issues, mark, goods_services, classes
            )
            return await asyncio.gather(desc_task, spec_task, filing_task, id_task)

        desc_result, spec_result, filing_result, id_result = await _run_other()
        other_issues = [desc_result, spec_result, filing_result, id_result]

        print(f"   [OTHER] Done: {len(other_issues)} issues analyzed")

        # ------ Step 4: Aggregate ------
        if high_risk:
            overall_confusion = "HIGH"
        elif med_risk:
            overall_confusion = "MEDIUM"
        else:
            overall_confusion = "LOW"

        highest_risk_mark = high_risk[0].prior_mark_name if high_risk else (
            med_risk[0].prior_mark_name if med_risk else None
        )

        # Sort results: HIGH first, then MEDIUM, then LOW
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

        print(f"\n   ANALYSIS COMPLETE!")
        print(f"   Overall confusion risk: {overall_confusion}")
        print(f"   LLM calls made: {len(llm_needed)} (out of {len(prior_marks)} marks)")
        if highest_risk_mark:
            print(f"   Highest risk: {highest_risk_mark}")

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
