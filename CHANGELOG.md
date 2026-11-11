# Changelog

[0.2.0…0.3.0]: https://github.com/anoscranel/rsi-skills/compare/v0.2.0...v0.3.0
[0.1.0…0.2.0]: https://github.com/anoscranel/rsi-skills/compare/v0.1.0...v0.2.0

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
