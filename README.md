# rsi-skills — the RSI layer for Agent Skills

Use the Skill pattern, then study it: this pack adds a **Recursive Self-Improvement** core to any skill library. Every included skill logs its triggers anonymously, and only after evidence gates green does it write typed edit proposals for its own author. It never writes code at runtime.

Built by the Anos Cranel desk; licensed MIT.

## What you get

- `skills/ac-rsi/` — the shared core skill (immutable at runtime) plus the event-log **schema**.
- `docs/SPEC-rsi-skills.md` — the stage ladder and the guardrails (what Stage 2 may and may not do).

## The pattern

```
  skill triggers  →   append-only ledger (leaf-events.jsonl)
                                   │
                  Stage 1 bars: ≥100 events/skill, 95% independent outcomes
                                   │
                validators score them  →  typed edit cards (never auto-applied)
                                   │
                        human review decides each card
```

The core hard rules stand:

1. **Immutable at runtime** — the core never edits, deletes or truncates itself or a sibling skill.
2. **Outcome Independence** — `task_outcome` and `validator_verdict` are written by the harness or an independent validator, never by the skill that was measured.
3. **Fail-closed** — an inconclusive signal produces nothing (not a proposal with a maybe).

## Install (opencode/Claude-style agents)

1. Place `skills/ac-rsi/` in your skills directory (Termux/opencode: `~/.agents/skills/ac-rsi/`; Claude Code: `<dir>/.claude/skills/ac-rsi/`).
2. Restart / reload. The skill claims only the `rsi` domain, so it never collides with craft skills.

From Stage 1 on, new skills you build may add a `00-rsi` leaf that follows the schema in `skills/ac-rsi/schema/log-schema.md`.

## Version

0.1.0 — Stage 1 only. The optimizer (Stage 2) is not included.

## License

MIT (© Anos Cranel 2026) — see LICENSE.
