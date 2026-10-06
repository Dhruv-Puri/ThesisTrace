# Feasibility Analysis — Paper2Reality

**Verdict: FEASIBLE** for a beginner-to-intermediate NLP team of 3, in 3–4 weeks, on
laptops without GPUs, at 0 INR cost — *if* the scope cuts in section 1 are respected.

---

## 1. Scope: what we build vs. what we deliberately do NOT build

The idea in `Idea.txt` has 8 dashboard tabs and 6 phases. Building all of it in 4 weeks
would fail. We keep the *spine* of the idea (paper → understanding → claims → evidence →
readiness) and cut everything that requires infrastructure we don't have.

| Feature | Decision | Why |
|---------|----------|-----|
| Paper Overview (stats, reading time, 3-bullet summary, ELI5) | **BUILD** | Classic syllabus NLP (tokenization, summarization) — fast, impressive, low risk |
| Key Concepts (NER + scientific entities) | **BUILD** | Directly syllabus (NER, information extraction); hybrid model+gazetteer is reliable |
| ClaimCheck (claims → retrieval → NLI → verdict) | **BUILD** | The core differentiator; pure syllabus tech (classification, semantic similarity, RAG) |
| Reproducibility checklist (rule-based, from text) | **BUILD (light)** | Keyword/section heuristics only — no code execution |
| TRL 1–9 with cited evidence | **BUILD (light)** | Deterministic rubric over signals we already extract; Gemini optional for prose |
| Executive Report | **BUILD (basic)** | Template fill + optional Gemini wording; no free-form agent |
| Automated experiment re-running (run GitHub code, reproduce results) | **FUTURE** | Needs sandboxed execution, containers-in-containers, hours of compute — not in 4 weeks |
| Market/Opportunity Score, competitive analysis | **FUTURE** | Requires external web data; weak syllabus fit |
| Three perspectives (Researcher/Engineer/Business) | **FUTURE / stretch** | Nice demo gimmick; only if Week 4 has slack |
| Batch analysis, teams, API, billing tiers | **FUTURE** | Product concerns, not course-project concerns |
| Machine translation | **NOT BUILT** | In syllabus as an *application example*; discussed in report only |

**MVP one-liner:** upload PDF → stats + summary + key concepts → claims with evidence and
verdicts → TRL with citations → executive report.

## 2. Team skill feasibility (beginner → intermediate)

| Assumed level | What's needed | Risk | Mitigation |
|---------------|---------------|------|------------|
| Python basics | FastAPI route + JSON | Low | Contract-first: mock JSON before models work |
| Never used Hugging Face | `pipeline()` calls are ~5 lines | Medium | Follow syllabus practicals 2/4 as written; pin models from our list |
| Never done NER/retrieval/NLI | Understanding the concepts | Medium | [NLP-Pipeline.md](NLP-Pipeline.md) explains each stage in plain language + syllabus link |
| No frontend experience | React dashboard tabs | **High** | Tabs are card layouts over one JSON; start with mock data (task A9); no router/state library beyond basics |
| No Docker experience | `docker compose up` | Low | We provide the files; one member (P2) owns them |

**Key insight:** the *frontend* is the biggest beginner risk, not the NLP. The NLP stages
are each a known recipe; the dashboard is repetitive JSON rendering. Frontend starts in
Week 1 with mocks so it never blocks the NLP work.

## 3. Hardware feasibility (weak PCs — the hard constraint)

Design rule: **everything must run CPU-only, in parallel, on 8 GB RAM.**

| Model (task) | Type | Params | Approx. RAM (weights+runtime) | CPU speed on 8GB laptop |
|--------------|------|--------|-------------------------------|-------------------------|
| `distilbert-base-uncased` NER (CoNLL) | encoder-only | 66M | ~0.5 GB | ~2–5 s / page |
| `cross-encoder/nli-deberta-v3-small` or `distilbert-base-uncased-mnli` | encoder-only | 66–86M | ~0.5 GB | ~10–30 ms / pair |
| `sshleifer/distilbart-cnn-12-6` | enc-dec | 306M | ~1.5 GB | ~5–15 s / summary |
| `google/flan-t5-small` (ELI5, fallback) | enc-dec | 80M | ~0.5 GB | ~2–8 s |
| `sentence-transformers/all-MiniLM-L6-v2` (optional semantic retrieval) | encoder | 22M | ~0.3 GB | ~50 ms / chunk |
| scikit-learn TF-IDF | classical | — | negligible | instant |
| Gemini free tier (optional prose) | API | — | 0 local | network-bound |

Rules:
- Load models **once at startup**, cache in-process; never per-request downloads.
- HF cache lives in a Docker named volume (`hf_cache`) — weights downloaded once per machine.
- If a machine is 4 GB RAM: run `flan-t5-small` + DistilBERT only (documented toggle).
- Do NOT pull `bart-large`, `t5-large`, or full LLMs locally — quality gain doesn't justify it.

## 4. External dependency feasibility

| Dependency | Cost | Constraint | Fallback |
|------------|------|------------|----------|
| Hugging Face models | Free | First download ~0.5–1.5 GB per model, needs internet once | Pre-warm volume before demo; ship with 4 core models only |
| Google Gemini API | Free tier | Rate limits (~15 RPM on free tier), key in `.env`, quota errors possible | **Entire app must work with no key** — Gemini only rewrites prose; local templates produce the same report |
| Docker Desktop / Docker Engine | Free | ~4 GB disk; Docker Desktop license free for students/small orgs | Linux classmates use engine directly; document both |
| PyPI packages | Free | Installed only inside image/venv | — |
| PDFs for demo | Free | Need 3–5 real papers (arXiv is public) | Also ship 1–2 synthetic `.txt` papers we write ourselves |

## 5. Time feasibility

4 weeks × ~10–12 focused hours/person = **~120 person-hours total**.
Estimated effort: NLP stages ~45 h · backend+jobs ~30 h · frontend ~35 h · eval/docs ~20 h.
Buffer: ~15% (kept in Week 4). Detailed day-level plan:
[Build-Plan-Roadmap.md](Build-Plan-Roadmap.md).

Slip triggers (if these happen, cut in this order): (1) drop sentiment demo →
(2) drop semantic retrieval, keep TF-IDF → (3) drop ELI5 mode → (4) TRL report becomes
template-only (no Gemini). **Never cut:** citations, claim evidence, evaluation.

## 6. Risk register

| # | Risk | L | I | Mitigation |
|---|------|---|---|------------|
| 1 | Model too big / OOM on 4–8 GB machines | M | H | Model table above; RAM toggle; test on the weakest team laptop first (Day 1) |
| 2 | NLI verdicts are noisy (partial vs supported) | H | H | Tune thresholds on our 50-pair gold set; default to 🟡 when uncertain; show evidence and let user judge |
| 3 | Summaries hallucinate numbers | M | H | Summarize only abstract+conclusion; strip generated numbers not present in source (rule check) |
| 4 | PDF extraction garbage (2-column, scanned) | M | M | Test on real arXiv PDFs early; fallback to `.txt` upload; OCR explicitly out of scope |
| 5 | Gemini free-tier rate limit during demo | M | M | Local-first outputs; key optional; never block a request on the API (timeouts → fallback) |
| 6 | Frontend takes longer than expected | H | H | Mock JSON contract on Day 1; tabs are clones of each other; no fancy state mgmt |
| 7 | Prompt injection via uploaded document | M | M | See [Prompts-and-Grounding.md](Prompts-and-Grounding.md) section 5; test suite of hostile PDFs |
| 8 | One member drops / gets busy | M | H | Contract-first work; docs are the handover; each phase demoable independently |
| 9 | First-run model download fails (no internet at venue) | L | H | Pre-warm `hf_cache` volume; demo laptop carries the volume; screenshots backup |
| 10 | Scope creep ("let's add market analysis") | H | M | Section 1 of this file is binding; new ideas go to Future Scope only |

## 7. Cost (runs at zero)

| Item | Cost |
|------|------|
| Local models (Hugging Face) | 0 |
| Gemini free tier (optional) | 0 (paid tier never required) |
| Docker, FastAPI, React, scikit-learn, spaCy | 0 |
| arXiv papers, fonts, charts (recharts) | 0 |
| **Total** | **0 INR** |

## 8. Explicit non-goals (our definition of "done")

A successful submission is: **a working, evaluated, syllabus-mapped NLP pipeline with a
web UI** — not a product. We are done when a judge can upload a paper and see cited
claims/verdicts/TRL in under a minute, and we can explain every syllabus concept we used.

Future scope (post-submission, in priority order): reproducibility automation, market
analysis, multi-document comparison, fine-tuned claim model, deployment on a server,
user accounts/billing.
