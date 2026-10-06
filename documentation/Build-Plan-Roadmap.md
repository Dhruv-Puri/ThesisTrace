# Build Plan & Roadmap — Paper2Reality

**Duration:** 4 weeks (aggressive; compress by dropping stretch items, never the spine)
**Team:** 3 members — P1 NLP core · P2 backend/Docker · P3 frontend/docs/eval
**Cadence:** daily 15-min sync (or every morning), full build check every Sunday.
**Golden rule:** every Friday ends with a *running demo*, even if it's ugly.

---

## Week 1 — NLP MVP (Goal: upload → stats + summary + entities)

| Day | P1 (NLP) | P2 (backend) | P3 (frontend/eval) |
|-----|----------|--------------|--------------------|
| 1 | Repo, venv, `requirements.txt`; **run tokenizers BPE/WordPiece/SentencePiece on 1 paper** (Practical 1 table) | FastAPI skeleton, `/api/health`, PyMuPDF ingest to JSON | React+Vite scaffold, tab shell, **author `mocks/paperAnalysis.json` from the contract** |
| 2 | Stats + regex + TF-IDF key terms; complexity score | `POST /api/jobs` + job store (dict + thread) | Upload page → poll job (against mock server) |
| 3 | NER model pick (test 2 checkpoints on a paper) + gazetteer merge | Wire pipeline stages 1–3 into job runner | OverviewTab with real stats JSON |
| 4 | Summarizer (DistilBART) + ELI5 (T5); number-hallucination check | Stage timing logs; error handling | ConceptsTab entity chips by type |
| 5 | Tokenizer study write-up + polish | **GATE A support** | **GATE A demo:** PDF → stats, 3 bullets, ELI5, entities |

**Gate A:** upload a real arXiv paper, see correct stats + bullets + entities in < 45 s.
If you're behind on Day 4: ELI5 → deferred, gazetteer-only NER.

## Week 2 — Evidence layer (Goal: ClaimCheck end-to-end)

| Day | P1 | P2 | P3 |
|-----|----|----|----|
| 6 | Claim extraction heuristic + few-shot prompt (k=0/2/4 variants) | Sentence segmentation + TF-IDF cosine retrieval service | ClaimCheckTab with mock verdicts |
| 7 | NLI stage: pick model, decision thresholds v0 | Combine: claims → retrieve → verdict → evidence JSON | Render verdicts + evidence + citations |
| 8 | **Label 10 gold pairs** (rotate: everyone labels) | Endpoint returns full `claims[]` (contract §3) | Label 10 gold pairs; gold-set file format |
| 9 | Tune thresholds on gold; retrieval recall@k probe | Prompt-injection fixture PDFs + `tests/test_injection.py` | Label remaining gold pairs; polish ClaimCheck UI |
| 10 | Prompt-vs-heuristic comparison table (Practical 5) | **GATE B support** | **GATE B demo:** claim → 🟢/🟡/🔴 with cited passage |

**Gate B:** every verdict shows the exact passage + page; 🟡 includes the one-line note;
at least one intentionally unsupported claim shows 🔴 honestly.

## Week 3 — App + assessments (Goal: full click-through, containerized)

| Day | P1 | P2 | P3 |
|-----|----|----|----|
| 11 | Repro checklist heuristics + weights | Docker: `Dockerfile.api` + compose (hf_cache volume) | ReproTab table + score gauge |
| 12 | TRL rubric rules + evidence links (Stage 10) | `Dockerfile.web` + nginx proxy; `.env.example` | TRLTab ladder (1–9, current highlighted) |
| 13 | Report template (deterministic) | Async polish: progress per stage; `/api/config` | ReportTab + markdown download |
| 14 | Gemini adapter (optional path) + fallback tests | **Run compose on P1's and P3's machines** | Wire all tabs to real API; loading/error states |
| 15 | Buffer for whatever broke | **GATE C support** | **GATE C demo:** `docker compose up` on a clean laptop, full flow |

**Gate C:** a teammate who didn't code it can run the whole app from a fresh clone with
one command and complete a full analysis without assistance.

## Week 4 — Evaluation, report, demo

| Day | P1 | P2 | P3 |
|-----|----|----|----|
| 16 | `eval/run_eval.py`: ROUGE, NER F1, verdict macro-F1, recall@k | Latency/RAM measurements into CO6 table | Error analysis pass 1 (bucket every failure) |
| 17 | Tokenization + prompt-ablation experiment (Practical 7) | Fix top-2 errors from bucket A/C | Error analysis pass 2; slides draft |
| 18 | Fix thresholds; re-run eval; commit results | README + run instructions for judge | Report: syllabus mapping + pipeline sections |
| 19 | Buffer / re-run everything | Buffer | Slides + demo script (90-sec story) |
| 20 | **Rehearsal → FINAL DEMO** | same | same |

**If a week slips:** cut order from [Feasibility-Analysis.md](Feasibility-Analysis.md)
section 5. Week 4 is *protected* — evaluation and the report are graded work.

## Milestones summary

| Milestone | Date target | Evidence of done |
|-----------|-------------|------------------|
| Gate A — NLP MVP | Fri Week 1 | demo + screenshots |
| Gate B — Evidence layer | Fri Week 2 | demo + gold set started |
| Gate C — Containerized app | Fri Week 3 | `docker compose up` on 2 machines |
| Final | Week 4 | eval tables + report + slides + live demo |

## Phase gates 4–6 (FUTURE — post-submission, from `Idea.txt`)

- **Phase 4 — Reproducibility automation:** discover GitHub/dataset links → sandboxed
  execution in a separate Docker service → compare reported vs reproduced metrics.
  *Requires:* compute, sandboxing; revisit after submission.
- **Phase 5 — Advanced TRL:** multi-document evidence, external signals (patents/citations).
- **Phase 6 — Commercialization layer:** market/competitor analysis, opportunity score,
  three perspectives (researcher/engineer/business), batch API, billing tiers.
- Architecture already reserves room: `report.py` takes pluggable analyzers; future
  features add fields to `PaperAnalysis` without breaking the contract (additive JSON).
