# Evaluation evidence index

This page indexes **historical real-model business trials**, **live ERP integration checks**, and **offline code regressions** separately. A trial recorded on one commit is **not** automatically a pass on a later commit. The numbers below are not the recruiter's held-out test score.

## A. Historical real-model evaluation families

| Suite | Size and basis | Reported core / full-answer outcomes | Source and caveat |
|---|---|---|---|
| E01–E08 | 8 developer-stage independent variants; fixed reference date, question-only model input | Final historical rerun: **8/8 core, 6/8 full** | [Follow-up review](evidence/FOLLOWUP_REVIEW.md), [raw full rerun](evidence/variants_followup.json), [questions](review_cases.json); later targeted reruns must not be substituted for initial scores |
| H01–H10 | 10 scoring-oriented variants, tested on an **earlier 7-tool application** | **10/10 core, 7/10 full** | [Review](evidence/SCORING_REVIEW.md), [raw baseline](evidence/scoring_baseline.json), [questions](scoring_cases.json); not strict blind / not same SHA as current main |
| C01–C06 | 6 closeout scenarios including unknown DocType, child join, partial failure, cross-turn calculation, empty scope | Following correction of the original C02 test assumption: **6/6 core, 4/6 full** | [Business acceptance](BUSINESS_ACCEPTANCE.md), [per-case review](evidence/closeout_review.json). C02 initial and corrected runs are distinct records of *one scenario*, not two passes |
| S01–S03 | 3 scope-routing tests (out-of-domain and mixed) | **3/3 scope/core, 2/3 full** | [Scoring-stage review](evidence/SCORING_REVIEW.md), [raw](evidence/scope_acceptance.json), [questions](scope_cases.json); targeted, not a calibrated classifier benchmark |
| J01, B01 | 2 targeted child-join and partial batch-read scenarios | Both core pass; J01 full pass and B01 full partial | [Scoring-stage review](evidence/SCORING_REVIEW.md), [batch raw](evidence/batch_acceptance.json), [join ERP proof](evidence/join_and_currency_live.json). These do not increase H-suite pass percentage |
| R01–R03 | 3 boundary scenarios, with before/after multi-turn records | Mixed: known overstatement and date errors preserved; no aggregated passing headline | [Boundary review](evidence/ANSWER_BOUNDARIES_REVIEW.md), [raw after](evidence/answer_boundaries_after.json), [date follow-up](evidence/INVOICE_DATE_REVIEW.md) |
| N05, N07 | 2 independent pressure cases on subgroup totals and child-line statistics | Targeted repaired runs reached correct business result; older initial faults retained | [Review](evidence/N05_N07_REVIEW.md), [structured review](evidence/n05_n07_review.json). The independent later first-runs for a newer SHA are tracked separately; **not** 10/10 in one SHA |

The E/H/C/S/J/B/R/N family names above represent **34 labelled business scenarios** (8 + 10 + 6 + 3 + 2 + 3 + 2), not 34 independent hidden tests. Some themes and business documents overlap across suites. Other focused real-model rounds (e.g. invoice dates, tool registration, and three-turn interaction) are available in the historical audit but intentionally **not added** to a fabricated grand total.

## B. Mechanical tests are not model-answer scores

| Layer | What is actually supported |
|---|---|
| Unit and protocol regression | Original application `5fe679e`: 170 tests; nine-tool reviewed `main-v2` PR #2: **190/190 on GitHub Actions** ([PR #2](https://github.com/chengzhideng2026/gonghe-homework/pull/2)). A later code-candidate PR may have a different count; always check its SHA and CI log |
| ERP REST contract tests | **19** live REST checks on various historical stages; e.g. [read-only integration record](evidence/live_read.json). These do not involve model reasoning |
| Write-side evidence | Historical purchase preview, explicit user confirmation, draft creation and GET read-back have recorded tests; newer business evaluations typically forbid POST. No cross-host exactly-once claim; see [write-path design](RECOVERY_AND_DESIGN.md) |
| Source and error handling | Model-tool receipts, query scope, raw join-vs-parent counts, decimal calculations, date comparison, partial-result flags, and read/call-budget controls have dedicated evidence in [AUDIT](AUDIT.md) |

## C. How to publish a defensible final score

1. **Freeze one target commit SHA** after final candidate review; record provider, model, thinking settings, temperature, prompts, business reference date, ERP seed state, and limits.
2. Construct a numbered **single-version** bank: original homework questions, E/H/C regression questions, final independent FNL cases (if their source/oracle can be archived safely), and new **unseen** generalization cases. Record overlaps/duplicate wordings instead of counting them as separate independent coverage.
3. Freeze business oracles and grading rubric *before* model calls. Only question text goes to Agent. Distinguish answer correctness from transport errors, script persistence failures and budget-unrun cases.
4. One first pass for each case on the **same SHA** with no repeated sampling to select good answers; any targeted repair/retest is a separate phase, never silently spliced into the first-pass headline.
5. Score core and whole-answer separately (PASS / PARTIAL / FAIL / not-run), and report invalid or missing evidence. Preserve attempts, tool traces, per-case ERP GET/POST, model requests, provider token usage (if supplied), time, read scope and purchase-name audit.
6. Publish a compact summary with **denominator, commit, seed, executed count, result table, and raw evidence manifest**. Older E/H/C runs are regressions and historical context, not substitutes for running the final candidate.

Current external FNL frozen-suite results have been discussed during final review, but its locally stored evidence has **not** been committed to this public repository. It is deliberately **excluded from the public-reproducible scores above**. The same applies to any old outside-worktree report until linked and inspected.

**Interpretation:** Many tests have been performed; a single **final-commit, reproducible, real-model** benchmark score is still a separate deliverable. More test cases do not prove a higher hidden-test success rate, especially when the sets differ in difficulty, grading and model provider.
