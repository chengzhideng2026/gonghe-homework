# Design Write-up — ERPNext Agent

> **Core decision:** The model interprets requests and chooses tools; deterministic code owns ERP facts, money arithmetic, authorization, and side effects. The objective is **auditable business correctness**, not simply fluent answers. [Run the project](README.md) · [Inspect evaluation evidence](EVALUATION_EVIDENCE.md).

### 1. Tool-layer design

The **nine built-in typed tools** are: `get_doctype_meta`, `count_documents`, `list_documents`, `get_document`, `get_documents`, `aggregate_documents`, `calculate`, `summarize_details`, and `prepare_purchase_order`. Each Schema, handler and effect/version lives in one ToolRegistry entry. The LLM never obtains arbitrary SQL, shell execution, or a general ERP mutation primitive.

The read surface works on **unknown DocTypes**: discover fields and Link/Table relations, filter the parent endpoint, page within explicit limits, and fetch shortlisted parent documents with their child rows. The client detects duplicate parents caused by child joins, distinguishes raw matched rows from distinct documents, rejects conflicting repeated projections, and separates partial reads from a complete scan. `calculate` uses restricted `Decimal` expressions; `summarize_details` operates on current-turn read evidence rather than LLM-supplied numeric arrays.

### 2. Uncertainty handling

A failed query is not an empty ERP dataset; a name search is not a complete business category; a current `Bin` warehouse label is not proof of stock-transfer history. The response must distinguish on-hand vs ordered vs reserved, invoice `outstanding_amount` vs actual allocations in `Payment Entry.references`, and raw ERP `status` vs **overdue as of 2025-10-15**.

Tool receipts record scope, pagination, freshness, partial failures and math. A bounded program evidence check catches selected unsupported numerical/wording claims and may request **one** repair, then fail closed. It is not a semantic truth theorem: a real H08 EUR-quote test still triggers a **false rejection of a safe answer**. The false rejection is disclosed, not converted into a PASS.

### 3. Write path and recovery

`prepare_purchase_order` only validates and persists a **single-line local pending proposal**, with the agreed unit price explicitly denominated in the company's currency. The model cannot call `/confirm`. After a human independently enters `/confirm <proposal_id>`, code revalidates supplier, item, UOM, dates, quantity, amount, connection scope and expiration; atomically claims local SQLite state; then POSTs a draft and GETs it back. Failure/uncertain response is journaled and reconciled against **known ERP identity**; no blind second POST. These are local replay controls—not a claim of ERP server-side distributed exactly-once. Foreign-currency quotes without a user-agreed conversion cannot be executed.

### 4. Extensibility

For a new read-only DocType, an engineer can usually reuse metadata + scoped list/get/aggregate without changing the model loop. To add a new operation, register its Schema/handler/effect in `erp_tools.py`, write unit tests for validation/partial failures/source receipts, then add a focused actual-ERP scenario. New **write** operations require a separate human-approval path, not merely registering a tool. The registry is a trusted-code capability catalog, not an untrusted plugin sandbox or tenant ACL system.

### 5. Judgment under constraints

I prioritized: **(i)** correct ERP reads and date/quantity/currency semantics; **(ii)** deterministic computation and source boundaries; **(iii)** purchase confirmation, journal and recovery; **(iv)** read-only adversarial regression. I deliberately did **not** build a web frontend, RAG/Milvus, cloud service, multi-agent orchestration, autonomous ERP writes, multi-line POs or an FX service; none addressed the assignment's principal failure modes.

The assignment framed a **six-hour** budget. I did **not** retain reliable hour-by-hour timing, and later hardening/review continued after the initial deliverable, so I do not invent a six-hour timesheet or claim all commits were completed within that window. The priorities above describe effort allocation rather than measured hours. Git history and dated evidence preserve the actual sequence.

### 6. Coding-agent workflow and validation

Coding agents helped implement bounded changes, generate edge-case tests, and inspect business traces. I retained decisions about tool effect boundaries, evidence strength, confirmation requirements and what **not** to ship. Implementation, independent evaluator and documentation workspaces used fixed Git SHAs; failing **first attempts remain preserved** rather than replaced by successful reruns. A real-model trace caught `Payment Entry.reference_no` being mistaken for allocation, and another caught the difference between a safely declined foreign-currency purchase and the checker rejecting a safe explanation.

**Measured evidence has separate layers:** GitHub CI **234/234 offline tests** at proposed code SHA `3636ddb2` ([PR #4](https://github.com/chengzhideng2026/gonghe-homework/pull/4)); earlier six-case actual-model run with **five acceptable business replies and one H08 exception** at `f11d6c09`; H08-only actual-model **exception** again at `3636ddb2` despite **zero ERP writes**. Neither is a hidden-set score; the 60-case bank is unexecuted. See [the test matrix](EVALUATION_EVIDENCE.md).

**Limits:** statement-level checks can under- or over-block; bounded paging does not guarantee a transaction snapshot; the SQLite journal is not globally exactly-once; ERP security still depends on its own API account permissions. These are explicit engineering tradeoffs, not unseen guarantees.
