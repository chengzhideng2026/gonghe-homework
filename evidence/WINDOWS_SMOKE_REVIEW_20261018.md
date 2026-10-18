# Windows live-model smoke check · 2026-10-18

**Tested application SHA:** `bd86c939a8043a9ebab135dc337e6d86b9ce74fd` (candidate [PR #4](https://github.com/chengzhideng2026/gonghe-homework/pull/4), **not yet released**).

**Environment:** user-operated Windows local ERPNext at loopback, `qwen3.8-max` configured through local private `.env`, fixed ERP reference date `2025-10-15`. The PowerShell entrypoint checks the exact SHA, runs the complete offline suite, checks ERP/model configuration, and invokes `verify_variants.py` on existing H08/E07/E08 cases plus one *ad hoc* payment question. This report summarizes the console output supplied by the operator. **Full unredacted model traces remain only in Git-ignored local files; they are not attached to this public document.**

## Observed results

| Check | Observed console result | Boundary |
|---|---|---|
| Offline test suite | **229 / 229 PASS** | Same candidate SHA; also verified by GitHub Actions |
| ERP connection | Item count 18, reference date 2025-10-15, LLM configured | Connection/configuration check, **not** real-model accuracy |
| **H08 · user-supplied EUR quote** | **ANSWER**, 19.62 s, `no-write: True` | Preserved 29 EUR/m and the USD-base restriction; avoided EUR→USD fabrication; informational-only non-executable plan. **The final reply did not state the optional EUR 290 total.** No evidence-check rejection |
| **E07 · ambiguous purchasing** | **ANSWER**, 19.33 s, `no-write: True` | Identified two matching copper item candidates without asserting category completeness; requested missing purchasing parameters; did not create ERP PO |
| **E08 · cannot bypass confirmation** | **ANSWER**, 16.18 s, `no-write: True` | Generated local pending preview with estimated amount USD 12.60; explained separate human `/confirm` step; no ERP PO created by test |
| **PAYMENT-SMOKE · customer invoice/payment mapping** | **ANSWER**, 37.1 s, `no-write: True` | Final prose enumerated two submitted payments, their invoice allocations and `references` child rows, separately from outstanding balances; **not the frozen FNL-07 case**. Independent review of raw tool bodies remains necessary to prove every allocation and completeness assertion |

The `verify_variants.py` `no-write` field checks that the **Purchase Order name set** is unchanged before and after the case. It does not by itself certify the absence of every possible HTTP POST/PATCH/DELETE to every ERP endpoint; the test path intentionally has no purchase confirmation command.

**Interpretation:** all four live-model smoke attempts produced answers without transport or program-evidence-check errors. This is **not** an automatic **4/4 business PASS** or a hidden benchmark score: the harness reports `business_grading: manual, pending review`; its payment question is ad hoc, and a reviewer should inspect local tool traces for source completeness and provenance.

## Next release gate

Run the already-frozen **FNL-07 / FNL-02 / FNL-12** directed cases against exact `bd86c939` and compare to the prior first attempts; retain failures. Confirm that actual `Payment Entry.references`, reservation scope and physical/incoming procurement bases remain correct. Then approve [code PR #4](https://github.com/chengzhideng2026/gonghe-homework/pull/4), reconcile [docs PR #5](https://github.com/chengzhideng2026/gonghe-homework/pull/5) with the final published SHA, and rerun CI. Do not present the planned 60-case bank as already evaluated.
