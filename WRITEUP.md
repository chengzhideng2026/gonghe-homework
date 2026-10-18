# Design Write-up — Plantcore ERPNext Agent

**Principle:** The LLM selects **what to investigate**; typed tools and deterministic code control **what is true, how it is computed, and who may cause a side effect**. [Run instructions](README.md) · [Evidence matrix](EVALUATION_EVIDENCE.md).

### 1. Tool-layer design

**Nine registered tools:** `get_doctype_meta`, `count_documents`, `list_documents`, `get_document`, `get_documents`, `aggregate_documents`, `calculate`, `summarize_details`, `prepare_purchase_order`. Schemas, handlers and effect metadata are registered together; no arbitrary SQL, shell or generic ERP-write tool is exposed.

For **unseen DocTypes**, the Agent discovers fields and Link/Table relations, then filters/paginates ERP parents and reads their child rows. It distinguishes joined raw rows from distinct parents, detects conflicting projections and represents partial failures. Math runs via `Decimal` or evidence-bound child-row statistics, not free-form LLM arithmetic.

### 2. Uncertainty and source boundaries

An empty filtered result is not a failed read; a warehouse snapshot does not establish historical stock transfer; a payment `reference_no` is not invoice allocation evidence. The Agent uses `Payment Entry.references`, reports stock/on-order/reserved bases separately, and assesses overdue against **2025-10-15** rather than blindly trusting ERP `status`.

Tool receipts expose scope, pagination, freshness and calculation outputs. Narrow source/wording checks can request **one** repair and then refuse an unsupported answer. They are **not** a formal natural-language truth verifier: an independently tested EUR-quote case still produced a conservative false rejection, documented as a real failure.

### 3. Write path and errors

`prepare_purchase_order` produces a **validated, single-line, local SQLite pending proposal**, not an ERP document. The LLM cannot execute `/confirm`; a human must enter `/confirm <proposal_id>` separately. Code then revalidates inputs and connection scope, atomically claims the proposal, POSTs the ERP draft and GETs its actual state.

If a response is lost, the journal preserves uncertainty; `/reconcile` checks only a known ERP identity instead of blindly retrying the POST. This is local duplicate-prevention, **not** ERP-server global exactly-once. Unagreed foreign-currency prices remain non-executable.

### 4. Extensibility

A new **read-only** DocType normally uses existing discovery/query tools. New calculations require a typed registry handler plus source, error and contract tests. Each new **write** operation needs its own business validation and human-confirmation boundary. The registry loads trusted code; it is not a sandbox or tenant-authorization layer.

### 5. Judgment and time constraint

Under the assignment's **six-hour framing**, priority was: (1) live and correctly scoped ERP facts; (2) deterministic numbers and uncertainty; (3) guarded write/recovery; (4) adversarial read-only validation. I cut a frontend, RAG/vector store, multi-agent runtime, cloud deployment, automated FX and multi-line PO support because none improved the specified core evaluation risks.

I did not maintain a reliable hour-by-hour log, so this is a **qualitative allocation**, not an invented six-hour timesheet. Later audit/hardening is visible in dated commits and evidence.

### 6. Coding-agent workflow and evidence

Coding agents helped implement bounded changes, write negative tests and inspect tool traces. I retained scope/permission decisions and reviewed first-sample failures in **separate code, evaluator and documentation workspaces**, pinned to exact SHAs. A real-model trace exposed a mistaken payment-allocation shortcut; another found a safe currency answer rejected by the provenance checker. Failed first attempts remain in the record.

**What is demonstrably tested:** merged code source SHA `3636ddb2` (PR #4 merged as `f806519b`) passes **234/234 offline tests**. An **independent, same-SHA 60-case actual-model evaluation** attempted every frozen case once: **55/60 core business PASS (91.7%)** and **50/60 complete-answer PASS (83.3%)**, with four core PARTIAL, three complete FAIL and one timed-out case. The evaluator performed **271 independent ERP GET before scoring**, then observed **209 model calls, 298 Agent ERP GET and zero ERP writes**. All failures are preserved with case IDs and evidence, not cherry-picked; the suite is not an employer hidden-set benchmark. [Per-case evidence](evidence/UNIFIED_60_FIRST_RUN_20261018.md) · [Evaluation index](EVALUATION_EVIDENCE.md).

**Observed limits:** O05 applied a future-effective price to the 2025 valuation context; FNL-04 asserted a finance link without reading Purchase Invoice; G13 asserted a false universal shortage comparison; G16 reversed a return flag and inferred unverified payment history; G11 timed out on a wide join. An earlier H08-only run falsely rejected a safe answer, whereas the same-SHA unified 60-case H08 passed; source/format variance remains an answer-availability consideration.

**Remaining limits:** language checks can over/under-block; scans are not transaction snapshots; SQLite does not give distributed exactly-once, and ERP permissions still depend on the configured API identity.
