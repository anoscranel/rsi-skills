# Miss rate — the protocol nobody has implemented

Status: **protocol only, not implemented.** Written 2026-11-11 from research cycle 5
(`ops/rsi-skills-research-2026-11`). No vendor ships this measurement.

## What is already measured (free, from telemetry)

- **Fired-leaf outcome rate** — of the routings that happened, how often the leaf helped.
  Derivable from `leaf-events.jsonl` joined to `harness-outcomes.jsonl` on sessionID+callID. A leaf record with a null callID cannot join; SPEC §0 counts it as a miss.
- **Activation counts per skill** — how often each skill fired. Available from vendor
  telemetry (opencode's `skill` tool event; Claude Code's `claude_code.skill_activated`).

## What no vendor measures: the miss rate

A skill that **should** have fired and did not emits **no event at all**. Absence of
telemetry is therefore indistinguishable from correctness. The miss rate is the fraction of
tasks where the right skill existed and was not selected. It cannot be computed from any
activation log, because the denominator (tasks that needed a skill) never appears in one.

## The protocol (offline, held-out, human-scored)

1. **Build the expected-skill set.** Take N tasks (recommend N ≥ 30) with a human-assigned
   expected skill for each — drawn from a held-out pool that no optimizer pass has seen.
2. **Run each task cold**, with the full skill library installed, no hint of which skill
   applies. Record which skill actually fired (if any) and the outcome.
3. **Score three states per task:** `hit` (expected skill fired and helped), `miss`
   (expected skill did not fire), `false-fire` (a different skill fired).
4. **Report** `hit / N`, `miss / N`, `false-fire / N` with the task set's hash and size.
5. **Re-run after any proposal is admitted.** A change that improves outcome rate while
   increasing the miss rate has traded one failure for another.

## Why this is a protocol and not code

Running it costs a held-out task set plus human-assigned expectations. Both are the
operator's to define. The harness can execute step 2 mechanically once step 1 exists.

## What would falsify the "unmeasured" claim

Any vendor publishing a miss rate (a recall figure against ground truth), or any paper
reporting routing recall on a real skill library. As of 2026-11-11 none was found
(⚠️ absence claim; vendor docs, changelogs and arXiv searched).
