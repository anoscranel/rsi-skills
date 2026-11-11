# Changelog

[unreleased]: https://github.com/anoscranel/rsi-skills/compare/v0.5.1...HEAD
[0.5.0…0.5.1]: https://github.com/anoscranel/rsi-skills/compare/v0.5.0...v0.5.1
[0.4.0…0.5.0]: https://github.com/anoscranel/rsi-skills/compare/v0.4.0...v0.5.0
[0.2.0…0.3.0]: https://github.com/anoscranel/rsi-skills/compare/v0.2.0...v0.3.0
[0.3.0…0.4.0]: https://github.com/anoscranel/rsi-skills/compare/v0.3.0...v0.4.0
[0.1.0…0.2.0]: https://github.com/anoscranel/rsi-skills/compare/v0.1.0...v0.2.0

## 0.5.1 — 2026-11-11

CI fix: the Python 3.8 leg could not run on `ubuntu-latest` (now Ubuntu 26.04, which ships no 3.8), so the workflow pins that leg to `ubuntu-22.04`. Python 3.8 support is kept, not dropped — the reader is written to that floor (no walrus, no `match`, no PEP-604 unions). The 3.12 leg was unaffected. Found by the first real CI run on v0.5.0.

## 0.5.0 — 2026-11-11

Repeatable verification and repository hygiene. Drafted from the 2026-11-11 cycle-3 frozen scope only.

### Added
- `tests/test_gate_read.py`: an 11-test contract suite for the reader, stdlib `unittest` only (the repo stays dependency-free). Fixtures are built in a `tempfile.mkdtemp()` and removed at teardown; the tests invoke the shipped reader as a subprocess and assert on its real stdout. Mutation-checked on six surfaces (join matching, rotated-window exclusion, duplicate-count semantics, per-skill tally, validator presence, final status line); known gaps: `--until` boundary inclusivity, same-size-write detection, and unmatched-leaf counts are not asserted.
- `.github/workflows/tests.yml`: GitHub Actions job running `python -m unittest discover -s tests -v` on Python 3.8 and 3.12 for every push and pull request; `contents: read` permissions only.
- `.gitignore`: `__pycache__/`, `*.pyc`, `*.pyo`, `.DS_Store` — prevents the bytecode residue that recurred in earlier cycles.

### Fixed
- README now points at `CONTRIBUTING.md`, in the What-ships table and the License section; the proposal path was previously documented but unlinked.
- Removed two dead functions from `scripts/gate-read.py` (`count_first_prev_checks`, `read_records_with_lines`) — no call sites, no output change.

## 0.4.0 — 2026-11-11

Diagnosability of the real opencode logs: rotation semantics, the reader V2, and the surrounding docs. Drafted from the 2026-11-11 cycle-2 frozen scope only.

### Added
- Schema: rotation semantics (V1.1) — outcome files may rotate with numeric suffixes; canonical history spans the files in suffix order (live first, then older); cross-file chain semantics are design intent, owner-revisable; the measured recorder rotation break (2026-11-11) recorded in the schema.
- Schema: writer requirements for the three harness-supplied fields (`sessionID`, `callID`, `ts`), mechanism-neutral.
- `scripts/gate-read.py` V2: `--outcome2` flag for a rotated/older outcome file (one rotation level; `.2`+ passes not in scope); chain report classifies mid-file breaks per file and reports the rotation boundary once, labeled (boundary break vs cross-file-intact when the first live `prev` matches the rotated file's last-line hash).
- `scripts/gate-read.py` V2: duplicate-key tallies on BOTH sides, reported as `duplicate keys: N of M` per record type.
- `scripts/gate-read.py` V2: `--since` / `--until` ISO-8601 window flags on `ts` (both sides; excluded records reported).
- `scripts/gate-read.py` V2: `validator_verdict` tally — count, with an explicit `0 present (recorder does not write this field)` when zero.
- Spec §6: scale and retention subsection — observed log growth on the reference device; growth/rotation/retention are harness-owned, operator's choice; no retention threshold set by the spec.
- README: Diagnostics section (what the reader reports, sample reference-device output, diagnostic-only reminder).
- `CONTRIBUTING.md`: proposal and review policy (propose via GitHub issue; human review; accepted scope = spec/schema/reader text only).

## 0.3.0 — 2026-11-11

Drafted from the repairs and telemetry findings of the 2026-11 audit pass.

### Added
- `scripts/gate-read.py`, a diagnostic join-report for the two logs (per-skill counts, join rate, chain continuity, trust tally). Diagnostic-only — the §0 gate is not evaluated by any script in this release.
- `docs/PILOT-2026-11.md`, a pilot-window template; it is not pre-registered until the owner fills in and commits it.
- Spec §0: the pilot window opens only when a dated pilot card is committed (start date, pilot skills, recorder identity + first chain hash, margin).
- Schema: callID tie-break rule — the LAST tool call the routed leaf issued before the event; if none, the id of the call that routed to it.
- Spec §5: every proposal must name the exact line it would change.
- Schema: outcome-record chain rule — each outcome record carries `prev` (hash of the preceding line); a break is a `prev` that does not match the hash of the preceding line.
- Spec §1: evidence card defined (a dated record of one pass or proposal, written outside every skill tree).
- Leaf template: personal-data guard — never log secrets, credentials, or personal data; `trigger_text` is copied from SKILL.md, never the user's words.

### Fixed
- SECURITY.md channel honesty: private advisory reporting requires the owner to enable it on the repository; until then contact the owner through GitHub.
- Install path: opencode reads skills from `~/.agents/skills/` or the project's `.opencode/skills/`, not `~/.config/opencode/skills/`.
- Opt-in honesty (README + Spec): logging is off by default; a `00-rsi` leaf logs nothing until the operator enables RSI logging in the harness.
- Changelog 0.2.0 date corrected to 2026-10-21 (the release tag's commit date); compare link added.
- `ac-rsi` SKILL description no longer implies a validator ships: a diagnostic reader ships; no validator or gate evaluator does.

## 0.2.0 — 2026-10-21

Fixes from an independent audit of 0.1.0.

### Fixed
- README no longer claims that skills already log events (v0.1.0 did); it now lists what ships and what does not.
- Schema: split into a leaf record and an outcome record; added `callID` so the two join exactly; removed outcome fields from the leaf example.
- Spec: success gates now state their denominator and are marked not yet measurable; the hard rules are marked as written, not enforced at runtime.
- Spec: private citations replaced with a References section of 9 arXiv papers; stale skill names and private IDs removed.
- `ac-rsi` frontmatter is strict YAML; the domain moved to `metadata.domain`.

### Added
- CHANGELOG, SECURITY.

## 0.1.0 — 2026-10-21

First release: core skill, schema, spec.
