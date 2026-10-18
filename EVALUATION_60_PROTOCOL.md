# Unified 60-Case Evaluation: Protocol and Execution

**Status: completed, first attempt, 2026-10-18.** The evaluator froze its independent question/Oracle source before testing. All 60 cases then ran against the **same exact code SHA** `3636ddb2e10a285421c5580891fd50e6d09939c9` without changing that code, rewriting the Oracle or picking favorable resamples.

**Measured outcome: [55/60 core PASS (91.7%) and 50/60 full-answer PASS (83.3%)](evidence/UNIFIED_60_FIRST_RUN_20261018.md).** Zero ERP writes. One wide join timed out. This is an independently constructed business suite, **not** the employer's hidden test set or a fully blind benchmark: certain original and follow-up cases were known during earlier development.

## 1. Fixed 60-question composition

The original independent evaluator's `PLAN.json` contained 46 historical candidates and 20 new G-series drafted questions. Five explicit semantic overlap clusters removed six duplicated items, **before this scored run**:

| Overlap | Kept | Excluded | Removed |
|---|---|---|---:|
| E01, H01, FNL-01 | **FNL-01** | E01, H01 | 2 |
| E02, FNL-03 | **FNL-03** | E02 | 1 |
| H04, C01 | **C01** | H04 | 1 |
| O04, FNL-02 | **FNL-02** | O04 | 1 |
| O08, C06 | **C06** | O08 | 1 |
| **Total removed** | | | **6** |

The **40 historical distinct** cases comprise eight original-assignment slots, twenty other E/H/C slots and twelve FNL slots. The excluded O04 and O08 behaviors are represented by more discriminating FNL-02 and C06 variants rather than counted twice.

The **20 existing G01–G20 generalized drafts** were used as written:

| ID group | Original evaluator's problem dimensions |
|---|---|
| G01–G04 | AR aging buckets; customer concentration; actual cash-flow events; bounded cash forecast |
| G05–G08 | Item/Bin/BOM price and valuation bases; time-correct realized margin; supplier delivery; partial goods receipt |
| G09–G12 | Item Group coverage; reverse multilevel BOM dependencies; order-to-invoice joining; manufacturing versus customer demand |
| G13–G16 | Two-target replenishment; new quality DocType; purchase returns and net value; credit notes and sales returns |
| G17–G20 | Supplier payable terms; stock ledger at historical dates; effective price selection; purchase proposal revision and confirmation |

G13 lacked demand targets; G18/G19/G20 lacked some requested identifying/time inputs. The evaluator **kept those ambiguities** and accepted a justified clarification as core-compliant. Those PASS outcomes do **not** establish fully executed historical-stock, pricing or mutation workflows.

## 2. Oracle independence and freeze

Before any scored model response, the evaluator:

- verified source-file hashes and deduplication rules and pinned the application commit;
- ran **271 independent ERP GET**, verified complete count/page/count coverage across **20 DocTypes**, inspected necessary parent documents and their child tables, and processed **327 Stock Ledger Entry rows**;
- used Decimal rather than the candidate's natural-language answer to independently determine numerical checks;
- passed **19 model-free adapter compatibility checks** (outside the 60 business score);
- froze the 60 question-only model inputs, private Oracle, validation policy and relevant ERP snapshot hashes. The question-only projection SHA256 was `3c5cae04fc16651404d2c6bbc69b056f09ebbc7982f9d1dc7f83f58fa218337a`.

**Strict separation:** the candidate Agent received **question projections only**, never private expected answers or grader notes. The public repository stores **aggregate grades and per-case IDs**, while the original questions, private Oracle and unredacted HTTP/model traces remain with the evaluator; do not publish them casually as evidence.

## 3. Execution and limits

| Control | Recorded configuration / behavior |
|---|---|
| Application checkout | Independent detached worktree at exactly `3636ddb2e10a285421c5580891fd50e6d09939c9` |
| Model | DashScope `qwen3.8-max`, temperature 0, thinking enabled, budget 4,096 |
| Date interpretation | Business reference date `2025-10-15`, not local machine date |
| Batch isolation | Six batches × ten independent cases, separate counts/session/local proposal state |
| Per-batch cap | 80 model calls, 240 Agent ERP GET, 1,800 s, USD 20 cost reservation |
| Per-case budget | Up to 12 LLM rounds, 30 ERP GET, 180 s; no budget inflation to force 60 successes |
| ERP write safety | GET/HEAD permitted in runner; other ERP HTTP methods denied; no CLI `/confirm` |
| Original attempt retention | PASS/PARTIAL/FAIL/timeout preserved, never overwritten with best-of-N |
| Independent grade | Core business result and *full final answer* graded separately against actual source receipts, not runner completion alone |

Six batches were within their own cap. One case, **G11**, exhausted its single-case time/read budget; it remains **EXCEPTION**, not a silent omission.

Actual runtime: **209 model requests** (208 returned usage, one response timed out with unknown usage), **298 Agent ERP GET**, total **1,725,399 returned tokens** excluding unknown timeout usage. Preflight Oracle GET (271), end drift GET (45) and batch PO audits (12) bring recorded ERP GET count to **626**. All ERP POST/PUT/PATCH/DELETE counts were **0**. The evaluator compared 14 key-table snapshots and PO identifiers, status and totals before/after with no observed change.

## 4. Actual core/full results

| Group | Cases | Core PASS | Full PASS | Key nuance |
|---|---:|---:|---:|---|
| Distinct original-assignment slots | 8 | **7** | **7** | O05 2026-effective price was not fully qualified for the 2025 reference date |
| E/H/C/FNL distinct cases | 32 | **31** | **31** | FNL-04 failed full finance-link evidence |
| Newly drafted generalized G-series | 20 | **17** | **12** | G11 timeout; G13/G16 unsupported claims; G05/07/09/17/18 extra caveats |
| **Total** | **60** | **55 (91.7%)** | **50 (83.3%)** | **59 completed, one timeout, no unrun** |

**[Full per-case results, specific defect evidence and tool usage](evidence/UNIFIED_60_FIRST_RUN_20261018.md).**

## 5. Why first-sample business review matters

A program can use the right tool and still draw an unjustified conclusion. This evaluation caught unsupported `Purchase Invoice.bill_no` verification without reading Purchase Invoice, a future-effective price used in a 2025 margin conclusion, the wrong universal replenishment inequality, and reversed `is_return` semantics. Conversely, it credited valid item metadata discovery, real `Payment Entry.references` allocations, exact joined-parent dedup, multilevel BOM and historical stock ledger checks.

The older isolated H08 evidence checker occasionally rejected safe EUR quotes. The **unified 60-case H08 passed** on the *same* code SHA when the model returned a correctly bounded answer. Both observations remain documented; this does not turn the historical exception into a pass.

**Delivery boundary:** this suite provides evidence for a human-supervised ERP Agent demonstration. It does not execute the human `/confirm` flow, verify distributed exactly-once, certify broad ERP ACLs or constitute employer-hidden-set success. See [one-page design choices](WRITEUP.md), [older regressions](EVALUATION_EVIDENCE.md), and [original task](ORIGINAL_README.md).
