# System Architecture — ThesisTrace

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
| `pipeline/models.py` | lazy HF pipeline registry, load-once cache, safe failure status | P1 |
| `pipeline/ner.py` | HF NER + merge with gazetteer → typed entities | P1 |
| `pipeline/summarize.py` | 3-bullet summary, ELI5 (DistilBART / Flan-T5) | P1 |
| `pipeline/claims.py` | claim extraction (few-shot prompt or local model) | P1 |
| `pipeline/evidence.py` | sentence retrieval (TF-IDF cosine, top-k) + NLI verdict | P1 |
| `pipeline/repro.py` | reproducibility checklist (section/keyword heuristics) | P1 |
| `pipeline/trl.py` | deterministic TRL rubric over extracted signals | P1 |
| `pipeline/report.py` | Executive Report assembly; optional Gemini rewrite | P2 |
| `pipeline/llm.py` | optional Gemini REST adapter (stdlib urllib, no SDK) | P2 |
| `pipeline/analyze.py` | orchestrator: stages, progress, timings, warnings | P1+P2 |
| `pipeline/warmup.py` | pre-download models/tokenizers into `.data/hf` | P2 |
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
    "score": 72,                            // 0-100, weighted over 12 signals
    "summary": "8 present, 2 partial, 2 missing.",
    "items": [ { "key": "dataset_available", "name": "Dataset availability",
                 "weight": 2, "status": "yes", "points": 1.0,
                 "evidence": "p.12 - “dataset is publicly available”" } ]
  },
  "trl": { "level": 5, "label": "Validated in a relevant environment",
           "evidence": [ {"signal": "working_prototype", "page": 8} ],
           "why": "..." },
  "report": { "achieved": [], "proven": [], "not_proven": [],
              "risks": [], "next_steps": [], "markdown": "# Executive Report..." },
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
| `GET /api/health` | container healthcheck + queue depth | `{"status":"ok","models_loaded":[...],"queue":{"mode":"inline","queued":0,"running":0}}` |
| `POST /api/jobs` | multipart upload (`file`), enqueues analysis | `{"job_id":"..."}` (202); `503 QUEUE_FULL` + `Retry-After` when the queue is at capacity |
| `GET /api/jobs/{id}` | poll status/result | `PaperAnalysis` (above) with `status`; queued jobs add `queue_ahead` |
| `DELETE /api/jobs/{id}` | delete the analysis and its uploaded file | `{"status":"deleted"}`; `409 JOB_ACTIVE` while running |
| `GET /api/jobs/{id}/report?format=md` | downloadable executive report | markdown |
| `GET /api/config` | feature flags to the UI | `{"gemini_enabled":false,"low_ram":false}` |

Errors: `{"status":"error","error":{"code":"UNSUPPORTED_FILE","message":"..."}}`.
Limits: PDF/TXT ≤ 30 MB; a `.pdf` must really start with `%PDF`; the queue holds at most
`THESISTRACE_JOB_MAX_QUEUE` queued + running jobs (default 20). One analysis at a time per
worker by default — honest about CO6: a laptop CPU cannot run two summarizers at once.

## 5. Frontend (React) structure

```
client/src/
├── App.jsx              upload → job polling → dashboard shell with tabs
├── api.js               fetch wrappers for the 5 endpoints above
├── styles.css           design system (no UI framework dependency)
├── components/          StatCard, VerdictPill, MarkdownLite, etc.
├── mocks/paperAnalysis.json   the SAME shape as section 3 (demo mode)
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
 ├─ api   build: Dockerfile.api    ports 8000    bind: ./.data/hf → /models/hf
 │                                  env: HF_HOME=/models/hf, GEMINI_API_KEY (optional)
 │                                  bind: ./.data → /data (uploads)
 └─ web   build: Dockerfile.web    ports 8080    nginx proxies /api → api:8000
```

- Weights persist in `./.data/hf` → downloaded once, survive restarts/rebuilds.
- Uploaded files live under `./.data/uploads` (bind-mounted to `/data`) — inside the repo.
- No host-side Python/Node installs required at all; only Docker. The entrypoint drops
to the non-root `app` user after fixing bind-mount ownership.
- `docker compose down --rmi local && rm -rf .data` removes everything the project
created except Docker's own image cache.

## 8. Async job flow (why not one long request)

PDF → NER → summary → claims → evidence takes 15–60 s on CPU. A 60 s HTTP request will
time out through nginx and feels broken. So: `POST /api/jobs` returns immediately with an
id; a worker thread runs the pipeline, updating `status`/`progress`; the UI polls. This is
also our honest CO6 story: latency is *managed* (progress feedback + queue), not hidden.

### Job queue, workers and retention

```
POST /api/jobs ──► JobStore (SQLite, WAL, durable) ◄── Worker threads / worker processes
                          ▲                                   │ claim (atomic) · heartbeat · finish
                          └──────────── Janitor ◄─────────────┘ lease recovery · upload/result TTL
```

* **Durable.** Jobs and results live in `jobs.sqlite3` under the data directory, so a restart
  loses nothing: queued jobs run after the restart, finished jobs stay downloadable.
* **Atomic claim + leases.** `claim` runs in `BEGIN IMMEDIATE`; a running job holds a lease that
  its worker extends (heartbeat). A crashed worker's job is retried (`JOB_MAX_ATTEMPTS`, default
  2) and then failed with `WORKER_LOST`. Progress/finish/fail are fenced by the lease owner, so a
  zombie worker cannot overwrite a retried job.
* **Bounded.** The queue rejects new uploads above `JOB_MAX_QUEUE` *before* reading the file
  body, and a job running longer than `JOB_TIMEOUT_SECONDS` is stopped at its next progress call.
* **Two modes.** `inline` (default): the API process runs `JOB_WORKERS` worker threads - one
  command, laptop-friendly. `external`: the API only enqueues and `python -m api.jobs.worker`
  (compose profile `scale`) runs workers and the janitor, one model set per process.
* **Retention.** A failed job loses its upload immediately; a finished job keeps its upload for
  `UPLOAD_TTL_SECONDS` (1 h; the Ask tab re-reads it) and the whole analysis for
  `RESULT_TTL_SECONDS` (24 h); at most `JOB_MAX_STORED` finished jobs are kept; unreferenced
  files in the upload folder are removed after an hour; files outside the upload folder are never
  touched. Users can also `DELETE /api/jobs/{id}` (the UI does this on "new paper").
* **Why SQLite, not Redis/Celery.** The models live inside the worker process, so the queue only
  needs to be durable and safe for a few workers on one host - no extra service to run. The
  `JobStore` interface is small enough to re-implement on Redis or Postgres if you outgrow it.
  Known limits: one host (SQLite is not for network filesystems), no per-client rate limiting yet
  (put a reverse proxy rate limit in front for a public deployment).
