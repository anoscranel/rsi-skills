---
status: growing
op: rsi-skills
date: 2026-10-08
type: specification
depends: the subskills standard (its parent)
evidence: findings/001-rsi-prior-art.md (DGM/SGM/Voyager/GEPA/SkillsBench + safety line)
owner_mandate: "if it Succeeds it must be a #1 Subskill in Every Skill of our Pipeline"
---

# SPEC — RSI Skills: Recursive Self-Improvement as the universal #1 subskill

> **Scope.** This is the architecture standard for a Recursive Self-Improvement (RSI)
> capability shipped as the first subskill (`00-rsi`) of every skill-with-subskills we
> author. It is NOT an installable skill. Building it is a human gate (the pack's change-control rule (human gate)).

## 0. The one-sentence verdict (read this first)

A universal per-skill RSI leaf is feasible and safe TODAY **only in log-and-propose
form.** The leaf OBSERVES and PROPOSES; it never rewrites or reinstalls itself. This is
not the diluted version of the vision — per the evidence it **is** the vision, at the
highest automation level that survives an adversarial audit (findings/001 §RECOMMENDED).

**What "succeeds" means (condition made testable; ⚠️ the thresholds below are the pack owner's choices, no published basis — revisit after the pilot):** the RSI
capability succeeds when ALL of these hold across a ≥30-day measured window on the pilot
skills, against a pre-RSI baseline:
- **Trustworthy log:** ≥100 routing events logged per pilot skill, with ≥95% of outcome
  fields filled by the independent recorder (not the skill itself), zero append-only
  violations. ("Trustworthy" = independently-recorded outcomes + intact append-only history.)
- **Replicated improvement:** ≥1 typed edit proposal passes the human+validator gate AND
  measurably improves the fired-leaf outcome rate (§6's honest metric) by a pre-registered
  margin, replicated on BOTH pilot skills — not a single lucky prune on one.
- **No safety regression:** zero poison-tripwire fires, zero unauthorized writes attributed
  to the RSI leaf or core across the window.

**Failure handling:** if Stage 2 does not meet these bars by the window's end, the result
is STOP-and-report (RSI stays a pilot or is retired) — NOT retry-forever until a lucky
run passes. **Full runtime self-rewrite is explicitly OUT of scope and out of "success"** —
no published system does it safely for unverifiable rewrites (§4).

## 1. Definitions

- **RSI leaf (`00-rsi`)** — a per-skill subskill that logs its skill's trigger/outcome
  events and queues typed edit proposals. Domain segment `rsi`. First leaf in the index.
- **Shared RSI core (`rsi/`)** — a single, separately-installed, **immutable-at-runtime**
  skill that owns the log schema, the outcome-scoring, the offline optimization pass, and
  the proposal format. Audited once; no skill ever rewrites it. The Voyager/overlay pattern
  (the agent program is fixed; only an append-only library changes — no in-place rewrite of stored skills by design (Voyager admits new skills after GPT-4 self-verification, so admission is still same-model-judged); lower-risk, not zero-risk, findings/001 §1).
- **Typed edit proposal** — a machine-checkable patch to a skill's routing text or leaf
  content, of a declared type (see §5). Emitted as an evidence card, never applied by RSI.
- **Entrance / trigger-rate** — whether the correct subskill fires and helps. The standing
  unmeasured flank (SPEC-subskills §7). RSI narrows it: the log measures fired-leaf outcome rate; trigger recall needs §6's offline paired replay.

## 2. The architecture (three cooperating parts)

```
~/.agents/skills/
├── rsi/                              # SHARED CORE — installed once, immutable at runtime
│   ├── SKILL.md                      # how to run an optimization pass + read the log
│   ├── schema/log-schema.md          # the event-log format every skill appends to
│   ├── scripts/optimize.py           # offline bandit/GEPA pass → typed proposals
│   └── scripts/score.py              # outcome scoring from INDEPENDENT signals
│
└── <any-skill>/                      # EVERY pipeline skill
    ├── SKILL.md                      # index lists 00-rsi FIRST
    └── subskills/
        ├── 00-rsi.md                 # THE RSI LEAF (this spec) — observe + propose only
        └── …task leaves…
```

The **shared core holds the machinery** (no domain claim → no Rule 4 collision); each
**skill's `00-rsi` leaf holds only its own log, metric bindings, and proposal queue**
(scope = "observe and propose edits to THIS skill's triggers/leaves" → Rule 4 satisfied).
This is exactly how Voyager's library sits outside the agent program (findings/001 §5.1).

## 3. The `00-rsi` leaf (what every skill carries)

Mandatory routing header, then a short body. First in the index (the pack's #1 mandate).

```markdown
---
name: 00-rsi
domain: rsi                            # reserved top segment; NOT the parent's domain
trigger: Always — passively, after any leaf in this skill fires, to log the event.
anti_trigger: Never blocks a task; never rewrites a file; never installs anything.
scope: Observe this skill's trigger/outcome events and queue typed edit proposals
       for THIS skill only. Acts on no other skill and on no shared core.
status: seedling
---

# RSI — self-improvement logger + proposer (this skill only)

This leaf NEVER edits a file, NEVER installs, and NEVER blocks a task. It only appends
and proposes.

## On every routing event (append-only — a hard rule, not just an instruction)
Append one line to `~/.local/share/opencode/rsi/leaf-events.jsonl` (outside every skill tree) with `{ ts, skill, leaf_routed, model, sessionID }`. Never write a file inside a skill tree at run time.
This leaf NEVER edits, deletes, or truncates any file — including the log itself
(append-only is enforced as a hard rule in SPEC-rsi-skills §4 rule 1, not merely stated here).
The `task_outcome` field is filled by the HARNESS or validator, NOT by this skill —
a skill never records its own outcome (SPEC-rsi-skills §4 rule 3).

## On demand (propose, never apply)
When the operator (or the shared `rsi` core on a schedule) runs an optimization pass,
this leaf surfaces the typed edit proposals queued for THIS skill as evidence cards.
It does NOT apply them. Every proposal goes to the human+validator gate (§6).
```

Why `domain: rsi` and not the parent's domain: an RSI leaf *observes and proposes* rather
than *acts in the domain*. Giving it the reserved `rsi` top segment keeps routing honest —
it never competes with a task leaf for a trigger, and it structurally cannot widen the
parent's claimed domain (goal drift at the routing layer is blocked, findings/001 §5.6).

## 4. Closed-loop SAFETY (the load-bearing section)

A self-modifying artifact is the highest-risk kind. These are the hard, non-negotiable
rules, each tied to the evidence:

1. **No runtime self-rewrite, ever — and append-only is a hard rule, not an instruction.**
   The `00-rsi` leaf and the `rsi` core never edit, delete, or truncate ANY file at
   runtime — not a skill file, not a non-skill file, and not the central leaf-events log itself. The
   log's append-only property is enforced here as a load-bearing rule (instructions are
   what drift eats first), not merely asserted in the leaf body. RSI *proposes*; the
   human+validator gate *disposes*. (No published system self-installs **unverifiable**
   rewrites safely — findings/001 §1, §2; verified-rewrite self-install under sandbox +
   oversight, à la DGM, is the lab exception, not our case.)
2. **No same-model self-grading as the admission signal.** A skill must not grade its own
   rewrites — spontaneous reward hacking arises in-context even with no adversary (Pan et
   al., findings/001 §2). The scoring signal must be **independent of the artifact**:
   recorded task outcomes (exit codes, validator verdicts, user follow-ups), not the
   skill's self-judgment. **And the outcome must be RECORDED independently too** — see rule 3.
3. **No self-selected benchmark as the sole validator — and no self-recorded outcome.**
   Self-evaluation loops are poisonable and contaminated lineages persist (Roesner & Kohno,
   findings/001 §2). Our inference from their attack (not their wording): a design is exposed when the skill's own
   log is **both the metric and the training signal without independent validation.** So:
   (a) every proposal gets a validator ≠ producer review; AND (b) the **outcome signal
   must be recorded OUTSIDE the skill's own append path** — written by the harness or the
   validator, not by the same agent that benefits from a favorable log — **plus periodic
   held-out re-runs** as a poison tripwire. Reviewer-independence alone does not
   decontaminate poisoned source data; the DATA's independence is the requirement.
4. **Immutable core.** The `rsi` shared core is never rewritten by any skill at runtime.
   Updates to the core itself go through the full `skill-author` audit pipeline as a
   normal (human-gated) skill change.
5. **Fail-closed, evidence-carded.** Every optimization pass and every proposal is an
   evidence card on the op board — same posture as the auto-install audit
   (subskills-architecture Amendment 2). An inconclusive signal = no proposal, not a maybe.
6. **Drift tripwire.** A skill whose routing/content has drifted far from its last-audited
   state (too many queued additive proposals, or a trigger edited beyond a bound) is
   flagged for full re-audit, not allowed to keep self-tuning. (Occupancy-measure
   regularization to a reference policy — Correlated Proxies, findings/001 §2.)

## 5. Typed edit proposals (prune-lane preferred)

Proposals are typed so they are machine-checkable and so risk is priced by type. Per
ClawTrace/CostCraft (findings/001 §3): **"preserve" patches drove all quality
regressions; "prune" patches acted as guardrails.** So:

| Type | What it changes | Risk | Review lane |
|------|-----------------|------|-------------|
| **prune** | narrows/removes trigger text or leaf content | lowest | default lane — fast human approve |
| **repair** | fixes a broken/contradictory trigger or stale fact | medium | standard validator review |
| **preserve (keep observed behaviour)** | keeps observed successful behaviour as trigger text or content | highest | **strictest** — full audit pass |

Repair is the type that adds steps. Preserve stays the strictest lane (TD-22).

Additive proposals are the exception, not the default. The optimizer (offline bandit /
GEPA-style, findings/001 §4) emits prune-lane proposals first.

## 6. The measurement hook (closing SPEC §7)

The RSI leaf's log is the instrument for the measurement problem — but it can only measure
**what fired and how it ended**, not "was the RIGHT leaf selected." Those are different
quantities, and conflating them is the trap this section must avoid.

- **Per-event:** which leaf fired, the trigger text, the outcome, the validator verdict,
  the model. Schema in `rsi/schema/log-schema.md`. **The outcome fields are written by
  the harness/validator, outside the skill's own append path (§4 rule 3)** — otherwise the
  log is both metric and training signal, the exact Roesner & Kohno poisoning trap.
- **What the log CAN measure (the honest metric): fired-leaf outcome rate** — of the
  routings that happened, how often did the fired leaf help? This is real and useful.
- **What it CANNOT measure alone: trigger/recall** — "would a DIFFERENT leaf (or no leaf)
  have done better?" needs a counterfactual the firing-trace doesn't contain. So the spec
  claims **fired-leaf outcome rate**, NOT trigger recall, as the measured quantity.
- **The counterfactual mechanism (for the recall question, offline only):** the shared
  core runs **paired replay** à la SkillsBench (findings/001 §3): on a held-out task set,
  run each task once with the routed leaf and once against candidate/alternate routings
  (or no skill), comparing outcomes — an offline A/B, never a live self-experiment. The
  bandit/GEPA optimizer tunes trigger/description WORDING against this offline signal, not
  against the live log alone. Held-out re-runs are the poison tripwire (§4 rule 3).
- Stage 1 has no data source for this metric until leaf events are logged (see item 2).
- **Evaluator independence:** outcome = independently-recorded signal (exit code,
  validator verdict, harness follow-up), never the skill's self-rating (§4 rules 2–3).
- **Aggregation is a liability, stated honestly:** the shared core aggregates logs across
  skills — that makes the CORE a high-value behavioral-telemetry store. It is protected
  from *rewrites* (§4 rule 1) but aggregation itself is a sensitive-read surface: the core
  reads logs only to produce proposals, never exposes raw cross-skill telemetry outward,
  and its read scope is part of its own audit.
- **Honest gap:** no published system measures routing recall as a first-class production
  metric; the pieces exist (paired offline evals, online bandits, FSM monitors) but the
  composition is novel (findings/001 §3, ⚠️ absence-claim). We build a new combination.

## 7. The path to "#1 subskill in every skill" (the owner's mandate)

RSI is adopted in stages; promotion to universal #1 is gated on the quantitative bars in
§0, not on vibes. **Reading of the mandate (stated as an interpretation, honestly):**
"#1 subskill in every skill" is taken to mean every NEW skill ships `00-rsi` by default
and existing pipeline skills get it backfilled — the achievable form of "every."

- **Stage 0 (this spec):** standard only. Stage 1 built and authorised by the pack owner; its gates are not yet measurable.
- **Stage 1 (pilot):** add `00-rsi` to TWO pipeline skills (`skill-author`,
  `ag-security-and-hardening`) + the `rsi` shared core. Log passively, outcomes recorded
  by the harness. NO proposals yet. **Gate = the §0 "trustworthy log" bar** (≥100 events/
  skill, ≥95% independent outcomes, intact append-only) over ≥30 days.
- **Stage 2 (propose):** turn on the offline optimization pass. **Gate = the §0
  "replicated improvement" + "no safety regression" bars.** Miss → STOP-and-report, not
  retry-forever.
- **Stage 3 (universal):** only on Stage-2 success, `skill-author`'s emit-tree is updated
  so every NEW skill ships `00-rsi` by default, and existing skills are backfilled. This
  is the "#1 subskill in every skill" end-state.

Each stage is human-gated. "Succeeds" is defined quantitatively in §0.

## 8. Interaction with the parent standard (subskills-architecture)

- **Rule 4 unique-scope:** satisfied — each `00-rsi` scopes to its own skill; the shared
  core claims no domain. No collision.
- **Closed enum:** requires minting **`rsi`** as a reserved top segment in
  `skill-author/subskills/domain-vocabulary.md`. The lint special-case is NARROW to prevent
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
  defensible (findings/001 §RECOMMENDED).
- **No live in-session prompt self-edit that self-installs.** No published safe existence
  proof.
- **No same-model self-grading admission signal** and **no self-selected benchmark as sole
  validator** (both poisonable / reward-hackable).
- **No cross-skill action.** A skill's `00-rsi` touches only its own log and proposals.

## 10. Honest summary for the pack owner

You mandated "#1 subskill in every skill if it succeeds." The evidence says: the version
that can succeed *and* survive an audit is **log-and-propose** — `00-rsi` observes every
routing event (measuring fired-leaf outcomes on the trigger-rate flank; recall stays an offline measurement) and queues human-gated,
prune-first edit proposals. That is genuinely self-improving and genuinely universal. The
stronger version — a skill that rewrites itself live — is what every credible source warns
against; building *that* would betray the fail-closed posture we just hardened. So this
spec delivers the mandate at its defensible maximum, and draws the line where the
evidence draws it.
