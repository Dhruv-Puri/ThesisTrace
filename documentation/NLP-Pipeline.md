# NLP Pipeline Specification — Paper2Reality

Stage-by-stage: what goes in, what comes out, which model, which syllabus concept, how
long on a CPU laptop, and what to do if it fails. Read alongside
[Concepts-and-Syllabus.md](Concepts-and-Syllabus.md).

```
PDF → 1 INGEST → 2 TOKENIZE → 3 CLASSICAL STATS/TF-IDF → 4 NER/GAZETTEER
    → 5 SUMMARIZE → 6 CLAIMS → 7 RETRIEVE → 8 NLI VERDICT
    → 9 REPRO CHECKLIST → 10 TRL RUBRIC → 11 REPORT
```

---

## Stage 1 — Document ingest
- **In:** uploaded PDF (or `.txt` fallback)
- **Out:** `pages[] = {page_no, text, sections[]}`, title guess, references count
- **Tool:** PyMuPDF (`fitz`); per-page text keeps page numbers for citations
- **Rules:** de-hyphenate line breaks (`energy-` + newline + `consumption` → `energyconsumption`
  needs dictionary check — keep a small wordlist; else keep hyphen), normalize whitespace,
  detect section headings via regex on numbered headings (`^\d+(\.\d+)*\s+[A-Z]`)
- **Syllabus:** Introduction to NLP (pipelines, libraries); Word Level (regex)
- **Budget:** <1 s for 20 pages · **Fallback:** plain-text upload; scanned PDF → clear error

## Stage 2 — Tokenization study (also feeds everything downstream)
- **In:** page texts · **Out:** token lists per tokenizer + comparison table
- **Tool:** HF `GPT2TokenizerFast` (BPE), `BertTokenizerFast` (WordPiece),
  `T5Tokenizer` (SentencePiece) — all local files, no downloads beyond first cache fill
- **Measures:** vocab size, token count per document, tokens per technical term,
  `[UNK]` rate (SentencePiece/BPE ≈ 0 vs WordPiece splitting rare scientific terms)
- **Syllabus/Practical:** Key NLP tasks — tokenization (Intro + Word Level); **Practical 1**,
  and the tokenization half of **Practical 7**
- **Budget:** <2 s · **Fallback:** none needed (this stage is the experiment itself)

## Stage 3 — Classical tier: stats, regex, TF-IDF, POS
- **In:** tokenized document · **Out:** `stats`, `key_terms`, metrics/numbers found
- **Tooling:**
  - Reading stats: words, reading time (`words/220`), pages, sections, figures/tables
    captions (`^(Figure|Table) \d+`), references (`\[\d+\]` or numbered lines)
  - Regex extractors: percentages `(\d+(\.\d+)?)\s*%`, p-values `p\s*[<=>]\s*0?\.\d+`,
    accuracy/F1 `(\d+(\.\d+)?)` near `accuracy|F1|BLEU|ROUGE`
  - TF-IDF: `sklearn.TfidfVectorizer(stop_words='english', ngram_range=(1,2), max_features=2000)`
    → top-10 terms per section; global top terms = "key terms"
  - Technical-term density: distinct n-grams matching gazetteer/metric patterns ÷ tokens
  - POS: `en_core_web_sm` → avg sentence length, noun-phrase density → `complexity_score`
- **Syllabus:** Word Level (regex, FSA, word classes, POS), Text Classification/Classical
  context (feature-based models, TF-IDF), Syntactic Analysis (chunking via spaCy)
- **Budget:** <2 s · **Fallback:** spaCy missing → POS-based features default to neutral

## Stage 4 — NER + scientific gazetteer
- **In:** text · **Out:** typed entities with `page`, `source`
- **Model:** `dslim/bert-base-NER` is accurate but 430M params total download — preferred
  default is a DistilBERT/CoNLL-03 fine-tune (`dce/distilbert-base-uncased-finetuned-conll03`
  family) or `BertForTokenClassification` CoNLL checkpoint ≤ ~250 MB; merge duplicates
  (model finds "National Energy Lab", gazetteer confirms type `ORG`)
- **Gazetteer (rules):** curated lists + patterns for datasets (`ImageNet`, `*Bench`),
  metrics (`accuracy`, `F1`, `p-value`), models (`BERT`, `GPT-*`, `CNN`, `ResNet-*`),
  drugs/materials; type heuristics: `XNet|Corp|Lab` → ORG, `Dr\.|Prof\.` → PER
- **Merge rule:** model wins on boundaries; gazetteer wins on type for known terms;
  every entity records `source` (transparency for the report)
- **Syllabus/Practical:** NER for information extraction (Applications and Building Models);
  **Practical 2** (HF models for basic NLP tasks)
- **Budget:** 2–5 s / 5k words · **Fallback:** gazetteer-only mode (`LOW_RAM=1`)

## Stage 5 — Summarization (3-bullet + ELI5)
- **In:** abstract, intro, conclusion sections (extracted by heading detection)
- **Out:** `summary.bullets[3]`, `summary.eli5`, `abstractive_supported`
- **Model:** `sshleifer/distilbart-cnn-12-6` (306M, enc-dec, CPU ok) for bullets;
  `google/flan-t5-small` for ELI5 ("Explain like I'm a beginner" instruction-tuned)
- **Prompt/model notes:** generate 3 sentences with `num_beams=4, max_new_tokens=130`,
  then split/filter to exactly 3 bullets; ELI5 = T5 input
  `"explain like I'm a beginner: <abstract>"`
- **Grounding rule:** any number appearing in output must exist in the source text —
  check tokens; strip/regenerate bullet if violated (anti-hallucination, CO4)
- **Syllabus/Practical:** natural language generation; text summarization techniques;
  **Practical 4** (summarization pipeline with a pretrained transformer)
- **Budget:** 5–15 s · **Fallback:** `flan-t5-small` (faster, weaker) or extractive
  baseline (TF-IDF sentence ranking — doubles as the CO1 classical-vs-neural comparison)

## Stage 6 — Claim extraction
- **In:** full text (claims usually in Abstract/Results/Conclusion) · **Out:** `claims[]`
  with `text`, `claim_type` (`quantitative|qualitative|comparative`), provenance span
- **Method (two options, we build both — that's Practical 5):**
  1. **Prompt-based (primary):** few-shot prompt → strict JSON list of claims
     (template in [Prompts-and-Grounding.md](Prompts-and-Grounding.md) section 2);
     runs on Gemini when a key is present; **no key → falls back to the heuristic below** (sentence
     classifier over result markers:
     `we show|outperform|reduces|improves|significant|p <|achieves`)
  2. **Local heuristic (baseline):** rule-based result-sentence detection as above
- **Filter:** dedupe near-identical claims (TF-IDF cosine > 0.9), cap at top 8 by
  section importance (Abstract/Conclusion ranked higher)
- **Syllabus/Practical:** classification and generation; prompting (CO2/CO3);
  **Practical 3** (zero/few-shot) and **Practical 5** (prompt vs model comparison)
- **Budget:** <1 s (rules) or API latency · **Fallback:** heuristic always available

## Stage 7 — Evidence retrieval (RAG step 1)
- **In:** claim + sentence-indexed document · **Out:** top-k candidate passages
  (default k=5) with `relevance` scores and `page`
- **Method:** sentence segmentation (spaCy `sentencizer`), TF-IDF vectors over sentences
  fitted on the document, cosine similarity claim↔sentence; optional semantic rerank with
  `all-MiniLM-L6-v2` embeddings (flag `SEMANTIC=1`, +0.3 GB RAM)
- **Why this design:** works offline, free, interpretable; also classic syllabus
  (feature-based models) — the semantic model is the "modern" contrast for CO1
- **Syllabus/Practical:** feature-based models/retrieval; supports **CO5 (RAG)**; feeds QA
- **Budget:** <1 s · **Fallback:** if all scores < 0.05 → claim marked `insufficient`
  *without* NLI (score floor prevents confident nonsense)

## Stage 8 — NLI verdict (RAG step 2)
- **In:** (claim, candidate passage) pairs · **Out:** verdict + confidence + evidence list
- **Model:** `cross-encoder/nli-deberta-v3-small` (~180M, good quality) or
  `distilbert-base-uncased-mnli` (66M, weakest machines); labels entailment/neutral/contradiction
- **Decision rule:**
  - ≥1 entailment with relevance ≥ 0.35 → 🟢 `supported`
  - neutral/entailment with high overlap but scope mismatch (e.g., "up to 50%" vs "50%") →
    🟡 `partially_supported` + generated note quoting the mismatch
  - else → 🔴 `insufficient` + list of nearest passages searched (transparency)
- **Calibration:** thresholds tuned on our 50-pair gold set
  (see [Evaluation.md](Evaluation.md)); default conservative (prefer 🟡 over 🟢)
- **Syllabus/Practical:** text classification; ambiguity resolution/semantic analysis;
  **Practical 3** (NLI as zero-shot classifier) — and this stage is the heart of CO5/CO4:
  the system *checks evidence* rather than trusting the LLM
- **Budget:** 10–30 ms/pair (~0.5 s for 8 claims × 5 passages) · **Fallback:** none needed

## Stage 9 — Reproducibility checklist (light, rule-based)
- **In:** sections + gazetteer hits · **Out:** `reproducibility{score, items[]}`
- **Signals (each yes/no/partial with evidence location):** dataset availability
  (`available at|github.com|doi.org|kaggle` in Data/Availability), source code link
  (`github.com|gitlab`), model details (architecture names present), hyperparameters
  (learning rate/batch/epochs numbers present), preprocessing described, random seed
  mentioned, environment/dependencies (`requirements|conda|docker`), experimental procedure
  (steps in Methods), sample size stated, baseline described
- **Score:** weighted sum → 0–100 (weights in `api/pipeline/repro.py`, documented in report)
- **Deliberately NOT doing:** running any code (scope cut — see [Feasibility-Analysis.md](Feasibility-Analysis.md))
- **Syllabus:** experimental/procedural reading + evidence citation; supports CO4-style
  "check what's actually stated, not what's assumed"
- **Budget:** <0.5 s · **Fallback:** never fails (missing signals are just ❌)

## Stage 10 — TRL rubric (deterministic, evidence-cited)
- **In:** checklist + entities + claims verdicts + section signals · **Out:** `trl{level, why, evidence[]}`
- **Rubric (level = highest rule whose conditions all hold; every condition cites pages):**

| Level | Condition (all must hold) | Signal source |
|-------|---------------------------|---------------|
| 1 | problem stated / principle observed | abstract contains motivation |
| 2 | technology concept formulated | method described |
| 3 | proof of concept (analytical/experimental) | small experiment mentioned |
| 4 | lab validation | results vs baseline in controlled setup |
| 5 | relevant-environment validation | larger/realistic dataset, prototype language |
| 6 | relevant-environment demonstration | field/pilot/real-world test keywords |
| 7 | operational environment demo | in-the-wild deployment keywords |
| 8 | completed & qualified | certification/scale/standards keywords |
| 9 | proven in operation | deployed user/deployment keywords |

- **Honesty rule:** TRL output lists the *matched keywords/pages* as evidence; if evidence
  is thin, level is capped and stated ("max TRL 4 evidenced; claims of field testing not found")
- **Gemini's role (optional):** rewrite `why` in polished prose — never change `level`
- **Syllabus:** semantic analysis (meaning representation) + NLG for the justification;
  this stage is our differentiator, not a syllabus task per se
- **Budget:** <0.5 s (+Gemini latency if enabled) · **Fallback:** rule text is final output

## Stage 11 — Executive report
- **In:** all prior results · **Out:** markdown report (what achieved / proven / not proven /
  risks / next steps) + UI view
- **Assembly:** pure Python f-string template over the JSON (deterministic, offline);
  **optional** Gemini polish pass with the same grounded facts (system prompt in
  [Prompts-and-Grounding.md](Prompts-and-Grounding.md) section 4)
- **Grounding enforcement:** before render, every sentence of the report must contain a
  citation token (`[p.N]`) or be a heading/bullet from the template — else it's dropped
- **Syllabus:** NLG + CO5 (grounded generation) + CO6 (graceful degradation without API)
- **Budget:** <0.5 s local · **Fallback:** n/a (template is the baseline)

## End-to-end latency budget (8-core CPU laptop, 5k-word paper)

| Stage | Budget | Cumulative |
|-------|--------|------------|
| 1 Ingest | 1 s | 1 s |
| 2 Tokenizer study | 2 s (lazy: runs in background, not blocking) | 3 s |
| 3 Classical stats/TF-IDF | 2 s | 5 s |
| 4 NER + gazetteer | 3 s | 8 s |
| 5 Summarization (2 calls) | 15 s | 23 s |
| 6 Claims | 1 s | 24 s |
| 7 Retrieval | 1 s | 25 s |
| 8 NLI | 1 s | 26 s |
| 9+10 Repro + TRL | 1 s | 27 s |
| 11 Report (local) | 1 s | **≈28 s** (Gemini +3–10 s, optional) |

Target: **≤ 45 s wall time** with progress messages per stage (CO6). Log `timings` per
stage to prove it.

## Failure modes & fallbacks (summary)

| Failure | Behavior |
|---------|----------|
| Scanned/image PDF | error: "no text layer — upload .txt" (OCR out of scope) |
| Model download fails | API starts with `models_loaded: []`; NER/summary tabs show offline notice; classical stages still work |
| OOM on small machine | `LOW_RAM=1`: flan-t5-small + gazetteer-only + MNLI-distilbert |
| Gemini quota/timeout | warning banner; template report (never blocks >5 s) |
| Claim with no evidence | 🔴 insufficient with searched passages shown — never silently pass |
