# rsi-skills

A design for letting Agent Skills improve themselves safely: skills log how they are used, an offline pass proposes edits, and a human approves every change. Nothing ever rewrites itself at run time.

**Status: Stage 1, a specification.** This repo ships the shared core skill, the event-log schema and the safety spec. It does not ship anything that writes logs or proposals. No skill logs events yet, so none of the spec's success gates can be measured.

**Current release: v0.5.0.**

## What ships

| Path | What it is |
|---|---|
| `skills/ac-rsi/` | The shared core skill. It owns the event-log schema. It writes nothing. |
| `skills/ac-rsi/schema/log-schema.md` | Two record types: a *leaf record* (written by a skill) and an *outcome record* (written by the harness, never by the skill). They join on `sessionID` + `callID`. |
| `docs/SPEC-rsi-skills.md` | The stage ladder, the success gates, the safety rules and the research they rest on (9 arXiv papers). |
| `scripts/gate-read.py` | A diagnostic join-report of the two logs (per-skill counts, join rate, chain continuity, trust tally). Diagnostic-only — it does not evaluate the §0 gate. |
| `docs/PILOT-2026-11.md` | Pilot-window template (dates, skills, recorder, margin — owner-fillable). Not pre-registered until the owner fills and commits it. |
| `CONTRIBUTING.md` | How to propose a change: issues only, human review, accepted scope. |

## What does not ship

- **An outcome recorder.** Your harness must run it, not the agent, so a skill can never grade itself. Without one, the spec's gates cannot be measured.
- **The Stage 2 optimizer.** It is not built.
- **A skill that logs events.** One reference `00-rsi` leaf exists in [agent-skills-subskills](https://github.com/anoscranel/agent-skills-subskills/blob/main/skills/ac-subskills-author/subskills/00-rsi.md). It defines the logging step, but nothing in either repo has run it yet.

## The design

```
skill fires ──► leaf record (append-only log)
harness     ──► outcome record (independent; the skill cannot write it)
                      │  join on sessionID + callID
                      ▼
Stage 2 (not built): offline pass ──► typed edit proposals ──► human approves or rejects
```

The safety rules (spec §4) in brief:

1. Logs are append-only. Nothing edits a skill at run time.
2. A skill never records its own outcome. Outcomes come from the harness or an independent validator.
3. An inconclusive signal produces no proposal.
4. A skill whose triggers drift outside its scope goes back to full review.

Today these rules are written, not enforced. Only a lint checks the leaf's static shape. Before the Stage-1 gate is evaluated, BOTH files — leaf-events.jsonl and harness-outcomes.jsonl — must sit outside the agent's write reach, matching the §0 recorder bar.

## Stages

| Stage | What happens | Status |
|---|---|---|
| 0 | The spec | Done |
| 1 | Pilot skills log events; a harness recorder logs outcomes | Approved, not running |
| 2 | Offline optimizer proposes edits; a human reviews each one | Not built; gated on Stage 1 data |
| 3 | Every new skill carries a `00-rsi` leaf | Only if Stage 2 succeeds |

## Install

1. Copy `skills/ac-rsi/` into your harness's skills directory (opencode: `~/.agents/skills/ac-rsi/` or the project's `.opencode/skills/ac-rsi/`; Claude Code: `~/.claude/skills/ac-rsi/`).
2. To log events, add a `00-rsi` leaf to a skill AND enable RSI logging in your harness (default off — nothing logs until you enable it).
3. Add an outcome recorder that your harness runs. This repo does not provide one.

## Diagnostics

`python3 scripts/gate-read.py` joins the two logs (if present) and reports event counts, join rate, duplicate keys, and chain continuity across rotation boundaries — including the measured opencode rotation break. It is diagnostic-only: it does not evaluate the spec's §0 gate and writes nothing. To include a rotated/older outcome file (e.g. `harness-outcomes.jsonl.1`), run `python3 scripts/gate-read.py --outcome2 <path>` — without the flag no rotation boundary is checked or reported.

Sample output (values from the reference device):

```
duplicate keys: 195 of 80,775 outcome keys
```

## License

Contributions follow [CONTRIBUTING.md](CONTRIBUTING.md).

MIT, © 2026 Anos Cranel. See [LICENSE](LICENSE).
