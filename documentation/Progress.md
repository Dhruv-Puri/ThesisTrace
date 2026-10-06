# Progress Tracker — Paper2Reality

**Sprint length:** 4 weeks (3–4 weeks until submission)
**Roles (3 members):** P1 = NLP core · P2 = FastAPI backend + jobs · P3 = React frontend + docs/evaluation
*Adjust names/roles to your actual team size — keep the role boundaries.*

**Status legend:** `⬜` not started · `🔶` in progress · `✅` done · `⛔` blocked

---

## Phase A — NLP MVP (Week 1) → *demoable by Friday*

| # | Task | Owner | Status | Blockers / notes |
|---|------|-------|--------|------------------|
| A1 | Project scaffold: git repo, `.venv`, `requirements.txt`, folder layout | P1 | ⬜ | venv ONLY — no global installs |
| A2 | PDF text extraction (PyMuPDF): pages, sections, word counts, reading time | P1 | ⬜ | fallback: plain `.txt`/`.md` upload |
| A3 | Tokenization study: HF tokenizer vs spaCy vs regex — BPE vs WordPiece vs SentencePiece (Practical 1) | P1 | ⬜ | save comparison table for report |
| A4 | Sentence segmentation + reading stats (words, pages, sections, references count) | P1 | ⬜ | |
| A5 | TF-IDF key terms + technical-term density + complexity score | P1 | ⬜ | sklearn `TfidfVectorizer` |
| A6 | NER: HF small NER model + gazetteer for scientific terms (datasets, metrics, models) | P1 | ⬜ | see [NLP-Pipeline.md](NLP-Pipeline.md) |
| A7 | Summarization: pretrained transformer → 3-bullet summary + ELI5 mode (Practical 4) | P1 | ⬜ | DistilBART / Flan-T5 |
| A8 | `POST /api/analyze` returning `PaperAnalysis` JSON (stats + summary + entities) | P2 | ⬜ | contract in [Architecture.md](Architecture.md) |
| A9 | React shell: upload page + Paper Overview tab + Key Concepts tab | P3 | ⬜ | mock data until A8 lands |
| A10 | **GATE A demo:** upload PDF → stats + bullets + entities on screen | all | ⬜ | Fri Week 1 |

## Phase B — Evidence layer (Week 2) → *ClaimCheck works end-to-end*

| # | Task | Owner | Status | Blockers / notes |
|---|------|-------|--------|------------------|
| B1 | Claim extraction: few-shot prompted extraction of major claims (Practical 3) | P1 | ⬜ | structured JSON output |
| B2 | Sentence-level retrieval: TF-IDF + cosine similarity, top-k evidence candidates | P1 | ⬜ | recall@k measured (see [Evaluation.md](Evaluation.md)) |
| B3 | NLI verdict per claim: support / partially supported / insufficient (DistilBERT MNLI) | P1 | ⬜ | threshold tuning |
| B4 | Evidence cards: claim → passages → verdict → page citation | P2 | ⬜ | no citation, no verdict — hard rule |
| B5 | Zero-shot classification experiment: NLI model vs prompt-based labels (Practical 3) | P1 | ⬜ | |
| B6 | Prompt-vs-model comparison: prompt-based summary/claims vs fine-tuned/small model (Practical 5) | P1 | ⬜ | record for report |
| B7 | Frontend: ClaimCheck tab with 🟢/🟡/🔴 verdicts + evidence snippets | P3 | ⬜ | |
| B8 | Hand-label 50 evidence pairs as gold set (see [Evaluation.md](Evaluation.md)) | P3 | ⬜ | start early, label in batches |
| B9 | **GATE B demo:** claim on screen → verdict + cited passage | all | ⬜ | Fri Week 2 |

## Phase C — App + TRL report (Week 3)

| # | Task | Owner | Status | Blockers / notes |
|---|------|-------|--------|------------------|
| C1 | Reproducibility checklist extraction (rule/keyword-based from methods sections) | P1 | ⬜ | scoring rubric in [NLP-Pipeline.md](NLP-Pipeline.md) |
| C2 | TRL 1–9 rubric scorer: evidence-cited, deterministic first; optional Gemini wording | P1 | ⬜ | score must list its evidence |
| C3 | Optional Gemini layer (free key): ELI5, TRL justification prose, report text | P2 | ⬜ | degrade gracefully with NO key |
| C4 | Prompt hardening: document-as-untrusted-data, JSON-schema outputs (Practical 3) | P2 | ⬜ | see [Prompts-and-Grounding.md](Prompts-and-Grounding.md) |
| C5 | Async job flow: upload → job id → poll → result (long analyses don't block) | P2 | ⬜ | |
| C6 | Frontend: Reproducibility + TRL tabs, Executive Report view | P3 | ⬜ | |
| C7 | Docker: `Dockerfile.api`, `Dockerfile.web`, `docker-compose.yml` up on all machines | P2 | ⬜ | HF cache as named volume |
| C8 | **GATE C demo:** full click-through, works from `docker compose up` on a clean laptop | all | ⬜ | Fri Week 3 |

## Phase D — Evaluation, buffer, demo (Week 4)

| # | Task | Owner | Status | Blockers / notes |
|---|------|-------|--------|------------------|
| D1 | Run full metric suite: ROUGE, entity F1, claim macro-F1, entailment acc, recall@k | P1+P3 | ⬜ | [Evaluation.md](Evaluation.md) |
| D2 | Error analysis: categorize failures (extraction/retrieval/reasoning/generation) | all | ⬜ | 10 worst cases table in report |
| D3 | Tokenization & prompt design impact experiment write-up (Practical 7) | P1 | ⬜ | |
| D4 | End-to-end pipeline description for report (Practical 8) | P1 | ⬜ | |
| D5 | Concept ↔ syllabus table final check for viva (CO1–CO6 talking points) | P3 | ⬜ | [Concepts-and-Syllabus.md](Concepts-and-Syllabus.md) |
| D6 | Demo rehearsal + slide deck + report assembly | all | ⬜ | |
| D7 | **FINAL DEMO** | all | ⬜ | |

---

## Weekly standup log (copy per meeting)

```
Date:
Since last:      (what actually got done)
Next:            (max 3 items each)
Blockers:        (anything needing a decision or a download/machine)
Decisions made:  (e.g., "swap flan-t5-small → distilbart for quality")
```

## Definition of Done (per phase)

- Feature works on a **real paper** (not a toy string), on a laptop with **no GPU**.
- Every number/verdict shown in UI has a **citation or provenance** (page/sentence or "heuristic").
- Code pushed; `docker compose up` still works (Phase C onward).
- One entry added to the report/log: screenshot + metric or observation.

## Demo-day checklist

- [ ] Sample papers downloaded in advance (1 CS, 1 medical/energy — diversity sells TRL story)
- [ ] App pre-warmed: models downloaded into the `hf_cache` volume (first run downloads weights)
- [ ] Gemini key in `.env` **optional path tested with key removed** (graceful degradation)
- [ ] Backup: screenshots/video of the full flow in case of Wi-Fi failure
- [ ] Slides include: pipeline diagram, syllabus mapping table, metrics table, 10 worst errors
