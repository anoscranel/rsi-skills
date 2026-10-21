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
| `callID` | string | the harness id of the tool call this event belongs to; the join key with the outcome record |

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
