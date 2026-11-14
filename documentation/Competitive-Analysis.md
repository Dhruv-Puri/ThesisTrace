# Competitive Analysis

**One line:** PaperLens tells you what the literature says. ThesisTrace tells you whether to
build on it.

The product is not in the "read papers faster" category. It is in the "decide whether a
piece of research is worth acting on" category. That distinction is the whole strategy, and
it is the first thing to say in the viva.

---

## 1. Two different jobs

| | Literature assistant (PaperLens, Elicit, SciSpace) | Readiness audit (ThesisTrace) |
|---|---|---|
| Question | "What does the literature say about X?" | "Should we build on this paper, and what is missing?" |
| Unit of work | A corpus of papers | One artifact: paper, patent or technical report |
| Output | Answers, summaries, agreements/contradictions | Verdicts, audit receipts, TRL, gaps, next steps |
| Buyer | Researcher exploring a field | Supervisor, tech-transfer office, R&D scout, founder |
| Success | You found the relevant work | You avoided building on an unsupported claim |

Both are legitimate. They are not substitutes. A customer can use PaperLens in the morning
to map a field and ThesisTrace in the afternoon to screen one paper before a go/no-go
meeting.

---

## 2. Feature matrix

Competitor cells reflect public product descriptions as of November 2026 and must be
re-verified before the viva. "Partial" means the capability is reachable through generic
extraction or chat, not a dedicated workflow.

| Capability | ThesisTrace | PaperLens | Elicit | SciSpace | Scite | Consensus | General chatbots |
|---|---|---|---|---|---|---|---|
| Multi-paper synthesis | No (deliberate) | Yes | Yes | Partial | Partial | Yes | Partial |
| Cross-paper agreement / contradiction | Partial (Portfolio, same claim only) | Yes | No | No | Partial (citation context) | Partial | No |
| Claim checked against the paper's own evidence | Yes | Partial | Partial | Partial | No | No | Partial |
| Page-referenced citations | Yes | Yes | Partial | Yes | Yes | Yes | Partial |
| Machine-readable verdict receipt | Yes | No | No | No | No | No | No |
| Reproducibility audit (12 signals) | Yes | No | No | No | No | No | No |
| TRL 1–9 readiness with cited evidence | Yes | No | No | No | No | No | No |
| Roadmap to the next readiness level | Yes | No | No | No | No | No | No |
| Runs locally, no API key | Yes | No | No | No | No | No | No |
| Deterministic verdicts (LLM never decides) | Yes | No | No | No | No | No | No |
| Published evaluation with N | Partial (seed set, N=15) | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown |

**Where PaperLens wins:** breadth. It can answer a question across many papers and find
agreements and contradictions at corpus scale. ThesisTrace does not do this and should not
pretend to.

**Where ThesisTrace wins:** it turns one paper into a decision with an auditable trail. No
competitor in this table ships a readiness level, a reproducibility audit, or a receipt
that a reviewer can re-check.

---

## 3. Positioning map

```
                        DECIDE
                           ^
                           |
              ThesisTrace  |        (empty: decision tools
          (depth + audit)  |         for a single artifact)
                           |
   NARROW <----------------+----------------> BROAD
   (one paper)             |             (a literature)
                           |
          Scite / Consensus |     PaperLens / Elicit / SciSpace
          (citation signal) |     (search + synthesis)
                           |
                         READ
```

The top-left quadrant is the wedge: narrow scope, decision output. It is empty because the
incumbents optimised for search and synthesis, and the readiness question does not fit their
unit of work.

---

## 4. Win / loss scenarios

**Win — thesis submission screening.** A supervisor has 20 submissions and one hour. A
summary does not help; a TRL range, a reproducibility score and the three unsupported claims
do. PaperLens would require reading its synthesis and still not produce the score.

**Win — tech-transfer triage.** An office screens 60 disclosures a year. They need a
defensible readiness level and the gaps that block licensing. An answer engine gives them
prose; ThesisTrace gives them a report with page citations and a next-step list.

**Win — one paper, three stakeholders.** A lab reads the same paper for different reasons:
the researcher wants the open question, the engineer wants the missing seed and environment,
and the business lead wants the next milestone. The three decision lenses give each reader
the same evidence with a different emphasis, instead of three separate summaries that drift
apart. PaperLens has no role-specific view; it has one synthesis for everyone.

**Lose — "what is the state of the art in X?"** PaperLens is the right tool. Do not demo
against this question. Concede it explicitly on the comparison slide; judges reward a
positioning that knows its boundary.

**Lose — "just ask GPT-5 with citations".** A general model can produce a plausible verdict
and a page number. It cannot show the retrieval score, the NLI probabilities, the threshold,
the model version and the abstain reason. If the buyer only wants prose, a chatbot wins on
convenience. The Trust Ledger is the answer, and it must be visible in the demo.

---

## 5. If PaperLens adds readiness

They can copy the label. They cannot copy the calibration quickly. The defence is the
evaluation asset:

1. **A labelled benchmark.** Claim–evidence pairs plus TRL labels with two raters and
   reported agreement. A competitor shipping TRL without calibration is selling a vibe.
2. **Receipts as a workflow.** Once a thesis appendix or a diligence memo cites a receipt,
   switching cost is not the feature, it is the audit trail.
3. **Local deployment.** Labs and companies that cannot send unpublished papers to a SaaS
   are a segment PaperLens cannot serve without a self-hosted build.

The honest risk: a well-funded incumbent can ship a "readiness score" in a quarter. The
answer is not to out-feature them; it is to own the calibration and the institutional
workflow.

---

## 6. Beachhead choice

The pitch deck lists four segments. For a 10-day plan, pick one:

- **Adoption beachhead:** master's and PhD students writing a literature review or thesis.
  They feel the pain weekly, the product is free to try, and they generate word of mouth.
- **Revenue beachhead:** one research lab or tech-transfer office that pays per seat for
  reproducibility and readiness reports.

Students create usage; labs create revenue. Do not try to sell to enterprises in this
semester. The viva answer is: "students for adoption, labs for revenue, institutions later."

---

## 7. What to verify before presenting

- Every competitor cell in the matrix (public demos or documentation).
- Whether PaperLens is free, freemium or paid, and its actual limit.
- Whether any incumbent already exports a reproducibility checklist.
- One sentence from a real user in each beachhead, once the interviews are done.

No external links belong in this document or the deck. Cite sources by name and date.
