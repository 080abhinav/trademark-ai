# Trademark Risk Assessment — System Architecture

## Architecture Overview: Anti-Hallucination Design

This system uses a **Focused Analysis** architecture specifically designed to prevent LLM hallucination in legal trademark assessment.

### Design Constraint: LLM Context Overfeeding

Traditional LLM applications retrieve multiple documents per query and feed thousands of tokens to the model. For trademark analysis with ~120 prior marks, this approach fails because:
- **Overfeeding**: 120 prior marks × legal rules = severe context bloat → LLM confusion
- **Conflicting data**: Many prior marks have contradictory implications
- **Hallucinated citations**: LLMs invent legal section numbers when overloaded
- **Unreliable risk**: Mixed context produces inconsistent assessments

### Our Solution: Per-Mark Focused Analysis

```
┌─────────────────────────────────────────────────────┐
│                   PDF / Manual Input                |
│    • Mark: "TEAR, POUR, LIVE MORE"                  │
│    • Goods: "Energy drinks, supplements"            │
│    • 120 Prior Marks from CompuMark report          │
└─────────────┬───────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│              Document Parser                        │
│    Extracts mark, goods, classes, prior marks       │
└─────────────┬───────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│           Focused Analyzer (per-mark)               │
│                                                     │
│  For EACH prior mark (individually):                │
│  ┌─────────────────────────────────────────┐        │
│  │ Prior Mark #1: "POUR MORE"              │        │
│  │ + TMEP §1207.01(b)(i) (~200 tokens)     │        │
│  │ → LLM: SIMILAR=YES, RISK=HIGH           │        │
│  └─────────────────────────────────────────┘        │
│  ┌─────────────────────────────────────────┐        │
│  │ Prior Mark #2: "LIVE WELL"              │        │
│  │ + TMEP §1207.01(b)(i) (~200 tokens)     │        │
│  │ → LLM: SIMILAR=NO, RISK=LOW             │        │
│  └─────────────────────────────────────────┘        │
│  ... (each mark analyzed independently)             │
│                                                     │
│  Then: Descriptiveness (§1209), Specimens (§904),   │
│        Filing basis (§806), Identification (§1402)  │
└─────────────┬───────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│             Risk Framework                          │
│  • Aggregates per-mark results                      │
│  • 4 risk dimensions (weighted scoring)             │
│  • Deterministic overrides (name containment)       │
│  • Confidence scoring + human escalation            │
└─────────────┬───────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│          Structured Risk Report                     │
│  • Overall risk level with confidence               │
│  • Per-mark breakdown (HIGH/MEDIUM/LOW)             │
│  • Validated TMEP citations (20 known sections)     │
│  • Recommendations + cost/timeline estimates        │
└─────────────────────────────────────────────────────┘
```

## Key Components

### 1. TMEP Knowledge Base (`tmep_knowledge.py`)

**20 hardcoded critical TMEP sections** covering >95% of trademark examination issues:
- 7 sections for likelihood of confusion (§1207)
- 5 sections for descriptiveness (§1209, §1212)
- 1 section for genericness (§1301)
- 2 sections for specimens (§904)
- 2 sections for identification (§1402)
- 1 section for filing basis (§806)
- 1 section for deceptiveness (§1304)
- 1 section for ownership (§819)

Each section includes: key rules, risk guidance, exact citation text, and category mapping.

**Why hardcoded, not retrieved:**
- Only ~20 sections are needed for typical analysis
- Zero retrieval errors — the exact text is always available
- No embedding model, no vector DB, no FAISS
- Citation validation is trivial — just check against 20 known IDs

### 2. Focused Analyzer (`focused_analyzer.py`)

Per-mark analysis architecture:

| Method | Input | TMEP Context | Output |
|--------|-------|-------------|--------|
| `analyze_single_prior_mark()` | 1 mark + 1 TMEP section | ~200-500 tokens | Confusion risk for that mark |
| `analyze_descriptiveness()` | Mark + goods | §1209 only | Descriptive/suggestive class (after fanciful check) |
| `analyze_specimen_issues()` | Classes | §904 only | Specimen compliance (fanciful-aware) |
| `analyze_filing_issues()` | Basis | §806 only | Filing basis compliance (ITU context-aware) |
| `analyze_identification_issues()` | Goods text | §1402 only | ID acceptability |

**The 6-Layer Anti-Hallucination Architecture:**
1. **Pre-loaded Knowledge Base (Static)**: 20 hardcoded TMEP sections injected as context, no retrieving from LLM memory.
2. **Per-Mark Isolation**: One prior mark per LLM call prevents context overfeeding and cross-contamination.
3. **Deterministic Scoring & Overrides**: Rules like "name containment" trigger automatic EXACT MATCH logic bypassing the LLM. Risk mathematical scoring is handled by Python (`risk_framework.py`), not the LLM.
4. **Fanciful Mark Pre-Check**: Marks are scanned against 150+ common English words. If no words exist (e.g., `ZRYXQWZ`), it is deterministically classified as Fanciful (LOW risk), bypassing the LLM to prevent hallucinated meanings.
5. **Classification-Risk Consistency**: If the LLM classifies a mark as `SUGGESTIVE` but assigns it a `HIGH` risk level, the system detects the contradiction and overrides risk to `LOW`.
6. **Citation Validation Regex**: LLM reasoning text is scanned for `TMEP` or `§` citations. Any citation not in our 20 known sections is tagged with a bold warning in the UI.

### 3. Risk Framework (`risk_framework.py`)

4 weighted risk dimensions:
- **Rejection Likelihood** (40%): Probability of examiner refusal
- **Overcoming Difficulty** (25%): Cost and effort to overcome objections
- **Legal Precedent** (20%): Strength of established case law
- **Examiner Discretion** (15%): Subjective judgment factors

### 4. Document Parser (`document_parser.py`)

Parses trademark search report PDFs (CompuMark, TESS) to extract:
- Applied-for mark, goods/services, classes
- Prior marks with registration numbers, goods, classes
- State marks, common law marks, domain conflicts

## Technology Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Backend | Python + FastAPI | REST API |
| LLM | Ollama (llama3.1:8b) | Local, temperature=0 |
| Frontend | React + Vite | Per-mark breakdown UI |
| PDF Parsing | PyPDF2 | Document extraction |
| Knowledge Base | Hardcoded Python dicts | No vector DB needed |


## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze` | POST | Analyze trademark (manual input) |
| `/api/analyze-pdf` | POST | Upload PDF + full analysis |
| `/api/upload` | POST | Parse PDF only |
| `/api/health` | GET | System health check |
