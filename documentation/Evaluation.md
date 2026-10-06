# Evaluation Plan — Paper2Reality

Satisfies **Practical 6**: *"Evaluate NLP models using standard metrics and perform
error analysis"* — plus the measurement story for **CO4** (failure modes) and **CO6**
(latency/cost). One member owns running metrics; *everyone* does error analysis.

**Principle:** a demo shows what works; evaluation shows what breaks. Report both.

---

## 1. What we evaluate

| Component | Metric | Tooling | Target (realistic) |
|-----------|--------|---------|---------------------|
| Summarization (3-bullet) | ROUGE-1 / ROUGE-2 / ROUGE-L | `rouge-score` (or `evaluate` lib) | R-1 ≥ 0.35 on our sample set |
| NER (model vs gazetteer vs merged) | entity-level P/R/F1 (span+type) | manual labels on 2 pages × 5 docs | merged F1 ≥ model alone |
| Claim extraction (heuristic vs prompt-based) | claim recall vs human list; precision | 3 papers, human gold claims | prompt-based recall > heuristic |
| Claim verdicts (NLI stage) | accuracy + macro-F1 (3 classes) | **gold set: 50 claim–passage pairs** | macro-F1 ≥ 0.6 (realistic for 🟢/🟡/🔴) |
| Evidence retrieval | recall@k (k=1,3,5) | gold set passages | recall@5 ≥ 0.8 |
| Reproducibility checklist | agreement with hand-checked answer | 3 papers, human checklist | agreement ≥ 80 % |
| TRL level | ±1 agreement with human judgment | 3 papers, 2 human raters | ≥ 2/3 papers within ±1 |
| Whole app | latency per stage, peak RAM | `timings` + `/api/health` | ≤ 45 s, ≤ 3 GB RSS |

**Sample set:** 5 papers (2 CS/ML, 1 medical-imaging, 1 energy/materials, 1 patent-style
technical report) — diversity makes the TRL story credible and stresses different entity
types. Store under `eval/corpus/` with `eval/gold/` labels (this *is* our corpora
construction practical — syllabus: "Corpora and their construction").

## 2. Gold sets (start labeling in Week 2 — it gates everything)

1. **Claim–passage gold (50 pairs):** sample verdict pairs from early runs + crafted hard
   cases (scope mismatch, "up to X%", lab vs real world). Label: supported / partial /
   insufficient. Two members label 10 pairs each and adjudicate disagreements → teaches
   inter-annotator agreement (report Cohen's kappa if time allows).
2. **Summary gold:** for 3 papers, keep human-written 3-bullet summaries (30 min each) as
   ROUGE references. (If time is short: use the abstract's first 3 sentences as a
   documented, weaker reference — say so in the report.)
3. **Entity gold:** 2 pages per paper, hand-tagged entities for NER F1.

## 3. Retrieval & grounding measurements (CO5)

- **recall@k:** fraction of gold evidence passages in top-k retrieved (k=1,3,5).
- **Score floor effect:** report how many claims short-circuit to 🔴 *before* NLI
  (a designed behavior — show it, don't hide it).
- **End-to-end grounded accuracy:** of verdicts shown as 🟢, what fraction agree with gold?
  This is the honest headline number: *"When we say Supported, we're right X% of the time."*

## 4. Failure-mode measurements (CO4)

| Failure mode | Measurement | Method |
|--------------|-------------|--------|
| Hallucination (summary numbers) | `number_hallucination_rate` | numbers in output not in source ÷ numbers in output |
| Hallucination (claims) | verbatim-check rejection rate | claims dropped by §6 checks ÷ claims proposed |
| Hallucination (report) | `citation_coverage` | sentences with `[p.N]` ÷ total sentences (target 100 %) |
| Prompt injection | injection test suite pass/fail | 6 hostile fixtures must yield identical verdicts to clean run (CO4) |
| Prompt sensitivity | output variance across k=0/2/4 few-shot | does claim set change? qualitative + count overlap (Practical 7) |
| Tokenization impact | tokens/term, split rate on rare scientific terms | BPE vs WordPiece vs SentencePiece table (Practicals 1, 7) |

## 5. Error analysis protocol (the report's best section)

Run the app on all 5 papers, collect **every** wrong verdict + worst summaries, then
classify each failure into exactly one bucket:

| Bucket | Meaning | Example fix |
|--------|---------|-------------|
| A — Ingest/extraction | wrong text, missing section, garbled PDF | better heading regex |
| B — Retrieval | gold passage not in top-k | raise k, semantic rerank |
| C — Reasoning/NLI | passage retrieved, verdict wrong | threshold tuning, better model |
| D — Generation | right facts, bad wording/extra facts | prompt fix, temperature |
| E — Gold-set error | *our label* was wrong | relabel (yes, this happens) |

**Deliverable:** table of the 10 worst errors (claim, expected, actual, bucket, one-line
root cause) + a bar chart of bucket counts. Buckets A–E map directly onto the pipeline
stages → the error analysis doubles as our architecture validation.

## 6. Prompt-vs-fine-tuned comparison (Practical 5)

Compare, on the same tasks: (a) few-shot prompted model, (b) zero-shot NLI approach,
(c) local heuristic/classical baseline. Table: metric per method + latency + RAM + cost.
Expected narrative: prompting wins on flexibility/quality-without-training; classical
wins on speed/offline; NLI wins on verdicts. **All three outcomes are acceptable** — the
comparison *is* the practical.

## 7. Reporting

- `eval/run_eval.py` prints a markdown table; paste into the final report + slides.
- Re-run after any model/threshold change; commit `eval/results/` (small JSON).
- Never report a metric without its sample size (N) and, for hand-labeled sets, the
  labeling protocol from section 2.
