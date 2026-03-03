# Risk Categorization Methodology v3.0

## Overview

This document explains how the Trademark Risk Assessment System categorizes legal risks using a **3-Tier Pipeline** of ML scoring, deterministic rules, and constrained LLM reasoning. The methodology is **defensible**, **explainable**, and strictly **anti-hallucination**.

## Core Principle: 3-Tier Pipeline

```
105 marks → Tier 1 (ML scores) → Tier 2 (Rules) → 68 filtered (~65% in benchmark)
                                                  → 37 to Tier 3 (LLM) → ~35%
```

> **Note:** The exact filter ratio depends on the dataset. Marks from a curated USPTO search report tend to have higher similarity, so fewer are filtered. Random marks would see a higher filter rate.

- **Tier 1**: Computes phonetic, semantic, and visual similarity scores (combined into a weighted overall score).
- **Tier 2**: Applies deterministic rules to classify obvious HIGH, MEDIUM, and LOW marks.
- **Tier 3**: LLM analyzes only ambiguous marks — one at a time with structured output.

## Risk Levels

| Level | Score Range | Description | Attorney Action |
|-------|-----------|-------------|----------------|
| **CRITICAL** | 75-100 | Near-certain refusal | Immediate review, consider abandoning |
| **HIGH** | 60-74 | Likely refusal | Formal legal opinion needed |
| **MODERATE** | 40-59 | Possible issues | Monitor, prepare arguments |
| **LOW** | 20-39 | Minor concerns | Standard prosecution |
| **MINIMAL** | 0-19 | No significant issues | Proceed with confidence |

## Tier 1 — ML Similarity Scoring

Each prior mark receives 4 scores computed by ML models:

| Score | Algorithm | What It Measures | Range |
|-------|-----------|-----------------|-------|
| **Phonetic** | Jaro-Winkler + Soundex | How marks sound when spoken | 0-100% |
| **Semantic** | MiniLM-L6-v2 cosine similarity | Meaning and concept similarity | 0-100% |
| **Visual** | Normalized Levenshtein distance | Character-level appearance | 0-100% |

These 3 scores are combined into a **weighted overall score** (35% phonetic + 35% semantic + 30% visual) used by Tier 2 rules.

**Score Interpretation:**
- **0-30%**: Noise floor — no meaningful similarity
- **30-55%**: Moderate — ambiguous territory
- **55-75%**: High — likely confusion
- **75%+**: Very high — near-identical marks

**Component-Level Matching:**
For asymmetric marks (short vs long), the system splits the longer mark into components and checks each against the shorter one. Example: "LIVEMORE" (1 word) vs "TEAR, POUR, LIVE MORE" (3 words) — "LIVEMORE" is found as a component, scoring 99% phonetic.

## Tier 2 — Deterministic Classification Rules

### DROP_HIGH Rules (Template reasoning, no LLM)
Obvious high-risk marks classified deterministically:

| Rule | Condition | Reasoning |
|------|-----------|-----------|
| **H1** | Name contained + class overlap | Mark containment creates strong presumption of confusion (§1207.01(d)(i)) |
| **H2** | Overall score ≥ 0.75 + class overlap | Extremely high similarity across all dimensions |
| **H3** | Phonetic ≥ 0.90 + visual ≥ 0.80 | Near-identical sound and appearance |
| **H4** | Semantic ≥ 0.80 + class overlap | Strong conceptual similarity with goods overlap |

### Other Rules

| Rule | Condition | Verdict |
|------|-----------|---------|
| Name contained, no class overlap | Different markets reduce risk | DROP_MEDIUM |
| Name contained, no class overlap | Different markets reduce risk | DROP_MEDIUM |
| Overall score ≥ 0.65, no class overlap | Similar but different markets | DROP_MEDIUM |
| Moderate similarity + class overlap | Ambiguous — needs LLM | PASS_TO_TIER3 |
| Low overall score + semantic < 0.35 | Clearly different marks | DROP_LOW |

## Tier 3 — LLM Reasoning

Only ~35% of marks reach the LLM. Each is analyzed individually with:
- **Structured JSON output**: `is_similar`, `risk_level`, `reasoning`, `key_factor`, `tmep_section`
- **Focused TMEP context**: Only relevant sections injected (~200-500 tokens)
- **Sequential execution**: One mark per call with 3.5-7s delay between calls
- **Retry logic**: Exponential backoff for rate limits (5s → 10s → 20s → 40s)

## Risk Dimension Weights

The overall risk score is a weighted average of 4 dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| **Rejection Likelihood** | 40% | Probability of examiner refusal |
| **Overcoming Difficulty** | 30% | Cost/effort to overcome issues |
| **Legal Precedent** | 20% | Strength of established case law |
| **Examiner Discretion** | 10% | Role of subjective judgment |

## Issue Analysis Framework

### 1. Likelihood of Confusion (TMEP §1207) — Most Critical
All 13 DuPont factors covered:
1. Mark similarity (sight, sound, meaning, commercial impression)
2. Goods/services relatedness
3. Trade channels
4. Consumer sophistication
5. Fame of prior mark
6. Number and nature of similar marks
7. Nature and extent of actual confusion
8-13. Additional factors (survey evidence, intent, etc.)

### 2. Descriptiveness (TMEP §1209)
**Abercrombie Spectrum**: Generic → Descriptive → Suggestive → Arbitrary → Fanciful

Pre-check: **Fanciful Detection** — if mark has no recognizable English words, automatically classified as Fanciful (LOW risk), bypassing LLM.

### 3. Specimen Requirements (TMEP §904)
Checks if mark functions as source identifier vs. mere slogan/ornamentation.

### 4. Filing Basis (TMEP §806)
Evaluates ITU vs. use-in-commerce strategy and multi-class filing risks.

### 5. Identification of Goods/Services (TMEP §1402)
Validates goods description against USPTO ID Manual standards.

## Confidence Scoring

| Confidence | Meaning | Action |
|-----------|---------|--------|
| 85-100% | High certainty — deterministic rule | Trust the assessment |
| 60-84% | LLM analysis with good context | Review reasoning |
| 40-59% | Limited context or LLM uncertainty | Human review required |
| 0-39% | LLM failed or data insufficient | Manual assessment needed |

## Anti-Hallucination Validation

| Component | Source | Validation |
|-----------|--------|-----------|
| TMEP section text | Hardcoded (26 sections) | 100% verified — zero retrieval errors |
| TMEP citations | Validated against 26 known sections | Unknown citations flagged with ⚠️ |
| Risk categories | Tier 2 rules + LLM | LLM constrained to JSON schema |
| Name containment | Deterministic substring matching | No LLM involved |
| Class overlap | Deterministic set intersection | No LLM involved |
| Similarity scores | ML models (Tier 1) | No LLM involved |
| Reasoning text | LLM or template (DROP_HIGH) | Displayed for attorney review |
