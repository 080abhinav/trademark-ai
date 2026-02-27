# Risk Categorization Methodology

## Overview

This document explains how the Trademark Risk Assessment System categorizes legal risks. The methodology is designed to be **defensible**, **explainable**, and strictly **anti-hallucination**.

## Core Principle: Per-Mark Analysis

To prevent LLM context overfeeding and hallucination, our system analyzes **each prior mark individually** rather than feeding all prior marks into a single prompt. This means:

- Each confusion assessment is independent and verifiable.
- No cross-contamination of facts between different prior marks.
- The LLM receives ~200-500 tokens of highly focused legal context per analysis.
- Every citation is validated against a pre-loaded knowledge base of 20 critical TMEP sections.

## Risk Levels

| Level | Score Range | Description | Attorney Action |
|-------|-----------|-------------|----------------|
| **CRITICAL** | 75-100 | Near-certain refusal, major legal obstacles | Immediate review, consider abandoning or major modification |
| **HIGH** | 60-74 | Likely refusal, significant issues | Formal legal opinion needed, consider alternatives |
| **MODERATE** | 40-59 | Possible issues, examiner judgment involved | Monitor, prepare arguments, consider minor modifications |
| **LOW** | 20-39 | Minor concerns, generally manageable | Standard prosecution, no major concerns |
| **MINIMAL** | 0-19 | No significant issues identified | Proceed with confidence |

## Risk Categorization Criteria

### 1. Likelihood of Confusion (Most Critical)

**Deterministic Overrides (no LLM needed):**
- **CRITICAL**: Applied mark literally contains a prior mark name (e.g., "POUR" in "TEAR, POUR, LIVE MORE") — per TMEP §1207.01(d)
- **HIGH**: Name containment + class overlap — both marks in same International Class

**LLM-Assisted Assessment (per-mark):**
Each prior mark is compared against the applied-for mark using DuPont factors (TMEP §1207.01(b)):
- **Mark Similarity**: Sound, appearance, meaning, commercial impression (§1207.01(b)(i))
- **Goods Relatedness**: Same class, complementary goods, same trade channels (§1207.01(b)(ii))
- **Key Factor**: Which DuPont factor is decisive for this specific pair

**Risk Assignment:**
- **HIGH**: Marks share dominant element AND goods overlap
- **MEDIUM**: Some similarity in marks OR some relatedness in goods
- **LOW**: Marks clearly different OR goods unrelated

### 2. Descriptiveness (§1209)

**Classification Spectrum**: Generic → Descriptive → Suggestive → Arbitrary → Fanciful

**Risk Criteria:**
- **HIGH**: Mark directly describes a key feature/ingredient/quality (e.g., "POUR" for beverages)
- **MEDIUM**: Mark is in the grey zone between descriptive and suggestive
- **LOW**: Mark is clearly suggestive, arbitrary, or fanciful

### 3. Specimen Requirements (§904)

**Mostly Deterministic:**
- **LOW** for physical goods (Class 5, Class 32): product labels/packaging are standard specimens
- **MEDIUM** for digital/service marks: webpage specimens have specific requirements
- **HIGH** only if no specimen is available

### 4. Filing Basis (§806)

**Fully Deterministic:**
- §1(a) use-in-commerce: requires dates of use and specimens
- §1(b) intent-to-use: requires bona fide intent, SOU before registration

### 5. Identification of Goods/Services (§1402)

**LLM-Assisted:**
- Compared against USPTO ID Manual standards
- Risk based on clarity, specificity, and use of accepted terminology

## Risk Dimension Weights

The overall risk score is a weighted average of 4 dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Rejection Likelihood | 40% | Probability of examiner refusal |
| Overcoming Difficulty | 25% | Cost/effort to overcome issues |
| Legal Precedent | 20% | Strength of established case law |
| Examiner Discretion | 15% | Role of subjective judgment |

## Confidence Scoring

Each assessment includes a confidence score (0-100%):

| Confidence | Meaning | Action |
|-----------|---------|--------|
| 85-100% | High certainty — deterministic rule applied | Trust the assessment |
| 60-84% | Moderate certainty — LLM analysis with good context | Review reasoning |
| 40-59% | Low certainty — limited context or LLM uncertainty | Human review required |
| 0-39% | Very low — LLM failed or insufficient data | Manual assessment needed |

**Human Review Triggers:**
- Confidence < 60%
- Conflicting signals between dimensions
- Any invalid citations detected (hallucination flagged)

## Anti-Hallucination Methodology

### What We Validate vs. What We Accept from LLMs

| Component | Source | Validation |
|-----------|--------|-----------|
| TMEP section text | Hardcoded (20 sections) | 100% verified — no retrieval errors |
| TMEP citations | Validated against known 20 sections | Rejected if not in our knowledge base |
| Risk categories | Deterministic rules + LLM | LLM output parsed and constrained |
| Name containment | Deterministic string matching | No LLM involved |
| Class overlap | Deterministic set intersection | No LLM involved |
| Similarity assessment | LLM (structured output) | Constrained to YES/NO format |
| Reasoning text | LLM | Displayed as-is for attorney review |

### The 6 Layers of Anti-Hallucination Defense

This system is built to minimize LLM hallucinations through a strict "defense-in-depth" architecture:

1. **Pre-loaded Knowledge Base (Static)**: The LLM is never asked to recall law from its weights. 20 highly relevant TMEP sections are hardcoded into the system and injected directly into the prompt.
2. **Per-Mark Isolation**: Prior marks are analyzed individually (one per LLM call) rather than collectively. This strictly prevents cross-contamination and "overfeeding" the context window.
3. **Deterministic Scoring & Overrides**: The LLM only generates reasoning text. Risk scores and timelines are calculated by deterministic Python code (`risk_framework.py`). Critical risks (like exact name matches) and Fanciful marks (no English words) trigger deterministic overrides that bypass LLM judgment entirely.
4. **Fanciful Mark Detection**: A pre-check scans marks against a dictionary of 150+ common English words. Marks with no recognizable words are automatically classified as Fanciful (LOW risk), entirely preventing the LLM from hallucinating meaningless vitality/energy concepts for random strings. 
5. **Classification-Risk Consistency Checks**: The system parses the LLM's structured output and checks for logical contradictions. If the LLM classifies a mark as `SUGGESTIVE` but assigns a `HIGH` risk, the system overrides the risk to `LOW` and lowers confidence to flag it for human review.
6. **Citation Validation Regex**: Before reasoning text is displayed, an automated regex scanner identifies any TMEP sections the LLM cited (e.g., `§ 1209.04(b)`). It checks these against the known 20 sections. Any hallucinated sections append an automated `[⚠️ WARNING]` to the reasoning text.

## How an Attorney Verifies the Assessment

1. **Per-mark breakdown**: Each prior mark shown with individual risk assessment
2. **Exact TMEP text**: Citation text shown for each finding — attorney can verify
3. **Confidence scores**: Low-confidence assessments flagged for human review
4. **Expandable reasoning**: Click any prior mark to see full LLM reasoning
5. **Deterministic flags**: "NAME CONTAINED" badge shows when string matching applies
