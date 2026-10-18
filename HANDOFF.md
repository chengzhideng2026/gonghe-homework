# Maintainer Handoff / 项目交接

**Read first:** [README quick start](README.md) → [six-criterion design](WRITEUP.md) → [complete evidence matrix](EVALUATION_EVIDENCE.md). In-depth implementation: [PROJECT_GUIDE.md](PROJECT_GUIDE.md); historical changes/failures: [AUDIT.md](AUDIT.md).

## Release and workspace boundaries

| Branch | Current role | Validation |
|---|---|---|
| `main-v2` | Public default branch; code PR #4 merged at `f806519b` (source `3636ddb2`) and final docs from PR #5 | **234/234** offline CI on evaluated code SHA; **55/60 core, 50/60 full** in independent model benchmark |
| `fix/targeted-business-robustness` / [PR #4](https://github.com/chengzhideng2026/gonghe-homework/pull/4) | **Merged** code lineage; tested source SHA `3636ddb2` | **234/234** offline CI; 60-case **55 core PASS, 50 full PASS**; zero ERP writes during scored test |
| `docs/review-final-20261018` / [PR #5](https://github.com/chengzhideng2026/gonghe-homework/pull/5) | Reviewer-facing documentation release, merged after code PR #4 | Documentation CI passed; runtime code unchanged by this PR |

The **evaluated source code** is `3636ddb2`; the code-only merge was `f806519b`, and the final default branch HEAD advances again upon this docs-only merge. Keep those three commit identities separate. Verify [default branch](https://github.com/chengzhideng2026/gonghe-homework/tree/main-v2) and CI.

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
5. Preserve first attempts and their SHAs. The **executed same-SHA 60-case first sample** reports **55/60 core PASS, 50/60 full PASS** under `3636ddb2` ([full evaluation](evidence/UNIFIED_60_FIRST_RUN_20261018.md)). Separate these genuine model business results from **234 offline tests**, older E/H/C/S runs on other SHAs and the employer's unseen hidden score.

For review, prioritise a **stable fixed SHA, clean/secret-free public repo, short start path, truthful test matrix, and no-write evidence** over further last-minute regex or feature additions.


## Release review decision after unified evaluation

**Local take-home delivery: GO with documented P1 business limits.** An independent frozen 60-case first run on `3636ddb2` completed all attempts (59 final answers, G11 timed out). Core business: **55 PASS / 4 PARTIAL / 1 EXCEPTION**. Full final answer: **50 PASS / 6 PARTIAL / 3 FAIL / 1 EXCEPTION**. 209 model calls, 298 Agent ERP GET, **zero ERP writes**, no PO/table drift.

Do not suppress the main defects: O05 wrong price effective-date assumption; FNL-04 claimed Purchase Invoice association without fetching it; G13 false universal shortage inequality; G16 return-flag inversion and unverified payment inference; G11 wide-join timeout. The earlier isolated H08 failure persists as historical evidence, but the unified run H08 itself passed. This is **not** a production autonomous accounting/purchasing go-ahead.

**Release record:** code PR #4 merged as `f806519b`; release documentation PR #5 follows with source-SHA-aligned independent 60-case review. Inspect the current `main-v2` HEAD and Actions checks for the final docs-only merge. Preserve private Oracle outside GitHub.
