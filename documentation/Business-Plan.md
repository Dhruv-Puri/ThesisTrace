# Business Plan

**Status:** a plan with explicit assumptions, not a forecast. Every number marked
*assumption* must be replaced with a measured or sourced value before the viva. The
evaluation numbers in section 6 are measured on this checkout.

---

## 1. Lean canvas

| Block | Content |
|---|---|
| Problem | A paper's headline claim can be cited without anyone checking whether its own evidence supports it, whether it can be rebuilt, or how close it is to use. |
| Customer segments | (1) Thesis and literature-review writers; (2) supervisors and research labs; (3) tech-transfer and R&D scouting; (4) deep-tech founders and investors. |
| Unique value proposition | Turn one paper into an evidence audit and a readiness decision, with a receipt behind every verdict. |
| Solution | Claim verdicts + reproducibility audit + TRL + gaps + cited report + portfolio comparison. |
| Channels | Supervisor recommendation, university library/workshop, open local demo, conference and thesis-community content. |
| Revenue streams | Student subscription, researcher subscription, per-seat lab licence, self-hosted institutional licence, API. |
| Cost structure | CPU compute (small), model downloads (one-off), support and content (dominant), payment fees. |
| Key metrics | Papers audited per active user, weekly active labs, reports exported, verdict agreement on the gold set. |
| Unfair advantage | Calibrated evaluation set + audit receipts + local/private deployment. |
| Early adopters | One thesis cohort and one lab pilot, not "all researchers". |

---

## 2. Problem evidence

**What is established:** the category exists and is funded. Elicit, SciSpace, Scite and
Consensus all sell research reading or citation tools, which proves willingness to pay for
saving reading time. PaperLens targets multi-paper synthesis.

**What is not established yet:** that claim verification and readiness are top-three pains
for our beachhead, and what they will pay. Primary research is at **0 of 12 interviews**;
this is the largest gap in the business case and is scheduled in
[Validation-Plan.md](Validation-Plan.md).

Three hypotheses to test:

- **H1 — salience.** Thesis writers spend more than three hours a week checking or
  chasing claims and consider it a top-three friction.
- **H2 — willingness to pay.** At least one third of interviewees would pay about $6/month,
  or their lab would pay about $8/seat/month.
- **H3 — trust gap.** The audit receipt changes a decision: users accept a verdict more
  readily when they can see the retrieval score and NLI probabilities.

Do not put a market-size number on a slide before H1 and H2 have data behind them.

---

## 3. Market sizing (bottom-up)

Top-down figures such as "the research tools market is $2.8B by 2032" are not actionable:
the definition varies by report and says nothing about who will pay $6. The plan uses a
bottom-up identity instead.

```
TAM = reachable research writers × annual price
SAM = writers in the chosen beachhead and language × annual price
SOM = paying seats acquired in 12 months × annual price
```

**Worked example — hypothetical inputs, not market research:**

| Layer | Input (assumption) | Price | Annual value |
|---|---|---|---|
| TAM | 1,000,000 research-active writers worldwide reachable online | $72/yr | $72M |
| SAM | 50,000 thesis writers in Indian universities plus 2,000 labs | $72/yr students; $480/yr for a 5-seat lab | $3.6M + $0.96M |
| SOM (year 1) | 1,200 paying students + 10 labs × 5 seats | as above | $86k + $24k |

Replace the counts with institution or census data and state the source and date. A small,
defensible SOM is stronger than a large, unsourced TAM.

---

## 4. Value metric and pricing

**Value metric:** papers audited, not seats alone. It tracks the work the user actually
does, and it maps to compute cost.

| Tier | Price (proposed) | Included | Why it exists |
|---|---|---|---|
| Free | $0 | 3 papers/month, summary + concepts | Removes friction; the demo is the product. |
| Student | $6/month | 30 papers, ClaimCheck, readiness, Markdown export | The adoption tier. Priced below Elicit. |
| Researcher | $15/month | Fair-use papers, batch, API, priority | The individual power user. |
| Lab / institution | from ~$8/seat/month | Admin, SSO, self-hosted option, volume | The revenue engine. |

Pricing is a hypothesis. Test it with the Van Westendorp questions in the validation plan;
do not defend $6 as if it were discovered.

---

## 5. Unit economics

Measured on this checkout, fallback tier: **15.9 ms per paper** for the corpus documents.
A full model-backed run on a 9-page paper is budgeted at 15–45 s in
[Feasibility-Analysis.md](Feasibility-Analysis.md), but that tier has not been timed yet.

| Item | Value | Basis |
|---|---|---|
| Compute per paper (45 s at $0.05/CPU-hour) | ~$0.0006 | Assumption; measured fallback is effectively zero |
| Model download per machine | one-off, ~1–2 GB | Local/self-hosted |
| Payment fees | ~3% | Typical processor |
| Support per paying user | $0.50–$2.00/month | Assumption; the real cost driver |
| Student ARPU | $6/month | Proposed price |
| Gross margin | >95% on compute; 60–80% after support | Derived |
| CAC (content + campus ambassadors) | $8–$25 | Assumption |
| Monthly churn | 6–10% | Assumption for a student product |
| LTV at $6 ARPU | $60–$100 | ARPU ÷ churn |
| Payback | 2–4 months | CAC ÷ (ARPU × margin) |

The important conclusion is not the exact number: **compute is not the constraint, support
and acquisition are.** That is why the institutional tier matters and why a free tier must
be capped by papers, not by features.

---

## 6. Measured product evidence

From `python eval/run_eval.py --analyze` on the seed set, lexical-fallback tier:

| Metric | Value | N |
|---|---|---|
| Verdict accuracy | 0.667 | 15 |
| Macro-F1 (3 classes) | 0.618 | 15 |
| Retrieval recall@5 | 1.000 | 8 |
| Citation coverage on non-abstained verdicts | 1.000 | 9 |
| Mean pipeline time per paper | 15.9 ms | 7 |
| Peak Python allocation | 0.2 MB | 7 |

**Caveats:** the labels are a developer seed set, not two independent raters; the NLI tier
has not been run with models; the sample is small. These numbers are a starting point and a
regression guard, not a marketing claim. The deck must show N and the caveat on the same
slide.

---

## 7. Go-to-market

**Phase 1 (weeks 1–8): one cohort.** One department, one thesis cohort. Offer a free
workshop, analyse their own papers live, collect 12 interviews and 30 survey responses.
Success: 20 weekly active users, 5 unsolicited referrals.

**Phase 2 (weeks 9–24): one lab pilot.** A lab pays a small pilot fee for 5 seats and
reproducibility reports. Success: 20 papers analysed per month, three exported reports used
in a real review, one renewal conversation.

**Phase 3 (months 6–12): institutional.** Library or tech-transfer office, self-hosted
option, SSO, annual contract. Only after the pilot produces a reference.

Channels, in order: supervisor recommendation, library workshops, thesis-community content,
conference demo. Paid acquisition is out of scope until retention is known.

---

## 8. Twelve-month scenarios (assumptions)

| Scenario | Paying students | Labs (5 seats) | ARR |
|---|---|---|---|
| Conservative | 300 | 3 | ~$30k |
| Base | 1,200 | 10 | ~$110k |
| Upside | 4,000 | 30 | ~$430k |

Inputs: $72/yr student, $480/yr lab, 8% monthly churn, no enterprise contracts. These are
planning assumptions, not predictions. The point of the table is to show which lever matters:
lab seats contribute disproportionately because support cost per seat is lower.

---

## 9. Risks and kill criteria

| Risk | Trigger | Response |
|---|---|---|
| Problem is not salient enough | <15% of 30 surveyed students rank claim checking top-three | Pivot the beachhead to labs/tech transfer |
| Users will not pay | <3 of 12 interviewees would pay $6 | Keep a free student tool, sell reports to labs |
| TRL is not trusted | <70% within ±1 on 20 labelled papers | Do not sell readiness; sell the evidence audit |
| Incumbent ships readiness | Elicit or PaperLens announces TRL | Compete on calibration + local deployment + receipts |
| Model cost or latency | p95 > 60 s on a 4-vCPU VM | Default to the classical tier; models optional |
| Academic data policy | Institution forbids external uploads | Local/self-hosted deployment becomes the pitch |

**Kill criteria for the semester:** if H1 and H2 both fail, stop positioning this as a
student subscription and present it as an institutional audit tool. Do not keep a pricing
slide that the data contradicts.

---

## 10. What must be true for this to be a business

1. Claim verification is a recurring, budgeted pain, not a nice-to-have.
2. The audit receipt is trusted enough to replace manual checking.
3. A lab will pay for a report it can attach to a review.
4. The readiness rubric agrees with expert judgement often enough to defend.
5. Support cost per active user stays below the subscription price.

Every one of these is testable in the next ten days. That is the plan.
