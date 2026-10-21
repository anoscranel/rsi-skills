
# rsi-skills

The RSI layer for Agent Skills: a pinned experiment protocol for skills that observe their own trigger/outcome events and, only when the evidence gates green, write typed edit proposals to their author.

The pack carries the role that gives the system its name: `ac-rsi`, the shared core; plus the spec and the two reference `00-rsi` leaves that evidence what the pattern looks like on a live skill.

## What's inside

```
skills/
  ac-rsi/          the shared core. See architecture below.
    SKILL.md
    schema/log-schema.md   the event-log format every RSI leaf appends to (append-only, never the skill's own outcome)
docs/
  SPEC-rsi-skills.md    guardrails, stage gates, what Ske-2 builds are permitted under what evidence bars
```

## The two living reference leaves

| Skill | leaf | note |
|---|---|---|
| ac-subskills-author | `subskills/00-rsi.md` | meta-skill's logger leaf |
| ac-security-engineer | `subskills/00-rsi.md` | the pilot companion |

The leaves are pinned and immutable at runtime. Both log routing events to the same shared ledger (`~/.local/share/opencode/rsi/leaf-events.jsonl`), never to their own files.

## Stage posture

- **Stage 1 (NOW):** log-only. The core provides the schema and reads logs. It writes no proposals and runs no optimizer.
- **Stage 2 (gated):** an offline optimizer turns the trustworthy log (≥100 events, ≥95% independent outcomes) into typed edit proposals as evidence cards, never auto-applied. Every proposal passes human review.
- **Stage 3 (universal):** only on Stage-2 success does new skill authoring carry an `00-rsi` leaf by default.

## The rules that keep it safe (SPEC §4)

1. Nothing rewrites itself at run time; logs are append-only.
2. A skill never rates itself; the outcome column is written by the harness / a validator, never by the leaf.
3. An inconclusive signal = no proposal. Never a halfway course.
4. A skill whose triggers drift its account into a new area re-audits, not catches up.

## License

MIT (© Anos Cranel 2026)
