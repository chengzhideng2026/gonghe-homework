# Latest candidate independent six-case directed regression — pending review

**Candidate SHA:** `f11d6c09e9c3e328a191bd532f7b85e822b6db76` on unmerged [PR #4](https://github.com/chengzhideng2026/gonghe-homework/pull/4).

**Evidence status:** operator console excerpt from the first attempt at `D:\work\gonghe-targeted-bd86c93\attempt1_20261018T171421_cdedf915`; the detailed `completed.json` and raw traces remain local. This is an independent *directed regression*, not a blind benchmark or graded 6/6 PASS. Code branch still awaits release approval.

| Case | Runner status | Model calls | Agent ERP HTTP |
|---|---|---:|---:|
| FNL-12 | **exception** (cause not yet inspected) | 6 | 4 |
| FNL-02 | completed (business grading pending) | 5 | 3 |
| FNL-07 | completed (business grading pending) | 5 | 6 |
| E07 | completed (business grading pending) | 1 | 0 |
| E08 | completed (business grading pending) | 2 | 3 |
| H08 | completed (business grading pending) | 3 | 2 |
| **Total** | **5 completed; 1 exception** | **22** | **18** |

**Read-only guard:** `erp_before_after_equal: true`; recorded ERP HTTP methods: GET 18, POST/PUT/PATCH/DELETE 0; blocked ERP write attempts 0. Full purchase-order snapshot before/after verified equal by the evaluator; this does **not** test real `/confirm` or server-side idempotency. `reserved_cost_usd: 2.069908` is an internal cost reservation, not an actual provider invoice.

**Release gate remains open:** inspect the exact FNL-12 exception, verify FNL-02 warehouse reservation scope, FNL-07 parent `Payment Entry.references` evidence and invoice reconciliation, and manually grade E07/E08/H08 from their first answers. Preserve the original run and do not resample and relabel the first attempt as passed. Update this report with a review of the raw, redacted tool evidence before merging either PR.

## 后续审查

已取得本次完整的 `completed.json` 和 `raw/run.json` 并逐题核对；第一次结果及 FNL-12 exception 保留不改。人工业务审查判定与第二次修复证据参见 [逐题复盘](DIRECTED_SIX_CASE_BD86_REVIEW_20261018.md)。后续代码 SHA `f11d6c09` 231 项离线 CI 通过，尚需重新真实模型验证。
