# ERPNext Agent Homework — Crestwind Compressor

## 1. Background

This repo gives you a pre-seeded ERPNext running locally. Your job is to build an AI agent on top of it. We've removed the infrastructure and data-prep busywork so you can focus on agent design.

**The company:** Crestwind Compressor Manufacturing Co. (CCM) is a US-based manufacturer of rotary AC compressors selling B2B to HVAC OEMs. The fiscal year is 2025. The seed data includes raw materials, sub-assemblies, finished goods, multi-level BOMs, sales/purchase orders, work orders, invoices, and payments.

A few business situations worth knowing before you start:

- One Work Order for 30 units of the 1.5HP/R32 model is stuck at "Not Started" because three required components are short; a pending copper order covers one of them
- Four sales invoices are overdue, and receivables are concentrated in one customer
- A customer has ordered 12 of the 1HP model and only 9 are on hand

Read `erpnext/DATASET.md` before you start — it is the data ground truth and contains a critical note about the system date.

**Time budget:** 6 hours. More time doesn't mean a better submission.

---

## 2. Technical Guide

### ERP Setup

**Prerequisites:** Docker Desktop (or Engine + Compose v2), ~2 GB free RAM, ~3 GB free disk.

```bash
cd erpnext
docker compose up -d
docker compose logs -f restore-site   # wait for "Restore complete."
# First run: ~5 min (fresh ERPNext install + restore + migrate). Subsequent runs: ~30 s.
```

Open **http://localhost:8080** as `Administrator` / `admin`.

Smoke-test (also your first taste of the API):

```bash
curl -fs -X POST http://localhost:8080/api/method/login \
    -d 'usr=Administrator&pwd=admin' -c /tmp/c -o /dev/null
curl -fs -b /tmp/c 'http://localhost:8080/api/method/frappe.client.get_count?doctype=Item'
# expect: {"message":18}
```

ERPNext exposes REST at `/api/resource/<DocType>` and RPC at `/api/method/<dotted.path>`. The restore step provisions an API key pair for `Administrator`: key `crestwind-agent`, secret `crestwind-agent-secret`. Request header format: `Authorization: token <api_key>:<api_secret>`. (Cookie login via `POST /api/method/login` also works. Don't use "Generate Keys" in the UI: on a freshly restored site the first key it issues is unusable.)

**Reset to clean state:** `docker compose down -v && docker compose up -d`

**Port collision:** in `erpnext/`, copy `.env.example` → `.env`, change `HTTP_PORT`.

### Agent

You're free to pick any harness or framework — we recommend [Pi](https://github.com/badlogic/pi-mono). The agent will be graded on capabilities, not specific builds — implement them however you like (skills, a CLI, an MCP server, a Pi extension, …).

### UI

Anything a reviewer can run locally to ask questions and see answers — browser or terminal. If you went with Pi, it ships simple UIs (`pi-web-ui`, `pi-tui`).

---

## 3. Deliverables

### Code

You received this project as a zip. Either initialize a fresh git repo from its contents and add your agent code on top, or keep the agent in its own repo that expects the `erpnext/` directory beside it; say which in your README. Push to a new repo on your own GitHub (or GitLab/Bitbucket). Keep a complete git history — don't squash to a single commit. Send us the repo link when you submit.

Your `.env.example` must document all required config keys, at minimum:

```
LLM_API_KEY=
ERPNEXT_URL=http://localhost:8080
ERPNEXT_API_KEY=crestwind-agent
ERPNEXT_API_SECRET=crestwind-agent-secret
```

### Local Run Instructions

Your README must get a reviewer running and asking questions within **5 minutes**:

1. `docker compose up -d` (start ERPNext)
2. Copy `.env.example` → `.env`, fill in the LLM API key (the ERPNext key pair is pre-provisioned)
3. Start the agent per your instructions
4. Ask questions via the UI or CLI

### Write-Up (~1 page)

Submit a short document (in your repo or as a separate file). Structure it around the evaluation criteria below — we'll read both together.

1. **Tool layer design** — what tools did you define, how did you draw the boundaries, and why? Would the same surface work for a DocType you haven't seen yet?
2. **Uncertainty handling** — how does your agent behave on ambiguous queries or when data doesn't exist?
3. **Write path** — walk through your confirmation flow and how the agent handles ERPNext errors.
4. **Extensibility** — how would a new engineer add support for a new DocType without restructuring the agent?
5. **Judgment under constraints** — what did you cut, and why was that the right call? Include your time allocation across the 6 hours.
6. **Coding agent workflow** — how did you work with AI coding tools (Claude, Cursor, Copilot, etc.)? What did you delegate, what did you keep manual, what broke down? No right answer — just be specific.

---

## 4. Test Queries

Every query below has a deterministic answer. Use them as a self-test harness while building. They are not the grade: we evaluate with a held-out set of queries of the same shapes that you will not see.

### Read — Single DocType

| Query | Expected Answer |
|-------|----------------|
| "What's the current stock of copper coil?" | 50 m of RM-COIL-CU-2.0 in Stores - CCM (200 m more on order, 60 m reserved for a work order) |
| "List all open purchase orders." | 6 POs, status To Receive and Bill, total $15,065.50 |
| "Which customer placed the most sales orders?" | GreenAir HVAC Solutions, 5 orders (Summit Climate OEM is next with 4) |

### Read — Cross-DocType

| Query | Expected Answer |
|-------|----------------|
| "Which components are blocking Work Order MFG-WO-2026-00020?" | SA-MOTOR-1HP (need 30, have 20), SA-PUMP-R32 (need 30, have 20), RM-COIL-CU-2.0 (need 60, have 50) |
| "What's the gross margin on the 1HP/R32 compressor?" | States its cost and price basis. Cost: BOM / item valuation $575.20 (stock-ledger actual $566.81 also fine). Price: list $600, or realized sales-order rates $580–$610. Margin consistent with the bases chosen, e.g. $24.80 (4.1%) at list on BOM cost, $4.80–$34.80 over realized orders |
| "Show me overdue sales invoices." | Four, total $25,380: ACC-SINV-2026-00011 GreenAir $6,000 (due 2025-08-17), -00013 Polaris $4,640 (2025-08-31), -00015 Helio $8,640 (2025-09-28), -00017 GreenAir $6,100 (2025-10-10). Not -00018/-00020/-00021: unpaid but not yet due, whatever their `status` field says |

### Write (with confirmation flow)

> "Create a new purchase order for 100 m of RM-COIL-CU-2.0 from Tongling Magnet Wire Co. at $29 per meter."

Agent should: display the planned payload → request explicit confirmation → create the PO → return the new document name. Total should be $2,900.

> ⚠️ The pinned reference date (2025-10-15) applies to writes too. ERPNext defaults `transaction_date` to the system clock (2026), so if the agent passes a 2025 `schedule_date` without overriding `transaction_date`, the PO will fail with `Required By cannot be before Date`. Pin `transaction_date` explicitly when creating documents.

### Graceful Failure

| Query | Expected Behavior |
|-------|------------------|
| "What's the stock of laptops?" | No matching item — agent says so, does not invent a number |
| "How many employees do we have?" | Reports 0 or "no employee data", does not fabricate |
| "Cancel the manufacturing run for the new compressor model." | Three models exist and two work orders are open (MFG-WO-2026-00019 in process, -00020 not started). Agent asks which, or proposes the only not-started compressor run and asks to confirm. Cancels nothing unprompted |

---

## 5. Evaluation Criteria

Here's what we'll be looking at — no surprises:

- **Tool layer design** — granularity, boundary decisions, and whether the surface generalizes cleanly to DocTypes not explicitly shown in the test queries
- **Uncertainty handling** — clarification on ambiguous queries, honest reporting on missing data
- **Write path** — confirmation flow design and error handling
- **Extensibility** — can a new engineer add support for a new DocType without restructuring the agent?
- **Judgment under constraints** — what you chose to cut and whether that was the right call

We do not evaluate frontend aesthetics or cloud deployment.
