# RSI event-log schema (v1)

Every skill's `00-rsi` leaf appends one **JSON Line** per routing event. Append one line to the central log outside the skill tree (path: `~/.local/share/opencode/rsi/leaf-events.jsonl` — opencode default; set your harness's equivalent). Never write a file inside a skill tree at run time. Append-only. One event per line, UTF-8, no trailing comma.

There are two record types in two files. The leaf writes leaf records to `leaf-events.jsonl`. An outcome recorder run by the harness, not the agent, writes outcome records to `harness-outcomes.jsonl` in the same directory. This repo does not ship that recorder. Join the two on `sessionID` + `callID`; do not join on time. A leaf record with a `null` `callID` is unjoinable by definition — count it as a miss, never as a match.

## Leaf record (written by the leaf)

| field | type | meaning |
|-------|------|---------|
| `ts` | ISO-8601 string | event time (UTC) |
| `skill` | string | the skill's `name` (e.g. `ac-subskills-author`) |
| `leaf_routed` | string \| null | **self-reported by the leaf; no harness event names a subskill leaf.** The leaf names the subskill it believes it used, or null if only SKILL.md applied. Never treated as independently recorded. |
| `trigger_text` | string \| null | the index row text, copied verbatim from SKILL.md by the leaf; never the user's words; the optimizer re-derives it from the skill file and ignores the logged value. Nullable: a writer that cannot read the index row (e.g. a harness plugin) writes `null` rather than guessing. |
| `model` | string \| null | the model that produced the routing. Nullable: absent from every `session.tool.*` payload, so a harness-plugin writer cannot supply it without a second join; write `null` rather than a guess. |
| `sessionID` | string | the harness session id |
| `callID` | string \| null | **beware the vacuous join.** A writer that copies `callID` from the routing tool call itself gets a record that joins the outcome log *by construction* — a 100% join rate meaning only "the routing call returned". That is not evidence the leaf did work. Nullable: a writer with no independent call id writes `null` (fails the join honestly). The §0 bar additionally requires the joined outcome to be a *different* record from the routing call's own entry. |

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

## Writer requirements (whichever component writes leaf records):

- `sessionID` — the harness session identifier, verbatim.
- `callID` — string or null. The id of a tool call the routed leaf itself issued, or null if the writer holds none. **Never the id of the call that routed to the leaf**: that id joins the routing outcome by construction, and SPEC §0 refuses it.
- `ts` — UTC, ISO-8601, from a clock the harness provides; never the model's guess.

These are requirements; only `callID` may be null, for the reason above. No route (leaf-side vs harness-side logging) is implied.

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

## Attribution rule (observer-written leaf records, v1)

An observer that reads a session store (rather than living inside the harness process) must
convert an *activation* into a *leaf record*. The rule is fixed here so two observers cannot
disagree, and so the result cannot be the vacuous join.

Given activation `A` (skill `S`, session `X`, sequence `seq_A`):

1. Find the **first** tool call `T` in session `X` with `seq > seq_A`. An *activation* is not
   a tool call for this purpose: a later `skill` part must be skipped, or two consecutively
   activating skills swap attribution. Scan at most the next 40 assistant messages (the rows tool parts live in); if no eligible call
   appears in that window, treat the activation as unjoinable (step 3).
2. If `T` exists: write a leaf record `{ts: A.time, skill: S, leaf_routed: null,
   trigger_text: null, model: A.model, sessionID: X, callID: T.id}`.
3. If no such `T` exists: write the same record with `callID: null`.

**Never use `A`'s own call id** — that id names the call that *loaded* the skill, and joining
it reproduces the vacuous join (`SPEC §0` refuses it).

**Collision downgrade.** When several skills activate in one turn, rule 1 can attribute more
than one skill to the same call. A call id claimed by two skills is evidence for neither, so
it is written as `callID: null` — an honest miss. Measured 2026-11-12 (earlier same-day probe window, pre-influx): 8 of 100
distinct ids were shared, so this is not hypothetical.

⚠️ **This rule is an inference, not a measurement.** "The first tool call after activation" is
a defensible attribution, not proof that the leaf caused that call. A leaf that reasons without
calling any tool produces `callID: null` (step 3) and therefore counts as a **miss** under
`SPEC §0` — which is the correct conservative treatment, not a bug.

⚠️ Consequence: observer-written leaf records systematically under-count successful leaves,
because reasoning-only leaves are indistinguishable from leaves that did nothing. State the
observed rate as a **lower bound** on fired-leaf success, never as the rate.

**Where the rule comes from:** measured 2026-11-12 against this device's session store —
22 `skill` activations in 14 days (earlier same-day probe, 2026-10-29 → 2026-11-12; the since-Nov-1 window holds 111), each with its own call id, name, `state.input.id`, `status`
and `data.model.id`. The store supplies `model`, which an in-process harness writer cannot reach.
