# Trademark Risk Assessment — System Architecture v3.0

## Architecture Overview: 3-Tier Anti-Hallucination Pipeline

This system uses a **3-Tier Pipeline** specifically designed to prevent LLM hallucination in legal trademark assessment while minimizing API costs and maximizing throughput.

### The Problem with Traditional Approaches

| Approach | Failure Mode |
|----------|-------------|
| **Feed all 100+ marks to LLM at once** | Context overfeeding → hallucination, cross-contamination |
| **Send every mark to LLM individually** | 100+ API calls → rate limits, high cost, slow |
| **Use RAG with vector search** | Retrieval errors, irrelevant context, hallucinated citations |

### Our Solution: 3-Tier Pipeline

```
┌─────────────────────────────────────────────────────────┐
│                   PDF / Manual Input                    │
│    • Mark: "TEAR, POUR, LIVE MORE"                      │
│    • Goods: "Energy drinks, supplements"                │
│    • 105 Prior Marks from USPTO search report           │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│              Document Parser                            │
│    Extracts mark, goods, classes, prior marks           │
│    Supports: USPTO, CompuMark, TESS reports             │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│         TIER 1 — ML Similarity (Probabilistic)          │
│                                                         │
│  For each of 105 prior marks, compute:                  │
│  • Phonetic: Jaro-Winkler + Soundex (multi-word)        │
│  • Semantic: Cosine similarity (MiniLM-L6-v2)           │
│  • Visual: Normalized Levenshtein distance              │
│  • Overall score: Weighted average of above (35/35/30)  │
│  • Component matching: Asymmetric short↔long marks      │
│                                                         │
│  Output: Similarity scores for every mark               │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│        TIER 2 — Deterministic Rules Engine              │
│                                                         │
│  Apply rules based on Tier 1 scores + class overlap:    │
│                                                         │
│  DROP_HIGH (template reasoning, no LLM):                │
│  • H1: Name contained + class overlap                   │
│  • H2: Overall score ≥ 0.75 + class overlap             │
│  • H3: Phonetic ≥ 0.90 + visual ≥ 0.80                  │
│  • H4: Semantic ≥ 0.80 + class overlap                  │
│                                                         │
│  DROP_LOW: Low overall score and semantic < 0.35        │
│  DROP_MEDIUM: Moderate scores, no class overlap         │
│  PASS_TO_TIER3: Ambiguous — needs LLM judgment          │
│                                                         │
│  Benchmark result: ~65% filtered in test run            │
└─────────────────┬───────────────────────────────────────┘
                  │ (Only ~35% ambiguous marks)
                  ▼
┌─────────────────────────────────────────────────────────┐
│         TIER 3 — LLM Reasoning (Constrained)            │
│                                                         │
│  For each ambiguous mark (sequentially):                │
│  ┌─────────────────────────────────────────┐            │
│  │ Prior Mark: "POUR MORE" (Class 32)      │            │
│  │ + TMEP §1207.01(b)(i) (~200 tokens)     │            │
│  │ + Tier 1 scores as context              │            │
│  │ → Structured JSON output                │            │
│  │ → 3.5s delay before next call           │            │
│  └─────────────────────────────────────────┘            │
│                                                         │
│  Then: Descriptiveness, Specimens, Filing, ID           │
│  (4-5 additional focused calls)                         │
│                                                         │
│  Provider: Groq (Llama 3.1 8B Instant) or Gemini        │
│  Retry: Exponential backoff (5s → 10s → 20s → 40s)      │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│             Risk Aggregation & Report                   │
│  • Overall risk level with confidence                   │
│  • Per-mark breakdown (HIGH/MEDIUM/LOW)                 │
│  • 4 risk dimensions (weighted scoring)                 │
│  • Validated TMEP citations (26 known sections)         │
│  • Recommendations + cost/timeline estimates            │
└─────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Similarity Engine (`similarity_engine.py`)

Handles Tier 1 (ML) and Tier 2 (Rules) as an integrated pipeline.

**Tier 1 — ML Scoring:**

| Algorithm | What It Measures | Library |
|-----------|-----------------|---------|
| Jaro-Winkler | Phonetic similarity (character-level) | `jellyfish` |
| Soundex | Phonetic identity (pronunciation codes) | `jellyfish` |
| MiniLM-L6-v2 | Semantic similarity (meaning) | `sentence-transformers` |
| Levenshtein | Visual similarity (edit distance) | `jellyfish` |

**Component-Level Matching:**
For asymmetric marks (e.g., 1-word prior vs 3-word applied), the system splits the longer mark into components and checks each against the shorter mark. This catches cases like "LIVEMORE" (1 word) hidden inside "TEAR, POUR, LIVE MORE" (3 words).

**Tier 2 — Deterministic Rules:**

| Rule | Condition | Verdict | LLM? |
|------|-----------|---------|------|
| H1 | Name contained + class overlap | DROP_HIGH | ❌ |
| H2 | Overall score ≥ 0.75 + class overlap | DROP_HIGH | ❌ |
| H3 | Phonetic ≥ 0.90 + visual ≥ 0.80 | DROP_HIGH | ❌ |
| H4 | Semantic ≥ 0.80 + class overlap | DROP_HIGH | ❌ |
| R4-5 | Name contained or very high similarity, no class overlap | DROP_MEDIUM | ❌ |
| R7 | Moderate similarity + class overlap | PASS_TO_TIER3 | ✅ |
| R8 | Low overall score, low semantic | DROP_LOW | ❌ |

### 2. TMEP Knowledge Base (`tmep_knowledge.py`)

**26 hardcoded TMEP sections** covering all 13 DuPont factors:
- 7 sections for likelihood of confusion (§1207)
- 5 sections for descriptiveness (§1209, §1212)
- 1 section for genericness (§1301)
- 2 sections for specimens (§904)
- 2 sections for identification (§1402)
- 1 section for filing basis (§806)
- 1 section for deceptiveness (§1304)
- 1 section for ownership (§819)
- Additional sections for trade channels, consumer sophistication, fame

**Why hardcoded, not retrieved:**
- Only ~26 sections needed for comprehensive analysis
- Zero retrieval errors — exact text always available
- No embedding model, no vector DB, no FAISS
- Citation validation trivial — check against 26 known IDs

### 3. Focused Analyzer (`focused_analyzer.py`)

Orchestrates the 3-Tier pipeline and handles all LLM interactions.

| Method | Input | TMEP Context | Output |
|--------|-------|-------------|--------|
| `run_full_analysis()` | Mark + goods + all prior marks | All relevant | Complete risk report |
| `analyze_single_prior_mark()` | 1 mark + Tier 1 scores | §1207 sections | Confusion risk (structured JSON) |
| `analyze_descriptiveness()` | Mark + goods | §1209 only | Descriptive classification |
| `analyze_specimen_issues()` | Mark + classes | §904 only | Specimen compliance |
| `analyze_filing_issues()` | Filing basis | §806 only | Filing strategy advice |
| `analyze_identification_issues()` | Goods text | §1402 only | ID acceptability |

**LLM Provider Support:**
- **Groq** (primary): Llama 3.1 8B Instant via OpenAI-compatible API. 30 RPM, 3.5s delay.
- **Gemini** (fallback): Flash-Lite via REST API. 15 RPM, 5.0s delay.
- Selection based on environment variable (`GROQ_API_KEY` or `GEMINI_API_KEY`).
- Both use identical prompts, structured JSON output, and retry logic.

### 4. Document Parser (`document_parser.py`)

Parses trademark search report PDFs to extract:
- Applied-for mark, goods/services, classes
- Prior marks with registration numbers, goods, classes
- Supports USPTO, CompuMark report formats
- Handles state marks, common law marks, domain conflicts

## Anti-Hallucination Architecture (7 Layers)

| Layer | Defense | How It Works |
|-------|---------|-------------|
| 1 | **Pre-loaded Knowledge** | 26 TMEP sections hardcoded — LLM never recalls law from weights |
| 2 | **3-Tier Filtering** | Majority of marks classified without LLM — reduces hallucination surface |
| 3 | **Per-Mark Isolation** | One mark per LLM call — zero cross-contamination |
| 4 | **Structured JSON Output** | LLM fills a schema (is_similar, risk_level, reasoning) — can't ramble |
| 5 | **Fanciful Detection** | Dictionary check bypasses LLM for coined terms (e.g., ZENITHBLOOM) |
| 6 | **Citation Validation** | Regex scans LLM output for TMEP citations, warns if unknown |
| 7 | **Deterministic Scoring** | Risk scores, costs, timelines calculated by Python, not LLM |

## Risk Dimensions (Weighted Scoring)

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Rejection Likelihood | 40% | Probability of examiner refusal |
| Overcoming Difficulty | 30% | Cost and effort to overcome objections |
| Legal Precedent | 20% | Strength of established case law |
| Examiner Discretion | 10% | Role of subjective judgment |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze` | POST | Analyze trademark (manual input) |
| `/api/analyze-pdf` | POST | Upload PDF + full analysis |
| `/api/upload` | POST | Parse PDF only |
| `/api/health` | GET | System health check |

## Performance Metrics (105-mark USPTO report)

| Metric | Value |
|--------|-------|
| Tier 1+2 filtered | 68/105 (~65% in this test) |
| Deterministic HIGHs | 11 (zero API cost) |
| LLM calls needed | 37 (35%) |
| Total analysis time | ~3-5 minutes |
| TMEP sections coverage | 26 (all 13 DuPont factors) |
