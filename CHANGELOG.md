# Changelog

## 0.2.0 — 2026-10-22

Fixes from an independent audit of 0.1.0.

### Fixed
- README no longer claims that skills already log events or that a reference leaf ships here. It now lists what ships and what does not.
- Schema: split into a leaf record and an outcome record; added `callID` so the two join exactly; removed outcome fields from the leaf example.
- Spec: success gates now state their denominator and are marked not yet measurable; the hard rules are marked as written, not enforced at runtime.
- Spec: private citations replaced with a References section of 9 arXiv papers; stale skill names and private IDs removed.
- `ac-rsi` frontmatter is strict YAML; the domain moved to `metadata.domain`.

### Added
- CHANGELOG, SECURITY.

## 0.1.0 — 2026-10-21

First release: core skill, schema, spec.
