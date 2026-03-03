"""
Tier 1 & Tier 2: Probabilistic ML Similarity Engine + Deterministic Screening
===============================================================================
3-Tier Architecture:
  Tier 1 (HERE) — ML-based similarity: Phonetic (Jaro-Winkler), Semantic
                  (sentence-transformers), Visual (Levenshtein)
  Tier 2 (HERE) — Deterministic rules: decides PASS to Tier 3 or DROP
  Tier 3        — LLM
"""

import jellyfish
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SimilarityScores:
    """Tier 1 output: ML-computed similarity scores (0.0 to 1.0)."""
    phonetic: float
    semantic: float
    visual: float
    composite: float


@dataclass
class ScreeningResult:
    """Combined Tier 1 + Tier 2 output for a single prior mark."""
    # Tier 1: ML scores
    similarity_scores: SimilarityScores
    # Tier 2: Deterministic verdict
    verdict: str          # "PASS_TO_TIER3" | "DROP_HIGH" | "DROP_LOW" | "DROP_MEDIUM"
    reason: str           # Why this verdict was chosen
    risk_level: str       # "HIGH" | "MEDIUM" | "LOW" (for dropped marks)
    name_contained: bool  # Does one mark contain the other?
    class_overlap: bool   # Do the trademark classes overlap?


# ---------------------------------------------------------------------------
# Similarity Engine
# ---------------------------------------------------------------------------

class SimilarityEngine:
    """
    Tiers 1 & 2 of the 3-Tier Architecture.

    Tier 1: Uses ML models and string algorithms to compute probabilistic
            similarity scores across 3 dimensions:
            - Phonetic  (Jaro-Winkler + Soundex encoding)
            - Semantic   (sentence-transformers cosine similarity)
            - Visual     (Levenshtein distance, normalized)

    Tier 2: Deterministic rules that use the Tier 1 scores to decide:
            - DROP_HIGH:     Obviously confusing — deterministic HIGH (no LLM needed)
            - PASS_TO_TIER3: Mark is ambiguous — needs LLM analysis
            - DROP_MEDIUM:   Mark has moderate similarity but below LLM threshold
            - DROP_LOW:      Mark is clearly safe (low similarity)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SimilarityEngine, cls).__new__(cls)
            cls._instance.model = None
        return cls._instance

    def __init__(self):
        # Only initialize the model if it hasn't been loaded yet
        if self.model is None:
            logger.info("Loading sentence-transformers model ('all-MiniLM-L6-v2')...")
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("✅ Tier 1 ML model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load sentence-transformers model: {e}")
                self.model = None

    # ------------------------------------------------------------------
    # Tier 1: Probabilistic ML Similarity
    # ------------------------------------------------------------------

    def _cosine_similarity(self, a, b) -> float:
        if a is None or b is None:
            return 0.0
        norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _split_into_components(self, mark: str) -> list:
        """
        Split a mark into meaningful components for word-level comparison.
        'TEAR, POUR, LIVE MORE' → ['tear', 'pour', 'live', 'more', 'live more', 'tear pour live more']
        Includes individual words, consecutive bigrams, and the full mark.
        """
        import re
        # Remove punctuation, split on whitespace
        clean = re.sub(r'[,.\-;:!?]', ' ', mark.lower().strip())
        words = [w for w in clean.split() if len(w) >= 2]

        components = list(words)  # individual words

        # Add consecutive bigrams (e.g., "live more", "tear pour")
        for i in range(len(words) - 1):
            components.append(words[i] + " " + words[i + 1])

        # Add the full mark (no-space and with-space versions)
        full_nospace = "".join(words)
        full_withspace = " ".join(words)
        if full_nospace not in components:
            components.append(full_nospace)
        if full_withspace not in components:
            components.append(full_withspace)

        return components

    def _soundex_word_match(self, mark1: str, mark2: str) -> float:
        """
        Multi-word Soundex: compare each word's Soundex code against each
        word of the other mark. Returns the fraction of matching word pairs.
        'TEAR POUR' vs 'TEER PORE' → both word pairs match → 1.0
        """
        import re
        words1 = [w for w in re.sub(r'[,.\-;:!?]', ' ', mark1).split() if len(w) >= 2]
        words2 = [w for w in re.sub(r'[,.\-;:!?]', ' ', mark2).split() if len(w) >= 2]

        if not words1 or not words2:
            return 1.0 if jellyfish.soundex(mark1) == jellyfish.soundex(mark2) else 0.0

        # Count how many words in mark2 have a Soundex match in mark1
        codes1 = [jellyfish.soundex(w) for w in words1]
        codes2 = [jellyfish.soundex(w) for w in words2]

        matches = 0
        used = set()
        for c2 in codes2:
            for i, c1 in enumerate(codes1):
                if c1 == c2 and i not in used:
                    matches += 1
                    used.add(i)
                    break

        # Fraction of the shorter mark's words that matched
        return matches / min(len(words1), len(words2))

    def run_tier1(self, mark1: str, mark2: str) -> SimilarityScores:
        """
        TIER 1: Compute probabilistic similarity scores using ML models.

        Phonetic: Jaro-Winkler + multi-word Soundex encoding
        Semantic: sentence-transformers cosine similarity
        Visual:   Levenshtein distance (normalized)

        For asymmetric marks (3+ word vs 1-2 word), also does component-level
        matching to catch hidden substrings (e.g., "LIVEMORE" in "TEAR POUR LIVE MORE").

        Returns SimilarityScores with phonetic, semantic, visual, and composite.
        All scores are between 0.0 (completely different) and 1.0 (identical).
        """
        if not mark1 or not mark2:
            return SimilarityScores(phonetic=0.0, semantic=0.0, visual=0.0, composite=0.0)

        m1 = str(mark1).lower().strip()
        m2 = str(mark2).lower().strip()

        # 1. Phonetic (Jaro-Winkler + multi-word Soundex)
        jw_score = jellyfish.jaro_winkler_similarity(m1, m2)
        sx_score = self._soundex_word_match(m1, m2)
        phonetic_score = (jw_score * 0.6) + (sx_score * 0.4)
        if sx_score >= 1.0:
            phonetic_score = max(phonetic_score, 0.85)

        # 2. Semantic (Sentence Transformers — all-MiniLM-L6-v2)
        semantic_score = 0.0
        if self.model:
            try:
                emb1 = self.model.encode(m1)
                emb2 = self.model.encode(m2)
                semantic_score = self._cosine_similarity(emb1, emb2)
            except Exception as e:
                logger.error(f"Error calculating semantic similarity: {e}")

        # 3. Visual (Levenshtein distance, normalized to 0-1)
        max_len = max(len(m1), len(m2))
        if max_len == 0:
            visual_score = 1.0
        else:
            lev_dist = jellyfish.levenshtein_distance(m1, m2)
            visual_score = 1.0 - (lev_dist / max_len)

        # ── Component-level matching for asymmetric marks ──
        # Only when one mark has 3+ words and the other has 1-2 words.
        # Catches "LIVEMORE" hidden inside "TEAR, POUR, LIVE MORE".
        import re
        words1 = [w for w in re.sub(r'[,.\-;:!?]', ' ', m1).split() if len(w) >= 2]
        words2 = [w for w in re.sub(r'[,.\-;:!?]', ' ', m2).split() if len(w) >= 2]
        long_words = max(len(words1), len(words2))
        short_words = min(len(words1), len(words2))

        if long_words >= 3 and short_words <= 2:
            long_mark = m1 if len(words1) > len(words2) else m2
            short_mark = m2 if len(words1) > len(words2) else m1
            long_components = self._split_into_components(long_mark)

            for comp in long_components:
                if len(comp) < 3 or comp == long_mark:
                    continue

                # Component phonetic
                cjw = jellyfish.jaro_winkler_similarity(comp, short_mark)
                csx = 1.0 if jellyfish.soundex(comp) == jellyfish.soundex(short_mark) else 0.0
                cp = (cjw * 0.6) + (csx * 0.4)
                if csx == 1.0:
                    cp = max(cp, 0.85)
                phonetic_score = max(phonetic_score, cp)

                # Component visual
                cmax = max(len(comp), len(short_mark))
                if cmax > 0:
                    cv = 1.0 - (jellyfish.levenshtein_distance(comp, short_mark) / cmax)
                    visual_score = max(visual_score, cv)

                # Component semantic
                if self.model and len(comp) >= 3:
                    try:
                        ce1 = self.model.encode(comp)
                        ce2 = self.model.encode(short_mark)
                        cs = self._cosine_similarity(ce1, ce2)
                        semantic_score = max(semantic_score, cs)
                    except:
                        pass

        # Composite Score (Weighted Average)
        composite_score = (phonetic_score * 0.4) + (semantic_score * 0.35) + (visual_score * 0.25)

        return SimilarityScores(
            phonetic=max(0.0, min(1.0, phonetic_score)),
            semantic=max(0.0, min(1.0, semantic_score)),
            visual=max(0.0, min(1.0, visual_score)),
            composite=max(0.0, min(1.0, composite_score)),
        )

    # ------------------------------------------------------------------
    # Tier 2: Deterministic Screening
    # ------------------------------------------------------------------

    def run_tier2(
        self,
        scores: SimilarityScores,
        class_overlap: bool,
        name_contained: bool = False,
    ) -> tuple:
        """
        TIER 2: Deterministic rules to decide if a mark needs LLM analysis.

        STRICT legal-grade screening. Rules are applied in priority order:
        1. DROP_HIGH: Obviously confusing — classify HIGH without LLM
        2. PASS_TO_TIER3: Ambiguous — needs LLM for nuanced DuPont analysis
        3. DROP_MEDIUM/LOW: Not risky enough for LLM

        Returns: (verdict, reason, risk_level)
        """
        ps = scores.phonetic
        ss = scores.semantic
        vs = scores.visual
        comp = scores.composite

        # ===== DROP_HIGH: Obvious HIGH risk — deterministic, no LLM needed =====
        # These cases are so clearly confusing that LLM reasoning is unnecessary.
        # The system generates template reasoning using the ML scores.

        # Rule H1: Name contained + class overlap = near-certain confusion
        if name_contained and class_overlap:
            return ("DROP_HIGH", "name_contained_class_overlap", "HIGH")

        # Rule H2: Very high composite + class overlap = dominant similarity
        if comp > 0.75 and class_overlap:
            return ("DROP_HIGH", "very_high_composite_class_overlap", "HIGH")

        # Rule H3: Near-identical phonetic score (sounds almost the same)
        if ps > 0.90:
            return ("DROP_HIGH", "near_identical_phonetic", "HIGH")

        # Rule H4: Near-identical visual score + class overlap
        if vs > 0.90 and class_overlap:
            return ("DROP_HIGH", "near_identical_visual_class_overlap", "HIGH")

        # ===== PASS_TO_TIER3: Ambiguous — needs LLM for DuPont analysis =====

        # Rule 1: Name Containment without class overlap — still risky
        if name_contained:
            return ("PASS_TO_TIER3", "name_contained", "HIGH")

        # Rule 2: High Semantic Similarity (meanings are close)
        if ss > 0.70:
            return ("PASS_TO_TIER3", "high_semantic_similarity", "HIGH")

        # Rule 3: High Phonetic Similarity (sounds alike)
        if ps > 0.80:
            return ("PASS_TO_TIER3", "high_phonetic_similarity", "HIGH")

        # Rule 4: High Visual Similarity + Class Overlap
        if vs > 0.80 and class_overlap:
            return ("PASS_TO_TIER3", "visual_similarity_class_overlap", "HIGH")

        # Rule 5: High composite + Same Class = likely confusing
        if class_overlap and comp > 0.55:
            return ("PASS_TO_TIER3", "class_overlap_high_composite", "HIGH")

        # Rule 6: Extremely high composite even without class overlap (Dilution)
        if comp > 0.80:
            return ("PASS_TO_TIER3", "dilution_risk", "HIGH")

        # Rule 7: Any moderate signal + class overlap = escalate
        if class_overlap and (ps > 0.65 or ss > 0.50 or vs > 0.65):
            return ("PASS_TO_TIER3", "moderate_signal_class_overlap", "HIGH")

        # ===== DROP: Low/Medium — deterministic, no LLM needed =====

        # Rule 8: Medium-range similarity
        if comp >= 0.30 or ss >= 0.30:
            return ("DROP_MEDIUM", "medium_similarity_deterministic", "MEDIUM")

        # Rule 9: Low similarity = safe drop
        return ("DROP_LOW", "low_similarity", "LOW")

    # ------------------------------------------------------------------
    # Combined: Run Tier 1 + Tier 2
    # ------------------------------------------------------------------

    def run_full_screening(
        self,
        mark: str,
        prior_mark_name: str,
        classes: list,
        pm_classes: list,
    ) -> ScreeningResult:
        """
        Run the complete Tier 1 + Tier 2 pipeline for a single prior mark.

        This is the main entry point called by the orchestrator (FocusedAnalyzer).
        Returns a ScreeningResult with ML scores and the deterministic verdict.
        """
        # Compute name containment
        mark_norm = mark.lower().strip().replace(" ", "")
        pm_norm = prior_mark_name.lower().strip().replace(" ", "")
        name_contained = bool(
            pm_norm and len(pm_norm) >= 2
            and (pm_norm in mark_norm or mark_norm in pm_norm)
        )

        # Compute class overlap
        class_overlap = bool(
            set(classes) & set(pm_classes)
        ) if classes and pm_classes else False

        # Tier 1: ML Similarity
        scores = self.run_tier1(mark, prior_mark_name)

        # Tier 2: Deterministic Screening
        verdict, reason, risk_level = self.run_tier2(scores, class_overlap, name_contained)

        return ScreeningResult(
            similarity_scores=scores,
            verdict=verdict,
            reason=reason,
            risk_level=risk_level,
            name_contained=name_contained,
            class_overlap=class_overlap,
        )

    # ------------------------------------------------------------------
    # Legacy compatibility (keep evaluate_similarities for tests)
    # ------------------------------------------------------------------

    def evaluate_similarities(self, mark1: str, mark2: str) -> dict:
        """Legacy wrapper — returns dict format for backward compatibility."""
        scores = self.run_tier1(mark1, mark2)
        return {
            "phonetic": scores.phonetic,
            "semantic": scores.semantic,
            "visual": scores.visual,
            "composite": scores.composite,
        }


# Global instance for easy access
engine = SimilarityEngine()
