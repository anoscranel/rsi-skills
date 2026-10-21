---
name: ac-rsi
description: "Shared Recursive Self-Improvement core. Owns the event-log schema and (in Stage 2, not built yet) the offline optimization pass that turns per-skill 00-rsi logs into typed edit proposals. Installed once; immutable at runtime. Use when reading or validating 00-rsi logs across skills."
license: MIT
metadata:
  domain: rsi
---

# RSI — shared self-improvement core (log-and-propose)

## Overview

`ac-rsi` is the shared, **immutable-at-runtime** core behind the per-skill `00-rsi` leaves
(SPEC-rsi-skills). It owns the machinery every skill's RSI leaf relies on: the event-log
**schema** and, from Stage 2, the offline **optimization pass** that aggregates logs into
typed, prune-first edit proposals. It makes **no domain claim** — that is why it never
collides with any skill's scope (Rule 4). It is the Voyager/overlay pattern: the program
is fixed; only the append-only logs change.

## Stage posture

- **Stage 1 (NOW):** log-only. This core provides the schema and reads logs. It writes NO
  proposals and runs NO optimizer. Nothing self-modifies.
- **Stage 2 (gated, NOT built):** `scripts/optimize.py` + `scripts/score.py` — an offline
  bandit/GEPA pass producing typed edit proposals as evidence cards. Built only after the
  Stage-1 quantitative gates (SPEC §0) pass, and human-approved.
- Stage 1 has no reader: no script measures the §0 gate yet.

## Hard rules (SPEC §4 — non-negotiable)

These rules bind, but nothing enforces them at runtime today. A lint checks only the
leaf's static shape; see SPEC §4 rule 1.

1. This core NEVER edits, deletes, or truncates ANY file at runtime — not a skill file,
   not a log. Logs are append-only.
2. It NEVER grades a skill by the skill's own self-judgment; outcomes come from the
   harness/validator, independently recorded.
3. It NEVER trains on a skill's self-recorded log alone (the Roesner & Kohno poisoning
   trap); optimization uses independently-recorded outcomes + held-out re-runs.
4. This core is NEVER rewritten by any skill at runtime. Changes to the core go through
   the full `ac-subskills-author` audit pipeline as a normal human-gated skill change.
5. Fail-closed, evidence-carded. An inconclusive signal = no proposal, never a maybe.
6. Drift tripwire (SPEC §4 rule 6): a skill whose triggers drift past the bound is flagged for full re-audit.

## What it holds

- `schema/log-schema.md` — the event-log format every `00-rsi` leaf appends to.
- Leaf events go to `~/.local/share/opencode/rsi/leaf-events.jsonl` (opencode default; set your harness's equivalent). Harness outcomes go to `harness-outcomes.jsonl` in the same directory, written by a recorder this repo does not ship. Join on `sessionID` + `callID`.

## Aggregation liability (honest)

This core reads logs across skills, making it a high-value behavioral-telemetry store. It
reads logs ONLY to produce proposals, never exposes raw cross-skill telemetry outward,
and its read scope is part of its own audit (SPEC §6).
