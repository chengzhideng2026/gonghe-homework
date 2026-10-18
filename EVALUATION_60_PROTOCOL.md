# 60-Case Independent Evaluation Protocol

**Status: preflight / suite construction.** This document is the publicly reviewable **test protocol and coverage plan**, **not** a claim that 60 model cases have run. The reviewer can verify evidence from [existing evaluated case families](EVALUATION_EVIDENCE.md), and later verify an independently frozen 60-case first-sample report. [Original homework rubric](ORIGINAL_README.md).

## Objective

Validate the actual ERPNext Agent as a business system—not just its transport functions—against real seeded ERP facts, ambiguous user requests, cross-document joins, repeat turns, and forbidden/unsafe writes.

Keep these three layers distinct:

1. **Code contract CI:** 234 passing unit/contract tests on candidate `3636ddb2` (separate from business questions).
2. **Historic actual-model evaluations:** E, H, C, S, J/B, R, N and FNL have version-pinned original evidence; these are already documented and must **not be added across code SHAs to manufacture a pass rate**.
3. **Unified 60-case first-sample business evaluation:** **not yet run**. Once frozen, it must execute on **one exact candidate SHA**, same model parameters, same ERP seed/reference date, independent read-only Oracle, predeclared grading, and no best-of-N resampling.

## Coverage manifest / 60-case allocation

Existing **46 potential source cases**:

| Source | Candidate identifiers | Count | Emphasis |
|---|---|---:|---|
| Original assignment | `O01–O10` | 10 | Stock, PO/customer ranking, Work Order shortages, BOM margin, overdue AR, safe PO create-preview/approval, graceful missing data |
| E series | `E01–E08` | 8 | Stock + on order + reserves, user ambiguity, multi-turn procurement and date/account scope |
| H series | `H01–H10` | 10 | Evidence boundaries, units, actual payments, no fabricated pricing / FX |
| C series | `C01–C06` | 6 | Unknown DocType, parent-child joins, missing/partial read, multi-turn resolution |
| Final new business | `FNL-01–FNL-12` | 12 | Real ERP business joins, payment `references`, mixed shortage / ordered stock, follow-up |
| **Source total** |  | **46** | **Source candidates, not 46 guaranteed distinct questions** |

The **actual independent evaluator's original PLAN.json** specifies the following de-duplication groups **before final model scoring** (6 eliminated, 40 retained). This source is preserved in the evaluator's separate workspace; the rules below are the published protocol, not a model-generated best-case selection:

| Overlap cluster | Keep | Exclude | Removed |
|---|---|---|---:|
| `E01 / H01 / FNL-01` | `FNL-01` | `E01, H01` | 2 |
| `E02 / FNL-03` | `FNL-03` | `E02` | 1 |
| `H04 / C01` | `C01` | `H04` | 1 |
| `O04 / FNL-02` | `FNL-02` | `O04` | 1 |
| `O08 / C06` | `C06` | `O08` | 1 |
| **Total** | | | **6** |

The private evaluator's recorded source-file hashes and dedup decisions are fixed inputs; confirm the original files still match them before freezing any scored suite. The resulting **40 historical slots are defined**, but their independent ground truth still needs reconciliation for this new unified run.

**The 20 new case drafts are also already written in the evaluator's original PLAN.json** with `oracle_status=pending_independent_GET_validation` and `model_executed=false`. Preserve the original scenario definitions and natural-language questions; **do not invent or substitute a different G01–G20 suite**:

| IDs | Original independent-plan dimensions | Count |
|---|---|---:|
| `G01–G04` | AR aging buckets; customer concentration and aging; actual cash-flow events; bounded cash forecast | 4 |
| `G05–G08` | Item/Bin/BOM valuation provenance; realized margin at cost-date; supplier delivery facts; partial receipts | 4 |
| `G09–G12` | Item Group category completeness; reverse BOM dependencies; order-to-invoice linkage; manufacturing vs customer demand | 4 |
| `G13–G16` | Two-basis replenishment; unfamiliar quality DocType; purchase returns and net amount; credit notes / sales returns | 4 |
| `G17–G20` | Payable terms and due dates; stock-ledger history; effective-date price lists; proposal-change confirmation | 4 |
| **Total** | | **20** |

The independent evaluator already saved exact draft questions for all twenty slots; the remaining work is **ERP-based Oracle verification/freeze and scored execution**, not an entirely new test-design exercise. The private original PLAN.json and EVALUATION_PLAN.md should remain the source of truth.

## Freeze-before-run gate

The test thread must produce **before any scored model call**:

- `questions_only.json`: 60 stable cases, actual user-turn texts, scenario ID, reference date; no expected answers, secret keys or Oracle attached.
- `oracle_private.json`: independent sources, explicit ERP filters/fields/parent child-row evidence, expected core facts, acceptable alternative descriptions and disallowed actions; **keep outside the public repo before evaluation**.
- `manifest.json`: the exact predefined 40 source IDs and six excluded duplicates with original evaluator evidence, 20 newly authored IDs, per-case `question_sha256`, full file SHA256s, selected Git commit, ERP baseline snapshot, model configuration, USD cost controls, dates and grading policy.
- `preflight.json`: confirm all required source files exist, **60 unique case IDs and question texts** (or documented valid near-neighbor adversarial exceptions), Oracle complete, 60 cases actually grounded, `main-v2` versus PR candidate explicit, safe ERP transport and enough provider quota.
- Separate `grading_policy.md` defined in advance: core PASS/PARTIAL/FAIL; full PASS/PARTIAL/FAIL; exception/timeout/rejected/blocked/unrun separately; **unjustified definitive factual claim → full-answer downgrade**; safety policy violations cannot be hidden by other passes.

**Do not run a claimed 60-case benchmark when any freeze/preflight gate fails.** In that event, return an **inventory and gap report** instead of a fabricated 60-case score.

## Independent execution, resource and write safety

- Fix one **exact Git SHA** for all 60 cases; independent `git worktree add --detach`, verify SHA and clean tree. **Never** move the evaluation target mid-run.
- Hold reference date `2025-10-15`; capture actual model ID, temperature, thinking parameters and API limits. Existing independent test model is `qwen3.8-max`, temperature `0`, thinking budget `4096`.
- **Hard-block ERP POST/PUT/PATCH/DELETE and RPC writes in transport**, log method attempts, and compare relevant Purchase Order identifiers/status before and after. Any attempted write triggers a safety failure and stops the current test; do not execute `/confirm` in the scored suite.
- The prior evaluator's per-batch limits were **80 model calls / 240 ERP GET / 1800 seconds / USD20 reservation**, not a guaranteed 60-case capacity. **Use six batches of ten questions** with independently reset limits; record each case's original first attempt and a single combined report for the same SHA. If a batch exceeds limits, preserve the failure and mark cases unrun rather than silently moving them to a permissive protocol.
- Oracle and expected answers **must never** enter system/user/tool payloads seen by the candidate Agent. The evaluator may compare outputs against private Oracle **after** completion, with raw evidence retained outside the public repo.
- Record `tool_calls`, `tool_receipts`, source scope, complete/has_more, partial failure, `actual_usage`, observed ERP HTTP methods, and error types. Do not score `completed` alone as business PASS.
- If model output is unsafe but rejected by an evidence checker, distinguish **safe fail-closed behavior** from **usable final answer**. If the final answer is missing, full-answer **FAIL** even though unauthorized writes remain zero.
- No hand-adjusted Oracle, rewritten questions, hidden resampling, or replacement of first attempts with more favorable second runs.

## Reviewer-facing release report (after execution)

Publish a **redacted, source-backed** [EVALUATION_EVIDENCE.md](EVALUATION_EVIDENCE.md) update containing: fixed candidate SHA; 60 frozen-case inventory checksum; actual N executed, counts of PASS/PARTIAL/FAIL/EXCEPTION/UNRUN for **core and full** outcomes; per-case ID / category / status / evidence summary; mean/p95 model turns and ERP GET counts **only if actually computed**; correct no-write audit; and representative success and failure traces with sensitive ERP values/keys redacted.

Publish `questions_only.json` after the scored freeze if acceptable for reviewer reproducibility, but keep the private pre-run Oracle, model raw HTTP payloads, credentials and unredacted business traces out of the public repository. **A comprehensive, honest, independently reproducible evaluation is a stronger engineering signal than an invented aggregate passing percentage.**

The initial implementation and evaluation history is preserved in [AUDIT.md](AUDIT.md), [BUSINESS_ACCEPTANCE.md](BUSINESS_ACCEPTANCE.md), and the [evidence/](evidence/) tree. Actual scored results override neither historical initial failures nor code-only unit test counts.
