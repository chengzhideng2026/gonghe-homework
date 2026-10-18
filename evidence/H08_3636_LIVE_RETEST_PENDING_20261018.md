# H08 FX quote: read-only live-model retest — known false rejection

**Tested code:** `3636ddb2e10a285421c5580891fd50e6d09939c9` on the unmerged hardening PR #4.
**First attempt:** 2026-10-18, independent H08-only `qwen3.8-max` directed regression. Private evidence root:
`D:\work\gonghe-targeted-3636ddb\attempt1_20261018T180339_4785206a`.
The operator supplied the full redacted `completed.json`, including both assistant drafts, tool bodies and program repair feedback; this report is based on that content (not just console status). The original first sample remains unchanged.

## Exact failure

1. The Agent fetched the exact `Item` `RM-COIL-CU-2.0` (stock UOM `Meter`) and `Supplier` `Tongling Magnet Wire Co.` successfully (2 ERP GET).
2. **First draft:** correctly attributed **29 EUR/m** and 10 m to the **user**, rejected treating EUR as USD or inventing an exchange rate, and emitted only a **non-executable** preliminary plan with **290 EUR = 10×29** in its table. It had **not called `calculate`** before publishing the derived subtotal, so the program's initial request for deterministic calculation was **justified**.
3. The evidence checker sent a single repair instruction asking for quoted-source and calculation evidence. The model called `calculate("10 * 29")`, which returned `290`.
4. **Second draft:** properly separated verified ERP facts, user-provided quote, deterministic 290 EUR subtotal, pending USD conversion and absence of an ERP proposal. However the answer **repeated `290 EUR` as an unqualified amount cell in a later Markdown table**. The narrow `answer_checks.py` currency guard treats that table cell in isolation and loses the source heading / current calculation attribution. It rejected the entire response a second time. The runner raised `RuntimeError: Answer failed the evidence check after one repair`; **no final answer was returned**.
5. There was **no** ERP order preview tool call, `/confirm`, currency exchange, foreign-currency-to-USD coercion or ERP write. Pre/post purchase-order sets match.

**Assessment:** this is **answer availability / a provenance-format false positive after valid calculation**, **not** unauthorized purchasing or numeric corruption. The initial feedback correctly enforced calculation discipline; the *second* refusal discarded an otherwise correctly bounded business response. It remains a real **FAIL/exception** in business grading, not a PASS.

## Reproducibility and scope

- Candidate SHA `3636ddb2`, model `qwen3.8-max`, thinking budget 4096, temperature 0, reference date `2025-10-15`.
- The independent run used **4 model requests**, **2 ERP GET**, **0 ERP POST/PUT/PATCH/DELETE**; `blocked_erp_writes=0`; before/after PO snapshots equal. The reported USD 0.360498 is budget reserved, **not** actual billed cost.
- On the **earlier** `f11d6c09` first sample, a deterministic replay against `3636ddb2` had reported `REPLAY_GATE: PASS` for the old first H08 draft. The new model answer is different, so that replay cannot be treated as new actual-model success.
- The current code has **234/234 offline tests** passing. Offline tests prove those scenarios' program contracts, not this variable model response format.
- The team accepted this limitation for this take-home release rather than endlessly expanding generic text regexes. No claim of H08 live pass or 6/6 score should be made.

**Potential future remediation, not implemented:** keep the source/currency identity as structured evidence attached to `calculate` results and table columns rather than recognizing source solely from adjacent free-form language; add case-driven negative tests for forged amounts before any release. This should be a bounded new change, not a last-minute unverified regex relaxation.
