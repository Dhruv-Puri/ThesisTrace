# Paper2Reality — Documentation Hub

> **From a research paper to evidence, readiness, and a real-world roadmap.**
> Course project for **CSR322: Natural Language Processing** (Session 2026-27, Credits 3, L:2 T:0 P:2).

Upload a research paper, patent, or technical report → Paper2Reality explains what it
does, extracts the key concepts, checks whether the paper's own claims are supported by
its own evidence, scores technology readiness (TRL 1–9) with cited evidence, and lists
what still needs to happen to turn the research into a real-world product.

**This is not a paper summarizer.** It is a research-to-commercialization intelligence
tool — and it is built as a *proper NLP pipeline* first, with the LLM layer grounded on
top (never the other way around).

**Core question the system answers:**
> "What has actually been demonstrated, how strong is the evidence, how ready is the
> technology, what could stop it from reaching the real world, and what needs to happen next?"

---

## Documentation index

| # | Document | What it answers |
|---|----------|-----------------|
| 1 | [Progress.md](Progress.md) | Where are we right now? Weekly milestones, task status, blockers, demo checklist |
| 2 | [Concepts-and-Syllabus.md](Concepts-and-Syllabus.md) | Which syllabus concept does each feature use? Full mapping to Units I–VI, CO1–CO6, and all 8 practicals |
| 3 | [Feasibility-Analysis.md](Feasibility-Analysis.md) | Can a beginner–intermediate team build this in 3–4 weeks on weak PCs? Scope cuts, risks, costs |
| 4 | [Architecture.md](Architecture.md) | System design: services, modules, data contracts, REST API, React tabs, Docker topology |
| 5 | [NLP-Pipeline.md](NLP-Pipeline.md) | Stage-by-stage pipeline spec: input/output, models, syllabus link, CPU budget, fallbacks |
| 6 | [Prompts-and-Grounding.md](Prompts-and-Grounding.md) | Prompt templates, RAG grounding, anti-hallucination and anti-prompt-injection design (CO2–CO5) |
| 7 | [Evaluation.md](Evaluation.md) | Metrics, gold-standard set, error-analysis protocol (maps to Practical 6) |
| 8 | [Build-Plan-Roadmap.md](Build-Plan-Roadmap.md) | The 4-week sprint plan with day-level tasks, roles, phase gates, future phases |
| 9 | [Setup-and-Containerization.md](Setup-and-Containerization.md) | How to run everything with Docker (zero host installs) or a local `.venv` |

## Repository map (target state)

```
paper2reality/
├── documentation/          ← you are here (all design docs)
├── api/                    FastAPI backend + NLP engine
│   ├── main.py             app entrypoint (routes)
│   ├── pipeline/           ingest → NER → summarize → claims → evidence → TRL
│   └── jobs/               background analysis jobs
├── client/                 React frontend (dashboard tabs)
│   ├── package.json
│   └── src/
├── Dockerfile.api          Container for the API + NLP engine
├── Dockerfile.web          Container for the React build (nginx)
├── docker-compose.yml      One command runs the whole system
├── requirements.txt        Python dependencies (installed ONLY inside venv/Docker)
├── .env.example            Template for optional GEMINI_API_KEY
└── .dockerignore           Keeps images small and your host clean
```

## Ground rules (team agreement)

1. **Nothing is installed on anyone's machine globally.** Python deps go in a project
   `.venv`; everything else runs in Docker. See [Setup-and-Containerization.md](Setup-and-Containerization.md).
2. **Every assessment cites evidence.** No claim, TRL score, or risk in the UI may exist
   without a page/sentence citation from the uploaded document.
3. **The classic NLP pipeline is real**, not decorative: tokenization, TF-IDF, NER, and
   retrieval run as actual models/rules — the LLM only structures and verbalizes.
4. **Syllabus fidelity:** every feature traces to a syllabus block, a course outcome, and
   (where possible) one of the 8 prescribed practicals — see
   [Concepts-and-Syllabus.md](Concepts-and-Syllabus.md).
5. **The project stays free:** local Hugging Face models by default; Google Gemini free
   tier only as an optional enhancement; ₹0 required to run the demo.

## Current status

- [x] Idea defined (see `Idea.txt`)
- [x] Feasibility analysis and build plan (this folder)
- [ ] Phase A — NLP MVP (Week 1)
- [ ] Phase B — Evidence layer (Week 2)
- [ ] Phase C — App + TRL report (Week 3)
- [ ] Phase D — Evaluation, buffer, demo (Week 4)

Track live status in [Progress.md](Progress.md).
