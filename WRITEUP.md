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

**What is demonstrably tested:** proposed code SHA `3636ddb2` has **234/234 offline CI tests**; on earlier `f11d6c09`, five known directed business cases produced supported final answers, while H08 failed; H08-only testing on `3636ddb2` **still failed** to return an answer despite **zero ERP writes**. No hidden-test success or completed 60-case benchmark is claimed. Full per-version results: [EVALUATION_EVIDENCE.md](EVALUATION_EVIDENCE.md).

**Remaining limits:** language checks can over/under-block; scans are not transaction snapshots; SQLite does not give distributed exactly-once, and ERP permissions still depend on the configured API identity.
