# RSI event-log schema (v1)

Every skill's `00-rsi` leaf appends one **JSON Line** per routing event. Append one line to the central log outside the skill tree (path: `~/.local/share/opencode/rsi/leaf-events.jsonl` — opencode default; set your harness's equivalent). Never write a file inside a skill tree at run time. Append-only. One event per line, UTF-8, no trailing comma.

There are two record types in two files. The leaf writes leaf records to `leaf-events.jsonl`. An outcome recorder run by the harness, not the agent, writes outcome records to `harness-outcomes.jsonl` in the same directory. This repo does not ship that recorder. Join the two exactly on `sessionID` + `callID`. Do not join on time.

## Leaf record (written by the leaf)

| field | type | meaning |
|-------|------|---------|
| `ts` | ISO-8601 string | event time (UTC) |
| `skill` | string | the skill's `name` (e.g. `ac-subskills-author`) |
| `leaf_routed` | string \| null | the subskill leaf that fired, or null if only SKILL.md |
| `trigger_text` | string | the index row text, copied verbatim from SKILL.md by the leaf; never the user's words; the optimizer re-derives it from the skill file and ignores the logged value. |
| `model` | string | the model that produced the routing |
| `sessionID` | string | the harness session id |
| `callID` | string | the harness id of the LAST tool call the routed leaf issued before the event; if none, the id of the call that routed to it; the join key with the outcome record |

A leaf record never contains outcome fields.

## Outcome record (written by the harness only)

| field | type | meaning |
|-------|------|---------|
| `ts` | ISO-8601 string | outcome time (UTC) |
| `sessionID` | string | the harness session id |
| `callID` | string | the harness tool-call id |
| `tool` | string | the tool that ran |
| `outcome` | `completed` \| `error` | independent outcome signal — NEVER the skill's self-rating |
| `validator_verdict` | string \| null | the independent validator's verdict when one ran |

## Example

Leaf record:

```json
{"ts":"2026-10-08T12:00:00Z","skill":"ac-subskills-author","leaf_routed":"lint-tree","trigger_text":"run the 4 rules + bidirectional check","model":"example-model","sessionID":"abc123","callID":"call_01"}
```

## Integrity rules (SPEC §4)

1. **Append-only** — never edit, delete, or truncate a prior line. History is immutable.
2. **Outcome independence** — `outcome` and `validator_verdict` are written by the
   harness/validator, OUTSIDE the skill's own append path. A skill never records its own
   outcome (the Roesner & Kohno poisoning guard).
3. **No PII / secrets** — never log secrets, credentials, or personal data. The log is
   telemetry, not a data store.
4. **Fired-leaf outcome rate** is the honest metric derivable from this log. Trigger
   *recall* requires the offline paired-replay (SPEC §6), not this log alone.
5. **Chain** — each outcome record carries `prev` (the hash of the preceding line; the live opencode recorder's field name); a break is any record whose `prev` does not match the hash of the preceding line. Within the canonical history (Rotation, V1.1), a record first in its file but not first in the history chains to the previous file's last line; that form is design intent, owner-revisable — the measured opencode recorder does not do it, so real boundaries are boundary breaks, not errors.

## Rotation (V1.1)

Rotation: outcome files may rotate with numeric suffixes (`harness-outcomes.jsonl.1`, `.2`, …). Canonical history spans the files in suffix order — the live file first, then each higher suffix (older). The desired cross-file chain semantics are **design intent, owner-revisable**.

Measured with this repo's diagnostic reader on 2026-11-11: the opencode recorder rotates **without** cross-file chaining (the first live record's `prev` does not match the hash of the previous file's last line), so every rotation boundary is a chain break under canonical-history semantics. The reader reports these as boundary breaks, not errors.

## Writer requirements (whichever component writes leaf records — leaf or harness — the harness supplies:)

- `sessionID` — the harness session identifier, verbatim.
- `callID` — per SPEC §0: the id of the LAST tool call the routed leaf issued before the event; if none, the id of the call that routed to it.
- `ts` — UTC, ISO-8601, from a clock the harness provides; never the model's guess.

These are requirements, mechanism-neutral; no route (leaf-side vs harness-side logging) is implied.

## Activation records (producer examples — none canonical)

These are **not** leaf records and **not** outcome records. They record that a skill was
*selected*, which neither of the other two types captures. Measured producer shapes, listed
as examples only; a conformant reader takes whichever shape its harness emits:

- **opencode** — a `tool_use` event whose `part.tool` is `"skill"`, with the skill name at
  `part.state.input.id` (verified on device, 2026-11-11).
- **Claude Code** — `claude_code.skill_activated` with an `invocation_trigger` field
  (`claude-proactive` = agent-selected, `user-slash` = user-invoked), since v2.1.126.
- **Cursor** — `cursor.skill.trigger`.
- **Org-analytics exports** — vendor-specific; treat as opaque and map explicitly.

⚠️ Activation records carry **no `callID`**, so they support **session-level association
only**. Do not derive per-skill outcome rates from them: a session may contain several
skills, and nothing in an activation record says which outcome belongs to which.

⚠️ Activation counts are **not** recall. A skill that should have fired and did not emits no
event at all, so the miss rate is invisible to every activation log (see `docs/MISS-RATE.md`).
