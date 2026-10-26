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
| 1 | History and evolution of NLP; rule-based → statistical → neural paradigms | The architecture mirrors the evolution: regex/rules → TF-IDF statistical retrieval → transformer/NLI → optional LLM; discussed in [Architecture.md](Architecture.md) and the viva notes | Introduction to NLP |
| 2 | Key NLP tasks: **tokenization** | Stage 1 of pipeline; BPE vs WordPiece vs SentencePiece comparison experiment (Practical 1) | Introduction to NLP; Word Level |
| 3 | **Tagging** and parsing; Part-of-speech tagging | POS-tag density used in the complexity score; NER is sequence tagging (same family of tasks) | Introduction to NLP; Word Level |
| 4 | Classification and generation | Claim verdicts = classification (entailment); summaries/reports = generation | Introduction to NLP |
| 5 | Challenges: **ambiguity and context dependence** | ClaimCheck keeps the claim and its cited sentence together, so a verdict is never read out of context; ambiguity is handled operationally rather than with a separate WSD module | Introduction to NLP; Semantic Analysis |
| 6 | Transition from traditional NLP pipelines to deep learning and Transformer-based systems | Two-tier design: sklearn/regex tier → transformer tier → LLM tier (see [Architecture.md](Architecture.md)) | Introduction to NLP |
| 7 | Modern NLP libraries and frameworks | Hugging Face `transformers`/`tokenizers`, scikit-learn, spaCy, PyMuPDF; FastAPI/React for the app layer | Introduction to NLP |
| 8 | **Corpora and their construction** | The ingest corpus is every uploaded paper (page-preserving); a 50-pair gold set is specified in [Evaluation.md](Evaluation.md) and is a Phase D task, not yet built | Word Level |
| 9 | **Regular expressions** | Reference/section/number/metric extraction (percentages, p-values), gazetteer term matching | Word Level |
| 10 | **Finite state automata** | Not implemented in the MVP. The tokenizer study uses a regex word/punctuation baseline; an FSA-style validator is a documented extension for Practical 1, not a claim of the current build | Word Level |
| 11 | Morphological parsing; spelling error detection and correction | Preprocessing hygiene: normalize hyphenation (`energy-` + `consumption`), digit variants; classical-tier step | Word Level |
| 12 | Words and word classes | Technical-term lexicons (dataset/metric/model/device classes) for the Key Concepts tab | Word Level |
| 13 | Context-free grammar, constituency/dependency/probabilistic parsing | Scope-limited: section-aware chunking and spaCy POS features; dependency parsing is deliberately not used by the MVP (claim selection is regex/heuristic), and the reason is documented in [NLP-Pipeline.md](NLP-Pipeline.md) | Syntactic Analysis |
| 14 | Meaning representation; **word sense disambiguation** | The gazetteer canonicalises spelling/alias variants into one concept entry; true word-sense disambiguation is not built and is listed as future work | Semantic Analysis |
| 15 | **Text classification** and clustering; supervised vs unsupervised | Claim verdicts are a 3-way classification (supported / partial / insufficient); clustering is not implemented in the MVP | Text Classification, Clustering and Classical NLP Context |
| 16 | **Feature-based models** (conceptual role) | TF-IDF bag-of-words features behind retrieval and the classical baseline compared against transformers | Text Classification, Clustering and Classical NLP Context |
| 17 | Discourse processing: coherence and reference resolution | Not implemented in the MVP; resolved-term/coreference handling is an identified extension in [NLP-Pipeline.md](NLP-Pipeline.md) | Text Classification, Clustering and Classical NLP Context |
| 18 | Fundamentals of **natural language generation** — summarization, content creation | 3-bullet summary, ELI5 mode, Executive Report generation | Text Classification, Clustering and Classical NLP Context; Applications and Building Models |
| 19 | Classical models: **n-gram language models, HMM, CFG** (+ their limitations) | Discussed as the conceptual baseline that motivates the transformer tier; no n-gram/HMM model is trained in the MVP (scope cut) | Text Classification, Clustering and Classical NLP Context |
| 20 | **Transformer architecture and self-attention**; encoder-only / decoder-only / encoder-decoder | Model choices table: encoder-only (BERT NER, DistilBERT NLI) vs encoder-decoder (T5/BART summarization) vs decoder-only (Gemini, optional) | Transformers and Hugging Face Workflows; Transformers |
| 21 | Pretrained models: **BERT, RoBERTa, GPT, T5** (ALBERT noted) | `distilbert-*` NER & MNLI, `distilbart-cnn`/`flan-t5` summarization; Gemini API in report layer | Transformers and Hugging Face Workflows; Transformers |
| 22 | **Transfer learning and fine-tuning** strategies | Zero-shot/few-shot prompting is implemented; the prompt-vs-fine-tuned comparison (Practical 5) is planned for Phase D, not run yet | Transformers; Transfer Learning |
| 23 | Hugging Face ecosystem: **datasets, tokenizers, transformers**; end-to-end pipelines | `AutoTokenizer` and `pipeline` throughout the neural stages; the `datasets` library is not a runtime dependency (eval sets would use it in Phase D) | Transformers and Hugging Face Workflows |
| 24 | **Question answering** systems | Evidence retrieval renders as extractive QA: claim → answer passage with citation | Transformers; Applications and Building Models |
| 25 | **Named Entity Recognition (NER)** — information extraction | Key Concepts tab: persons, orgs, locations, plus scientific entities (datasets, metrics, models, drugs, materials) | Applications and Building Models |
| 26 | **Text summarization**: techniques and models | Paper Overview tab: 3-bullet + ELI5 (Practical 4) | Applications and Building Models |
| 27 | Text classification applications; sentiment analysis | Not built (scope cut); the TRL/reproducibility rules already demonstrate applied classification without adding a sentiment module | Applications and Building Models |
| 28 | **Machine translation** — applications in global communication | *Not built* (scope cut); mentioned in the report's related-work section only | Applications and Building Models |
| 29 | **Prompt engineering**: zero-shot and few-shot, model-agnostic prompts | Claim extraction and ELI5 prompts (templates in `api/prompts/`, few-shot block in `claims.py`); the TRL rubric is deterministic and never uses an LLM | CO2/CO3 (prompting strand of course outcomes) |
| 30 | **RAG**: grounding LLM outputs | Every generated sentence must carry a retrieved citation; prompt-injection defense | CO5 |
| 31 | Failure modes: **hallucination, prompt injection** | Hard grounding rule + document-is-data hardening; measured in evaluation | CO4 |
| 32 | Production: **cost, latency, scalability, reliability** | CPU-only models, caching, async jobs, per-stage latency budget logged | CO6 |

## Table B — Course outcome → Concrete artifact in our project

| CO | Evidence we can show | Artifact |
|----|----------------------|----------|
| CO1 | The pipeline itself shows the evolution: regex/rules → TF-IDF statistical retrieval → transformer NLI/summarization → optional LLM; the comparison is documented and visible in the UI's stage labels | [NLP-Pipeline.md](NLP-Pipeline.md), [Architecture.md](Architecture.md) |
| CO2 | Explained mechanism: next-token probabilities + in-context examples = why few-shot extraction works; the ablation with/without examples is a planned experiment | [Prompts-and-Grounding.md](Prompts-and-Grounding.md), Practicals 3/7 |
| CO3 | Reusable, model-agnostic prompt templates with structured JSON outputs; the Gemini adapter can be swapped for a local instruction model without changing the templates | [Prompts-and-Grounding.md](Prompts-and-Grounding.md) |
| CO4 | Hallucination rate measured (unsupported sentences in generated report); injection test suite (strings embedded in uploaded PDFs) | [Evaluation.md](Evaluation.md) section 4, [Prompts-and-Grounding.md](Prompts-and-Grounding.md) section 5 |
| CO5 | TF-IDF retrieval then NLI; only cited text reaches the LLM; recall@k is specified in the evaluation plan, not measured yet | [NLP-Pipeline.md](NLP-Pipeline.md) stages 7-8, [Evaluation.md](Evaluation.md) section 3 |
| CO6 | Stage-level latency log, model size table, single-container CPU deployment, optional-API cost note (0 INR default) | [Feasibility-Analysis.md](Feasibility-Analysis.md), [Setup-and-Containerization.md](Setup-and-Containerization.md) |

## Table C — Feature → Prescribed practical(s)

**Implementation status:** Practicals 1, 2, 4 and 8 are implemented in this build.
Practicals 3/5/6/7 have a working code path, but their formal comparison/metric runs
remain Phase D tasks (see [Progress.md](Progress.md)).

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
