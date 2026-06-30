# pm-orchestrator

Authoritative workflow doc: `engine/workflows/pm-orchestrator/README.md`.
Ledger convention: `engine/rules/orchestrator-ledger.md` · memory-by-reference: `engine/rules/context-manifest.md`.

## Required Behavior

- Owner invocation starts the run (`manual_only`). The PM is the one sanctioned auto-route, but a *run* is
  owner-started; gated workflows inside a recipe still owner-confirm per phase.
- **Gate inputs before tick 1:** task scope; `recipe` (preset `review|espresso|bugfix|feature` or a custom
  ordered phase list); review/scope `base`; ACTIVE worktree slug+slot (required for any source-editing phase);
  `tier_policy` (from `scripts/tier_policy.json`, keyed by `risk_tier`); per-phase `risk_tier` + `risk_class`;
  phase/round cap. No worktree for a source-editing recipe → **STOP** (`BLOCKED`).
- **Run start:** create the run folder + `00-pm-state.md` ledger from `templates/pm-state-template.md`, and write
  the ledger path into `.claude/.pm-run-active` (the marker that gates the invariants hook). Remove the marker at
  run end.
- You are the **coordinator**. The per-tick loop:

## Per-Tick Loop

1. **RE-READ the ledger** (`00-pm-state.md`) and re-derive current state from it. Never trust in-context memory
   of run state (stateless-over-ledger).
2. **Resolve the next phase** from the recipe (the first phase whose `done?` is `no`). A recipe phase is data:
   `{name, dispatch, tier, gate, done_check}`.
3. **Compute the gate** via gate-by-risk (table below) from the phase's `risk_tier` + `risk_class` + `dispatch`.
   - `auto` → proceed to dispatch.
   - `owner-confirm` → present the phase + risk to the owner and WAIT; log the answer in the ledger's gate log.
4. **Resolve the tier** for the phase from `scripts/tier_policy.json` keyed by `risk_tier` (with `risk_class`
   floor applied). Never bake a model name into the workflow.
5. **Build the context-manifest** (`engine/rules/context-manifest.md`): a list of PATHS + QUERIES the worker
   hydrates live (`rule_card fe`/`be` output, `recommended_prompt_file`, recalled `learning_recall` notes,
   ledger path, relevant `specs/<module>/NN-*.md#section`) + `allowlist` (worktree + files) + `done_check` +
   `return_format`. `verify_live: true`. Pass PATHS, never pasted bodies.
6. **Dispatch ONE worker FROM THE MAIN LOOP** — a Workflow (deep-review / espresso-test) or a depth-1 Agent
   (mh-rca / a scribe). Never delegate fan-out into a worker that itself re-fans-out (a plain Agent subagent may
   not be able to spawn further subagents; deep fan-out is the Workflow's `parallel()` or depth-1 Agent rounds).
7. **Record** the worker's compact return blob + artifact PATH in the ledger phase row (`status_blob`,
   `artifact_path`, `decision`). Do NOT open the artifact md.
8. **Evaluate `done_check`** from the blob (counts/flags, never a md read). Set `done?`. If the phase opened
   provisional/parked items, log them in the ledger's Provisional/Parked block.
9. **Decide next:** more phases with `done? = no` → next tick (go to 1). All phases done → `DONE`. Cap reached
   with fixable work open → `CAP_HIT`. No worktree / env gate failed → `BLOCKED`. Shippable done but items
   deferred → `PARKED`.
10. **Run end:** write `99-final-report.md` from `templates/final-report-template.md` (from blobs + ledger),
    record the stop reason in the ledger, and **remove `.claude/.pm-run-active`**.

## Gate-By-Risk Table

| condition | gate |
|---|---|
| `risk_tier ∈ {T0,T1}` AND phase is read-only OR reversible-worktree-bounded | **auto** (dispatch, no ask) |
| `risk_tier ∈ {T2,T3}` AND `risk_class ∈ {clinical,billing,permission,migration,irreversible-data}` | **owner-confirm** (HARD gate) |
| `phase.dispatch ∈ {technical-design, task-slicing, ui-spec, dev-from-handoff, robust-test}` | **owner-confirm** (owner-gated workflow) |
| `phase.dispatch == promote` | **never dispatchable** — refuse |
| implement phase | never `incremental-impl`. In the `feature` recipe the PM fans out **`mh-implementer` per slice (depth-1 from the main loop)** rather than `mh-implement`, because `mh-implement` would re-fan-out into its own subagents → depth-2 (unsupported); the PM itself plays that orchestrator role. |

Rationale (plan sec.6.B, LOCKED): auto-everything would silently auto-decide clinical/billing/permission/
migration — forbidden by the harness safety canon. Risk-gating is the steady state, not timidity.

## Recipe Resolution (presets)

Presets live in `engine/workflows/pm-orchestrator/manifest.json → recipes`:

- **`review`** (read-only): `scope-freeze → deep-review (review tier; pass args.tier_policy) → scribe writes
  findings md`. Zero source edits. The first validation run uses this preset (plan sec.6.D).
- **`espresso`** (loop): `pre-sweep → loop{ review → fix → re-review } until open_block_high == 0 or cap`.
  **REUSES `engine/workflows/espresso-test/` verbatim** — dispatch the espresso workflow as a phase; do NOT
  reimplement or modify any espresso file. The espresso coordinator owns the inner loop's role split.
- **`bugfix`**: `mh-rca → /mh-fix → deep-review`. RCA verdict → worktree-bounded fix → regression review.
- **`feature`** (token-efficient module build): `distill (read BA once) → spec (ui-spec | technical-design) →
  slice (task-slicing) → implement (fan-out mh-implementer per slice) → converge (espresso loop)`. Full runbook
  below. `distill`/`spec`/`slice` always fire the owner-confirm gate; `implement` computes the gate per slice.
- **`single-skill`** (T1 small scope): `implement-or-fix (mh-implement | mh-fix, gate-by-risk) → self-review`.
  One skill does the change and its OWN diff self-review — no separate review pass.
- **`implement+review`** (T2 shared/contract/cross-file): `implement (mh-implement, gate-by-risk) → review
  (deep-review, auto)`. A separate deep-review pass catches regressions the self-review can miss.
- **`triage-only`** (read-only): `adjudicate (mh-rca + mh-reviewer — verify each finding real vs false-positive
  on live evidence) → report`. For "verify this bug/finding list, don't fix yet". Zero source edits.
- **`batch-bugfix`** (analyst-first · PM blind): `analyze → fix → self-review → downstream (optional)`. For
  "here's a list of bugs, fix them". **MIRRORS `feature`'s distiller pattern — the PM NEVER reads the input
  list/findings/source.** (1) **`analyze`** (auto · dispatch `mh-rca`/a bug-analyst): the worker reads the raw
  bug/findings list + source EXACTLY ONCE, adjudicates real vs false-positive, dedupes by shared root cause,
  WRITES one clean adjudicated md (the real bugs to fix), and tags **EACH** confirmed bug with a
  **complexity→tier** (complex→opus · medium→sonnet · simple/layout→haiku, keyed off `scripts/tier_policy.json →
  tiers`) + `risk_class`; returns a compact SUMMARY blob + the adjudicated-md path. (2) **`fix`** (computed
  gate-by-risk PER BUG · fan-out): ONE `mh-implementer` per confirmed bug / disjoint cluster, depth-1 from the
  MAIN LOOP, ordered BE→contract/DTO-regen→FE; per-bug `(model,effort)` = `tiers[bug.complexity_tier]` (that
  bug's analyst-assigned complexity tier, **NOT** a whole-prompt `risk_tier`) with `risk_class_floor`; each
  worker gets ONLY its bug **by reference** (reads only its bug, never the whole list). (3) **`self-review`**
  (auto · `deep-review`): a FRESH-CONTEXT verifier over the fix diff — independent, not self-congratulation. (4)
  **`downstream`** (OPTIONAL, workflow-dependent · owner-confirm): hand off to a tester / `robust-test` for E2E;
  omit when no downstream step is needed. **MUST NOT** dispatch `mh-implement` (re-fans-out → depth-2) NOR
  `incremental-impl`.
- **`design-only`** (read-only · owner-gated): `distill (gated) → spec (ui-spec | technical-design, gated) →
  STOP`. The front of `feature` without implement — emits 02-requirements + 03-ui/08-api for owner approval, no
  slicing, no code. To build, the owner re-runs with the `feature` recipe.

The `distill` phase (in `feature` and `design-only`) dispatches the **`distiller`** agent
(`engine/agents/distiller.md`): a read+write BA-analyst worker that reads the BA doc EXACTLY ONCE and writes
`specs/<m>/02-requirements.md` + a per-slice risk index (`risk_tier`+`risk_class`), no source edits. It fills the
real gap that no SDD skill distills the BA doc; the `feature.distill` `dispatch` value equals this agent name.

A custom recipe is any owner-supplied ordered phase list using the same `{name, dispatch, tier, gate,
done_check}` shape; `promote` may never appear in it.

## `feature` Recipe Runbook (the 5-phase module build)

Reuses the SDD skills (`ui-spec`/`technical-design`/`task-slicing`) + `mh-implementer` + `espresso-test`
verbatim — it does NOT reimplement them. Every dispatched worker prompt follows
`engine/prompts/subagent-prompt-template.md` (ZONE A = the context-manifest, ZONE B = the ask).

1. **`distill`** (owner-confirm · dispatch a general read+write worker). ONE worker reads the BA doc (e.g.
   `specs/Tài liệu Nội trú.md`) **EXACTLY ONCE** and emits `specs/<m>/02-requirements.md` + a **per-slice risk
   index** (`risk_tier`+`risk_class` per prospective slice). This fills a real GAP — no SDD skill distills the BA
   doc today (`02-requirements` was owner-authored). Hard owner-confirm gate (it anchors the whole build).
2. **`spec`** (owner-confirm · dispatch `ui-spec` and/or `technical-design`). From `02-requirements` +
   owner-authored `07-schema` → `03-ui.md` (UI reuse map) and/or `08-api.md` (API contract). Owner-gated SDD
   workflows → always owner-confirm. Does NOT receive the BA doc.
3. **`slice`** (owner-confirm · dispatch `task-slicing`). From `03-ui` + `08-api` + `07-schema` → `10-plan.md`.
   Each task carries **normalized `risk_tier`(T0–T3) + `risk_class`** alongside the freeform `risk` (see
   `engine/skills/task-slicing/DETAILS.md`) so the next phase keys `tier_policy` deterministically per slice.
   Does NOT receive the BA doc.
4. **`implement`** (computed gate-by-risk PER SLICE · dispatch `mh-implementer`). The PM **is** the orchestrator:
   it fans out **ONE `mh-implementer` per disjoint slice, depth-1 from the MAIN LOOP**, ordered by `10-plan`
   dependency rounds. Each worker's context-manifest carries **ONLY its slice by reference**:
   `specs/<m>/10-plan.md#task-NN` + the specific `03-ui`/`08-api` rows it touches + `rule_card`(fe|be) —
   **NEVER the BA doc, NEVER the whole spec**. Per-slice `(model, effort)` = `scripts/tier_policy.json →
   tiers[slice.risk_tier]`, with `risk_class_floor` applied when `slice.risk_class ∈
   {clinical,billing,permission,migration}`; that same risk also computes each slice's gate. **MUST NOT** dispatch
   `mh-implement` (it re-fans-out → depth-2, unsupported per the execution note) **NOR** `incremental-impl`.
5. **`converge`** (computed per inner phase · dispatch `espresso-test`). Replaces the old one-shot `deep-review`
   final phase with the espresso review→fix→re-review loop, **reused verbatim** from `recipes.espresso` — no
   espresso file is reimplemented; loop until `open_block_high == 0` or the round cap.

**Read-BA-once rule (hard):** only `distill` ever opens the BA doc; its path is placed in that worker's manifest
ONLY and is never added to any later worker's manifest. Every downstream phase rides on the distilled/owner
specs (`02-requirements` → `03-ui`/`08-api` → `10-plan`).

## Marker Lifecycle

```text
run start : create runs/<scope>/run-NNN/00-pm-state.md → echo its path into .claude/.pm-run-active
each turn : the orchestrator_invariants.py UserPromptSubmit hook sees the marker and re-injects the PM invariants
            (incl. "re-derive state from this ledger each tick"); gated on the marker so normal turns pay no cost
run end   : remove .claude/.pm-run-active (stop re-injecting)
```

The marker's **contents = the ledger path**, so the hook knows which ledger to point the PM back at.

## Ledger Contract

- Path: `engine/workflows/pm-orchestrator/runs/<scope>/run-NNN/00-pm-state.md` — **never** under `main-brain/`
  (guard-blocked) and never written by a Workflow engine (a scribe/the coordinator writes the md).
- Authored ONLY from compact blobs; regenerable from the artifact paths it points at; carries pointers +
  decisions, not copied content. Re-read every tick. Full convention: `engine/rules/orchestrator-ledger.md`.

## Context-Manifest Usage

The coordinator hands each worker a manifest of references (not content): `rule_card` output (`fe` AND `be`),
the route's `recommended_prompt_file`, recalled notes (paths), the ledger path, and relevant spec sections —
plus `allowlist`, `done_check`, `return_format`, and `verify_live: true`. The worker self-hydrates from the live
references; the coordinator never reads them on the worker's behalf (that would break the blind invariant). A
referenced path the worker cannot verify is a STOP, not a guess. Full convention:
`engine/rules/context-manifest.md`.

## Stop Conditions

Terminal states, decided by the coordinator from compact blobs — never from md:

- **DONE** — every phase `done_check` satisfied; nothing fixable open.
- **CAP_HIT** — phase/round cap reached with fixable BLOCK/HIGH still open → honest residual (split scope / new
  change), never claim clean, never loop forever.
- **BLOCKED** — no worktree for a source-editing recipe / environment gate failed / required dependency missing.
- **PARKED** — shippable work done, but M findings deferred to owner (irreversible-data / migration / business
  ambiguity that the provisional protocol parked).

## Hard Boundary

- Coordinator reads NOTHING (no output md, no source, no rules). Writes only its ledger, final report, and the
  run marker.
- All source edits inside `worktrees/<slug>/{fe,be}` only (fix/implement phases inherit `/mh-fix` and
  `/mh-implement` safety in full). Never `myhospital-fe/`, `myhospital-be/`, generated DTO/client/`Constants.ts`,
  or EF migrations by hand.
- No `git commit/push/reset`. No self-launching any workflow/executor/browser beyond the recipe's named phases.
- `promote` never dispatchable; dispatch `mh-implement`, never `incremental-impl`. Tiers from
  `scripts/tier_policy.json` at dispatch — never baked in.

## Output Contract

Final chat response should be compact:

```text
Run folder: <path>
Result: DONE | CAP_HIT | BLOCKED | PARKED
Recipe: <preset> · phases <done>/<total> (cap <cap>)
Per phase: <name> → <status_blob> (done? gate?)
Worktree: <slug> (diffs left for owner review)  | — (read-only)
Gates fired: <N owner-confirm | none>
⚠ Provisional decisions: <N → confirm/correct · specs/<module>/06-decision-log.md>  | none
Parked (need owner): <ids — irreversible-data/migration>  | none
Residual OPEN (fixable): <ids + severities>  | none
Next step: <exact options>
```
