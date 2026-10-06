# Concepts Used ↔ CSR322 Syllabus Mapping

Every NLP concept in Paper2Reality is mapped to (a) a **syllabus block**, (b) a **course
outcome**, and (c) at least one of the **8 prescribed practicals**. Use this file in the
viva and in the project report's "syllabus alignment" section.

**Source:** `CSR322_2026-10-06.pdf` (Session 2026-27). Syllabus references below quote the
exact block headings from the PDF. *Note: the PDF's Unit I–VI markers are interleaved with
paragraph text in the extracted layout, so blocks are cited by their exact headings; ask
your faculty which heading maps to which Unit number for your answer sheet, or cite both.*

**Course outcomes (verbatim summary):**
- **CO1** — evolution of NLP from classical methods to modern transformer-based approaches
- **CO2** — explain why prompting works: probabilistic language modelling + context-driven reasoning
- **CO3** — design effective, model-agnostic prompts using systematic prompt engineering
- **CO4** — evaluate prompt outputs; failure modes: hallucination and prompt injection
- **CO5** — design Retrieval-Augmented Generation (RAG) systems to ground LLM outputs
- **CO6** — production considerations: cost, latency, scalability, reliability

---

## Table A — Concept → Where it is used in Paper2Reality → Syllabus block

| # | Concept (syllabus wording) | Used in our build | Syllabus block |
|---|---------------------------|-------------------|----------------|
| 1 | History and evolution of NLP; rule-based → statistical → neural paradigms | Report's "why this design" section: classic pipeline (rules+TF-IDF) feeds the neural/LLM layer — the architecture mirrors the evolution | Introduction to NLP |
| 2 | Key NLP tasks: **tokenization** | Stage 1 of pipeline; BPE vs WordPiece vs SentencePiece comparison experiment (Practical 1) | Introduction to NLP; Word Level |
| 3 | **Tagging** and parsing; Part-of-speech tagging | POS-tag density used in the complexity score; NER is sequence tagging (same family of tasks) | Introduction to NLP; Word Level |
| 4 | Classification and generation | Claim verdicts = classification (entailment); summaries/reports = generation | Introduction to NLP |
| 5 | Challenges: **ambiguity and context dependence** | ClaimCheck exists because sentences are ambiguous out of context; WSD/ambiguity discussion in report | Introduction to NLP; Semantic Analysis |
| 6 | Transition from traditional NLP pipelines to deep learning and Transformer-based systems | Two-tier design: sklearn/regex tier → transformer tier → LLM tier (see [Architecture.md](Architecture.md)) | Introduction to NLP |
| 7 | Modern NLP libraries and frameworks | Hugging Face `transformers`/`tokenizers`/`datasets`, scikit-learn, spaCy, PyMuPDF | Introduction to NLP |
| 8 | **Corpora and their construction** | Our evaluation gold set (50 hand-labeled claim–passage pairs) + upload corpus of sample papers | Word Level |
| 9 | **Regular expressions** | Reference/section/number/metric extraction (percentages, p-values), gazetteer term matching | Word Level |
| 10 | **Finite state automata** | Report experiment: FSA-style token validator/morpheme splitter built by hand and compared to BPE (Practical 1) | Word Level |
| 11 | Morphological parsing; spelling error detection and correction | Preprocessing hygiene: normalize hyphenation (`energy-` + `consumption`), digit variants; classical-tier step | Word Level |
| 12 | Words and word classes | Technical-term lexicons (dataset/metric/model/device classes) for the Key Concepts tab | Word Level |
| 13 | Context-free grammar, constituency/dependency/probabilistic parsing | Scope-limited: section-aware chunking + dependency parse to pull claim subjects/objects (spaCy); discussed as "what we used and what we skipped" | Syntactic Analysis |
| 14 | Meaning representation; **word sense disambiguation** | Same term in different senses (e.g., "resolution" = metric vs display); entity linking step in Key Concepts | Semantic Analysis |
| 15 | **Text classification** and clustering; supervised vs unsupervised | Claim support/partial/insufficient labels; k-means clustering of key terms as an unsupervised view | Text Classification, Clustering and Classical NLP Context |
| 16 | **Feature-based models** (conceptual role) | TF-IDF bag-of-words features behind retrieval and the classical baseline compared against transformers | Text Classification, Clustering and Classical NLP Context |
| 17 | Discourse processing: coherence and reference resolution | Coreference pass (`it/this/that method`) so claims attach to the right entity before retrieval | Text Classification, Clustering and Classical NLP Context |
| 18 | Fundamentals of **natural language generation** — summarization, content creation | 3-bullet summary, ELI5 mode, Executive Report generation | Text Classification, Clustering and Classical NLP Context; Applications and Building Models |
| 19 | Classical models: **n-gram language models, HMM, CFG** (+ their limitations) | Baseline comparison in report: n-gram / HMM-style tagger vs transformer outputs — motivates CO1 | Text Classification, Clustering and Classical NLP Context |
| 20 | **Transformer architecture and self-attention**; encoder-only / decoder-only / encoder-decoder | Model choices table: encoder-only (BERT NER, DistilBERT NLI) vs encoder-decoder (T5/BART summarization) vs decoder-only (Gemini, optional) | Transformers and Hugging Face Workflows; Transformers |
| 21 | Pretrained models: **BERT, RoBERTa, GPT, T5** (ALBERT noted) | `distilbert-*` NER & MNLI, `distilbart-cnn`/`flan-t5` summarization; Gemini API in report layer | Transformers and Hugging Face Workflows; Transformers |
| 22 | **Transfer learning and fine-tuning** strategies | Zero-shot/few-shot prompting vs optional fine-tuned baseline (Practical 5); transfer learning explained in report | Transformers; Transfer Learning |
| 23 | Hugging Face ecosystem: **datasets, tokenizers, transformers**; end-to-end pipelines | `AutoTokenizer`/`AutoModel`/`pipeline` throughout; `datasets` for eval sets | Transformers and Hugging Face Workflows |
| 24 | **Question answering** systems | Evidence retrieval renders as extractive QA: claim → answer passage with citation | Transformers; Applications and Building Models |
| 25 | **Named Entity Recognition (NER)** — information extraction | Key Concepts tab: persons, orgs, locations, plus scientific entities (datasets, metrics, models, drugs, materials) | Applications and Building Models |
| 26 | **Text summarization**: techniques and models | Paper Overview tab: 3-bullet + ELI5 (Practical 4) | Applications and Building Models |
| 27 | Text classification applications; sentiment analysis | Document-type/field classifier; sentiment as an optional demo extra on abstracts | Applications and Building Models |
| 28 | **Machine translation** — applications in global communication | *Not built* (scope cut); mentioned in the report's related-work section only | Applications and Building Models |
| 29 | **Prompt engineering**: zero-shot and few-shot, model-agnostic prompts | Claim extraction, ELI5, TRL justification prompts (Practicals 3, 7) | CO2/CO3 (prompting strand of course outcomes) |
| 30 | **RAG**: grounding LLM outputs | Every generated sentence must carry a retrieved citation; prompt-injection defense | CO5 |
| 31 | Failure modes: **hallucination, prompt injection** | Hard grounding rule + document-is-data hardening; measured in evaluation | CO4 |
| 32 | Production: **cost, latency, scalability, reliability** | CPU-only models, caching, async jobs, per-stage latency budget logged | CO6 |

## Table B — Course outcome → Concrete artifact in our project

| CO | Evidence we can show | Artifact |
|----|----------------------|----------|
| CO1 | Report section "From n-grams to transformers": classic pipeline vs transformer results side by side; architecture mirrors the evolution | [NLP-Pipeline.md](NLP-Pipeline.md), report section 2 |
| CO2 | Explained mechanism: next-token probabilities + in-context examples = why few-shot extraction works; ablation with/without examples | [Prompts-and-Grounding.md](Prompts-and-Grounding.md), Practicals 3/7 |
| CO3 | Reusable, model-agnostic prompt templates with structured JSON outputs; same prompt runs on local model AND Gemini | [Prompts-and-Grounding.md](Prompts-and-Grounding.md) |
| CO4 | Hallucination rate measured (unsupported sentences in generated report); injection test suite (strings embedded in uploaded PDFs) | [Evaluation.md](Evaluation.md) section 4, [Prompts-and-Grounding.md](Prompts-and-Grounding.md) section 5 |
| CO5 | Retrieval (TF-IDF/embeddings) then NLI, only cited text reaches the LLM; recall@k reported | [NLP-Pipeline.md](NLP-Pipeline.md) stages 7-8, [Evaluation.md](Evaluation.md) section 3 |
| CO6 | Stage-level latency log, model size table, single-container CPU deployment, optional-API cost note (0 INR default) | [Feasibility-Analysis.md](Feasibility-Analysis.md), [Setup-and-Containerization.md](Setup-and-Containerization.md) |

## Table C — Feature → Prescribed practical(s)

| # | Prescribed practical (syllabus wording) | Where Paper2Reality satisfies it |
|---|------------------------------------------|----------------------------------|
| 1 | Explore and compare different tokenization techniques including BPE and Sentence Piece | Task A3: same paper tokenized by BPE (GPT-2 HF), WordPiece (BERT), SentencePiece (T5); table of vocab sizes, OOV behavior, token counts on scientific terms |
| 2 | Use Hugging Face tokenizers and transformer models for basic NLP tasks | Whole pipeline: `AutoTokenizer` + `pipeline` for NER, summarization, NLI (tasks A6, A7, B3) |
| 3 | Perform zero-shot and few-shot text classification using prompt-based approaches | Claim-support classification: zero-shot (NLI) vs few-shot prompted LLM (tasks B1, B5) |
| 4 | Build a text summarization pipeline using a pre-trained transformer | 3-bullet + ELI5 summarization stage (task A7) |
| 5 | Compare prompt-based NLP solutions with fine-tuned transformer models | Prompt-based vs small/fine-tuned model comparison for summary and claims (task B6) |
| 6 | Evaluate NLP models using standard metrics and perform error analysis | Full metric suite + 10-worst-errors analysis (tasks D1/D2, see [Evaluation.md](Evaluation.md)) |
| 7 | Analyze the impact of tokenization and prompt design on model outputs | Controlled experiment: tokenization variants + prompt ablations (few-shot k=0/2/4), task D3 |
| 8 | Develop an NLP pipeline combining tokenization, modelling, and evaluation | The entire system is this pipeline; documented end-to-end, task D4, [NLP-Pipeline.md](NLP-Pipeline.md) |

## Textbooks and references (from syllabus) — where we cite them

- *Mastering Large Language Models* (Khandare, BPB) — prompting and LLM layer
- *Building Transformer Models with PyTorch 2.0* (Timsina, BPB) — transformer/fine-tuning sections
- *Practical Natural Language Processing* (Vajjala et al., O'Reilly) — pipeline and evaluation design
