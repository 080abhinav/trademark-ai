# AI Trademark Risk Assessment System v3.0

> **3-Tier Anti-Hallucination Architecture** — ML similarity scoring, deterministic rules, and constrained LLM reasoning work together to provide reliable, source-verified trademark risk analysis.

## Why This Architecture?

Legal tools cannot tolerate AI hallucinations. Most AI tools feed hundreds of prior trademarks into an LLM at once, causing "context overfeeding" and severe hallucinations where the AI mixes up facts or invents legal rules.

This system solves this with a **3-Tier Pipeline**:

```
Tier 1 (ML)  →  Tier 2 (Rules)  →  Tier 3 (LLM)
  Phonetic        DROP_HIGH          Structured
  Semantic        DROP_LOW           JSON output
  Visual          DROP_MEDIUM        TMEP-grounded
                  Class Overlap      Per-mark isolation
```

- **Majority of marks** are classified without any LLM call (Tiers 1+2) 
- The remaining marks get individual, focused LLM analysis with strict prompt constraints.
- All 13 DuPont factors are covered with 26 hardcoded TMEP sections.

## Architecture Evolution

| Version | Architecture | Issue |
|---------|-------------|-------|
| **v1.0** | RAG (FAISS + LLM) | Context overfeeding, hallucinated citations |
| **v2.0** | Per-mark focused analysis | All marks hit LLM — rate limits, high cost |
| **v3.0** | 3-Tier Pipeline (ML → Rules → LLM) | ✅ Majority filtered without LLM, DROP_HIGH for obvious cases |

## Screenshots

  <img src="docs/images/img1.png" alt="Dashboard Overview"><br>
  <img src="docs/images/img2.png" alt="Per-Mark Analysis"><br>
  <img src="docs/images/img3.png" alt="Risk Dimensions Breakdown"><br>
  <img src="docs/images/img4.png" alt="Detailed Issue Findings">

## Setup Instructions

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **Groq API Key** (free at [console.groq.com](https://console.groq.com)) — or **Gemini API Key** (free at [aistudio.google.com](https://aistudio.google.com/apikey))

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/080abhinav/trademark-ai.git
cd trademark-ai
```

---

### Step 2: Set up the Python Backend
```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# Install required packages
pip install fastapi uvicorn requests python-multipart PyPDF2 numpy jellyfish

# Set your LLM API key (choose one):
# Option A — Groq (recommended, higher free tier limits):
set GROQ_API_KEY=your_groq_key_here
# Option B — Gemini:
set GEMINI_API_KEY=your_gemini_key_here

# Start the API server
python main.py
```
*The backend runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.*

---

### Step 3: Set up the React Frontend
```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```
*Visit `http://localhost:5173` — dark mode UI with bluish theme.*

---

### Step 4: Run Automated Tests
```bash
cd backend
python test_system.py
```
*Validates all 3 tiers, DuPont factors, citation validation, and anti-hallucination logic.*

## Usage

### Option 1: PDF Upload (Recommended)
Upload a USPTO/CompuMark trademark search report (PDF). The system parses the document, extracts up to 155 prior marks, and analyzes each one through the 3-tier pipeline.

### Option 2: Manual Input
Enter trademark name, goods/services, classes, and known prior marks.
Format: `NAME, REGISTRATION, CLASS` (one per line).

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Backend | Python + FastAPI | REST API |
| ML Similarity | Jaro-Winkler, Soundex, Levenshtein | Phonetic, visual similarity |
| Semantic Model | all-MiniLM-L6-v2 (sentence-transformers) | Semantic similarity embeddings |
| LLM (Primary) | Groq (Llama 3.1 8B Instant) | Structured reasoning for ambiguous marks |
| LLM (Fallback) | Gemini 2.0 Flash-Lite | Alternative provider |
| Frontend | React + Vite | Dark mode UI with per-mark breakdown |
| PDF Parsing | PyPDF2 | USPTO report extraction |
| Knowledge Base | 26 hardcoded TMEP sections | No vector DB needed |

## Project Structure

```
backend/
  main.py              # FastAPI server (REST API)
  focused_analyzer.py  # 3-Tier analysis orchestrator
  similarity_engine.py # Tier 1 (ML) + Tier 2 (Rules) engine
  tmep_knowledge.py    # 26 hardcoded TMEP sections (all 13 DuPont factors)
  document_parser.py   # PDF parsing (USPTO, CompuMark)
  test_system.py       # System validation tests (8 tests)

frontend/
  src/App.jsx          # React UI with per-mark breakdown
  src/index.css        # Dark mode styles

docs/
  ARCHITECTURE.md      # System architecture (3-Tier pipeline)
  methodology.md       # Risk categorization framework
  RISK_ASSESSMENT_REPORT.md  # Sample analysis report
```

## The 3-Tier Pipeline

### Tier 1 — ML Similarity (Probabilistic)
Computes 4 similarity scores for each prior mark:
- **Phonetic**: Jaro-Winkler + Soundex (multi-word aware)
- **Semantic**: Cosine similarity on MiniLM embeddings
- **Visual**: Normalized Levenshtein distance
- **Component Matching**: Asymmetric check for short marks inside longer ones

These 3 scores are combined into a weighted overall score (35/35/30) used by Tier 2 rules.

### Tier 2 — Deterministic Rules
Applies rules based on Tier 1 scores + class overlap:
- **DROP_HIGH**: Name containment + class overlap, high overall similarity + class overlap, phonetic ≥0.90 + visual ≥0.80 — template-based reasoning, no LLM needed
- **DROP_LOW**: Low overall score and semantic <0.35 — clearly different marks
- **DROP_MEDIUM**: Moderate scores without class overlap
- **PASS_TO_TIER3**: Ambiguous cases requiring LLM judgment

### Tier 3 — LLM Reasoning (Constrained)
For ambiguous marks only (~35% of total):
- One mark per API call (prevents cross-contamination)
- Structured JSON output (is_similar, risk_level, reasoning, key_factor)
- TMEP sections injected as context (not retrieved)
- Citation validation on output
- Exponential backoff retry for rate limits

## Anti-Hallucination Defenses

1. **Pre-loaded Knowledge Base**: 26 TMEP sections hardcoded — LLM never recalls law from weights
2. **Per-Mark Isolation**: One mark per LLM call — zero cross-contamination
3. **3-Tier Filtering**: Majority of marks classified without LLM involvement (up to ~65% in testing)
4. **Structured JSON Output**: LLM fills a schema, can't free-form hallucinate
5. **Fanciful Mark Detection**: Dictionary check bypasses LLM for coined terms
6. **Citation Validation**: Warns if LLM cites unknown TMEP sections
7. **Deterministic Scoring**: Risk scores calculated by Python, not LLM

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze` | POST | Analyze trademark (manual input) |
| `/api/analyze-pdf` | POST | Upload PDF + full analysis |
| `/api/upload` | POST | Parse PDF only |
| `/api/health` | GET | System health check |
