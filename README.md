# Plantcore ERPNext Agent

**A business-grade ERP Agent designed for accuracy, traceability and controlled execution—not a chatbot wrapped around an API.**

**9 typed tools · 234/234 offline tests · 60-case real-model business benchmark: 91.7% core acceptance / 83.3% full-answer acceptance · 0 ERP writes in the independent read-only campaign.**

It solves the hard problems that a simple tool-calling demo typically misses: **unfamiliar DocTypes, payment allocation through child tables, joined-row deduplication, partial failures, reference-date accounting, reproducible Decimal calculations, and recovery after uncertain writes.** Every claimed result has a scope and an evidence trail.

A Python standard-library CLI on the supplied Crestwind Compressor Manufacturing Co. ERPNext seed. The LLM chooses from **9 typed tools**; it has no arbitrary SQL, shell, or direct purchase-creation tool. Business reference date: **2025-10-15**.

**Reviewer path:** [Run](#quick-start) · [Try scenarios](#review-three-workflows) · [60-case independent results](evidence/UNIFIED_60_FIRST_RUN_20261018.md) · [Design (~1 page)](WRITEUP.md) · [Test matrix](EVALUATION_EVIDENCE.md) · [Original assignment](ORIGINAL_README.md).

## Independently evaluated on 60 real ERP business questions

| Result at **one fixed commit** `3636ddb2` | Observed first-attempt outcome |
|---|---|
| **Core business requirements** | **55/60 PASS — 91.7%** (4 PARTIAL, 1 timeout) |
| **Complete, evidence-disciplined answers** | **50/60 PASS — 83.3%** (6 PARTIAL, 3 FAIL, 1 timeout) |
| **Read-only execution audit** | **209 LLM requests, 298 Agent ERP GET, zero ERP writes; verified unchanged Purchase Order and 14 business-table snapshots** |
| **Automated code quality** | **234/234 Python contract and regression tests passed in GitHub Actions** |

All 60 questions used **the same SHA, a pre-frozen independent answer Oracle, first-sample grading and six bounded batches**. The suite combines 40 de-duplicated existing ERP scenarios with 20 newly drafted generalization cases. Failures and the G11 timeout are retained—not replaced by re-sampling. This is our independent technical evaluation, **not** the employer's private hidden-test result.

**[Read the complete 60-case evaluation with per-case grades and evidence](evidence/UNIFIED_60_FIRST_RUN_20261018.md)** · [test methodology](EVALUATION_60_PROTOCOL.md).

## Quick start

Requires Python 3.10+, Docker with Compose 2.24.4+, Git, and an OpenAI-compatible LLM API key. The **first** Docker pull/ERP restore can take longer than five minutes.

~~~bash
git clone -b main-v2 https://github.com/chengzhideng2026/gonghe-homework.git
cd gonghe-homework
docker compose -f erpnext/compose.yml -f compose.local.yml up -d
docker compose -f erpnext/compose.yml -f compose.local.yml logs -f restore-site
~~~

After `Restore complete.`, Ctrl+C stops log following, not ERP. Docker publishes ERP only to **localhost:8080**. Do not use `down -v` for routine restart (it deletes volumes).

Copy `.env.example` to `.env` (Windows: `Copy-Item .env.example .env`; Linux/macOS: `cp .env.example .env`). Set `LLM_API_KEY` and, if different, `LLM_MODEL`/`LLM_BASE_URL`. The supplied ERP seed provisions the example ERP API key pair. **Do not commit `.env`.**

~~~bash
python agent.py --demo             # no model / ERP needed
python agent.py --check            # ERP GET + config; no model call
python agent.py                    # ask natural-language business questions
~~~

## Review three workflows

Enter each question in the CLI, then use `/trace` to inspect source, filtering, pagination and calculation receipts.

| Ask | What makes a correct answer |
|---|---|
| “Which components block Work Order MFG-WO-2026-00020? Compare requirement and Stores stock.” | Cross-DocType Work Order/Bin read; per-component shortfall and UOM; warehouse-level reservations **not** falsely attributed to this Work Order. |
| “For GreenAir HVAC Solutions, reconcile submitted sales invoices, outstanding balances and actual payment allocations.” | Reads submitted `Payment Entry.references` child rows; does **not** infer invoice allocation from `reference_no` or from total paid alone. |
| “Prepare but don't create a PO for 3 Nos of RM-BRG-NSK-6203 from Hangzhou Precision Bearings at USD 4.20 each.” | **Local preview only** (USD 12.60 estimate). Actual ERP creation requires a separately typed `/confirm <proposal_id>`. Do **not** confirm in a read-only review. |

More cases: unknown DocType, missing/partial records, join duplicates, reference-date aging, multi-turn replenishment, adversarial purchase requests, and foreign-currency quotes. **[Full real-model case coverage](EVALUATION_EVIDENCE.md)** · **[60-case independent evaluation protocol](EVALUATION_60_PROTOCOL.md)**.

## Why this implementation is different

```text
User/CLI → LLM + typed ToolRegistry → ERP GET / metadata & scoped query
                                ↘ Decimal calculate / aggregate / detail statistics
                                 → provenance checks → answer + /trace

LLM may prepare → validated local SQLite proposal (no ERP write)
Human /confirm  → revalidate, atomically claim → ERP POST draft → GET readback
Unknown outcome → journal + read-only /reconcile; never blind retry
```

- **Generalizes:** nine registered tools cover metadata, counts, filtered pages, parent/batch details, aggregates, evidence-bound detail statistics, arithmetic and PO preparation. New read-only DocTypes normally need **no new tool**.
- **Evidence before fluency:** distinguish raw join rows from distinct parents; bound pagination and partial failures; preserve UOM, company, currency, cache age and reference date. A Bin snapshot is not a stock-transfer history.
- **Computes outside the LLM:** Decimal arithmetic and local subtotal checks; receipts link claims to real ERP responses. Heuristic language checks are deliberately **not** a proof of every sentence.
- **Effects require humans:** model output cannot execute `/confirm`; the CLI and SQLite journal control state, retries and ERP readback. This is not distributed server-side exactly-once.

Design/tradeoffs: [WRITEUP.md](WRITEUP.md) · [Tool Registry](TOOL_REGISTRY.md) · [Write recovery](RECOVERY_AND_DESIGN.md).

## Engineering differentiators

| Frequent ERP-Agent failure mode | This implementation's concrete boundary |
|---|---|
| An LLM returns a plausible total without source coverage | Decimal tools and source receipts distinguish verified facts, calculated values and unsupported assertions. |
| A child-table join duplicates invoice amounts | Separate raw joined rows from distinct parent documents; reject conflicting parent projections. |
| A payment reference string is mistaken for an allocation | Read submitted **Payment Entry parent + references child rows** before linking payments to invoices. |
| Current inventory is confused with incoming or work-order reservations | Label **actual, ordered, projected and warehouse-reserved** quantities with the correct UOM and scope. |
| Model receives a generic write API and approves itself | **Local proposal → separate human /confirm → ERP draft → GET read-back**, with journal-based uncertain-outcome recovery. |
| A small demo passes simple happy-path tests | Regression coverage includes **negative, partial, ambiguous, cross-document, multi-turn and safety** cases, with saved first-run failures. |

## Verification layers, clearly separated

| Layer | Status |
|---|---|
| **Unified 60-case actual-model first run** | **55/60 core PASS, 50/60 full PASS** on candidate SHA `3636ddb2`; [detailed first-attempt review](evidence/UNIFIED_60_FIRST_RUN_20261018.md) |
| **Offline code regression on the same SHA** | **234/234** Python tests in [PR #4](https://github.com/chengzhideng2026/gonghe-homework/pull/4) and GitHub Actions |
| **Released code on `main-v2`** | [Code PR #4](https://github.com/chengzhideng2026/gonghe-homework/pull/4) merged as `f806519b`; tested source SHA `3636ddb2` with **234/234** offline CI. The newer documentation merge changes Git HEAD but not the evaluated code. |
| **Earlier focused model regressions** | Preserved in [evidence index](EVALUATION_EVIDENCE.md), including a prior H08 false refusal; the **new same-SHA 60-case H08 passed both grades** |

```bash
python -m unittest discover -s tests -v
```

**What remains:** one G11 wide-join timeout, incomplete or unsupported statements in O05/FNL-04/G13/G16, and several less serious full-answer limitations. These are business accuracy/availability boundaries, **not** observed unauthorized ERP writes. This take-home demonstrates a *human-supervised ERP Agent*, not a production-certified autonomous buyer or accountant.

**Deliberately omitted:** frontend, Milvus/RAG, multi-agent runtime, cloud hosting, arbitrary ERP writes, foreign-currency conversion, multi-line purchases. Current preview supports one line and agreed company currency. Source scans are not transactional snapshots; local journal idempotency is not an ERP-wide exactly-once guarantee.

**Release:** [`main-v2`](https://github.com/chengzhideng2026/gonghe-homework/tree/main-v2) contains the merged nine-tool hardening from [PR #4](https://github.com/chengzhideng2026/gonghe-homework/pull/4) and evaluator-first documentation from [PR #5](https://github.com/chengzhideng2026/gonghe-homework/pull/5). The independently evaluated **source code SHA** is `3636ddb2`, contained in code merge `f806519b`. See [the 60-case report](evidence/UNIFIED_60_FIRST_RUN_20261018.md) for the exact test provenance.
