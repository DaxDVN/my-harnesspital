# Fugu-style Orchestrator Upgrade — Detailed Plan

> Date: 2026-06-25 · Status: **DRAFT — owner review required before execution** · Type: harness-maintenance (T3)
> Authoritative plan. Grounded in a 4-agent read-only survey of the live harness (routing, orchestration,
> pool+verifier, memory+hooks). All file:line cites are from that survey.

## 0. Target architecture (Fugu → this harness)

A thin **always-on PM orchestrator** that, per task: (1) classifies risk/difficulty **deterministically**,
(2) picks worker **(model, effort)** tier, (3) dispatches to bounded worker subagents **driven from the main
loop / Workflow tool**, (4) runs a **verifier** stage, escalating model/effort **only on failure**, while
staying **blind** (routes paths + compact blobs, never reads worker output md) and **stateless over a durable
ledger** (cannot forget across a long session).

| Fugu layer | This harness (REUSE) | Status |
|---|---|---|
| TRINITY (route, ~free) | `harness_router.py::build_decision` + `rule_card.py` | exists; add `(model,effort)` |
| Conductor (decompose + ground) | `task-slicing`→`10-plan.md` + `mh-implement` live-conv injection | exists; wrap in PM |
| Pool (per-agent model/effort) | `deep-review/workflow.js` `parallel()` + `mh-implementer/reviewer/rca` | exists; add `effort`, lift hardcodes |
| Verifier (inference-time reward) | self-adversarial + adversarial-verify stages (workflow.js:188-275) | exists; make tier-able |
| PM shell (blind, ledger) | `espresso-test` coordinator + `00-espresso-state.md` ledger | exists (DRAFT); generalize |
| Anti-forget | `.claude/settings.json` hooks (stdout every turn) | exists; add invariants hook |
| Memory by-reference | `recommended_prompt_file` + `learning_recall` + `rule_card` | exists; formalize manifest |

**Verdict: UPGRADE + focused restructure of the orchestration/entry layer. 0% rebuild.** The engine, workers,
verifier, memory and hook machinery are reused unchanged; only the orchestration spine is new.

## 1. Hard constraints discovered (these shape every phase)

1. **Fan-out MUST be main-loop / Workflow-tool driven.** A plain Agent-tool subagent may not be able to spawn
   further subagents (espresso README:226). Confirmed working: parent→child depth-1 (the 4 mappers) and
   `workflow.js` internal `parallel()`. **Design rule: never delegate fan-out into a worker that re-fans-out.**
   The PM's "deep" fan-out is realized by the PM (main loop) launching a Workflow, OR by depth-1 Agent rounds.
2. **Never delete entry skills.** `harness_doctor.py check_registry` hard-fails on any dangling manifest ref;
   `espresso-test/manifest.json` already declares `skills_used`/`agents`/`reuses_workflows`. Entry skills stay
   as **dispatch targets**, not deletions.
3. **Always-on vs owner-gate clash.** Every entry is `manual_only/auto_route_allowed=false`; AGENTS.md §3 forbids
   self-launch from intent words. The PM must be the **one sanctioned auto-route**, and gated workflows inside
   its recipe **still fire the preflight-confirmation gate per phase**. This is a governance change → OWNER
   DECISION (§6.B).
4. **`effort` is net-new.** Zero `effort` usage in any `agent()` call today; adding it touches every call site
   in `workflow.js` (no config-file shortcut). `model` exists but verifier sites are hardcoded `'sonnet'`
   (workflow.js:228, :266, :298).
5. **Router edits are contract-gated.** `harness_router.py` self_test (L518) + `harness_preflight.py` self_test
   (L260) + `promptfoo:router` + `harness_quality_eval.py` gate harness edits. Adding fields = safe; changing
   existing tier outputs = breaks tests. Derive `(model,effort)` **from** `risk_tier`, never replace it.
6. **Hooks fail-open.** All hooks silently `exit 0` on error. An invariants hook that errors would silently stop
   re-injecting → needs a self-test + heartbeat marker.
7. **Every-turn injection is a token cost.** `UserPromptSubmit` stdout is injected each turn → invariant payload
   must be tiny AND gated on an active-run marker (don't print on normal turns).
8. **espresso is DRAFT / never run.** Generalizing an unproven prototype into the spine compounds risk → a real
   validation run is the eval floor BEFORE it becomes always-on.
9. **Workflow scripts can't write files** (workflow.js:5) → a scribe writes any md; the engine returns data only.
10. **Workers must not decide architecture/contract/business** (worker-task.md:53-58) → those return BLOCKED to
    the PM. Memory write gates stay: `main-brain/` guard-blocked, `second-brain/` ask-owner.

## 2. Phase plan

### Phase 0 — Runtime smoke (eval floor, de-risks everything)
- **Goal:** confirm main-loop-driven fan-out with per-agent `(model, effort)` works end-to-end before building on it.
- **Action:** a throwaway minimal `workflow.js` that spawns 2–3 `agent()` calls at different `{model, effort}`
  and returns their tags; run via the Workflow tool from the main loop. Confirm `effort` is accepted per-call.
- **Validation:** workflow returns distinct results; no runtime error on `effort`.
- **Risk:** low. If `effort` is rejected, fall back to model-only tiering (degrade gracefully).
- **Fan-out:** main-loop only (Workflow runs in main loop). ~1 small run.

### Phase 1 — `(model, effort)` policy layer (the Conductor brain) — FOUNDATION
- **Goal:** deterministic `risk_tier (+confidence, +risk_class) → (model, effort) + escalation ladder`.
- **Changes:**
  - `scripts/harness_router.py`: new `select_model_effort(risk_tier, confidence, route)` next to `escalate_tier`
    (~L217); add `tier_policy: {model, effort, escalation:[...]}` to the `build_decision` return dict (~L430).
  - New data table `scripts/tier_policy.json` (or module-level dict) — default map, manifest-overridable:
    - T0 → (haiku, low) · T1 → (sonnet, medium) · T2 → (sonnet, high) escalate→(opus, high)
    - T3 → (opus, high) escalate→(opus, xhigh) · ladder e.g. `[(sonnet,medium),(sonnet,high),(opus,high),(opus,xhigh)]`
    - **risk_class override:** `clinical|billing|permission|migration` → floor at (opus, high) regardless of diff size.
  - `scripts/harness_preflight.py`: surface `tier_policy` via the `decision` passthrough (L221) + a `render_card`
    line (L225) so the owner sees the chosen model/effort.
  - Extend `harness_router.py` self_test (L518) + preflight self_test (L260) with `tier_policy` assertions
    (ADD cases; do not alter existing tier asserts).
- **Validation:** `python scripts/harness_router.py --self-test`; `promptfoo:router`; `python scripts/harness_quality_eval.py`.
- **Risk:** brittle substring keyword tables inherited; mitigate by deriving from `risk_tier` only.
- **Fan-out:** YES — 1 bounded agent owns `harness_router.py` + `tier_policy.json` + self-tests (disjoint file set).

### Phase 2 — Pool + verifier `(model, effort)` plumbing + escalation
- **Goal:** make the pool/verifier consume the policy and escalate on failure.
- **Changes (`engine/workflows/deep-review/workflow.js`):**
  - Add `effort` to every `agent()` options object (audit :140, scope :98, self-adv :225, verify :266, fill :298).
  - Lift hardcoded verifier `model:'sonnet'` (:228, :266, :298) to params read from `args.tier_policy`.
  - Read `tier_policy`/per-dimension tiers from `args` (currently `{module,base,scope}` at :7) instead of the
    baked `DIMENSIONS[].tier`.
  - **Escalation:** on a worker/verify stage returning fail/low-confidence, re-dispatch that unit at the next
    ladder rung (main-loop `parallel()` re-call). Bound by ladder length (no infinite escalate).
- **Validation:** Workflow smoke run of deep-review with an injected `tier_policy` on a tiny scope; assert verify
  stage ran at the escalated tier on a forced failure.
- **Risk:** verifier only runs on BLOCK/HIGH today (MED/LOW blind spot) — document; do not silently widen.
- **Fan-out:** 1 bounded agent edits `workflow.js` (disjoint); smoke run is main-loop.

### Phase 3 — Generalize espresso-coordinator → always-on PM orchestrator (the spine)
- **Goal:** one PM that dispatches any task through a pluggable phase-recipe, blind + stateless.
- **Changes:**
  - New `engine/workflows/pm-orchestrator/` (`manifest.json` kind:"orchestrator", `README.md`, `templates/`).
    Keep `espresso-test` intact; express it as a **phase-recipe preset** of the PM (review→fix→re-review).
  - **Phase-recipe**: ordered `[{phase, entry_skill, tier_from_policy, done_check, gate?}]`. Generalize the
    espresso ledger columns `BLOCK/HIGH/parked` → `{phase, status_blob, artifact_path, decision, done?}`.
    Reuse the coordinator invariant + tier-split + path-routing + `00-state` ledger **verbatim**.
  - New `engine/skills/pm-orchestrator/SKILL.md` (thin stub) + `DETAILS.md` (runbook): blind coordinator,
    memory-by-reference, stateless-over-ledger, consumes Phase-1 `tier_policy`, drives fan-out from main loop.
  - `engine/REGISTRY.md`: add the workflow row (REGISTRY L114-121 procedure).
  - `AGENTS.md §3`: carve-out naming the PM as the one sanctioned auto-route; gated workflows still owner-confirm
    per phase (depends on §6.B).
  - Exclusions baked in: `promote` never dispatchable; dispatch `mh-implement` not `incremental-impl`.
- **Validation:** `python scripts/harness_doctor.py` (check_registry green, no dangling refs); PM dry-run on a
  trivial task (recipe resolves, ledger written, no md read by coordinator).
- **Risk:** generalizing an unproven prototype (constraint #8) → gated behind Phase 5 validation before always-on.
- **Fan-out:** parent (me) owns the design/spec; bounded agents draft templates/manifest/SKILL from the spec.

### Phase 4 — Anti-forget operating contract (hooks + ledger + manifest) — co-develops with Phase 3
- **Goal:** PM cannot forget invariants/workflow/state across a long session.
- **Changes:**
  - New `.claude/hooks/orchestrator_invariants.py` in `.claude/settings.json` `UserPromptSubmit.hooks[]`. Prints
    a **tiny** invariant block to stdout **only when a PM run-marker file exists** (token-gated). Includes a
    self-test + heartbeat (mitigates fail-open #6/#7).
  - New `engine/rules/orchestrator-ledger.md` — run-state ledger convention: per-run file under a `runs/` or
    `docs/audit/<date>/` dir (NOT `main-brain/` — guard-blocked), re-read each tick, regenerable (model on
    `learning_recall`'s `INDEX.md` rebuild pattern).
  - New `engine/rules/context-manifest.md` — subagent hydration-by-reference: the manifest lists files-to-load
    (`rule_card` output + `recommended_prompt_file` + recalled notes + ledger path) + **verify-live** instruction;
    orchestrator passes paths, never content. Extend `engine/prompts/incremental-impl-worker.md` as the template.
- **Validation:** hook self-test; `harness_doctor`; confirm invariants print only under an active run-marker.
- **Risk:** `.claude/hooks/` are real files (not symlinks) — edit canonical path; keep payload minimal.
- **Fan-out:** YES — 3 disjoint files, up to 3 bounded agents.

### Phase 5 — End-to-end validation + eval floor + distillation loop
- **Goal:** prove the PM on one real small task; only then flip DRAFT→LAB / enable always-on.
- **Actions:** run the PM (or espresso preset) on a small real changeset; record `eval_summary` + `last_real_run`
  in the manifest; run `python scripts/harness_scanner_promotion.py scan` and promote any repeated `bug_class`
  into a deterministic guard/rule (the ongoing "figurative training" loop).
- **Validation:** the run converges/stops honestly; doctor green; eval recorded.
- **Fan-out:** main-loop run + 1 agent for the distillation promotion.

## 3. Sequencing & dependencies

```
Phase 0 (runtime smoke) ──► Phase 1 (policy, FOUNDATION) ──┬─► Phase 2 (pool plumbing)
                                                           ├─► Phase 4 (ledger/manifest/hook conventions)
                                                           └─► Phase 3 (PM spine) ◄── needs Phase 4 conventions
                                                                       │
                                                                       ▼
                                                              Phase 5 (validate + eval floor → always-on)
```
Phase 1 is the foundation everything consumes. Phases 2 and 4 can run in parallel after 1. Phase 3 needs 1 + 4.
Always-on (§6.B) is only switched on after Phase 5.

## 4. Validation & rollback
- Whole harness is git-tracked and committed (owner confirmed) → every phase is revertable by `git checkout`.
- Per-phase gates: router self-tests + `promptfoo:router` + `harness_quality_eval` (Phase 1); Workflow smoke
  (Phase 0/2); `harness_doctor check_registry` (Phase 3/4); real run + eval (Phase 5).
- No irreversible ops used (no commit/push/reset/recursive-delete/DB) even under the rule-bypass grant.
- Additive-only: new files + new fields; existing entry skills/workflows untouched except the AGENTS.md §3
  carve-out and additive self-test cases.

## 5. Execution model (per owner instruction: fan out, don't self-do)
The PARENT (me) holds the design/integration and decides stop; bounded agents do disjoint file work and return
compact blobs (no md dumps). Disjoint allocations: A=`harness_router.py`+`tier_policy.json`+self-tests ·
B=`workflow.js` · C=PM templates/manifest/SKILL (from parent spec) · D=ledger rule · E=context-manifest rule ·
F=invariants hook. A/B/D/E/F are file-disjoint → parallelizable in dependency rounds (1 before 2/4; 4 before 3).

## 6. LOCKED decisions (owner: "pick optimal, no phased compromise" — 2026-06-25)
- **A. Tier policy — LOCKED to §2 defaults, plus:** `coordinator_tier = (sonnet, low)` (blind router, script-backed,
  count-based stop); verifier candidate-find = `(sonnet, high)`; **BLOCK/HIGH adjudication = (opus, high)** (per
  quality-gates "cheap finds, strong decides"). Global escalation ladder
  `[(sonnet,medium),(sonnet,high),(opus,high),(opus,xhigh)]`. `risk_class ∈ {clinical,billing,permission,migration}`
  force-floors `(opus, high)` regardless of diff size.
- **B. Governance — LOCKED: risk-gated auto-route (single permanent policy, NOT a migration).** The PM is the one
  sanctioned auto-route. It auto-dispatches WITHOUT asking when `risk_tier ∈ {T0,T1}` AND the phase is read-only or
  reversible-worktree-bounded. It fires a HARD owner-confirm gate ONLY for `risk_tier ∈ {T2,T3}` ∧ `risk_class ∈
  {clinical,billing,permission,migration,irreversible-data}`, OR an explicitly owner-gated workflow
  (technical-design, task-slicing, ui-spec, dev-from-handoff, robust-test). `promote` is never dispatchable. Mid-run
  business ambiguity uses espresso's provisional-or-park protocol (never silent invention). AGENTS.md §3 amended to
  name the PM as this gate-by-risk auto-route. Rationale: "auto everything" would silently auto-decide
  clinical/billing — forbidden by the harness safety canon; risk-gating is the optimal steady state, not timidity.
- **C. Structure — LOCKED: new `engine/workflows/pm-orchestrator/` workflow; espresso becomes a phase-recipe preset.**
  espresso skill/manifest stay intact (no registry breakage).
- **D. First validation — LOCKED: a READ-ONLY review-only PM run** (recipe = dispatch `deep-review` only, zero source
  edits) on the smallest available real changeset; exact file-set frozen by the PM's scope-freeze step at run time.
  Lowest-risk proof of route → fan-out → verify → ledger → stop.

## 7. Reuse ledger (Ponytail evidence)
- REUSE unchanged: workers (`mh-implementer/reviewer/rca`), `worker-task.md`, verifier stages, `deep-review`
  fan-out engine, hooks/stdout channel, `learning_recall`, `rule_card`, `engine/prompts/*`, espresso ledger.
- CREATE-NEW (minimal): `select_model_effort` + `tier_policy.json`, `effort` plumbing, PM workflow/skill,
  3 rule/hook files. Everything new is additive; no existing behavior removed.

## 8. Execution outcome (2026-06-25 — all 5 phases built)

Built additively via fan-out agents (parent owned design/integration/governance edits); harness git-committed/reversible;
no irreversible ops. Doctor stayed **80 OK / 0 FAIL** throughout.

| Phase | Status | Key result |
|---|---|---|
| 0 runtime smoke | ✅ | per-agent (model,effort) + main-loop fan-out proven (4 probes, effort accepted) |
| 1 policy layer | ✅ | `select_model_effort()` + `scripts/tier_policy.json` + fail-safe loader; router+preflight self-tests PASS; clinical→opus/high |
| 2 pool/verifier | ✅ | every agent() site carries `effort`; verifier hardcode lifted; escalate-on-survival (opus/high adjudication) |
| 3 PM spine | ✅ | `engine/workflows/pm-orchestrator/` + skill; recipes review/espresso/bugfix/feature; gate-by-risk; `orchestrator` registered as a governance class |
| 4 anti-forget | ✅ | `orchestrator_invariants` hook (marker-gated, heartbeat, fail-open) + `orchestrator-ledger.md` + `context-manifest.md`; **fired LIVE during the eval** |
| 5 eval floor | ✅ | PM `review` run end-to-end; pm-orchestrator DRAFT→LAB |

**The eval floor caught + fixed 2 real defects + 1 policy gap** (runs/eval-floor/run-001/99-final-report.md):
1. `DEFAULT_TP` before `export const meta` → Workflow rejected (node --check missed it) → FIXED.
2. Workflow tool delivers `args` as a JSON STRING → empty scope → FIXED (parse-if-string).
3. gate-by-risk gap (T2/T3 ∧ read-only) → REFINED: read-only auto regardless of tier; cutoff applies to source-editing phases (manifest updated).

**Residual / owner test:** full audit fan-out on a POPULATED scope not re-run (token-conscious; Phase 0 proves effort, args fix
proven by 0-agent probe). `auto_route_allowed` stays **false** until the owner's populated-scope test. Follow-ups:
(a) sync the gate wording in `pm-orchestrator/DETAILS.md` with the refined manifest; (b) owner may promote the 2 scanner
candidates surfaced by `harness_scanner_promotion` (`status-display-bypasses-status-badge`, `swallow_catch-json-parse-silent-rule-skip`).

## 9. Extension — recipe-depth policy + feature pipeline + Anthropic-grounded prompting (2026-06-26)

Built additively via 3 file-disjoint fan-out agents (parent owned synthesis + integration). Doctor stayed **80 OK / 0 FAIL**;
router + preflight self-tests OK; both JSON valid. Driver: **token economy = match orchestration cost to the task** —
(a) right-size recipe DEPTH, (b) read big sources ONCE + by-reference, (c) right-size (model,effort) per slice (already built).

| Piece | What | Files |
|---|---|---|
| **Recipe-depth policy** (Ponytail-for-orchestration) | `recipe_depth` ladder in tier_policy + `select_recipe()`/`recipe_signals()` in router → shallowest safe recipe; a small task is never inflated to a heavy pipeline | `scripts/tier_policy.json`, `harness_router.py`, `harness_preflight.py` + self-tests |
| **`feature` recipe flesh-out** | deferred stub → 5-phase token-efficient pipeline: `distill`(BA read ONCE)→`spec`→`slice`→`implement`(fan-out mh-implementer/slice, depth-1, by-reference, per-slice (model,effort))→`converge`(espresso) | `pm-orchestrator/{manifest,README}`, `skills/{pm-orchestrator,task-slicing}/DETAILS` |
| **Anthropic-grounded subagent prompting** | canonical worker-prompt template from Anthropic's prompting guides (`temp/anthropic-guideline/`): goal+intent · imperative · literal boundaries · context-manifest XML ordering (long-top/ask-bottom) · autonomy · ponytail · TLDR-first/grounded output · per-tier notes; + Opus-4.8 autonomy line in the invariants hook; + coverage-first mh-reviewer | `engine/prompts/subagent-prompt-template.md` (NEW), `rules/context-manifest.md`, `hooks/orchestrator_invariants.py`, `agents/mh-reviewer.md` |

Ladder: `none`(T0/trivial) · `single-skill`(T1) · `implement+review`(T2) · `bugfix`(bug+repro) · `review`(audit) · `espresso`(drive-to-0) ·
`full-SDD`(T3/module/BA-doc). Precedence = intent-locked first (espresso→review→bugfix) then tier-driven. Verified live.

**Real GAP filled:** no SDD skill distilled the BA doc → `02-requirements` (was owner-authored). New `distill` phase automates it
(owner-gated; BA doc read ONCE, never re-fed to later workers).

**Runtime constraint honored:** implement fan-out = PM → `mh-implementer` per disjoint slice, **depth-1** from the main loop
(NOT `mh-implement` which re-fans-out → depth-2; NOT `incremental-impl`).

**Residual:** `full-SDD` feature recipe is authored + JSON/registry-valid but NOT yet run on a real module (awaits owner's first
populated run, like the spine). Per-slice (model,effort) relies on task-slicing emitting the new normalized `risk_tier`+`risk_class`
task fields (added to its DETAILS spec).
