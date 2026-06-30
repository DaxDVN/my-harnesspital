# HARNESS-GUIDE — how to use this harness (the MAP)

One discoverable page. You prompt in natural language; the harness picks the right machinery. You do **not**
memorize skill names. For the component INVENTORY (who composes what), read `engine/REGISTRY.md`. For the law,
`AGENTS.md` + `engine/rules/`. This file is the map between them.

## 1. One front door

Describe the work in plain language (Vietnamese or English). The **PM orchestrator** is the single front door: a
*blind, stateless* coordinator that classifies risk + complexity, picks a **recipe** (an ordered phase plan),
assigns each phase a `(model, effort)` tier, and dispatches workers **gate-by-risk** — one worker per tick, from
its own main loop. It never reads worker output, source, or rules; it routes file PATHS + compact status through
a ledger and a context-manifest. You hold the steering wheel (it stops at risky gates); it holds the recipe.

Today the PM is owner-invoked (see §7). The router still predicts the same recipe for any prompt:
`python scripts/harness_router.py "<prompt>"` then `python scripts/harness_preflight.py "<prompt>"`.

## 2. What each kind of work does

Recipe names below are exactly the `recipes` in `engine/workflows/pm-orchestrator/manifest.json`.

| You say… | Recipe | What happens (1 line) |
|---|---|---|
| "review / audit module X before merge" | `review` | Freeze scope → `deep-review` (D1–D7) → findings md. Read-only. |
| "fix this bug" (known repro) | `bugfix` | `mh-rca` (RCA) → `mh-fix` in a worktree → `deep-review` confirms no regression. |
| "fix this LIST of bugs" | `batch-bugfix` | An analyst reads+adjudicates the list ONCE (real vs false-positive, deduped, each tagged complexity→tier) → fan-out one fixer per bug at its own tier, BE→DTO→FE → fresh-context review. |
| "drive it to clean / lặp tới sạch" | `espresso` | review→fix→re-review **loop** until 0 BLOCK/HIGH open or round cap. Reuses `espresso-test` verbatim. |
| "build feature / module Y" (from a BA doc) | `feature` | distill BA→`02-requirements` (read-once) → spec (`ui-spec`/`technical-design`) → `task-slicing` → fan-out `mh-implementer` per slice → `espresso` converge. |
| "small change / extend this component" | `single-skill` | One `mh-implement` (or `mh-fix`) makes the change + self-reviews its own diff. No separate review pass. |
| "change this shared API/DTO/permission" | `implement+review` | `mh-implement` → a SEPARATE `deep-review` to catch regressions in callers. |
| "design only, don't build yet" | `design-only` | distill + spec (`ui-spec`/`technical-design`) → STOP. Produces specs for owner approval, no code. |
| "is this bug list real? don't fix" | `triage-only` | `mh-rca` + `mh-reviewer` verify each item real/false-positive/needs-evidence. Zero edits. |
| "refactor X" | `single-skill` or `implement+review` | Small/local → `single-skill`; shared/cross-file/contract → `implement+review` (so callers get reviewed). |
| "redesign this clinical screen" | (skill, not a PM recipe) | `clinical-ui-design` drives the live screen + emits before/after HTML mocks to `docs/ui-mocks/` for you to pick a direction; THEN build via `feature`/`single-skill`. |
| "workflow X broke / fix the harness" or "this repeats, build a workflow for it" | `adapt` (owner-gated meta-workflow) | Mode A: RCA + patch a failing workflow (≥2 same root-cause). Mode B: design + build a new workflow for a repeated pattern (≥3, conflict-checked). POST-run, six safety gates, owner approves every apply. |

## 3. Gate-by-risk (when it asks vs. just runs)

The PM **auto-runs** a phase when it is read-only (any tier — reading can't damage) OR `risk_tier ∈ {T0,T1}` and
reversible/worktree-bounded. It raises a **HARD owner-confirm** before a SOURCE-EDITING phase when
`risk_tier ∈ {T2,T3}` AND `risk_class ∈ {clinical, billing, permission, migration, irreversible-data}`, OR when
the phase dispatches an owner-gated workflow (`technical-design`, `task-slicing`, `ui-spec`, `dev-from-handoff`,
`robust-test`). `promote` is never dispatchable; the PM dispatches `mh-implement`, never `incremental-impl`.
Source: `manifest.json#gate_by_risk` (locked, plan sec.6.B).

## 4. Model tiers (who gets which model)

From `scripts/tier_policy.json`, keyed per phase/slice/bug — never baked into a workflow:

- **risk_tier:** T0 → `haiku/low` · T1 → `sonnet/medium` · T2 → `sonnet/high` · T3 → `opus/high`.
- **complexity** (batch-bugfix / per-slice): complex → `opus` · medium → `sonnet` · simple/layout → `haiku`.
- **risk_class floor:** clinical/billing/permission/migration always lifts to `opus/high`.
- **orchestrator** itself runs `opus/low` (cheap to coordinate); workers run at their per-task tier.

## 5. New machine (one command)

`just bootstrap` (idempotent) or `just bootstrap --check` (prereqs + doctor only, no mutation). What **travels**
in git is small (~4 MB: `engine/`, `scripts/`, `main-brain/`, `docs/`, configs). What **regenerates locally** and
is never copied: `node_modules/`, the product repos `myhospital-fe`/`myhospital-be`, `worktrees/` + DB slots, and
the machine-specific graphify / CodeGraph indexes (all gitignored). Bootstrap auto-runs safe installs and prints
the exact clone/worktree/index commands for the rest, then runs the doctor.

## 6. Where things live

- `engine/skills/` — **capabilities** + entry skills (`mh-review` `mh-implement` `mh-fix` `mh-scaffold` `bug-fix` `espresso-test` `pm-orchestrator` `ui-spec` `technical-design` `task-slicing` `ponytail` `promote` `mh-debrief`).
- `engine/workflows/` — **engines** (one folder + `manifest.json` each): `deep-review` (review), `espresso-test` (loop), `pm-orchestrator` (the front door), SDD set, `bug-fix`, `robust-test`, `adapt` (meta — harness self-repair/extend).
- `engine/agents/` — **workers** the workflows fan out: `mh-reviewer` `mh-implementer` `mh-rca` `mh-rule-auditor` + `distiller` (reads a BA doc once).
- `engine/prompts/` — copy-paste runbooks: top-level = WIRED (router-dispatchable), `governance/` = harness-maintenance, `manual/` = read-only by-hand.
- `engine/rules/` — convention canon + policies (loaded scope-split; precedence in `rules/README.md`).
- `scripts/` — `harness_router.py` · `harness_preflight.py` · `tier_policy.json` · `bootstrap.py` · `harness_doctor.py` (+ `rule_card.py`, `worktree.py`).
- `main-brain/` (gated source-of-truth) · `second-brain/` (provisional learnings) — memory tiers.
- `docs/harness/` — plans · notes · evals · archive (history, not law).

## 7. Current status (honest)

The PM front door is **`auto_route_allowed: false`** — so today you **invoke it explicitly**
(`/pm-orchestrator` or "PM run …"), and natural-language prompts are routed by `harness_router.py` /
preflight, then run by the matching skill/workflow. The mechanism is proven end-to-end on a read-only run;
the full populated implement fan-out has not been re-run. To flip "prompt naturally → auto-fires": set
`auto_route_allowed: true` in the manifest. Until then, treat §1–2 as how the harness *chooses* — you still press start.
