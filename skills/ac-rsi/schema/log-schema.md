# RSI event-log schema (v1)

Every skill's `00-rsi` leaf appends one **JSON Line** per routing event. Append one line to the central log outside the skill tree (path: `~/.local/share/opencode/rsi/leaf-events.jsonl`). Never write a file inside a skill tree at run time. Append-only. One event per line, UTF-8, no trailing comma.

Leaf events go to `~/.local/share/opencode/rsi/leaf-events.jsonl`. Harness outcomes go to `~/.local/share/opencode/rsi/harness-outcomes.jsonl` (rsi-outcome.js), keyed by `sessionID`. Join on `sessionID` and nearest `ts`.

## Record fields

| field | type | written by | meaning |
|-------|------|-----------|---------|
| `ts` | ISO-8601 string | leaf | event time (UTC) |
| `skill` | string | leaf | the skill's `name` (e.g. `skill-author`) |
| `leaf_routed` | string \| null | leaf | the subskill leaf that fired, or null if only SKILL.md |
| `trigger_text` | string | leaf | the trigger/description text that matched |
| `task_outcome` | string | **harness/validator** | independent outcome signal (e.g. `success`, `fail`, `partial`, exit-code class) — NEVER the skill's self-rating |
| `validator_verdict` | string \| null | **harness/validator** | the independent validator's verdict when one ran |
| `model` | string | leaf | the model that produced the routing |
| `sessionID` | string \| null | leaf | optional session/correlation id |

Outcome fields are written as separate records keyed by `sessionID` + `ts` (see harness-outcomes.jsonl, rsi-outcome.js); a leaf record never contains them.

## Example

```json
{"ts":"2026-10-08T12:00:00Z","skill":"skill-author","leaf_routed":"lint-tree","trigger_text":"run the 4 rules + bidirectional check","task_outcome":"success","validator_verdict":"pass","model":"kimi-k3","sessionID":"abc123"}
```

## Integrity rules (SPEC §4)

1. **Append-only** — never edit, delete, or truncate a prior line. History is immutable.
2. **Outcome independence** — `task_outcome` and `validator_verdict` are written by the
   harness/validator, OUTSIDE the skill's own append path. A skill never records its own
   outcome (the Roesner & Kohno poisoning guard).
3. **No PII / secrets** — never log secrets, credentials, or personal data. The log is
   telemetry, not a data store.
4. **Fired-leaf outcome rate** is the honest metric derivable from this log. Trigger
   *recall* requires the offline paired-replay (SPEC §6), not this log alone.
