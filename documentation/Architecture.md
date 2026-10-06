# System Architecture — Paper2Reality

## 1. High-level diagram

```
                        ┌──────────────────────────────┐
                        │  USER (browser)              │
                        └──────────────┬───────────────┘
                                       │ upload PDF / view tabs
                                       ▼
                        ┌──────────────────────────────┐
                        │  web container (nginx)       │  React SPA build
                        │  static files + /api proxy   │  :8080 → :8000
                        └──────────────┬───────────────┘
                                       │ HTTP (JSON, multipart)
                                       ▼
                        ┌──────────────────────────────┐
                        │  api container (FastAPI)     │  :8000
                        │  routes · job queue · cache  │
                        └──────────────┬───────────────┘
                                       │ in-process call
                                       ▼
   ┌───────────────────────────────────────────────────────────────────┐
   │                     NLP ENGINE (api/pipeline)                     │
   │                                                                   │
   │  1 INGEST        2 CLASSICAL TIER       3 NEURAL TIER             │
   │  PyMuPDF         regex · TF-IDF         HF transformers           │
   │  pages/secs ───► POS/complexity ──────► NER · summarizer · NLI     │
   │                                                                   │
   │  4 EVIDENCE               5 ASSESSMENT              6 REPORT     │
   │  claims ► retrieval  ───► rubric scorer  ─────────► template +    │
   │           ► NLI verdict     (deterministic)          optional     │
   │                                              Gemini ▲  (free key) │
   └───────────────────────────────────────────────────────┬───────────┘
                              │ JSON result (PaperAnalysis)
                              ▼
                    FINAL REPORT: summary · evidence · TRL · risks · next steps
```

Three tiers, mirroring the syllabus arc (classical → neural → LLM):
- **Classical tier** — regex, TF-IDF, POS statistics (rule-based + statistical NLP)
- **Neural tier** — Hugging Face transformer models for NER, summarization, NLI (CO1)
- **LLM tier (optional)** — Gemini free key only rewrites *already-grounded* text (CO5);
  if the key is absent, local templates produce the same report content.

## 2. Modules and responsibilities

| Module (in `api/`) | Responsibility | Owner |
|--------------------|----------------|-------|
| `main.py` | FastAPI app, routes, CORS, static health | P2 |
| `pipeline/ingest.py` | PDF → pages, sections, raw text; `.txt` fallback | P1 |
| `pipeline/stats.py` | word count, reading time, section/reference/figure counts, complexity score | P1 |
| `pipeline/tokenizer_study.py` | BPE/WordPiece/SentencePiece comparison (Practical 1) | P1 |
| `pipeline/classical.py` | regex extractors, TF-IDF key terms, POS density, gazetteer | P1 |
| `pipeline/ner.py` | HF NER + merge with gazetteer → typed entities | P1 |
| `pipeline/summarize.py` | 3-bullet summary, ELI5 (DistilBART / Flan-T5) | P1 |
| `pipeline/claims.py` | claim extraction (few-shot prompt or local model) | P1 |
| `pipeline/evidence.py` | sentence retrieval (TF-IDF cosine, top-k) + NLI verdict | P1 |
| `pipeline/repro.py` | reproducibility checklist (section/keyword heuristics) | P1 |
| `pipeline/trl.py` | deterministic TRL rubric over extracted signals | P1 |
| `pipeline/report.py` | Executive Report assembly; optional Gemini rewrite | P2 |
| `jobs/runner.py` | background job table: status, progress, result JSON | P2 |
| `prompts/` | prompt templates (single source of truth, versioned) | P2 |
| `tests/` | pytest for pipeline units + evaluation scripts | P1+P3 |

**Design rules**
1. Pure functions: `(document, config) → result dict` — no globals, so tests are trivial.
2. Each stage records `latency_ms` → feeds the CO6 latency table.
3. Every produced verdict carries `evidence[]` (page + sentence indices). No evidence, no verdict.
4. Stages communicate only via the data contracts below — frontend and pipeline evolve independently.

## 3. Data contracts (the single source of truth)

Frontend and pipeline both code against these shapes. Mock in the client until the API
serves the real thing.

```jsonc
// PaperAnalysis — returned by GET /api/jobs/{id} (trimmed here)
{
  "job_id": "a1b2c3",
  "status": "done",                       // queued | running | done | error
  "doc": { "filename": "paper.pdf", "pages": 12, "title": "..." },
  "stats": {
    "words": 4821, "reading_minutes": 19, "sections": 7,
    "references": 34, "figures": 6, "tables": 2,
    "technical_term_density": 0.083,       // distinct technical terms / total tokens
    "complexity_score": 6.4               // 0-10 blend: term density, sent length, POS mix
  },
  "summary": {
    "bullets": ["...", "...", "..."],      // 3-bullet summary
    "eli5": "...",                         // explain-like-im-beginning mode
    "abstractive_supported": true          // numeric-hallucination rule passed
  },
  "entities": [
    { "text": "ImageNet", "type": "DATASET", "start": 1024, "end": 1032,
      "page": 3, "source": "gazetteer" },  // source: model | gazetteer
    { "text": "Dr. Rao", "type": "PER", "page": 1, "source": "model" }
  ],
  "key_concepts": { "models": [], "datasets": [], "metrics": [], "others": [] },
  "claims": [
    { "id": "c1",
      "text": "Our algorithm reduces energy consumption by 50%.",
      "claim_type": "quantitative",
      "verdict": "partially_supported",    // supported | partially_supported | insufficient
      "confidence": 0.71,
      "evidence": [
        { "page": 7, "sentence_id": 212, "text": "...consumption fell from 100 kWh to 50 kWh...",
          "relevance": 0.86, "nli": "entailment" }
      ],
      "note": "Lab-scale result; real-world conditions not demonstrated." }
  ],
  "reproducibility": {
    "score": 72,                            // 0-100
    "items": [ { "name": "dataset_available", "status": "yes", "evidence": "p.12, Sec 5.1" } ]
  },
  "trl": { "level": 5, "label": "Validated in a relevant environment",
           "evidence": [ {"signal": "working_prototype", "page": 8} ],
           "why": "..." },
  "report": { "achieved": [], "proven": [], "not_proven": [],
              "risks": [], "next_steps": [] },
  "timings": { "ingest_ms": 410, "ner_ms": 2300, "summary_ms": 8900, "...": 0 },
  "warnings": ["Gemini key absent: report text is template-based."]
}
```

Entity types: `PER ORG LOC DATASET METRIC MODEL ALGORITHM DRUG MATERIAL HARDWARE TECH`.
Verdict semantics: `supported` = NLI entailment + relevance above threshold;
`partially_supported` = strong overlap but scope mismatch; `insufficient` = nothing clears
thresholds (this last one must still explain *what was searched*).

## 4. REST API contract

| Method & path | Purpose | Returns |
|---------------|---------|---------|
| `GET /api/health` | container healthcheck | `{"status":"ok","models_loaded":["ner","nli","summarizer"]}` |
| `POST /api/jobs` | multipart upload (`file`), starts analysis | `{"job_id":"..."}` (202) |
| `GET /api/jobs/{id}` | poll status/result | `PaperAnalysis` (above) with `status` |
| `GET /api/jobs/{id}/report?format=md` | downloadable executive report | markdown |
| `GET /api/config` | feature flags to the UI | `{"gemini_enabled":false,"low_ram":false}` |

Errors: `{"status":"error","error":{"code":"UNSUPPORTED_FILE","message":"..."}}`.
Limits: PDF/TXT ≤ 30 MB; one analysis at a time per container (queue the rest) — honest
about CO6: a laptop CPU cannot run two summarizers at once.

## 5. Frontend (React) structure

```
client/src/
├── App.jsx              upload → job polling → dashboard shell with tabs
├── api.js               fetch wrappers for the 5 endpoints above
├── mocks/paperAnalysis.json   the SAME shape as section 3 (Week 1 development)
└── tabs/
    ├── OverviewTab.jsx      stats cards + 3 bullets + ELI5 toggle
    ├── ConceptsTab.jsx      entity chips grouped by type + key concepts
    ├── ClaimCheckTab.jsx    claim cards: verdict pill, evidence, citation, confidence
    ├── ReproTab.jsx         checklist table + score gauge
    ├── TRLTab.jsx           TRL 1–9 ladder with current level + cited signals
    └── ReportTab.jsx        executive report + download button
```

Tabs are dumb renderers of one JSON object — this is deliberately repetitive so any
member can clone a tab in an hour. Job flow: upload → poll `GET /api/jobs/{id}` every
1.5 s → render when `done`.

## 6. Tech stack

| Layer | Choice | Why (syllabus link) |
|-------|--------|---------------------|
| Ingest | PyMuPDF (`fitz`) | fast, pure-python, text+page numbers |
| Classical NLP | scikit-learn, regex, spaCy (small `en_core_web_sm`) | feature-based models, TF-IDF, POS, parsing |
| Neural NLP | Hugging Face `transformers` + `torch` (CPU wheel) | HF workflows unit of the syllabus |
| Orchestration | FastAPI + uvicorn | async-friendly, JSON-native |
| LLM (optional) | Google Gemini free tier via REST | prompt engineering + RAG, zero cost |
| Frontend | React + Vite, recharts | minimal dashboard SPA |
| Packaging | Docker Compose (api + web) | one-command reproducibility |
| Tests/eval | pytest + rouge-score | Practical 6 |

## 7. Docker topology (matches [Setup-and-Containerization.md](Setup-and-Containerization.md))

```
docker compose
 ├─ api   build: Dockerfile.api    ports 8000    volume: hf_cache → /models/hf
 │                                  env: HF_HOME=/models/hf, GEMINI_API_KEY (optional)
 └─ web   build: Dockerfile.web    ports 8080    nginx proxies /api → api:8000
```

- Weights persist in the named volume `hf_cache` → downloaded once, survive restarts.
- Uploaded files live under `/data/uploads` (anonymous volume) — never on the host.
- No host-side Python/Node installs required at all; only Docker.

## 8. Async job flow (why not one long request)

PDF → NER → summary → claims → evidence takes 15–60 s on CPU. A 60 s HTTP request will
time out through nginx and feels broken. So: `POST /api/jobs` returns immediately with an
id; a worker thread runs the pipeline, updating `status`/`progress`; the UI polls. This is
also our honest CO6 story: latency is *managed* (progress feedback + queue), not hidden.
