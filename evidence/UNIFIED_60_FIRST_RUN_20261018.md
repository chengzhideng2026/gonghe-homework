# Independent 60-Case ERPNext Business Evaluation — First Attempt

**One frozen code SHA. One question/Oracle manifest. Real ERP evidence. No favorable resampling.**

> **Core business acceptance: 55/60 PASS (91.7%). Full-answer acceptance: 50/60 PASS (83.3%).** All 60 questions were attempted exactly once: 59 completed, 1 timed out, 0 unrun. These are *independent evaluator case-by-case evidence reviews*, not employer hidden-set scores, not unit-test pass rates, and not unattended production certification.

| Metric | Independently recorded result |
|---|---|
| Candidate code | `3636ddb2e10a285421c5580891fd50e6d09939c9` · [code PR #4](https://github.com/chengzhideng2026/gonghe-homework/pull/4) |
| Execution | 2026-10-18 10:39:58–10:51:08 UTC; six isolated batches of ten |
| Real model | DashScope `qwen3.8-max`, temperature 0, thinking enabled, budget 4096 |
| Reference date | **2025-10-15**, independent of machine/system date |
| Core grade | **55 PASS · 4 PARTIAL · 0 FAIL · 1 EXCEPTION** (91.7% PASS) |
| Full-answer grade | **50 PASS · 6 PARTIAL · 3 FAIL · 1 EXCEPTION** (83.3% PASS) |
| Model usage | **209 model requests**; 208 returned usage, 1 timeout response usage unknown |
| Returned model tokens | **1,725,399** (1,650,799 input, 74,600 output); excludes unknown timeout usage |
| Agent-side ERP | **298 GET; zero POST/PUT/PATCH/DELETE** |
| Oracle and drift checks | 271 independent preflight GET + 45 post-run drift GET; 14 key-table snapshots and Purchase Order names/status/amounts unchanged |
| Total ERP requests counted | **626 GET** including Oracle, post-run drift and separate batch PO audits; **zero ERP writes** |
| Offline code checks | Separate **234/234** GitHub CI on this exact code SHA |

## What makes the 60-case result meaningful

- **Single-SHA first sample:** all 60 tests ran against the *same* candidate code. Previous E/H/C/FNL results on earlier SHAs were **not** mixed into this score.
- **Frozen questions and independently verified Oracle:** the evaluator retained 40 distinct historical scenarios after five predefined overlap groups (six duplicates removed), plus the original 20 generalized G-series drafts. Independent checks examined 20 DocTypes with complete count/page coverage, required parent/child records, **327 Stock Ledger Entry rows**, and Decimal arithmetic. The Agent was given questions, **not expected answers**.
- **Actual business review:** case grading checked final responses against ERP tool receipts and explicit account, date, company, currency and UOM semantics—not just `status=completed` or phrase matching.
- **Deterministic safety audit:** write-capable ERP methods were blocked by evaluation transport. Purchase Order and 14 key-table before/after states were equal. This proves read-only *evaluation behavior*, **not** that a real human `/confirm` creation/idempotency path was exercised during the 60 tests.
- **Original exceptions preserved:** timeout and partial/failed answers remain in the denominator. FNL-12 was an earlier known regression case and **not fully blind**; the twenty G cases are independently authored generalization tests, **not employer-held-out items**.

Freeze identification (question projection SHA256): `3c5cae04fc16651404d2c6bbc69b056f09ebbc7982f9d1dc7f83f58fa218337a`. Private Oracle, raw model/HTTP events and the question-only payload remain with the independent evaluator, not the public repository. The private manifest is not published as if it were publicly reproducible.

## Breakdown by test family

| Family | Cases | Core PASS / PARTIAL / EXCEPTION | Full PASS / PARTIAL / FAIL / EXCEPTION |
|---|---:|---|---|
| Original-assignment-derived (8 distinct) | 8 | **7 / 1 / 0** | **7 / 1 / 0 / 0** |
| E/H/C/FNL historical distinct cases | 32 | **31 / 1 / 0** | **31 / 0 / 1 / 0** |
| Independently drafted new G01–G20 | 20 | **17 / 2 / 1** | **12 / 5 / 2 / 1** |
| **Total** | **60** | **55 / 4 / 1** | **50 / 6 / 3 / 1** |

The initial ten assignment scenarios are represented: eight original-question slots remained after deduplication, while O04 and O08 were covered by stronger overlapping FNL-02 and C06 scenarios. A clarified question or a safely refused unsupported write may pass its **core** task without proving actual end-to-end execution.

## Demonstrated capabilities with concrete case evidence

| Engineering capability | Observed first-run evidence |
|---|---|
| **Dynamic ERP DocType discovery and recovery** | FNL-08 discovered Work Order; G14 found the Quality Inspection DocType and correctly reported a verified empty set; FNL-03 recovered a bad field (417), FNL-11 recovered unknown DocType (404), and G08 recovered a child-table aggregation error (500) by reading parents. |
| **Accurate cross-document finance** | H09 and FNL-07 read actual `Payment Entry.references` allocations; H03 reviewed 21 invoices; C02 distinguished **2 joined child rows from 1 distinct parent invoice**. |
| **Multilevel manufacturing and cost semantics** | FNL-03 exploded 11 leaf materials without double-counting subassemblies; G10 separated direct/indirect BOM dependencies; G06 used historical Stock Ledger Entry issue costs rather than today's item valuation for realized margin. |
| **Inventory, shortage and conversation state** | FNL-02 correctly distinguished work-order shortages from aggregate warehouse reservations; FNL-12 separated **35 physical shortfall** from **5 after incoming supply**, preserving provenance and provisional non-executable estimates. |
| **Human approval and currency boundary** | O07 and E08 created **local pending previews only**, not ERP orders; E07 sought missing supplier/quantity information. In this unified run **H08 passed both grades**, accepting user-supplied EUR terms without fabricating a USD quote. |

## Five material defects found—not hidden

| Case | Severity and result | Business significance |
|---|---|---|
| **O05** | Core/FULL PARTIAL | Main margin conclusion used a price record effective in **2026** without explicitly treating it as inapplicable to the **2025** reference date. |
| **FNL-04** | Core PARTIAL, full FAIL | Claimed to have verified `Purchase Invoice.bill_no` / payment-to-PO linkage without actually reading Purchase Invoice, despite accurate counts/amounts in other documents. |
| **G13** | Core PARTIAL, full FAIL | Claimed a replenishment-shortfall inequality *always* holds. The two demand targets can differ, so the universal comparison is false. |
| **G16** | Core PARTIAL, full FAIL | Reversed `is_return` semantics and inferred a payment event from outstanding balance without checking payment history. |
| **G11** | EXCEPTION, no final answer | Broad order-to-invoice join reached 30 ERP GET, 7 model requests, **180.128 s timeout** and an over-budget context (190,849 bytes). |

Additional **full-answer-only PARTIAL** cases: G05, G07, G09, G17, G18, involving unverified explanations, over-broad scope descriptions or potentially misleading historical ordering. Their primary business tasks or justified clarification were accepted. Historical isolated H08 runs contained checker false refusals, **but the present 60-case H08 returned a PASS/PASS first-sample result**. Neither result is erased.

## Full per-case scorecard (same run)

`ERP GET` below counts only Agent requests, not Oracle or batch safety reads. All per-case ERP POST counts were **zero**; only G11 did not return a final answer. Case wording and the answer Oracle are intentionally held outside this public report to preserve evaluator separation.

| Case | Core | Full answer | Model calls | ERP GET |
|---|---|---|---:|---:|
| O01 | PASS | PASS | 4 | 4 |
| O02 | PASS | PASS | 4 | 5 |
| O03 | PASS | PASS | 2 | 3 |
| O05 | PARTIAL | PARTIAL | 4 | 2 |
| O06 | PASS | PASS | 2 | 2 |
| O07 | PASS | PASS | 3 | 4 |
| O09 | PASS | PASS | 2 | 1 |
| O10 | PASS | PASS | 3 | 8 |
| E03 | PASS | PASS | 2 | 2 |
| E04 | PASS | PASS | 2 | 3 |
| E05 | PASS | PASS | 4 | 4 |
| E06 | PASS | PASS | 2 | 1 |
| E07 | PASS | PASS | 1 | 0 |
| E08 | PASS | PASS | 2 | 3 |
| H02 | PASS | PASS | 2 | 5 |
| H03 | PASS | PASS | 4 | 5 |
| H05 | PASS | PASS | 3 | 3 |
| H06 | PASS | PASS | 4 | 8 |
| H07 | PASS | PASS | 3 | 2 |
| H08 | PASS | PASS | 1 | 0 |
| H09 | PASS | PASS | 4 | 3 |
| H10 | PASS | PASS | 3 | 3 |
| C01 | PASS | PASS | 2 | 2 |
| C02 | PASS | PASS | 2 | 3 |
| C03 | PASS | PASS | 3 | 2 |
| C04 | PASS | PASS | 2 | 2 |
| C05 | PASS | PASS | 4 | 2 |
| C06 | PASS | PASS | 2 | 2 |
| FNL-01 | PASS | PASS | 5 | 6 |
| FNL-02 | PASS | PASS | 5 | 3 |
| FNL-03 | PASS | PASS | 6 | 5 |
| FNL-04 | PARTIAL | FAIL | 4 | 13 |
| FNL-05 | PASS | PASS | 3 | 3 |
| FNL-06 | PASS | PASS | 4 | 8 |
| FNL-07 | PASS | PASS | 4 | 6 |
| FNL-08 | PASS | PASS | 3 | 3 |
| FNL-09 | PASS | PASS | 4 | 12 |
| FNL-10 | PASS | PASS | 4 | 6 |
| FNL-11 | PASS | PASS | 5 | 6 |
| FNL-12 | PASS | PASS | 6 | 4 |
| G01 | PASS | PASS | 3 | 2 |
| G02 | PASS | PASS | 4 | 5 |
| G03 | PASS | PASS | 5 | 12 |
| G04 | PASS | PASS | 3 | 2 |
| G05 | PASS | PARTIAL | 5 | 4 |
| G06 | PASS | PASS | 5 | 3 |
| G07 | PASS | PARTIAL | 5 | 16 |
| G08 | PASS | PASS | 5 | 11 |
| G09 | PASS | PARTIAL | 4 | 7 |
| G10 | PASS | PASS | 6 | 9 |
| G11 | EXCEPTION | EXCEPTION | 7 | 30 |
| G12 | PASS | PASS | 5 | 7 |
| G13 | PARTIAL | FAIL | 4 | 4 |
| G14 | PASS | PASS | 4 | 4 |
| G15 | PASS | PASS | 3 | 4 |
| G16 | PARTIAL | FAIL | 4 | 7 |
| G17 | PASS | PARTIAL | 3 | 7 |
| G18 | PASS | PARTIAL | 3 | 5 |
| G19 | PASS | PASS | 1 | 0 |
| G20 | PASS | PASS | 1 | 0 |

## Performance / coverage limits

- Six batches of ten were executed under independently reset caps (per batch: up to **80 model requests / 240 ERP GET / 1,800 s / USD 20 reserved**). Actual total was **209 model requests and 298 Agent GET**. This was a bounded **evaluation policy**, not an external model-provider account quota.
- The overlapping batch wall time was **670.893 seconds**; the sum of individual case durations **1,865.742 seconds**. The reported USD **22.382222** was a conservative **reservation estimate**, not a provider invoice.
- G07, G08 and G11 reported `over_budget` context warnings; G07/G08 nevertheless returned answers, G11 timed out. Broad joins and source scans still require better bounded planning for production-scale requests.
- The exact questions included intentional ambiguous inputs: G18/G19/G20 accepted justified requests for missing details; such core acceptance is **not** proof that historical stock, effective pricing or PO-change execution was completed end-to-end.
- Limited text-level provenance checks cannot formally establish every ERP claim. Local SQLite proposal claims do not establish distributed server-side exactly-once; read pagination is not a transaction snapshot. No human `/confirm` was used in this scored suite.

**Release assessment:** technically credible local take-home and human-supervised ERP Agent demonstration; **not** validated for autonomous financial decisions or procurement. Code was not changed or re-sampled during this campaign. Historical case outcomes, prior failures and design evolution remain accessible via [evaluation index](../EVALUATION_EVIDENCE.md) and [original protocol](../EVALUATION_60_PROTOCOL.md).
