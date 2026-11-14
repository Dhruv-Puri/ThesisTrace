# ThesisTrace — Overview

> **PaperLens tells you what the literature says. ThesisTrace tells you whether to build on it.**

This document is for someone who has never seen the project, has never studied NLP, and
has a few minutes — or at most a few hours — to understand what it does, how it works,
why it is different, and whether it is useful.

You do not need to read the code to follow sections 1–9. Section 10 is a short study
path if you want to understand the machinery properly.

---

## 0. The 60-second version

ThesisTrace takes **one research paper** and turns it into a **readiness decision**.

You upload a PDF or text file. In seconds (or up to a minute with the optional local
models), you get:

- the paper's main claims, each marked **supported**, **partially supported**, or
  **unverified**, always with a page number;
- a **reproducibility score** built from twelve things a reader would need to rebuild it;
- a **Technology Readiness Level (TRL 1–9)** based on what the paper says about its own
  evidence;
- an **executive report** you can attach to a review or a funding conversation;
- a **Trust Ledger receipt** behind every verdict, showing the retrieval score, the NLI
  probabilities, the thresholds, the model, and the pipeline version;
- optionally, a **portfolio** that compares two to five papers on readiness and flags
  the same claim when two papers disagree.

The important sentence is not "AI reads papers". It is:

> **Every verdict is a recorded decision, not a paragraph of prose.**

The app runs locally. No API key is required. If an optional Gemini key is present, it can
help extract claims or polish two report sections, but it **never assigns a verdict**.

---

## 1. The problem, in plain words

Imagine a paper with this sentence in the abstract:

> "Our method reduces inference latency by 42% compared with a dense Transformer."

A summarising tool will repeat that sentence. A citation tool will let you cite it. A chat
assistant will explain it. None of them answer the questions a builder actually has:

1. **Is the claim supported by the paper's own evidence?** Was 42% measured on the same
   model, the same data, and a comparable setting? Or is it a single favourable run?
2. **Can another team rebuild the result?** Is the code released? Is the dataset public?
   Are the seed, split, hyperparameters, and evaluation procedure reported?
3. **How close is it to real use?** Was it tested in a lab, in a relevant environment, in
   the field, or in production?

A summary optimises for **breadth**: many papers, many ideas, fluent prose. ThesisTrace
optimises for **depth on one paper**: evidence, reproducibility, readiness, and a receipt.

That is the whole positioning:

> **PaperLens tells you what the literature says. ThesisTrace tells you whether to build
> on it.**

---

## 2. Who it is for — and who it is not for

**It is for:**

- a thesis writer deciding whether a paper is worth building on;
- a supervisor or lab lead checking a student's or a collaborator's claim;
- a technology-transfer office screening a disclosure;
- an R&D scout or deep-tech investor doing first-pass diligence;
- a founder deciding whether a paper is a real product ingredient.

**It is not for:**

- writing a literature review;
- finding papers (use a search engine or a literature database);
- asking free-form questions across a large corpus;
- detecting fraud or proving a paper wrong;
- replacing peer review or a domain expert.

The product is deliberately narrow. Breadth is someone else's job.

---

## 3. What you actually get

There are three screens: **Start**, **Analysis**, and **Portfolio**. Analysis has four
tabs.

| Tab | The question it answers | What it shows | In the sample paper |
|---|---|---|---|
| **Summary** | What does this paper say? | Three bullets, a plain-English explanation, key concepts, a coverage radar, and three gauges (claims, TRL, reproducibility) | 4,812 words, 7 sections, 22 min read; 2 of 6 claims supported; TRL 4/9; 63/100 |
| **Claims** | Which statements survive their own evidence? | Claim text, verdict, page, optional note, and a "Why this verdict?" receipt | Latency claim supported; energy claim partial; production claim unverified |
| **Readiness** | How close is it to real use, and what is missing? | TRL gauge and ladder, twelve reproducibility signals, and the gaps blocking the next level | TRL 4: lab-validated; 5 signals present, 3 partial, 4 missing |
| **Report** | What do I send to someone else? | A decision brief plus a Markdown report with cited sections and next steps | "Lab-validated — pilot next" plus a five-section report |
| **Portfolio** | Which of these papers is worth building on? | A readiness table and a shared-claim ledger for 2–5 papers | SparseRoute vs EfficientFormer: one claim conflicts |

The app never hides the evidence behind a single score. The score is a shortcut into the
evidence, not a replacement for it.

### The bonus feature: same paper, three decisions

Most research tools produce one answer for one kind of reader. ThesisTrace lets the same
analysis be read through three lenses:

- **Researcher** — which claims survived, which are still open, and what question to ask next.
- **Engineer** — how much of the paper is documented for rebuild, what is missing, and what
  blocks the next readiness level.
- **Business** — the readiness call, the evidence count, and the next milestone to fund.

The switch is not a cosmetic filter. Each view is generated from the same structured
claims, reproducibility checklist and TRL result; it changes the emphasis, not the facts.
That is the idea-file "killer feature": one paper, three stakeholders, no contradictory
stories.

---

## 4. The full workflow: what happens after you drop a PDF

This is the part most overviews skip. Here is the actual path through the code, in order,
with the technology named and the running example kept visible.

The sample used throughout is a nine-page paper called **SparseRoute: Adaptive Sparsity
for Efficient Neural Machine Translation**. It reports a 42% latency reduction on WMT14
English–German, a small BLEU change, and a 57% energy reduction on one GPU. It is the
demo fixture in the app, and its numbers are used in the examples below.

### The cast of technologies

| Layer | Technology | What it does here |
|---|---|---|
| PDF reading | **PyMuPDF** | Extracts text page by page while keeping page numbers |
| Text cleanup | **Regular expressions** | Removes running headers, footers, page numbers; finds section headings |
| Classical NLP | **TF-IDF + cosine similarity** | Ranks sentences as candidate evidence for a claim |
| NER and concepts | **spaCy small model + gazetteer** | Finds datasets, models, metrics, people and organisations |
| Claim judging | **Cross-encoder NLI** (`cross-encoder/nli-deberta-v3-small`) | Scores entailment, neutral and contradiction for a claim–passage pair |
| Summaries | **DistilBART / FLAN-T5 if installed; extractive fallback otherwise** | Produces three bullets and a plain-English explanation |
| Orchestration | **FastAPI** | Receives uploads, exposes job status, report and audit endpoints |
| Durability | **SQLite queue** | Survives a restart; gives each job a lease and a worker |
| Interface | **React + Vite** | Four tabs, a receipt disclosure, a portfolio screen |
| Optional LLM | **Google Gemini, only with a key** | Can propose claims or polish two report sections; never decides a verdict |

### Step 0 — The browser checks the file before uploading

**What happens.** The Start screen accepts a drag-and-drop or a file picker. Before any
network call, the browser checks the extension (`.pdf`, `.txt`, `.md`), rejects an empty
file, and rejects anything over 30 MB. It then sends the file as a multipart upload and
switches to the progress screen, polling the job every 1.5 seconds.

**Where.** `client/src/App.jsx`, `client/src/api.js`.

**Why it matters.** Bad input is rejected cheaply. The user sees progress instead of a
request that appears to hang.

---

### Step 1 — The API accepts the upload and puts it in a durable queue

**What happens.** `POST /api/jobs` checks that the queue has capacity (20 queued + running
jobs by default). It streams the upload to `.data/uploads/{job_id}.pdf` in 1 MB chunks.
If the file claims to be a PDF, the first bytes must contain `%PDF`; a renamed image is
rejected immediately. The job is written to a SQLite database, `.data/jobs.sqlite3`, with
status `queued`. The API returns `202` and a job id.

A worker claims the job with a lease. If the worker dies, the lease expires and the job is
retried; a progress update from a zombie worker cannot overwrite the retried job.

**Where.** `api/main.py`, `api/jobs/store.py`, `api/jobs/runner.py`, `api/jobs/worker.py`.

**Example.** A nine-page upload becomes a job id such as `db17212a…`; the response is
immediate, not after the analysis. The upload is deleted after one hour by the janitor;
the result is kept for 24 hours by default.

**Why it matters.** A 30–60 second analysis is too long for a normal HTTP request. A queue
also means the browser can close and come back.

---

### Step 2 — Text extraction, page map, and sentence index

**What happens.** PyMuPDF reads each page's text. The cleanup pass:

- removes lines repeated on most pages (running headers and footers) and bare page numbers;
- joins hyphenated line breaks;
- detects named sections such as Abstract, Introduction, Method, Results, Conclusion,
  References, using both named headings and numbered headings;
- guesses the title from the first page, skipping licence banners and arXiv-style stamps;
- builds a sentence index where **every sentence keeps its page number and section**.

Text files are treated the same way, but split into pseudo-pages of roughly 2,800
characters so citations still work. Scanned PDFs with no text layer are rejected with a
clear "OCR is out of scope" message, not silently analysed. The first 60 pages are used.

**Where.** `api/pipeline/ingest.py`.

**Example.** The sample yields 4,812 words across 7 sections. The sentence "SparseRoute
lowered median latency from 120 ms to 70 ms per sentence" is stored with `page: 6` and
`section: Results`. That page number is what the interface shows later.

**Why it matters.** A verdict without a page is an opinion. Page numbers are preserved
from this step onward.

---

### Step 3 — Classical features, counts, and the coverage profile

**What happens.** Four transparent passes run over the cleaned document:

1. a gazetteer finds known datasets, models, metrics and organisations;
2. regex extraction pulls percentages, p-values, metric values, and artifact links;
3. TF-IDF extracts the most distinctive terms;
4. part-of-speech statistics and text counts produce words, unique words, reading time,
   sections, references, figures and tables.

The six-part **complexity profile** behind the coverage radar is computed here: term
density, sentence length, grammar mix, reference density, structure, and vocabulary
variety, each on a 0–10 scale.

**Where.** `api/pipeline/classical.py`, `api/pipeline/stats.py`.

**Example.** The sample's profile scores 8.1 for technical terms, 6.5 for sentence length,
9.7 for references. That becomes the radar shape on the Summary tab. The header says
"4,812 words · 7 sections · 34 references · 22 min".

**Why it matters.** These are cheap, deterministic features. They do not need a model, so
the app still produces a useful profile on a laptop with nothing installed.

---

### Step 4 — Tokenizer comparison (a side stage, not a decision)

**What happens.** The pipeline compares how the document splits into tokens under a
built-in whitespace/punctuation baseline and, when installed, Hugging Face tokenizers. It
also shows how technical terms split differently across tokenizers.

**Where.** `api/pipeline/tokenizer_study.py`.

**Important honesty note.** This stage is still computed and stored in the analysis JSON,
but the current four-tab interface does not show a separate tokenizer screen. It exists
for the NLP syllabus and for technical inspection. It is **not** part of the readiness
decision, and it should not be sold as a user-facing feature.

---

### Step 5 — Named entities and key concepts

**What happens.** spaCy's small English model and the gazetteer find named entities and
group them into datasets, models and methods, metrics, people, organisations, and other
concepts. Each concept keeps the pages where it appeared.

**Where.** `api/pipeline/ner.py`, `api/pipeline/gazetteer.py`.

**Example.** WMT14, English–German, Transformer, BLEU and SparseRoute are extracted. They
appear as chips under "Key concepts" and in the report appendix.

**Why it matters.** It gives a non-specialist a quick map of what the paper is made of
without reading the whole PDF.

---

### Step 6 — The three-bullet summary

**What happens.** If a local summarisation model is installed, DistilBART writes the
bullets and FLAN-T5 writes the plain-English explanation. If not, an extractive fallback
scores sentences by centrality, numbers, and early position, removes near-duplicates, and
selects three. Before any generated text is accepted, every number in it must already
exist in the source. A number that appears from nowhere is a hallucination and is removed.

**Where.** `api/pipeline/summarize.py`.

**Example.** The sample's three bullets are: the learned top-2 router; the 42% latency
reduction with BLEU held within 0.3 points; and the limitation that evidence comes from a
single-GPU lab setting. The third bullet is not decoration — it is the reason readiness is
only TRL 4.

**Why it matters.** The summary is short enough to read and honest enough to include the
limitation, not just the result.

---

### Step 7 — Claim extraction

**What happens.** The baseline is a transparent heuristic over result-like sentences. It
prefers sentences from the abstract, conclusion, results and experiments; looks for
subject–verb patterns ("we show", "the method reduces"), result verbs ("reduces",
"outperforms", "achieves"), numbers, and comparisons; penalises background and future-work
wording; removes near-duplicates with Jaccard similarity above 0.75; and keeps at most
eight claims.

If a Gemini key is configured, a few-shot prompt can propose claims instead. Every
proposed claim is then checked **verbatim** against the document. A claim that is not
literally in the paper is rejected before the user sees it.

**Where.** `api/pipeline/claims.py`.

**Example.** Six claims survive from the sample:

- latency reduced by 42% (supported);
- BLEU within 0.3 points (supported);
- energy cut "up to 60%" in data centres (partial);
- may generalise to low-resource pairs (unverified);
- routing overhead negligible above batch 16 (partial);
- ready for production across all model sizes (unverified).

**Why it matters.** Claim selection is the first place an LLM could invent something. The
verbatim check makes that failure mode visible and bounded.

---

### Step 8 — Retrieval: find the sentences that could prove the claim

**What happens.** All usable sentences are indexed with TF-IDF. For each claim, the index
returns the top five most similar sentences by cosine similarity. The claim's **own
sentence is excluded**. If it were included, the claim would "prove" itself and every
verdict would look supported.

If the best candidate scores below the retrieval floor (0.05 by default), no language
model is called at all. The verdict is `insufficient` with an explicit note: nothing
cleared the floor, so the claim is unverified, not false.

**Where.** `api/pipeline/evidence.py`, `api/pipeline/classical.py`.

**Example.** For the latency claim, the top match is the results sentence on page 6 with a
relevance score of 0.87. For the energy claim, the match is page 8: "57% on a single GPU",
not the claimed "up to 60% in data-centre deployments".

**Why it matters.** Retrieval is where most RAG systems quietly fail: they retrieve
something plausible and the model writes a confident answer. Here the retrieved scores are
stored and shown.

---

### Step 9 — NLI: judge the claim against the passage

**What happens.** A cross-encoder NLI model reads the claim and each candidate passage
together and returns three probabilities: **entailment**, **neutral**, and
**contradiction**. The model is `cross-encoder/nli-deberta-v3-small` by default.

The decision rules are explicit:

| Condition | Verdict |
|---|---|
| entailment ≥ 0.60 and relevance ≥ 0.25 | **supported** |
| entailment ≥ 0.40 and relevance ≥ 0.12 | **partially supported** |
| contradiction ≥ 0.65, greater than entailment, relevance ≥ 0.15 | **insufficient** (the paper does not support it; treat as contradicted) |
| anything else | **insufficient** (unverified, not false) |

If the NLI model is not installed, a conservative lexical-overlap fallback runs. It
requires 55% content-word overlap plus matching numbers for "supported", 28% for
"partial", and otherwise abstains. The interface always says which method was used.

**Where.** `api/pipeline/evidence.py`, `models.py`, `config.py`.

**Example.**

- Latency claim: entailment 94%, contradiction 2%, relevance 87% → **supported**, confidence 91%.
- Energy claim: the passage says 57% on one GPU, while the claim says up to 60% in data
  centres → **partially supported**. The note explains the missing number and the wider scope.
- Production claim: the paper says deployment is future work → **insufficient**. The app
  does not call it false; it says the paper does not support it.

**Why it matters.** This is the core judgement. It is deterministic given the model and
thresholds, and both are recorded.

---

### Step 10 — The Trust Ledger: write the receipt

**What happens.** Every claim gets an `audit` object containing:

- the method (`nli`, `lexical-fallback`, or `retrieval-only`);
- the retrieval engine, `k`, floor, returned count, and each candidate's page and score;
- the NLI probabilities, the best sentence id, and the margin;
- the exact thresholds used;
- the model id and the pipeline version;
- the UTC timestamp;
- the abstain reason, if any.

No document text is stored in the receipt, so it can be exported safely.

The UI exposes it under **"Why this verdict?"**; the API exposes the whole set at
`GET /api/jobs/{id}/audit`; the Markdown report appendix lists how many verdicts used each
method.

**Where.** `api/pipeline/evidence.py`, `api/main.py`, `client/src/tabs/ClaimsTab.jsx`.

**Example.** The first claim's receipt says: NLI cross-encoder, confidence 91%, retrieval
top match 87% on page 6, entailment 94%, contradiction 2%, supported threshold ≥ 0.60,
model `cross-encoder/nli-deberta-v3-small`, pipeline 0.2.0, timestamp.

**Why it matters.** A citation says "look at page 6". A receipt says "this is the passage,
this is the score, this is the threshold, this is why the model was asked, and this is the
version that produced it". That is the difference between a quote and an auditable
judgement.

---

### Step 11 — Reproducibility audit

**What happens.** Twelve signals are checked against the paper's text:

1. dataset availability (weight 2)
2. source-code availability (weight 2)
3. model architecture details (weight 1)
4. hyperparameters (weight 2)
5. preprocessing (weight 1)
6. random seed (weight 1)
7. software environment (weight 1)
8. experimental procedure (weight 1)
9. train/validation/test split (weight 1)
10. sample size (weight 1)
11. baseline comparison (weight 1)
12. evaluation metrics (weight 1)

Each is **yes** (1 point), **partial** (0.5), or **no** (0), with a quoted line and page
when found. The score is the weighted percentage. The total weight is 15.

This is a **text-level audit**. The app does not run the paper's code, and it says so.
A paper can score 100/100 and still fail to reproduce; the score measures what is
documented, not what is true.

**Where.** `api/pipeline/repro.py`.

**Example.** The sample scores **63/100**: 5 present, 3 partial, 4 missing. The missing
signals are random seed, experimental procedure, train/validation/test split, and sample
size. Those become the "gaps" list and feed the report's risks and next steps.

**Why it matters.** "Can another team rebuild it?" is a business question disguised as a
technical one. This makes the answer inspectable.

---

### Step 12 — TRL: how close is it to real use?

**What happens.** TRL is a deterministic rubric over what the paper says about **its own**
work. There are two tracks:

- **Evaluation track (TRL 1–4):** problem → method → experiment → baseline comparison.
- **Environment track (TRL 5–9):** relevant environment → field/pilot → operational →
  certified/qualified → proven in operation.

The final level is the higher track. The environment track only counts if the paper also
contains an experimental evaluation. A released, installable, documented software artifact
can support up to TRL 6, but only alongside an experiment.

The rubric is deliberately suspicious:

- related work and future-work sections never count as evidence;
- a negation ("no field trial was conducted") does not count;
- hedging ("can be deployed", "may be used") does not count for levels 5–9;
- a sentence about someone else's system does not count;
- a review or survey is capped at TRL 3.

The result includes a confidence level, a plausible range, and the higher-level mentions
that were rejected and why.

**Where.** `api/pipeline/trl.py`, `api/pipeline/scope.py`, `api/pipeline/artifacts.py`.

**Example.** The sample has a problem statement, a method, an experiment, and a baseline,
so the evaluation track reaches **TRL 4**. It has no real-world environment, field trial,
or operational deployment, so the environment track contributes nothing. The result is
TRL 4 with medium confidence, a plausible range of 4–5, and the note "No field/pilot
evidence was found."

**Why it matters.** This is the moat. A summary tool can say "the paper reports 42%"; it
cannot say "the paper is lab-validated and the next missing evidence is a field pilot"
unless it has a rubric like this.

---

### Step 13 — The executive report and the decision brief

**What happens.** The baseline report is assembled **deterministically** from the
structured analysis. It has five sections:

1. What the paper achieved
2. What is proven
3. What is not proven
4. Main risks
5. Recommended next steps

Every factual bullet carries a `[p.N]` citation. An optional Gemini pass may rewrite only
sections 3 and 4. Its output is filtered mechanically: any sentence without a valid page
citation is dropped. If nothing valid remains, the template report is used.

The Report tab also shows a **Decision Brief**: a short readiness call ("Lab-validated —
pilot next"), the evidence count, one concrete gap, and the next step. It is a reading of
the evidence, not an investment recommendation.

**Where.** `api/pipeline/report.py`, `client/src/tabs/ReportTab.jsx`.

**Example.** The sample's report says 2 of 6 claims cleared the threshold, lists the two
supported claims with pages, lists the energy and generalisation claims as not proven,
names the missing seed and procedure as risks, and recommends a field/pilot evaluation to
move beyond TRL 4.

**Why it matters.** A decision-maker can read the brief in thirty seconds; a reviewer can
check every line against a page.

---

### Step 14 — The result goes back to the browser

**What happens.** The worker stores the full JSON result in SQLite. The browser's next poll
returns it. The React app renders the header verdict line, the four tabs, the radar, the
gauges and the receipt. Metadata about the analysis is saved in the browser's
`localStorage` so the Portfolio screen can offer it later; the document itself stays on the
server.

**Where.** `api/jobs/worker.py`, `client/src/App.jsx`, `client/src/tabs/*`.

**Why it matters.** The interface is a view over one stable JSON contract. The demo fixture
uses the same shape as a live analysis, so the sample is an honest preview of the product.
The three decision lenses are rendered from that payload; they add no new claims and call
no model.

---

### Step 15 — Portfolio: compare 2–5 papers without becoming a literature assistant

**What happens.** The Portfolio screen takes two to five finished job ids. It builds:

- a **readiness table**: TRL, reproducibility, supported claims, shipped artifacts, gaps;
- a **shared-claim ledger**: every claim from one paper is compared with every claim from
  another using TF-IDF; pairs with similarity ≥ 0.45 are then scored by the same NLI model
  in both directions and labelled **agree**, **conflict**, or **insufficient**.

There is no cross-paper chat and no merged summary. Breadth is added only where a readiness
decision needs it. At most five papers and twelve ledger entries.

**Where.** `api/pipeline/portfolio.py`, `api/main.py`, `client/src/components/PortfolioScreen.jsx`.

**Example.** SparseRoute claims a 42% latency reduction; EfficientFormer claims token
routing does **not** reduce latency. The pair has 0.71 claim overlap and 0.85 contradiction
in both directions, so the ledger marks it **conflict**. The readiness table shows
SparseRoute at TRL 4 with one shipped artifact and EfficientFormer at TRL 6 with two.

**Why it matters.** "Which of these should we build on?" is a portfolio question. The app
answers exactly that, and refuses the neighbouring question ("tell me everything about
these papers") that would turn it into a worse PaperLens.

---

### Step 16 — Retention and cleanup

**What happens.** A janitor deletes uploads after one hour and results after 24 hours by
default, and keeps at most 200 stored jobs. `DELETE /api/jobs/{id}` removes an analysis
and its uploaded file immediately when the job is not running.

**Where.** `api/jobs/cleanup.py`, `api/jobs/worker.py`.

**Why it matters.** Uploaded papers are sensitive. Retention is a product decision, not an
afterthought.

---

## 5. What the numbers mean (and do not mean)

| Number | Meaning | What it is not |
|---|---|---|
| **Supported** | Retrieval found a relevant passage and the NLI model's entailment probability cleared the threshold | Proof that the claim is true in the real world |
| **Partially supported** | The passage is related, but the claim is broader or slightly different (a missing number, a wider scope, a hedge) | A polite "supported" |
| **Unverified / insufficient** | Nothing cleared the thresholds, or the paper contradicts the claim | Proof that the claim is false |
| **Confidence** | A calibrated-looking score derived from entailment and relevance; it ranks verdicts, it does not certify them | A probability that the paper is correct |
| **Retrieval relevance** | Cosine similarity between the claim and the candidate sentence | A judgement of truth |
| **NLI entailment** | The model's probability that the passage entails the claim | A human peer review |
| **TRL** | The highest level for which the paper's own wording supplies evidence | A market forecast or an investment rating |
| **Reproducibility score** | How much of the twelve-signal documentation is present | A guarantee that the result reproduces |
| **N** | How many examples a measured number is based on | Statistical significance |

The app is built to abstain. An abstention is a feature: it tells you where the paper has
not earned your trust yet.

---

## 6. How it differs from competitors

The category is crowded. The mistake is to compete on breadth, because the incumbents are
already good at it and have more data. ThesisTrace competes on the **depth of one
decision**.

| Tool | What it is best at | What it optimises | Where it leaves a gap |
|---|---|---|---|
| **PaperLens** | Multi-paper synthesis and literature-level answers | Breadth | Does not audit each claim against the paper's own passages, score reproducibility, or assign a cited TRL |
| **Elicit** | Structured literature review and extraction tables | Breadth and speed | Produces review material, not a readiness decision or a per-verdict receipt |
| **SciSpace** | Chat with a PDF, explanations, writing support | Reading and writing | Answers are prose; there is no deterministic verdict trail or TRL rubric |
| **Scite** | Citation context: whether later work supports or contrasts a claim | Citation reliability | It audits the citation network, not the paper's internal evidence or readiness |
| **Consensus** | Yes/no questions across many studies, with an aggregate view | Corpus-level evidence | Not a single-paper audit, no reproducibility score, no TRL |
| **Undermind** | Deep literature search and recall | Finding relevant work | Search is the product; verification is not |
| **General PDF chatbots** | Flexible questions, fluent explanations, writing help | Conversational fluency | Stochastic answers, citations can be wrong, no fixed thresholds, no audit file, no local guarantee |
| **ThesisTrace** | One paper's evidence, reproducibility and readiness, with a receipt | Depth and decision quality | Deliberately weak at breadth, literature search and free-form chat |

**Where PaperLens wins, honestly:** breadth, multi-paper synthesis, prose explanations,
and the experience of exploring a literature. If your job is "tell me what the field
says", use PaperLens.

**Where ThesisTrace wins:** "Should we build on this one paper, and what is missing?"
That question needs claim-level evidence, a reproducibility audit, a readiness rubric, and
a receipt. The three lenses then let a researcher, an engineer and a business reader use
the same audit without three different summaries. A synthesis engine is the wrong shape
for it.

**What if Elicit or PaperLens ships TRL?** They can copy the label. The harder things to
copy are the calibration set, the per-verdict audit trail, and the local/private
deployment. The response is not to add more chat; it is to publish agreement numbers and
make the receipt the unit of trust.

**What we deliberately do not do:** cross-paper question answering, literature search,
writing assistance, or a general "chat with your corpus". Those are different products.

---

## 7. The business view

This is the short version of `documentation/Business-Plan.md` and the pitch deck.

**Who pays.** Students adopt; labs pay.

| Tier | Price (hypothesis) | Why it exists |
|---|---|---|
| Free | $0 | Three papers a month; the demo is the product |
| Student | $6/month | 30 papers, claims, readiness, Markdown export |
| Researcher | $15/month | Batch, API, priority |
| Lab / institution | from ~$8/seat/month | Reproducibility reports, self-hosted option, admin |

**Value metric.** Papers audited, not seats. It tracks the work the user actually does and
maps to compute cost.

**Unit economics.** Compute is not the constraint. A full model-backed paper is budgeted at
15–45 seconds of CPU; at an assumed $0.05 per CPU-hour that is roughly $0.0006 per paper.
Support and acquisition dominate the margin. The measured fallback tier is around 16 ms per
corpus document, effectively zero compute.

**Market sizing.** Bottom-up, not a borrowed TAM:

```
TAM = reachable research writers × annual price
SAM = one beachhead × annual price
SOM = paying seats sold in 12 months × annual price
```

An illustrative year-one case (explicitly an assumption, not a forecast): 1,200 students at
$72/year plus 10 labs at five seats and $96/seat/year is about **$110k ARR**. Replace the
counts with institution data before presenting it as market research.

**Moat.** The Trust Ledger (an auditable decision trail), a calibrated readiness rubric, and
local/private deployment. Not the model weights, which anyone can download.

**Current stage, stated honestly.** Pre-revenue. No interviews completed yet (0 of 12).
The evaluation set is a 15-case developer-labelled seed set, not two independent raters.
The NLI tier has not been timed on the deployment hardware. The pitch deck labels those
gaps rather than hiding them.

**Biggest risks.** Readiness is not trusted; an incumbent copies the label; verification is
not a budget line. Each has a test and a kill criterion in the business plan.

---

## 8. Run it yourself in about ten minutes

Prerequisites: Python 3.11+ and Node 22+ (or a portable Node build inside `.data/tools`).
The exact bootstrap is in `README.md`; this is the short path on Windows.

```bat
cd S:\Projects\ThesisTrace

REM 1. Python environment (once)
py -V:3.12 -m venv .venv
set UV_CACHE_DIR=%CD%\.data\pip-cache
uv pip install --python .venv\Scripts\python.exe fastapi uvicorn python-multipart pydantic PyMuPDF

REM Optional: full local NLP models (large download)
REM .venv\Scripts\python.exe -m pip install -r requirements.txt

REM 2. API
.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000

REM 3. UI, in a second terminal
cd client
npm install --cache="..\.data\npm-cache" --no-audit --no-fund
npm run dev
```

Open the local Vite address, click **See a sample analysis**, and walk the four tabs. No
key is needed. To upload a real paper, drop a text-based PDF or a `.txt`/`.md` file. If the
optional models are not installed, the app uses the lexical fallback and says so.

Useful checks:

```bat
REM backend tests
.venv\Scripts\python.exe -B -m unittest discover -s api/tests -t .

REM evaluation with N
.venv\Scripts\python.exe -B eval\run_eval.py --analyze

REM UI build
cd client
npm run build
```

The API documentation is served locally at `/docs` when the API is running. No external
service is required.

---

## 9. Questions people ask

**Is this just ChatGPT with a PDF?**
No. The verdict is produced by retrieval plus a cross-encoder NLI model with fixed
thresholds. The optional LLM can propose claims or polish two report sections, but it never
assigns a verdict, and generated claims must be verbatim in the paper.

**Does it upload my paper to the cloud?**
Not by default. The file is written to `.data/uploads` on the same machine. If you set a
Gemini key, claim extraction, two report sections, and the optional chat can call Gemini;
the claim verdicts still use the local NLI model.

**Do I need an API key?**
No. Without a key you get heuristic claim extraction, the lexical or local NLI verdicts,
the deterministic report, and the full audit trail.

**How accurate is it?**
On a 15-case developer-labelled seed set, the lexical-fallback tier scores 0.667 verdict
accuracy and 0.618 macro-F1. That is a regression guard, not a marketing number. The NLI
tier has not been evaluated with models on this checkout. Always read N and the caveat.

**Why "insufficient" instead of "false"?**
Because the paper not proving a claim is different from the claim being wrong. The app
abstains when retrieval or NLI does not clear the threshold, and it says so.

**How is TRL decided?**
A deterministic rubric over the paper's own wording, split into an evaluation track
(1–4) and an environment track (5–9), with section roles, negation/hedge filters, and a
review cap. It is not an LLM's opinion. It reports confidence and a plausible range.

**Is TRL appropriate for software?**
It is a standard readiness language, adapted with an artifact track for released code,
containers and documentation. It is indicative, not certified. The calibration study with
two raters is the next step.

**What if the PDF is scanned?**
The app rejects it because there is no text layer. OCR is out of scope.

**What are the limits?**
30 MB, 60 pages, 8 claims, 2–5 papers per portfolio. The NLP models are English-centric;
other languages are untested. Very short documents produce unreliable results and a warning.

**How long does it take?**
The fallback tier is milliseconds to a few seconds. The full local model tier is budgeted
at 15–45 seconds per paper on CPU. The UI shows progress and queue position.

**Can I compare papers?**
Yes, two to five. It compares readiness and near-duplicate claims. It does not answer
questions across the papers.

**Can I export the report?**
Yes, as Markdown. The verdict receipts can be exported as JSON from the Claims tab and the
audit endpoint.

**Is the report written by AI?**
The baseline report is deterministic. An optional Gemini pass can rewrite the "not proven"
and "risks" sections, but any sentence without a valid page citation is dropped.

**What are the three lenses?**
The same analysis read as a researcher, an engineer, or a business decision. They are
generated from the existing claims, reproducibility checklist and TRL result; switching a
lens changes emphasis, not the underlying evidence.

**Does it detect fraud or fabricated data?**
No. It checks whether the paper's own text supports its claims and documents what is
missing. It cannot verify the underlying experiment.

**Is it free?**
The prototype is free to run locally. The proposed pricing is a hypothesis, not a live
billing system.

**Who pays in the business model?**
Labs and institutions, for reports they can attach to a review. Students are the adoption
channel.

**What is the moat?**
The audit receipt, the calibration set, and local/private deployment. Not the model itself.

**What is the biggest risk?**
That readiness is not trusted enough to change a decision, or that an incumbent ships a
similar label. The response is published agreement numbers and a better receipt, not more
features.

**What should we build next?**
Two-rater calibration on 20–25 real papers, a model-backed Docker run, the interview study,
and pilot hardening (auth, quota, usage log). The deck and progress log name these as open
work.

---

## 10. Learn enough to understand it in a few hours

You do not need a maths degree. If you can read a little Python and you are comfortable
with percentages, you can follow the whole system. Do not read entire textbooks; read the
named sections and then open the matching file.

Total: about **4 hours 30 minutes**, split into five sessions. If you only have 30 minutes,
read sections 0–4 and the glossary.

### Session 1 — How a PDF becomes sentences (45 min)

- **Question:** What is text preprocessing, and why does a page number matter?
- **Concepts:** token, sentence segmentation, section detection, page mapping, regular
  expressions.
- **Read:** the first chapters of *Speech and Language Processing* by Jurafsky and Martin
  on regular expressions, words and corpora. Read only the sections on tokenisation and
  sentence splitting.
- **Open:** `api/pipeline/ingest.py`, especially `build_document` and
  `build_sentence_index`.
- **Do:** upload a `.txt` paper; find one sentence in the Summary or Claims tab and confirm
  its page in the PDF.
- **Checkpoint:** explain why the pipeline stores a page number on every sentence instead
  of looking it up later.

### Session 2 — How it finds evidence (60 min)

- **Question:** How can a computer find the sentence that might prove a claim?
- **Concepts:** bag of words, TF-IDF, cosine similarity, top-k retrieval, score floor.
- **Read:** *Introduction to Information Retrieval* by Manning, Raghavan and Schütze,
  chapters 1 and 6 (Boolean retrieval, term weighting and the vector space model).
- **Open:** `api/pipeline/classical.py` (the `TfidfIndex`) and the `SentenceIndex` in
  `api/pipeline/evidence.py`.
- **Do:** in a Python shell, build a small TF-IDF index over three sentences and query it.
  Then find the `RETRIEVAL_FLOOR` in `config.py`.
- **Checkpoint:** why is the claim's own sentence excluded from retrieval? What would
  happen to the verdicts if it were not?

### Session 3 — How it judges a claim (75 min)

- **Question:** How does a model decide whether a passage supports a claim?
- **Concepts:** text classification, cross-encoders, natural language inference,
  entailment / neutral / contradiction, thresholds, abstention.
- **Read:** the entailment and text-classification sections of Jurafsky and Martin, or
  chapter 1 and the classification sections of *Natural Language Processing with
  Transformers* by Tunstall, von Werra and Wolf.
- **Open:** `api/pipeline/evidence.py`, especially `_nli_scores`, `_lexical_verdict`, and
  `verify_claims`; then `api/pipeline/config.py` for the thresholds.
- **Do:** open "Why this verdict?" on a supported claim and a partial claim. Compare the
  entailment, contradiction and relevance numbers. Change one threshold in a scratch copy
  and see how the verdict changes.
- **Checkpoint:** explain the difference between "partially supported" and "insufficient".
  Why is an abstention safer than forcing a yes/no?

### Session 4 — How it scores readiness (45 min)

- **Question:** What makes a paper "ready", and why is that hard to automate?
- **Concepts:** reproducibility signals, weighted scoring, TRL, evidence scope, negation,
  hedging, confidence.
- **Read:** the module docstrings at the top of `api/pipeline/repro.py` and
  `api/pipeline/trl.py`. They are written as explanations, not just comments.
- **Open:** `repro.py` (`assess_reproducibility`) and `trl.py` (`assess_trl`); then
  `scope.py` for the negation and hedging rules.
- **Do:** score a paper you know by hand on the twelve signals, then compare with the app.
  Identify one place where the text-level audit over- or under-counts.
- **Checkpoint:** why can a paper score 100/100 on reproducibility and still fail to
  reproduce? Why is a review capped at TRL 3?

### Session 5 — How the system runs and how we know it works (45 min)

- **Question:** How does an upload become a result, and what do the evaluation numbers mean?
- **Concepts:** HTTP API, job queue, polling, JSON contract, accuracy, precision, recall,
  F1, recall@k, seed set.
- **Read:** the FastAPI "Tutorial – User Guide" first pages and the React "Describing the
  UI" guide. Then read `documentation/Evaluation.md`.
- **Open:** `api/main.py` (`POST /api/jobs`), `api/jobs/store.py` (the lease), and
  `client/src/App.jsx` (the polling loop). Run `eval/run_eval.py`.
- **Do:** run `python eval/run_eval.py --analyze` and read the table aloud, including N and
  the caveat.
- **Checkpoint:** why is a queue used instead of doing the analysis inside the upload
  request? What does recall@5 measure, and why is accuracy alone misleading on a small
  seed set?

### The 30-minute path

Read sections 0, 1, 3, 4 (steps 0–10) and the glossary. Skip the study sessions. You will
be able to explain the product, the verdict pipeline, and the Trust Ledger, which is enough
for most conversations.

---

## 11. Glossary

**Abstain / insufficient** — the system refuses to call a claim supported because the
evidence did not clear its thresholds. Not the same as "false".

**API** — the local HTTP service the interface talks to; it accepts uploads and returns
JSON.

**Artifact** — a released code repository, container, documentation site or demo that
supports reproducibility.

**Claim** — a sentence that asserts a result, comparison or capability of the paper's own
work.

**Confidence** — a score derived from entailment and retrieval relevance. It ranks verdicts;
it does not certify truth.

**Cross-encoder** — a model that reads two texts together (claim and passage) and scores
their relationship. More accurate than comparing independent embeddings, slower.

**Entailment** — the passage supports the claim as written.

**Contradiction** — the passage asserts something incompatible with the claim.

**Neutral** — the passage is related but does not settle the claim.

**F1** — the harmonic mean of precision and recall; a single number for classification
quality across classes.

**Hallucination** — generated text that is not supported by the source.

**Job queue** — a durable list of work. The API enqueues; a worker claims, runs and stores
the result.

**LLM** — large language model. Here it is optional and never the verdict-maker.

**NLI** — natural language inference; the task of classifying entailment, neutral or
contradiction.

**N** — the number of examples a measured result is based on. Always read it.

**Pipeline** — the ordered stages from upload to report.

**Precision / recall** — of the claims marked supported, how many were right (precision);
of the truly supported claims, how many were found (recall).

**RAG** — retrieval-augmented generation; retrieve passages first, then generate or judge.

**Recall@k** — whether the correct passage appears in the top *k* retrieved results.

**Reproducibility** — whether another team could rebuild the result from what is documented.

**Seed set** — a small labelled dataset used to check the pipeline. Ours has 15 cases and
developer labels.

**TF-IDF** — a weighting scheme that rewards words that are frequent in one document but
rare across the collection. Used here for sentence retrieval.

**Token** — a word or word-piece produced by a tokenizer.

**TRL** — Technology Readiness Level, a 1–9 scale from basic principles to proven operation.

**Trust Ledger** — the per-claim receipt: retrieval scores, NLI probabilities, thresholds,
model, pipeline version, timestamp, abstain reason.

**Verdict** — supported, partially supported, or insufficient.

---

## 12. Where to read more

- `README.md` — what it is, screenshots, setup, API table.
- `documentation/Architecture.md` — data contract, pipeline stages, queue, deployment.
- `documentation/Evaluation.md` — gold sets, metrics, caveats, how to reproduce the numbers.
- `documentation/Competitive-Analysis.md` — the full competitor matrix and positioning map.
- `documentation/Business-Plan.md` — lean canvas, pricing, unit economics, scenarios, kill criteria.
- `documentation/Validation-Plan.md` — interview script, survey, experiments, pilot design.
- `documentation/Production-Readiness.md` — shipped vs gap, SLOs, security, runbook.
- `documentation/Progress.md` — dated changelog and what remains open.
- `ThesisTrace_Pitch_Deck.pptx` — the 15-slide narrative plus appendix.

If you read only one more document, read `documentation/Architecture.md`. If you read two,
add `documentation/Evaluation.md` so you know exactly how strong the evidence is.

---

_This overview describes the code in this repository as of November 2026. Where a number
is an assumption, it is labelled. Where a tier has not been measured, it says so._
