# tests

Run from the repo root: `python3 -m unittest discover -s tests -v` (11 contract tests, ~2s).
Dependency-free: stdlib `unittest` only — no requirements file, no pytest, no network; fixtures are temp-dir-scoped (`tempfile.mkdtemp()`, removed in `tearDown`).
Tests invoke `scripts/gate-read.py` as a subprocess and assert on its real stdout; nothing is written into the repo.

Each assertion was mutation-checked during the cycle-3 review and audit: destroying the join matching, the rotated-window exclusion, the duplicate-count semantics, the per-skill tally, the validator presence test, or the final status line each makes at least one test fail. Coverage is contract-level, not exhaustive — known gaps: `--until` boundary inclusivity, same-size-write detection, and the unmatched-leaf count are not asserted.
