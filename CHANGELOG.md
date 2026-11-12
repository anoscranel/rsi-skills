## 0.9.2 — 2026-11-12

Release-metadata fix: the 0.9.0 and 0.9.1 tags shipped with the changelog's 0.9.0 heading still
marked Unreleased and the README still saying v0.8.0. This release dates the 0.9.0 heading,
records the 0.9.1 entry, and pins the current-release line.

## 0.9.1 — 2026-11-12

Private vulnerability reporting is now enabled on this repository, so SECURITY.md now points
at the *Report a vulnerability* flow directly instead of a fallback contact. This section was
added after the fact: the 0.9.1 tag shipped the SECURITY.md change but its changelog entry and
the dated 0.9.0 heading were lost to a publish-process error.

# Changelog

[unreleased]: https://github.com/anoscranel/rsi-skills/compare/v0.9.0...HEAD
[0.8.0…0.9.0]: https://github.com/anoscranel/rsi-skills/compare/v0.8.0...v0.9.0
[0.9.0…0.9.1]: https://github.com/anoscranel/rsi-skills/compare/v0.9.0...v0.9.1
[0.9.1…0.9.2]: https://github.com/anoscranel/rsi-skills/compare/v0.9.1...v0.9.2
[0.7.0…0.8.0]: https://github.com/anoscranel/rsi-skills/compare/v0.7.0...v0.8.0
[0.6.0…0.7.0]: https://github.com/anoscranel/rsi-skills/compare/v0.6.0...v0.7.0
[0.5.1…0.6.0]: https://github.com/anoscranel/rsi-skills/compare/v0.5.1...v0.6.0
[0.5.0…0.5.1]: https://github.com/anoscranel/rsi-skills/compare/v0.5.0...v0.5.1
[0.4.0…0.5.0]: https://github.com/anoscranel/rsi-skills/compare/v0.4.0...v0.5.0
[0.2.0…0.3.0]: https://github.com/anoscranel/rsi-skills/compare/v0.2.0...v0.3.0
[0.3.0…0.4.0]: https://github.com/anoscranel/rsi-skills/compare/v0.3.0...v0.4.0

## 0.9.0 — 2026-11-12

A reference observer, and the attribution rule that makes its output honest. The first code in this repo that can produce a joinable leaf record without the vacuous join.

### Added
- `scripts/skill-observer.py` — reads a session store read-only and emits leaf records using the schema's attribution rule. Prints a join summary and states plainly that the rate is a **lower bound**. Writes nothing except the leaf log.
- `tests/test_skill_observer.py` — 15 contract tests covering attribution, the later-activation guard, the collision downgrade, the repeated-activation-id guard, the read-only guarantee, and the lower-bound wording.
- Schema: **Attribution rule** section — the fixed procedure an observer must follow (first tool call after activation; `null` when the leaf issued none; never the activation's own id), the **collision downgrade**, and an explicit statement that the rule is an inference, not a measurement.

### Changed
- README lists the observer; `tests/README` test count corrected.

### Measured on the reference store (2026-11-12, window 2026-11-01 → now)
- 111 skill activations across 83 sessions; **86 attributable**, 25 unjoinable.
- Of those 86, **80** join an outcome record — but **75 of those 80 join records whose `tool` is `unknown`**, i.e. rows written during the recorder's defect window (98,178 such rows at the pre-fix snapshot earlier the same day; the live file continues to grow). Under this spec those joins carry no attribution and do not count.
- **SPEC-valid joins: 5 of 111 records (4.5%)** — one `read`, one `execute`, two `write`, one `shell`, all written after the recorder fix.
- **10 call ids were claimed by more than one skill** and were downgraded to `null`; the guard that skips a later *activation* as an attribution was also necessary (without it, two consecutively activating skills swapped ids).

⚠️ **The join rate is not yet measurable, and this release does not claim one.** The observer works; the outcome corpus does not yet contain enough post-fix rows to estimate a rate. Any figure derived from `tool:"unknown"` rows measures the old defect, not the leaf. Re-measure after a clean window of post-fix traffic.
[0.1.0…0.2.0]: https://github.com/anoscranel/rsi-skills/compare/v0.1.0...v0.2.0

## 0.8.0 — 2026-11-12

The leaf record is audited before any writer is built, and four of its fields turn out to be unsatisfiable or dishonest for an event-only writer. No code changes: the reader never validated leaf fields, and no writer shipped.

### Changed
- **Schema: `leaf_routed` is marked self-reported.** No harness event names a subskill leaf, so a writer can only report what it believes it used. Treating it as independently recorded was false.
- **Schema: `trigger_text` and `model` are now nullable.** A harness-plugin writer can reach neither the SKILL.md index row nor any model name in a `session.tool.*` payload. Requiring them forced a guess; `null` now records "not available to this writer" honestly.
- **Schema: `callID` is nullable and documented as the vacuous-join hazard.** A writer that copies the routing call's own id produces a record that joins the outcome log by construction — a 100% join rate meaning only that the routing call returned. Writing `null` fails the join honestly. The Writer requirements section previously *prescribed* the copy; it now forbids it.
- **Spec §0: the ≥95/100 bar now requires the joined outcome to carry a different `callID` from the routing call, and is computed over ALL leaf events rather than joinable ones.** Without both clauses a writer could report 100% over a shrinking sample by logging `null` for everything unjoinable. A leaf event counts toward the ≥100 only if `skill` and `callID` are both non-null.

### Not built
- A same-process leaf writer was designed and **rejected before implementation**: the plugin holds only the routing call's id, so such a writer can either copy it (vacuous) or write `null` (honest, but permanently unable to clear the ≥95 bar). An independent writer requires a separate process reading the session store — recorded as the named successor, not built.

## 0.7.0 — 2026-11-12

Corrections forced by the 2026-11-11 research cycle: the recorder bar now states what it can
actually support, the novelty claim now states what vendors really measure, and the Stage-2
gate now requires evidence that survives re-running.

### Added
- `docs/MISS-RATE.md`: the protocol for the one measurement no vendor ships — whether the
  *correct* skill fired when it should have. Protocol only; running it needs a held-out task
  set with human-assigned expected skills.
- Spec §6: a subsection recording what vendor telemetry actually measures (activation counts)
  and what it does not (the miss rate).

### Fixed
- Spec §0: the recorder bar no longer requires "a recorder the agent cannot write to", which
  is unsatisfiable on a single-user device, and instead states an independence triad —
  verifier ≠ writer, head committed outside the writer's reach, consecutive commitments
  checked — with the honest limit that a same-uid hash chain detects accidents, not tampering.
- Spec §7: the Stage-2 gate now requires ≥3 re-runs with a confidence interval, a frozen
  held-out set, a pre-measured noise floor, a per-proposal cost ledger, and an always-pass
  tripwire for gate collapse.

## 0.6.0 — 2026-11-11

The reader now matches the schema it ships with. Drafted from the 2026-11-11 cycle-4 frozen scope only.

### Added
- `scripts/gate-read.py`: `--outcome2` is repeatable (nearest-newest first), and the rotation-boundary check chains across every adjacent pair in the canonical order `[live, .1, .2, …]`; each boundary is reported and labeled, numbered from `Rotation boundary 1` when two or more rotated files are supplied. With exactly one rotated file the output line is unchanged from v0.5.1; the compatibility claim is defended by `test_multi_boundary_chain` and by the single-rotated cases in the suite. An absent or empty file in the chain is reported, never raised.
- `tests/test_gate_read.py`: five new contract tests — chained rotation boundaries (`test_multi_boundary_chain`), the absent/empty/no-prev boundary branches (`test_chain_absent_and_empty_branches`), `--until` boundary inclusivity, same-size-write detection by content hash and mtime, and the unmatched-leaf count. Suite: 11 → 16 tests.

### Fixed
- The three test gaps stated in 0.5.0 are now asserted: `--until` inclusivity, same-size-write detection, and the unmatched-leaf count — plus the join-denominator survivor (a leaf record with no `callID` is not joinable and must not inflate the denominator).
- README Diagnostics: rotation guidance now covers repeated `--outcome2` passes and says each adjacent pair is checked and labeled.

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
