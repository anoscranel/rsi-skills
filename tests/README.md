# tests

Run from the repo root: `python3 -m unittest discover -s tests -v` (16 contract tests, a few seconds).
Dependency-free: stdlib `unittest` only — no requirements file, no pytest, no network; fixtures are temp-dir-scoped (`tempfile.mkdtemp()`, removed in `tearDown`).
Tests invoke `scripts/gate-read.py` as a subprocess and assert on its real stdout; nothing is written into the repo.

Each assertion was mutation-checked during the cycle-3 review and audit: destroying the join matching, the rotated-window exclusion, the duplicate-count semantics, the per-skill tally, the validator presence test, or the final status line each makes at least one test fail. Cycle 4 closed the three gaps that check left open and added tests for chained rotation boundaries and their absent/empty/no-prev branches: `--until` boundary inclusivity, same-size-write detection (content hash + mtime, not size alone), the unmatched-leaf count, and the join denominator (a leaf with no `callID` must not count as joinable). Forcing any of the three absent/empty branches to print `INTACT` fails the suite. Coverage is contract-level, not exhaustive: the interior of a `prev`-less rotated file and unkeyed duplicate records are not checked — both are outside the schema's chain and join rules.
