# Maintainer Handoff / 项目交接

**Read first:** [README quick start](README.md) → [six-criterion design](WRITEUP.md) → [complete evidence matrix](EVALUATION_EVIDENCE.md). In-depth implementation: [PROJECT_GUIDE.md](PROJECT_GUIDE.md); historical changes/failures: [AUDIT.md](AUDIT.md).

## Release and workspace boundaries

| Branch | Current role | Validation |
|---|---|---|
| `main-v2` | Public default/released code at the time of this handoff; baseline `2d6ce5c` | **190/190** offline CI |
| `fix/targeted-business-robustness` / [PR #4](https://github.com/chengzhideng2026/gonghe-homework/pull/4) | Proposed code hardening at `3636ddb2`; **not merged** | **234/234** offline CI; most recent real H08 answer still rejected |
| `docs/review-final-20261018` / [PR #5](https://github.com/chengzhideng2026/gonghe-homework/pull/5) | Reviewer-facing documentation; **not merged** | Documentation checks only |

Do not assume code/docs PR results apply to default `main-v2` until both are merged. After a merge, verify **new main SHA + CI**, then update this table.

Operator's Windows repository `D:\work\gonghe-targeted-fix` was confirmed at **`3636ddb2`** after `git pull --ff-only`. Independent evaluator checkouts and results reside elsewhere under `D:\work\gonghe-eval-*` and `D:\work\gonghe-targeted-*`; they are not interchangeable with the developer branch. Private `.env`, raw `.local` traces, seeded ERP state and evaluator Oracle **must not** be committed.

## Run and inspect without writing ERP

~~~bash
python agent.py --demo
python agent.py --check
python -m unittest discover -s tests -v
python agent.py
~~~

Ask stock/Work Order, invoice allocation or PO **preview** questions from [README](README.md#review-three-workflows). In the CLI, `/trace` shows actual tool evidence; `/pending` lists local pending proposals; `/discard <proposal_id>` removes a preview; `/reconcile <proposal_id>` only GETs a known created ERP identity. **Do not type `/confirm` casually**; it may create an ERP purchase draft. If ERP is not yet up, follow the Docker Compose instructions in README. Do not run `docker compose down -v` unless resetting seed data is an intentional, approved operation.

## Where to change code

| File | Responsibility |
|---|---|
| [agent.py](agent.py) | ERPNextClient, Agent purchase validation, LLMRunner + CLI |
| [erp_tools.py](erp_tools.py), [tool_registry.py](tool_registry.py) | Typed tools, Schema-handler coupling, per-call capabilities |
| [read_policy.py](read_policy.py), [query_policy.py](query_policy.py) | Cache age, HTTP quota, filtering/pagination rules |
| [aggregation_checks.py](aggregation_checks.py), [detail_statistics.py](detail_statistics.py) | Distinct-parent arithmetic, child-row statistics |
| [answer_checks.py](answer_checks.py), [tool_receipts.py](tool_receipts.py) | Limited evidence and wording checks, trace summaries |
| [proposal_store.py](proposal_store.py), [http_transport.py](http_transport.py) | SQLite write journal, guarded outbound HTTP |
| [tests/](tests/) | Mock/contract regressions; run before and after focused changes |

New **read** DocTypes usually reuse existing tools. New **write** operations require dedicated validation, human approval, replay/uncertainty handling and read-back tests. ToolRegistry does not confer ERP permission or tenant isolation.

## Known risk and release discipline

1. Reference date is **2025-10-15**. Raw ERP `status`, today's computer clock and dates embedded in IDs are not equivalent; derive overdue from verified `due_date` and `outstanding_amount`.
2. `Payment Entry.references` proves actual allocations; `reference_no` does **not**. `Bin` reservations are warehouse aggregates, not exclusive Work Order ownership. Do not sum join-duplicated parent invoices.
3. `prepare_purchase_order` makes only a pending local preview; `/confirm` is separate. No automatic FX conversion, multi-line PO, cancellation or generic ERP mutation.
4. **Known H08 deficiency:** a safe EUR quote may be rejected after deterministic calculation due to provenance/table formatting, even though ERP writes and incorrect conversions remain blocked. See the [full first-run diagnosis](evidence/H08_3636_LIVE_RETEST_PENDING_20261018.md). Do **not** describe this case as passed.
5. Preserve first attempts and their SHAs. Label offline **234** tests, 19 historic real-REST checks, historic E/H/C/S series and the planned **60** cases separately. Do not roll across versions or claim a 60-case pass score.

For review, prioritise a **stable fixed SHA, clean/secret-free public repo, short start path, truthful test matrix, and no-write evidence** over further last-minute regex or feature additions.
