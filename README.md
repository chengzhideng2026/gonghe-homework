# Plantcore ERPNext Agent

**An ERP-grounded industrial AI agent that answers from live business records, computes with deterministic tools, and never lets an LLM authorize a purchase.**

Built on the supplied **Crestwind Compressor Manufacturing Co.** ERPNext seed. Python standard-library CLI, OpenAI-compatible LLM, Docker ERPNext. No copied answers in the prompt, SQL agent, vector database, frontend framework, or generic write tool.

> **Review in this order:** [run it](#run-locally) → [try three workflows](#three-review-workflows) → [examine the design](WRITEUP.md) → [inspect test evidence](EVALUATION_EVIDENCE.md). Original assignment: [ORIGINAL_README.md](ORIGINAL_README.md).

## Run locally

**Requirements:** Python 3.10+, Docker Engine/Desktop, Docker Compose 2.24.4+, Git, a working OpenAI-compatible model API key. After images are present, the commands are short; the **first** ERP restore may exceed five minutes while images download and migrations complete.

~~~bash
git clone --branch main-v2 https://github.com/chengzhideng2026/gonghe-homework.git
cd gonghe-homework
docker compose -f erpnext/compose.yml -f compose.local.yml up -d
docker compose -f erpnext/compose.yml -f compose.local.yml logs -f restore-site
~~~

Once you see \`Restore complete.\`, stop following logs with Ctrl+C (this does **not** stop Docker). The site is at [http://localhost:8080](http://localhost:8080); the Compose overlay binds only loopback interfaces. Do **not** use \`docker compose down -v\` for a routine restart: it removes ERP data volumes.

Copy \`.env.example\` to \`.env\` and set **\`LLM_API_KEY\`** (and adjust the model URL/name if needed). The ERP API demo values are pre-provisioned in the supplied seed. Never commit \`.env\`.

~~~bash
# Windows PowerShell: Copy-Item .env.example .env
# Linux / macOS:     cp .env.example .env
python agent.py --demo          # code/config demo; no model call
python agent.py --check         # ERP read connectivity; no model API call
python agent.py                 # interactive natural-language CLI
~~~

The **business reference date is 2025-10-15**. The system clock and ERP invoice \`status\` can disagree with this date; due-date decisions must use the requested reference date.

## Three review workflows

Ask these in the CLI. Each is a *question*, not a hard-coded response; use \`/trace\` to inspect the actual tool calls, scope, calculations, and receipts.

| Workflow | Try this | What to verify |
|---|---|---|
| **Work order → material shortage** | “Which components block Work Order MFG-WO-2026-00020? Compare requirements with Stores stock, respecting UOM.” | Reads Work Order and Bin; distinguishes missing components, physical stock and warehouse-level reservations without inventing ownership. |
| **Invoices → actual allocations** | “For GreenAir HVAC Solutions, show submitted sales invoices, outstanding balances, and which payments were actually allocated to each invoice.” | Reads \`Payment Entry.references\` child rows; never equates free-text \`reference_no\` or \`paid_amount\` to an invoice allocation; separates balance from payment history. |
| **Purchase → gated preview** | “Prepare, but do not create, a PO for 3 Nos of RM-BRG-NSK-6203 from Hangzhou Precision Bearings at USD 4.20 each.” | \`prepare_purchase_order\` creates only **local pending state**; USD 12.60 is a preview estimate. An actual ERP Draft requires an independent user-entered \`/confirm <proposal_id>\`. Do **not** confirm during read-only review. |

Also try an ambiguous supplier, an unknown DocType, partial/404 results, cross-currency pricing, and a multi-turn stock calculation. See the [case-by-case evaluation matrix](EVALUATION_EVIDENCE.md) and [business acceptance criteria](BUSINESS_ACCEPTANCE.md).

## Architecture: what is enforced outside the model?

\`\`\`text
CLI / user
  → LLM planning + typed ToolRegistry (9 built-in tools)
  → ERPNextClient (scoped GET; bounded pagination, cache-age receipts)
  → metadata, count/list, get/get-many, aggregate, calculate, summarize_details
  → provenance / arithmetic checks → sourced answer + /trace

  [purchase preview only] → validate → local SQLite pending proposal
  [separate human /confirm] → revalidate → state claim → ERP POST → GET read-back
  [uncertain write outcome] → preserve journal and reconcile, never blind retry
\`\`\`

| Engineering choice | Why it matters in ERPNext |
|---|---|
| **Generic typed tools** | Discover unfamiliar DocTypes and Link/Table relations at runtime; adding a new read-only DocType normally needs no new tool. Schema and handler are registered together, with revocation checks. |
| **Scoped, complete-enough evidence** | Pagination, join-induced duplicate parent rows, partial successes and stale reads are reported explicitly; empty search is not the same as unavailable or non-existent. |
| **Deterministic arithmetic** | \`Decimal\` calculation, grouping by company/currency/UOM, evidence-bound child-row statistics and subtotal checks reduce plausible-looking wrong totals. |
| **Purchase effect barrier** | Model can request a *proposal*, not approval. The CLI—not model text—owns confirmation, persistence, state transitions, and post-write read-back. |
| **Fail closed, with known limits** | Unsupported FX, missing agreed prices and uncertain source claims block execution. This can also conservatively reject a valid answer; limitations are documented, not hidden. |

Deep dive: [one-page design write-up](WRITEUP.md) · [architecture](ARCHITECTURE.md) · [tool contract](TOOL_REGISTRY.md) · [recovery](RECOVERY_AND_DESIGN.md).

## Verification: code tests ≠ business accuracy

| Version / evidence | Verified observation |
|---|---|
| **Current published \`main-v2\` baseline** | **190/190 offline tests**, from [PR #2](https://github.com/chengzhideng2026/gonghe-homework/pull/2). |
| **Proposed hardening, [PR #4](https://github.com/chengzhideng2026/gonghe-homework/pull/4)** | SHA \`3636ddb2\`: **234/234 offline tests**, GitHub Actions passed; **not yet merged**. |
| **Prior directed real-model run** | At \`f11d6c09\`, five of six known cases had supported final business answers; H08 foreign-currency case ended in a program evidence-check exception. **Not a score for PR #4.** |
| **Latest H08-only test** | At \`3636ddb2\`, the model correctly refused unsupported EUR→USD conversion and ERP writes, **but the final answer was rejected by a conservative provenance check**. This is an open **answer-availability** defect; not a safety bypass. |
| **Other real-model suites** | E01–08, H01–10, C01–06, S01–03, J01/B01, R and N-series have separate retained results, including partial/fail cases. **Not one combined pass rate.** |

Run all offline tests in whichever SHA you have checked out:

~~~bash
python -m unittest discover -s tests -v
~~~

Full evidence and links: **[EVALUATION_EVIDENCE.md](EVALUATION_EVIDENCE.md)**. A proposed 60-case bank is **not** a completed 60-case benchmark. Model tests do not exercise the full live \`/confirm\` write path; separate historical write/read-back and offline recovery tests exist.

## Scope and limits

Deliberate omissions: frontend, RAG/Milvus, multi-agent orchestration, cloud deployment, bulk/multi-line and FX-converting purchases. Current preview is **single line, agreed company currency**. The local SQLite journal is **not** a distributed ERP server-side exactly-once guarantee; complete pagination is **not** a transaction snapshot; heuristic wording checks are **not** a general proof of truth.

**Start here for judging:** [WRITEUP](WRITEUP.md) · [Evaluation Evidence](EVALUATION_EVIDENCE.md) · [Original Homework](ORIGINAL_README.md) · [Implementation Guide](PROJECT_GUIDE.md). Historical experiments and failures remain in \`evidence/\` and \`AUDIT.md\` for reproducibility; they are not all claims about the current SHA.

**Release state:** The public default branch is [\`main-v2\`](https://github.com/chengzhideng2026/gonghe-homework/tree/main-v2). PR #4 is the code-hardening candidate; this revised README is being prepared in [docs PR #5](https://github.com/chengzhideng2026/gonghe-homework/pull/5). Neither PR is merged as of this version of the document.
