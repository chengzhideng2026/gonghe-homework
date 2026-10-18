# Detail statistics: post-experiment review (2026-10-18)

This is a subsequent review of the frozen experiment at `ed912a8f507425e46ce6b6044e39071a265a8214`. It does **not** alter or replace the original experiment results. The earlier `experiment/REPORT.md` reflects the original interface failure; `experiment/INTERFACE_REVIEW.md` records the later interface repair and one successful D02 comparison.

## Findings

- The experiment's explicit body-level `evidence_ref` is preferable to asking a model to guess a provider protocol call ID. The original D02 failure was an interface usability problem, not proof the model was incapable of using the tool.
- Offline Decimal calculations provide deterministic line counts, parent counts, group-specific sums, minimum/maximum and quantity-weighted rates, without additional ERP API calls. `complete` only covers the explicitly referenced reads, not the upstream business-wide filter/pagination.
- The original `detail_statistics.py` could union disjoint child rows across two reads of the same parent when selected header fields remained equal, and report `complete=true`. This is a correctness defect.
- This review rejects repeated-parent snapshots whose selected child tables do not have the same complete child identity-to-value mapping. It preserves row-order independence, same-snapshot deduplication and separate-parent counting. A duplicate child identity inside one parent snapshot fails closed. This is **not** a transactional snapshot or a proof of upstream list completeness.

## Verification and limitations

- The original experiment history records a 181-test passing offline regression and one successful real-model D02 call after the body-reference fix. Those runs predate this review patch; they are retained evidence, **not** a fresh validation of this commit.
- On an isolated locally available earlier project snapshot, the deterministic statistics implementation with the snapshot fix and nine added edge tests passed **167 tests** total. This project snapshot does not reproduce the exact remote experimental integration, so those 167 tests are **not** a claim that the present GitHub commit passed the complete 190-test integrated suite.
- The GitHub branch adds `tests/test_detail_snapshot_fix.py` (9 tests) and adjusts the prior conflict-error assertion. **Run the full offline test suite against the actual merge candidate before production delivery:** `python -m unittest discover -s tests -v`. Expected suite size: approximately 190, contingent on the current repository test inventory.
- No new model or ERP requests were made for this review; no end-to-end hidden-question evaluation is claimed.
- The tool increases schema/context size, is limited to current-turn explicit parent-read evidence, and should be used only when line statistics and source traceability warrant that cost. Historical single-pair token and latency improvements must not be generalized.

## Decision

**Recommend a reviewable normal PR into `main-v2`, not a force-push or branch replacement**, conditional on the full integrated offline regression passing and a clean merge that retains `main-v2` README/documentation changes. Preserve the original experiment report as historical, not as current release guidance.
