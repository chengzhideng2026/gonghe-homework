# Plantcore ERPNext Agent

**A business-grade ERP Agent designed for accuracy, traceability and controlled execution—not a chatbot wrapped around an API.**

**9 typed tools · 234 automated contract tests on the hardening candidate · real ERPNext REST validation · multiple independent real-model business suites · explicit human approval for ERP writes.**

It solves the hard problems that a simple tool-calling demo typically misses: **unfamiliar DocTypes, payment allocation through child tables, joined-row deduplication, partial failures, reference-date accounting, reproducible Decimal calculations, and recovery after uncertain writes.** Every claimed result has a scope and an evidence trail.

A Python standard-library CLI on the supplied Crestwind Compressor Manufacturing Co. ERPNext seed. The LLM chooses from **9 typed tools**; it has no arbitrary SQL, shell, or direct purchase-creation tool. Business reference date: **2025-10-15**.

**Reviewer path:** [Run](#quick-start) · [Try scenarios](#review-three-workflows) · [Design (~1 page)](WRITEUP.md) · [Test matrix](EVALUATION_EVIDENCE.md) · [Original assignment](ORIGINAL_README.md).

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

## Tested, with version boundaries

| Evidence | Outcome |
|---|---|
| **Published `main-v2`** | **190/190 offline tests** (merged [PR #2](https://github.com/chengzhideng2026/gonghe-homework/pull/2)). |
| **Hardening candidate `3636ddb2`**, [PR #4](https://github.com/chengzhideng2026/gonghe-homework/pull/4) | **234/234 offline tests** in GitHub Actions; **not yet merged**. |
| Directed **real-model** regression on prior `f11d6c09` | Five of six known cases produced supported final business answers; H08 ended in an evidence-check exception. **Not a 5/6 score for the latest code**. |
| H08-only **real-model** test on `3636ddb2` | EUR quotation was **not** converted or written, but even after a correct `calculate` call the final answer was rejected. **Known answer-availability defect**; not a bypass. |
| Historic E/H/C/S/J/B/R/N suites | Multiple independently reviewed business scenarios, including partial/fail outcomes. **Scores differ by SHA and must not be combined.** |

~~~bash
python -m unittest discover -s tests -v
~~~

See the **[full test evidence matrix](EVALUATION_EVIDENCE.md)** and **[60-case independent validation protocol](EVALUATION_60_PROTOCOL.md)** for exact cases, data sources and the next unified holdout. The 60-case bank is designed but **not yet executed**; no score is fabricated. Offline tests ≠ model-answer accuracy; a no-write smoke test ≠ full live confirmation testing.

**Deliberately omitted:** frontend, Milvus/RAG, multi-agent runtime, cloud hosting, arbitrary ERP writes, foreign-currency conversion, multi-line purchases. Current preview supports one line and agreed company currency. Source scans are not transactional snapshots; local journal idempotency is not an ERP-wide exactly-once guarantee.

**Release scope:** public default branch [`main-v2`](https://github.com/chengzhideng2026/gonghe-homework/tree/main-v2); code hardening awaits [PR #4](https://github.com/chengzhideng2026/gonghe-homework/pull/4). This reviewer-facing documentation is prepared under [PR #5](https://github.com/chengzhideng2026/gonghe-homework/pull/5) and does not by itself change the released code.
