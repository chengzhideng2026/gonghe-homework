# Evaluation Evidence — reproducible test matrix

**Evidence-rich validation across code, ERP and real-model business behavior.** This project has **offline code checks, real ERP REST checks, and actual-LLM business cases**. They validate different things. Historic model cases span **different commits and sometimes overlapping questions**; they cannot be merged into an overall pass rate. The 60-case unified bank is **planned but not run**.

## Executive scorecard

| Layer | Tested version | Observed result | What it proves |
|---|---|---|---|
| **Current published `main-v2`** | `2d6ce5c` | **190/190** GitHub Actions unit/contract tests | Existing merged code passes offline test suite. |
| **Unmerged code hardening [PR #4](https://github.com/chengzhideng2026/gonghe-homework/pull/4)** | `3636ddb2` | **234/234** GitHub Actions unit/contract tests | Tool/checker/recovery contracts at this exact SHA; **not** the real-model business score. |
| **Real ERP REST** | historical client/API revisions | **19/19** scoped read checks in their recorded runs | Actual seed data and interface compatibility, **not** LLM judgment. [REST evidence](evidence/live_read.json) |
| **Six-case real-model directed run** | `f11d6c09` | **5 business-acceptable final answers; H08 exception** (independent AI-assisted review) | FNL-12/02/07 and E07/E08 worked; FX H08 failed to produce a final answer. [Case review](evidence/DIRECTED_SIX_CASE_F11_REVIEW_20261018.md) |
| **H08-only real-model retest** | `3636ddb2` | **exception**, despite correct ERP reads, `calculate(10*29)=290`, **0 ERP writes** | A safe EUR-quote answer can be blocked by the limited evidence checker. [Recorded diagnosis](evidence/H08_3636_LIVE_RETEST_PENDING_20261018.md) |
| **Unified 60-case bank** | **none** | **Not run; no score** | 40 deduplicated historical candidate questions + 20 new generalized cases remain a plan, not released validation. |

For the most recent six-case run, the operator-observed audit was **24 model requests / 21 ERP GET / 0 ERP write requests** with identical pre/post Purchase Order sets. Its runner set `scores=not_assessed`; the five acceptable outcomes are **case-by-case review**, not an official frozen-Oracle 5/6 result. A later isolated H08 test used 4 model calls / 2 GET / 0 ERP writes and ended in `exception` after one answer repair; neither draft was returned as a final answer.

## Business-case coverage (historic, deliberately not combined)

| Series | Scenarios exercised | Recorded core / complete | Evidence / qualification |
|---|---|---|---|
| **E01–E08** | Stock vs incoming, orders, BOM, invoices, ambiguity, purchase preview | **8/8 core; 6/8 complete** | [Review](evidence/FOLLOWUP_REVIEW.md) · [actual model responses](evidence/variants_followup.json). Additional unsupported statements cost completeness. |
| **H01–H10** | Source/boundary adversarial variants: UOM, stock provenance, FX, dates, payment evidence | **10/10 core; 7/10 complete** | [Review](evidence/SCORING_REVIEW.md) · [responses](evidence/scoring_baseline.json). **Older seven-tool SHA**, not today's model score. |
| **C01–C06** | Unknown DocType, child join dedup, missing/partial documents, multi-turn source use | **6/6 core; 4/6 complete** (after correcting C02 question's erroneous oracle) | [Case grades](evidence/closeout_review.json) · [acceptance method](BUSINESS_ACCEPTANCE.md). Original incorrect C02 expectation not counted as extra case. |
| **S01–S03** | Outside-scope, business-scope and mixed requests | **3/3 core; 2/3 complete** | [Actual model samples](evidence/scope_acceptance.json); a *soft domain prompt*, not calibrated safety classification. |
| **J01 + B01** | Joined child rows vs unique parents; batch details with a missing document | J01 complete PASS; B01 core PASS / complete PARTIAL | [Join/FX REST](evidence/join_and_currency_live.json) · [batch sample](evidence/batch_acceptance.json). |
| **R01–R03** | Historical-movement claims, reference-date/status, pending proposal wording | Mixed PASS/PARTIAL/FAIL, **no combined rate** | [Known boundaries](evidence/ANSWER_BOUNDARIES_REVIEW.md) · [after-run evidence](evidence/answer_boundaries_after.json). |
| **N05/N07** | Wrong subtotal and long child-table statistics | Targeted repaired core behaviors; original failures retained | [Before/after review](evidence/N05_N07_REVIEW.md) · [recorded variants](evidence/n05_n07_review.json). |
| **FNL-01–12** | Independent ERP business tasks including invoice payments and two-turn replenishment | Historical base reported **10/12 core; 9/12 full** | Original independent base was `2d6ce5c`; case questions/oracle held in private evaluator, not presented as public runnable artifact. |
| **FNL-12/02/07 + E07/E08/H08** | Version-pinned six-case regression of business correctness and safety | See below; **not 6/6** | [First attempt on bd86](evidence/DIRECTED_SIX_CASE_BD86_REVIEW_20261018.md) · [next attempt on f11](evidence/DIRECTED_SIX_CASE_F11_REVIEW_20261018.md). |

**What these tests revealed and improved:** a child-join can return two rows for one invoice; a payment's free-text `reference_no` cannot prove an allocation; a Bin reservation aggregate is not an individual Work Order assignment; projected/incoming quantity is not current physical stock; overdue must honor the pinned reference date; unagreed EUR prices cannot be silently treated as USD. The recorded remaining defect is **over-rejection of a safe user-quoted EUR amount**, not unauthorized ERP writing.

## Version-pinned latest six-case evidence

| Case | `bd86c939` first sample | `f11d6c09` first sample | Key business assertion |
|---|---|---|---|
| **FNL-12** | **FAIL** (second-turn checker exception) | **PASS** (reviewed) | Actual 65, incoming 30; physical deficit **35 Nos** vs conditional **5 Nos**; 19 historical rate has unknown ERP currency; **665/95 USD only as user-assumed non-executable estimates**. |
| **FNL-02** | PASS (reviewed) | PASS (reviewed) | Correct shortages **10 Nos / 10 Nos / 10 Meter** and surplus **175 Nos / 155 Nos**, without assuming an order-specific Bin reservation. |
| **FNL-07** | **FAIL** (complete first draft destroyed during checker repair) | **PASS** (reviewed) | Reads `Payment Entry.references`: allocations 6,000 and 7,200; unpaid balances **16,980 USD**, reference-date overdue **12,100 USD**, not yet due **4,880 USD**. |
| **E07** | PASS | PASS | Does not invent a supplier, cheapest quote or quantity. |
| **E08** | PASS | PASS | Local USD 12.60 purchase preview requires separate human `/confirm`; no ERP write. |
| **H08** | PASS | **FAIL** (evidence-check exception) | Safely declined to reinterpret **29 EUR** as **29 USD** without FX agreement. More recent `3636ddb2` H08-only **also failed** to emit a final answer, although it calculated 290 EUR and wrote nothing. |

The PASS/FAIL labels above are **manual full-response reviews** grounded in saved model/tool histories, not the runner's official scoring (the runner recorded `not_assessed`). These attempts run known directed cases and therefore **are not blind/hidden-set results**. Failures are preserved; no best-of-N cherry-picking. The public report summarizes redacted results; sensitive raw HTTP/model payloads remain only in the operator's private local workspace.

## How to reproduce what is actually public

~~~bash
# On an explicitly selected code SHA:
python -m unittest discover -s tests -v
python agent.py --demo
python agent.py --check
# Optional live model/API protocol probe, spends tokens:
python agent.py --check-model
~~~

- **Unit/contract CI**: open the relevant [GitHub Actions](https://github.com/chengzhideng2026/gonghe-homework/actions) run for that SHA; `234` belongs to PR #4, `190` to the merged baseline.
- **Business manual review**: run the seeded ERPNext with [README](README.md), ask [three review questions](README.md#review-three-workflows) in the CLI, and inspect `/trace`. Check evidence, not just whether the command exited with code zero.
- **Private directed evaluator**: historical first-run question SHA, operator's read-only ERP GET/HEAD transport, complete result JSON, pricing assumptions and seed date were saved outside the public repo. Do not represent their summaries as publicly executable test fixtures.
- **Write-path limitation**: offline state-machine/idempotency tests and historical local created-draft/readback evidence exist, but **this latest read-only directed run did not execute `/confirm`**; its 0-write audit cannot prove end-to-end exactly-once delivery.

## Release limitations and planned evaluation

The latest candidate's H08 answer checker can reject a correct response even when the foreign-currency boundary is safe. That reduces **answer availability**, not authorization. The current implementation also does not promise a transactional read snapshot, global ERP-server exactly-once, comprehensive tenant ACLs, or correct handling of arbitrary natural-language unsupported statements. These limitations are acceptance inputs, not hidden guarantees.

The [60-case independent evaluation protocol](EVALUATION_60_PROTOCOL.md) collects original questions (10), E (8), H (10), C (6), and FNL (12): 46 candidate sources, with six **already specified** duplicate exclusions leaving 40 historical cases. The independent evaluator's PLAN.json also has twenty fully drafted G01–G20 questions; the independent Oracle, new freeze manifest and actual unified scored run are still pending. **No frozen independent Oracle or completed all-60 run exists.** Previous estimate of 240–360 model and 400–700 ERP calls is planning only, not measured usage.

Further technical depth: [business grading criteria](BUSINESS_ACCEPTANCE.md) · [architecture](ARCHITECTURE.md) · [prior audit](AUDIT.md) · [H08 exception evidence](evidence/H08_3636_LIVE_RETEST_PENDING_20261018.md).
