# Validation Plan

**Purpose:** replace the assumptions in [Business-Plan.md](Business-Plan.md) with evidence.
Nothing here requires money, infrastructure or a recruited team.

**Rule:** record raw notes, not impressions. Every claim in the deck should trace to a
quote, a count or a measured number.

---

## 1. Three experiments with pass/fail thresholds

### E1 — Problem salience (survey, N ≥ 30)

Recruit thesis writers and research assistants. Ask:

1. How many papers do you read in a typical week?
2. How many hours per week do you spend checking whether a claim is actually supported?
3. Which three frustrations are largest when reading a paper? (rank)
4. Have you ever cited something you later found was not supported by its own evidence?
5. What do you currently use for this? (chatbot, spreadsheet, nothing)

**Pass:** ≥40% report more than three hours per week and rank claim checking in their top
three. **Fail:** treat the problem as a lab/tech-transfer pain instead of a student pain.

### E2 — Willingness to pay (12–15 interviews)

Show the product, then ask the Van Westendorp set:

- At what monthly price would this be too expensive to consider?
- At what price would it be a bargain?
- At what price does it feel expensive but still worth considering?
- At what price is it so cheap you doubt the quality?

Then ask directly: "Would you pay $6/month for this today? If not, what would need to
change?" For labs: "Would your group pay $8/seat/month for reproducibility reports?"

**Pass:** ≥4 of 12 individuals say yes, or one lab commits to a paid pilot. **Fail:** keep a
free student tool and sell reports to labs.

### E3 — Readiness agreement (20–25 papers, two raters)

Two people independently assign TRL 1–9 to the same papers using the public TRL
definitions, blind to the model output. Report exact agreement, within-±1 agreement, MAE
and Cohen's kappa. Then compare the rubric.

**Pass:** ≥70% within ±1 and MAE ≤ 1.0. **Fail:** do not claim readiness; present the
rubric as an assistive signal and sell the evidence audit.

**Current gap:** the shipped gold set has 11 synthetic regression cases labelled by the
developer. That is not E3. Recruit the two raters.

---

## 2. Interview script (30 minutes)

Warm-up

1. What are you working on right now?
2. Walk me through the last paper you read closely.

Current behaviour

3. How did you decide whether to trust its main result?
4. What did you do with the claims you could not verify?
5. Have you tried a tool for this? What happened?
6. How long did the last literature review take?

Pain and cost

7. What is the worst part of that process?
8. What happens if you miss an unsupported claim? Has that happened?
9. Who else is affected by that mistake?

Product reaction (show the sample analysis, then the receipt)

10. What would you use first? What would you ignore?
11. Does the receipt make the verdict more or less believable? Why?
12. What would make you stop using this after a week?

Close

13. May I follow up when the pilot opens?
14. Who else should I talk to?

**Do not pitch during questions 1–9.** Record verbatim quotes for the three strongest
pains. Tag each interview with role, field, and willingness to pay.

---

## 3. Survey (N ≥ 30, 8 questions)

1. Role: master's / PhD / postdoc / supervisor / industry researcher.
2. Papers read per week.
3. Hours per week checking claims or reproducibility details.
4. Rank three frustrations when reading a paper.
5. Have you cited a claim later found unsupported? Yes / no / unsure.
6. Current tools used.
7. Would you pay $6/month for claim checks + readiness? Yes / no / maybe.
8. What is missing from the tools you use?

Report counts and percentages with N. No inferential statistics needed.

---

## 4. Pilot design (one lab, eight weeks)

**Setup:** 5 seats, one research group, papers from their own reading list. Local deployment
or private instance. Weekly 15-minute check-in.

**Metrics**

| Metric | Target |
|---|---|
| Weekly active seats | ≥3 of 5 |
| Papers analysed per month | ≥20 |
| Reports exported and used in a review | ≥3 |
| Median time from upload to decision | ≤60 s |
| Unsupported claims the lab says they would have missed | ≥2 documented |
| Would renew at $8/seat | yes / no |

**Exit:** a written one-page case study with numbers and two quotes, or a documented no.

---

## 5. Privacy and ethics

- Tell interviewees what is recorded and get consent.
- Do not upload other people's unpublished papers without permission.
- The app stores uploads locally and deletes them by retention policy; state this in the
  consent note.
- Anonymise quotes in the deck unless the person agrees to be named.

---

## 6. Demo script (90 seconds)

1. "A paper claims a 42% latency reduction. Is that its own evidence?" Upload.
2. Open Claims. Point at Supported and Unverified side by side.
3. Expand the receipt: retrieval score, NLI probabilities, threshold, model version.
4. Open Readiness: "TRL 4, and here is what blocks level 5."
5. Open Portfolio: "These two papers make the same claim and disagree."
6. Close: "PaperLens tells you what the literature says. We tell you whether to build on it."

Rehearse twice. Record a backup video. Have a second paper ready in case the upload fails.
