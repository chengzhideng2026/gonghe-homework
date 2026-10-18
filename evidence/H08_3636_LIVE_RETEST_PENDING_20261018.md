# H08-only retest of 3636ddb2 — exception, requires raw trace review

**Candidate under test:** `3636ddb2e10a285421c5580891fd50e6d09939c9` in code PR #4 (unmerged).
**Operator execution:** `2026-10-18T180339` local output at `D:\work\gonghe-targeted-3636ddb\attempt1_20261018T180339_4785206a`. The original `completed.json` has **not yet been reviewed**, only console evidence.

Independent preflight: exact detached SHA; frozen questions path present. Read-only ERP transport blocks anything except GET/HEAD. H08-only directed known regression, not blind.

- Zero-network deterministic replay of **previous SHA** `f11d6c09` old saved drafts: FNL-12 and FNL-07 zero evidence issues; H08 original draft **0 issues**, its repaired second draft **1 issue**. Script reported `REPLAY_GATE: PASS`, which only gates acceptance of the **original H08 draft** on the new code, not every possible new model reply.
- **New live H08** runner status: **`exception`**, 4 model calls, 2 ERP GET; POST/PUT/PATCH/DELETE **0**; `blocked_erp_writes=0`. Independent before/after Purchase Order snapshots equal. **No accepted final model answer.**
- Reported model budget reservation: USD 0.360498, not actual provider invoice.
- This contradicts any claimed `H08 PASS` or completion of the latest release gate. **The reason for the new exception is unknown from console output alone**; do not infer the specific evidence-check complaint, model statement, timeout or bad tool call without inspecting the current `completed.json` history and program repair feedback.

**Code CI status:** 234/234 tests pass on `3636ddb2`; CI does not prove live H08 success.

**Next action:** preserve this first attempt unchanged and inspect `D:\work\gonghe-targeted-3636ddb\attempt1_20261018T180339_4785206a\completed.json` (only H08 case, model draft sequences, checker feedback, actual tool bodies, final exception). Diagnose whether the program checker is overblocking vs the model actually claiming unsupported currency; change only narrowly supported code and regression tests thereafter. Do not merge code PR #4 or docs PR #5 yet. No repeated model calls before determining the issue.
