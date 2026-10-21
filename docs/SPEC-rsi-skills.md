---
status: draft
date: 2026-10-08
type: specification
---

# SPEC — RSI Skills: Recursive Self-Improvement as the universal #1 subskill

> **Scope.** This is the architecture standard for a Recursive Self-Improvement (RSI)
> capability shipped as the first subskill (`00-rsi`) of every skill-with-subskills we
> author. It is NOT an installable skill. Building it requires human approval.

## 0. The one-sentence verdict (read this first)

A universal per-skill RSI leaf is feasible and safe TODAY **only in log-and-propose
form.** The leaf OBSERVES and PROPOSES; it never rewrites or reinstalls itself. This is
not the diluted version of the vision — per the evidence it **is** the vision, at the
highest automation level that survives an adversarial audit (see References).

**What "succeeds" means (condition made testable; ⚠️ the thresholds below are the pack owner's choices, no published basis — revisit after the pilot):** the RSI
capability succeeds when ALL of these hold across a ≥30-day measured window on the pilot
skills, against a pre-RSI baseline:
- **Trustworthy log:** ≥100 leaf events per pilot skill. Of those, ≥95 in every 100 have
  exactly one harness outcome record with the same sessionID and callID, written by a
  recorder the agent cannot write to (a different uid, or a hash chain anchored outside the
  agent's reach). Zero breaks in the chain. The improvement margin is fixed in a dated file
  before the window opens.
- **Replicated improvement:** ≥1 typed edit proposal passes the human+validator gate AND
  measurably improves the fired-leaf outcome rate (§6's honest metric) by that pre-registered
  margin, replicated on BOTH pilot skills — not a single lucky prune on one.
- **No safety regression:** zero poison-tripwire fires, zero unauthorized writes attributed
  to the RSI leaf or core across the window. ⚠️ No write monitor exists yet, so this bar
  cannot be measured until one is built.

**Status today:** no pilot skill logs leaf events yet, and no recorder ships with this
repo, so none of these gates can be checked yet.

**Failure handling:** if Stage 2 does not meet these bars by the window's end, the result
is STOP-and-report (RSI stays a pilot or is retired) — NOT retry-forever until a lucky
run passes. **Full runtime self-rewrite is explicitly OUT of scope and out of "success"** —
no published system does it safely for unverifiable rewrites (§4).

## 1. Definitions

- **RSI leaf (`00-rsi`)** — a per-skill subskill that logs its skill's routing events.
  It writes no proposals; from Stage 2 the shared core turns the logs into typed edit
  proposals. Domain segment `rsi`. First leaf in the index.
- **Shared RSI core (`ac-rsi/`)** — a single, separately-installed, **immutable-at-runtime**
  skill that owns the log schema, the outcome-scoring, the offline optimization pass, and
  the proposal format. Audited once; no skill ever rewrites it. The Voyager/overlay pattern
  (the agent program is fixed; only an append-only library changes — no in-place rewrite of stored skills by design (Voyager admits new skills after GPT-4 self-verification, so admission is still same-model-judged); lower-risk, not zero-risk; Voyager, arXiv 2305.16291).
- **Typed edit proposal** — a machine-checkable patch to a skill's routing text or leaf
  content, of a declared type (see §5). Emitted as an evidence card, never applied by RSI.
- **Entrance / trigger-rate** — whether the correct subskill fires and helps. The standing
  unmeasured flank (the open problem in the subskills spec). RSI narrows it: the log measures fired-leaf outcome rate; trigger recall needs §6's offline paired replay.

## 2. The architecture (three cooperating parts)

```
<skills-dir>/                         # e.g. ~/.agents/skills/ (opencode)
├── ac-rsi/                           # SHARED CORE — installed once, immutable at runtime
│   ├── SKILL.md                      # how to run an optimization pass + read the log
│   ├── schema/log-schema.md          # the event-log format every skill appends to
│   ├── scripts/optimize.py           # Stage 2, not built
│   └── scripts/score.py              # Stage 2, not built
│
└── <any-skill>/                      # EVERY pipeline skill
    ├── SKILL.md                      # index lists 00-rsi FIRST
    └── subskills/
        ├── 00-rsi.md                 # THE RSI LEAF (this spec) — observe + propose only
        └── …task leaves…
```

The **shared core holds the machinery** (no domain claim → no Rule 4 collision); each
**skill's `00-rsi` leaf holds only its own log and metric bindings**
(scope = "observe THIS skill's triggers/leaves" → Rule 4 satisfied).
This is exactly how Voyager's library sits outside the agent program (Voyager, arXiv 2305.16291).

## 3. The `00-rsi` leaf (what every skill carries)

Mandatory routing header, then a short body. First in the index (by design).

```markdown
---
name: 00-rsi
domain: rsi                            # reserved top segment; NOT the parent's domain
trigger: Always — passively, after any leaf in this skill fires, to log the event.
anti_trigger: Never blocks a task; never rewrites a file; never installs anything.
scope: Append this skill's routing events to the central log. Queue nothing in
       Stage 1. From Stage 2, proposals are written only by the ac-rsi core, to a path
       the Stage 2 spec must define before Stage 2 opens. Acts on no other skill and on
       no shared core.
status: seedling
---

# RSI — self-improvement logger + proposer (this skill only)

This leaf NEVER edits a file, NEVER installs, and NEVER blocks a task. It only appends
and proposes.

## On every routing event (append-only — a hard rule, not just an instruction)
Append one line to `~/.local/share/opencode/rsi/leaf-events.jsonl` (opencode default; set your harness's equivalent; outside every skill tree) with `{ ts, skill, leaf_routed, trigger_text, model, sessionID, callID }`. Never write a file inside a skill tree at run time.
This leaf NEVER edits, deletes, or truncates any file — including the log itself
(a hard rule in SPEC-rsi-skills §4 rule 1; nothing enforces it at runtime yet).
Outcome records are written by the HARNESS or validator, NOT by this skill —
a skill never records its own outcome (SPEC-rsi-skills §4 rule 3).

## Stage 2 only (propose, never apply)
This leaf writes no proposals. From Stage 2, when the operator (or the shared `ac-rsi`
core on a schedule) runs an optimization pass, the core writes the typed edit proposals
for THIS skill as evidence cards. Nothing applies them. Every proposal goes to the
human+validator gate (§4 rule 5).
```

Why `domain: rsi` and not the parent's domain: an RSI leaf *observes and proposes* rather
than *acts in the domain*. Giving it the reserved `rsi` top segment keeps routing honest —
it never competes with a task leaf for a trigger, and it structurally cannot widen the
parent's claimed domain (goal drift at the routing layer is blocked).

## 4. Closed-loop SAFETY (the load-bearing section)

A self-modifying artifact is the highest-risk kind. These are the hard, non-negotiable
rules, each tied to the evidence. They bind every implementation. Today most of them are
written rules only; rule 1 says what is and is not enforced.

1. **No runtime self-rewrite, ever — and the log is append-only.**
   The `00-rsi` leaf and the `ac-rsi` core never edit, delete, or truncate ANY file at
   runtime — not a skill file, not a non-skill file, and not the central leaf-events log itself.
   Today append-only is a written rule that nothing enforces at runtime. The lint
   (agent-skills-subskills `lint_tree.py`) checks the leaf's static shape only. The runtime
   safeguards are the harness recorder's hash chain (it detects edits but cannot stop them)
   and human review. Before Stage 2, the log must move outside the agent's write reach.
   RSI *proposes*; the
   human+validator gate *disposes*. (No published system self-installs **unverifiable**
   rewrites safely — see DGM, arXiv 2505.22954, and SGM, arXiv 2510.10232; verified-rewrite
   self-install under sandbox + oversight, à la DGM, is the lab exception, not our case.)
2. **No same-model self-grading as the admission signal.** A skill must not grade its own
   rewrites — spontaneous reward hacking arises in-context even with no adversary (Pan et
   al., arXiv 2402.06627). The scoring signal must be **independent of the artifact**:
   recorded task outcomes (exit codes, validator verdicts, user follow-ups), not the
   skill's self-judgment. **And the outcome must be RECORDED independently too** — see rule 3.
3. **No self-selected benchmark as the sole validator — and no self-recorded outcome.**
   Self-evaluation loops are poisonable and contaminated lineages persist (Roesner & Kohno,
   arXiv 2609.17817). Our inference from their attack (not their wording): a design is exposed when the skill's own
   log is **both the metric and the training signal without independent validation.** So:
   (a) every proposal gets a validator ≠ producer review; AND (b) the **outcome signal
   must be recorded OUTSIDE the skill's own append path** — written by the harness or the
   validator, not by the same agent that benefits from a favorable log — **plus periodic
   held-out re-runs** as a poison tripwire. Reviewer-independence alone does not
   decontaminate poisoned source data; the DATA's independence is the requirement.
4. **Immutable core.** The `ac-rsi` shared core is never rewritten by any skill at runtime.
   Updates to the core itself go through the full `ac-subskills-author` audit pipeline as a
   normal (human-gated) skill change.
5. **Fail-closed, evidence-carded.** Every optimization pass and every proposal is
   recorded as an evidence card for human review. An inconclusive signal = no proposal,
   not a maybe.
6. **Drift tripwire.** A skill whose routing/content has drifted far from its last-audited
   state (too many queued additive proposals, or a trigger edited beyond a bound) is
   flagged for full re-audit, not allowed to keep self-tuning. (Occupancy-measure
   regularization to a reference policy — Correlated Proxies, arXiv 2403.03185.)

## 5. Typed edit proposals (prune-lane preferred)

Proposals are typed so they are machine-checkable and so risk is priced by type. Per
ClawTrace (arXiv 2604.23853): **"preserve" patches drove all quality regressions
(3 of 3, one benchmark); "prune" patches acted as guardrails.** So:

| Type | What it changes | Risk | Review lane |
|------|-----------------|------|-------------|
| **prune** | narrows/removes trigger text or leaf content | lowest | default lane — fast human approve |
| **repair** | fixes a broken/contradictory trigger or stale fact | medium | standard validator review |
| **preserve (keep observed behaviour)** | keeps observed successful behaviour as trigger text or content | highest | **strictest** — full audit pass |

Repair is the type that adds steps. Preserve stays the strictest lane.

Additive proposals are the exception, not the default. The optimizer (offline bandit /
GEPA-style; GEPA, arXiv 2507.19457) emits prune-lane proposals first.

## 6. The measurement hook (the subskills spec's open measurement problem)

The RSI leaf's log is the instrument for the measurement problem — but it can only measure
**what fired and how it ended**, not "was the RIGHT leaf selected." Those are different
quantities, and conflating them is the trap this section must avoid.

- **Per-event:** which leaf fired, the trigger text, the outcome, the validator verdict,
  the model. Schema in `ac-rsi/schema/log-schema.md`. **The outcome fields are written by
  the harness/validator, outside the skill's own append path (§4 rule 3)** — otherwise the
  log is both metric and training signal, the exact Roesner & Kohno poisoning trap.
- **What the log CAN measure (the honest metric): fired-leaf outcome rate** — of the
  routings that happened, how often did the fired leaf help? This is real and useful.
- **What it CANNOT measure alone: trigger/recall** — "would a DIFFERENT leaf (or no leaf)
  have done better?" needs a counterfactual the firing-trace doesn't contain. So the spec
  claims **fired-leaf outcome rate**, NOT trigger recall, as the measured quantity.
- **The counterfactual mechanism (for the recall question, offline only):** the shared
  core runs **paired replay** à la SkillsBench (arXiv 2602.12670): on a held-out task set,
  run each task once with the routed leaf and once against candidate/alternate routings
  (or no skill), comparing outcomes — an offline A/B, never a live self-experiment. The
  bandit/GEPA optimizer tunes trigger/description WORDING against this offline signal, not
  against the live log alone. Held-out re-runs are the poison tripwire (§4 rule 3).
- Stage 1 has no data for this metric: leaf events are not yet logged.
- **Evaluator independence:** outcome = independently-recorded signal (exit code,
  validator verdict, harness follow-up), never the skill's self-rating (§4 rules 2–3).
- **Aggregation is a liability, stated honestly:** the shared core aggregates logs across
  skills — that makes the CORE a high-value behavioral-telemetry store. It is protected
  from *rewrites* (§4 rule 1) but aggregation itself is a sensitive-read surface: the core
  reads logs only to produce proposals, never exposes raw cross-skill telemetry outward,
  and its read scope is part of its own audit.
- **Honest gap:** no published system measures routing recall as a first-class production
  metric; the pieces exist (paired offline evals, online bandits, FSM monitors) but the
  composition is novel (⚠️ absence claim, not independently verified). We build a new
  combination.

## 7. The path to "#1 subskill in every skill"

RSI is adopted in stages; promotion to universal #1 is gated on the quantitative bars in
§0, not on vibes. **Interpretation of the goal:**
"#1 subskill in every skill" is taken to mean every NEW skill ships `00-rsi` by default
and existing pipeline skills get it backfilled — the achievable form of "every."

- **Stage 0 (this spec):** standard only. Stage 1 is approved but not measurable yet.
- **Stage 1 (pilot):** add `00-rsi` to two skills (`ac-subskills-author`, public;
  `ac-security-engineer`, not yet public) plus the `ac-rsi` core. Log passively, outcomes
  recorded by the harness. NO proposals yet. **Gate = the §0 "trustworthy log" bar**
  (≥100 leaf events/skill, ≥95 in 100 matched to one independent outcome record, zero
  chain breaks) over ≥30 days.
- **Stage 2 (propose):** turn on the offline optimization pass. **Gate = the §0
  "replicated improvement" + "no safety regression" bars.** Miss → STOP-and-report, not
  retry-forever.
- **Stage 3 (universal):** only on Stage-2 success, `ac-subskills-author`'s emit-tree is updated
  so every NEW skill ships `00-rsi` by default, and existing skills are backfilled. This
  is the "#1 subskill in every skill" end-state.

Each stage is human-gated. "Succeeds" is defined quantitatively in §0.

## 8. Interaction with the parent standard (subskills-architecture)

- **Rule 4 unique-scope:** satisfied — each `00-rsi` scopes to its own skill; the shared
  core claims no domain. No collision.
- **Closed enum:** requires minting **`rsi`** as a reserved top segment in
  `ac-subskills-author/subskills/domain-vocabulary.md`. The lint special-case is NARROW to prevent
  abuse: an `rsi`-segment leaf is legal **only** if (a) it is named `00-rsi`, (b) its
  `anti_trigger` matches the template ("never blocks a task; never rewrites a file; never
  installs anything"), and (c) its `scope` claims only its own skill (checked by lint as a heuristic; the manual review in audit-skill stage 5 is the binding check). Any other leaf
  claiming `domain: rsi/...` is a **lint error** — the carve-out cannot be used to park an
  out-of-domain leaf under `rsi`. The lint checks `rsi` leaves HARDER, not less.
- **Flat-first:** unchanged — `00-rsi` is one flat leaf, first in the index.
- **Bidirectional check:** `00-rsi.md` is indexed in SKILL.md like any leaf.
- **Audit posture:** the `rsi` core + every `00-rsi` leaf passes the robust `audit-skill`
  pipeline before install.

## 9. Explicit non-goals

- **No full RSI** (a skill that rewrites and reinstalls itself). Not shippable today even
  for code with perfect verifiers; for prose skills with fuzzy verifiers it is not
  defensible (see References).
- **No live in-session prompt self-edit that self-installs.** No published safe existence
  proof.
- **No same-model self-grading admission signal** and **no self-selected benchmark as sole
  validator** (both poisonable / reward-hackable).
- **No cross-skill action.** A skill's `00-rsi` touches only its own log and proposals.

## 10. Summary

The goal is an RSI leaf in every skill. The evidence says: the version
that can succeed *and* survive an audit is **log-and-propose** — `00-rsi` observes every
routing event (measuring fired-leaf outcomes on the trigger-rate flank; recall stays an offline measurement), and from Stage 2 the core proposes human-gated,
prune-first edits. That is genuinely self-improving and genuinely universal. The
stronger version — a skill that rewrites itself live — is what every credible source warns
against; building *that* would break this spec's fail-closed posture. So this
spec delivers the goal at its defensible maximum, and draws the line where the
evidence draws it.

## References

- DGM — Darwin Godel Machine: Open-Ended Evolution of Self-Improving Agents. https://arxiv.org/abs/2505.22954
- SGM — SGM: A Statistical Godel Machine for Risk-Controlled Recursive Self-Modification. https://arxiv.org/abs/2510.10232
- Voyager — Voyager: An Open-Ended Embodied Agent with Large Language Models. https://arxiv.org/abs/2305.16291
- GEPA — GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning. https://arxiv.org/abs/2507.19457
- SkillsBench — SkillsBench: Benchmarking How Well Agent Skills Work Across Diverse Tasks. https://arxiv.org/abs/2602.12670
- Roesner & Kohno — Reflections on Trusting Trust, Revisited: Contaminating Self-Modifying AI Coding Agents with Poisoned Benchmarks. https://arxiv.org/abs/2609.17817
- Pan et al. — Feedback Loops With Language Models Drive In-Context Reward Hacking. https://arxiv.org/abs/2402.06627
- Correlated Proxies — Correlated Proxies: A New Definition and Improved Mitigation for Reward Hacking. https://arxiv.org/abs/2403.03185
- ClawTrace — ClawTrace: Cost-Aware Tracing for LLM Agent Skill Distillation. https://arxiv.org/abs/2604.23853
