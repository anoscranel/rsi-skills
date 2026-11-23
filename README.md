# rsi-skills

A design for letting Agent Skills improve themselves safely: skills log how they are used, an offline pass proposes edits, and a human approves every change. Nothing ever rewrites itself at run time.

**Status: Stage 1 pilot — registered and open.** This repo ships the shared core skill, the event-log schema, the safety spec, one reference leaf-log writer (`scripts/skill-observer.py`, operator-run), and the miss-rate scoring half (`scripts/miss-rate.py`). No proposal writer or outcome recorder ships — your harness must run the recorder, and the log's independence is caveated (see SPEC §0), so the pilot measures join-validity and attribution coverage, not certified tamper-evidence.

**Current release: v0.10.0.**

## What ships

| Path | What it is |
|---|---|
| `skills/ac-rsi/` | The shared core skill. It owns the event-log schema. It writes nothing. |
| `skills/ac-rsi/schema/log-schema.md` | Two record types: a *leaf record* (written by a skill) and an *outcome record* (written by the harness, never by the skill). They join on `sessionID` + `callID`; a leaf record with a null `callID` cannot join. |
| `docs/SPEC-rsi-skills.md` | The stage ladder, the success gates, the safety rules and the research they rest on (9 arXiv papers). |
| `scripts/gate-read.py` | A diagnostic join-report of the two logs (per-skill counts, join rate, chain continuity, trust tally). Diagnostic-only — it does not evaluate the §0 gate. It also reports activation counts (`--skill-events`/`--adapter`). |
| `scripts/skill-observer.py` | Emits leaf records from a session store using the schema's attribution rule. Read-only on the database; writes nothing but the leaf log. Reference producer — the operator runs it or does not. |
| `docs/PILOT-2026-11.md` | The registered pilot window (2026-11-19 → 2026-12-19): pilot skills, recorder identity, first chain hash, pre-registered improvement margin, and what the window can and cannot measure. |
| `scripts/miss-rate.py` | Scores the miss-rate protocol (steps 3–4): hit / miss / false-fire / unrun per labeled task, each as a fraction of N, with the label set pinned by sha256 so any relabel is detectable. Diagnostic — it does not certify ground truth. |
| `docs/miss-rate-seed.jsonl` | 16 desk-proposed expected-skill labels from real prompts, pending owner confirmation. Every label is `desk-proposed`; none is certified ground truth. |
| `CONTRIBUTING.md` | How to propose a change: issues only, human review, accepted scope. |

## What does not ship

- **An outcome recorder.** Your harness must run it, not the agent, so a skill can never grade itself. Without one, the spec's gates cannot be measured.
- **The Stage 2 optimizer.** It is not built.
- **An autonomous per-skill logger.** The operator-run `scripts/skill-observer.py` is the reference leaf producer; no harness switch makes a skill log on its own. The per-skill `00-rsi` leaf in [agent-skills-subskills](https://github.com/anoscranel/agent-skills-subskills/blob/main/skills/ac-subskills-author/subskills/00-rsi.md) defines the logging step but still needs a writer to run.

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
| 1 | Pilot skills log events; a harness recorder logs outcomes | Registered, window open (2026-11-19 → 2026-12-19) |
| 2 | Offline optimizer proposes edits; a human reviews each one | Not built; gated on Stage 1 data |
| 3 | Every new skill carries a `00-rsi` leaf | Only if Stage 2 succeeds |

## Install

1. Copy `skills/ac-rsi/` into your harness's skills directory (opencode: `~/.agents/skills/ac-rsi/` or the project's `.opencode/skills/ac-rsi/`; Claude Code: `~/.claude/skills/ac-rsi/`).
2. To log events, add a `00-rsi` leaf to a skill AND run a leaf writer (e.g. `scripts/skill-observer.py`); no harness switch exists today — nothing logs until a writer runs.
3. Add an outcome recorder that your harness runs. This repo does not provide one.

## Diagnostics

`python3 scripts/gate-read.py` joins the two logs (if present) and reports event counts, join rate, duplicate keys, and chain continuity across rotation boundaries — including the measured opencode rotation break. It is diagnostic-only: it does not evaluate the spec's §0 gate and writes nothing. To include rotated/older outcome files, pass `--outcome2 <path>` once per file (nearest-newest first, e.g. `--outcome2 harness-outcomes.jsonl.1 --outcome2 harness-outcomes.jsonl.2`); each adjacent pair is checked and labeled — order is taken as given, so listing `.2` before `.1` reports a meaningless break on every pair, and without the flag no rotation boundary is checked or reported.

Sample output (values from the reference device):

```
duplicate keys: 195 of 80,775 outcome keys
```

## License

Contributions follow [CONTRIBUTING.md](CONTRIBUTING.md).

MIT, © 2026 Anos Cranel. See [LICENSE](LICENSE).
