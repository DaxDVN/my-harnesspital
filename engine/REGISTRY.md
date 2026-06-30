# engine/ REGISTRY — what exists + who composes what

The single index of the harness's composable parts. **Read THIS to know the inventory.** Components are
flat shared POOLS (`agents/` `skills/` `rules/` `review/`); **workflows COMPOSE them by name** via each
`engine/workflows/<name>/manifest.json` (no duplication). Relationships are many-many. `harness_doctor.py
check_registry` validates that every manifest reference resolves to a real pool file.

## Agents (`engine/agents/<name>.md`)
| agent | role | rules it works against | used by workflow(s) |
|---|---|---|---|
| `mh-reviewer` | single-dimension code reviewer (D1–D7) | backend-/frontend-rules, deep-review/checklist | `deep-review` |
| `mh-implementer` | bounded convention-safe implementer | backend-/frontend-rules | (skill `mh-implement`) |
| `mh-rule-auditor` | read-only BLOCK/WARN rule auditor | backend-/frontend-rules | (ad-hoc) |
| `mh-rca` | read-only root-cause investigator — follows the **bug-trace playbook** (`docs/harness/plans/bug-trace-workflow-research-2026-06-16.md`) | backend-/frontend-rules | `bug-fix` |

## Skills (`engine/skills/<name>/SKILL.md`)
| skill | what | entry for workflow |
|---|---|---|
| `mh-scaffold` | emit canonical BE/FE patterns | — |
| `mh-implement` | guided feature implementation | — |
| `mh-fix` | safe bug-fix from a findings file | — |
| `mh-review` | ≤3-round partitioned review | `deep-review` |
| `promote` | second-brain → main-brain (owner-gated) | — |
| `ponytail` | minimal-correct-diff/YAGNI discipline; prevents over-building | — |
| `robust-test` | owner-gated targeted/sweep testing; one folder per bug; final review-ready bundle | `robust-test` |
| `espresso-test` | owner-gated review→fix→re-review loop until 0 BLOCK/HIGH; blind coordinator routes paths only | `espresso-test` |
| `pm-orchestrator` | always-on blind/stateless PM; runs ANY task through a pluggable phase-recipe; gate-by-risk dispatch | `pm-orchestrator` |
| `impact-analysis` | preflight blast-radius (CodeGraph) | `impact-analysis` |
| `bug-fix` | investigate→RCA→fix→verify (any source) | `bug-fix` |
| `ui-spec` | DOCX+mockups → detailed `03-ui.md` reuse-map (FE keystone) | `ui-spec` |
| `technical-design` | **API-contract** draft (schema=owner, UI=`/ui-spec`) | `technical-design` |
| `task-slicing` | vertical slices → `10-plan` (large modules) | `task-slicing` |
| `incremental-impl` | **internal** per-task executor (called BY `mh-implement`) | `incremental-impl` |
| `dev-from-handoff` | owner handoff docs → technical plan → owner approval → bounded dev slices → validation/receipt | `dev-from-handoff` |
| `adapt` | owner-gated semi-automated harness adaptation: Mode A RCA+fix a failing workflow (≥2 same root-cause), Mode B design+build a new workflow for a repeated pattern (≥3, conflict-checked). POST-run, six safety gates | `adapt` |
| `mh-debrief` | post-task teaching/debrief (read-only; verifies owner understands problem/solution/impact via checklist + incremental teach + explain-back + quiz) | — |

## Rules (`engine/rules/`) — pool every agent/workflow may obey
`backend` · `frontend` · `source-discovery` ·
`ponytail` · `quality-gates` · `preflight-confirmation` · `cross-tool-enforcement` · `worktree-workflow` · `memory-policy` · `artifact-policy` ·
`spec-driven-development` · `graphify` · `multi-agent-execution`. Review knowledge pool:
`engine/workflows/deep-review/{protocol,checklist,findings-schema}.md`.

## Shared workflow primitives (`engine/workflows/_shared/`) — support, not a workflow
Deterministic pieces the SDLC workflows compose so gates/receipts/state are ONE implementation (no `manifest.json`, so `check_registry` skips it; each self-tests under `harness_doctor`). Full contract: `engine/workflows/_shared/README.md`.
| primitive | what | composed by (`uses_shared`) |
|---|---|---|
| `envelope.schema.json` + `validate-envelope.py` | the ONE round-receipt schema + validator (drift-detecting) | every workflow that emits a receipt |
| `runtime-boundary.md` | shared wrapper/validator/allowlist boundary contract for external executors | workflows calling Claude/Codex/OpenCode/MiMo/agent-browser |
| `gate-check.py` | deterministic SDD precondition gate (exit 2 = STOP) | technical-design · task-slicing · incremental-impl |
| `module-state.py` | per-module SDLC state on `00-module-state.md` (`DISCOVERY→DESIGN→DESIGN_REVIEW→SLICED→IMPLEMENTING→VERIFYING→DONE` + `BLOCKED_*`) | technical-design · task-slicing · incremental-impl |

**Fast-path (C8):** trivial + local + no-contract change skips the chain → `/mh-implement` or `/mh-fix` direct.

## Eval and workflow governance
| file/script | purpose |
|---|---|
| `docs/harness/evals/_TEMPLATE.yaml` | minimal run ledger for workflow quality/cost evidence |
| `docs/harness/evals/README.md` | eval artifact conventions (historical) |
| `scripts/harness_eval.py` | validate/scan/summarize eval ledgers (P4) |
| `scripts/harness_workflow_governance.py` | scan taxonomy/deprecation invariants (P5) |
| `scripts/harness_runtime_contract.py` | scan workflow runtime-boundary contracts (P7) |
| `scripts/harness_context_audit.py` | read-only context footprint baseline for staged token/context optimization |
| `scripts/harness_daily_eval.py` | daily router/context/readiness eval for staged optimization acceptance |
| `scripts/codex_preflight.py` | Codex-friendly wrapper around the natural-language preflight card |
| `scripts/harness_preflight.py` | natural-language route prediction + owner confirmation card |
| `scripts/artifact_gate.py` | validate small quality-gate artifacts (reuse/fix-plan/regression/review) and main-brain budget |
| `scripts/harness_quality_eval.py` | run the quality suite router/gate expectation checks |
| `scripts/harness_scanner_promotion.py` | reports repeated `bug_class:` markers (`scan`) + emits a deterministic scanner skeleton for one (`promote <bug_class>`) |
| `scripts/main_brain_promotion_candidates.py` | reports second-brain notes ready for owner promotion review; never writes main-brain |
| `scripts/harness_ready.py` | one-shot readiness gate before real workflow testing (P6/P7/P8) |
| `docs/harness/plans/harness-v2-p5-consolidation-plan-2026-06-20.md` | current consolidation candidates and no-deprecation decision |

## Workflows (`engine/workflows/<name>/` — one folder each, + manifest.json)
Manifest `kind` is the P0 governance class (`workflow` · `internal` · `advisory` · `orchestrator`). The previous machinery label lives in `implementation_kind`.
| workflow | class | implementation | entry skill | agents | external | rules |
|---|---|---|---|---|---|---|
| `deep-review` | workflow | workflow-tool-js (`workflow.js`) | `mh-review` | `mh-reviewer` | — | backend-, frontend-, ponytail, quality-gates |
| `impact-analysis` | advisory | orchestrated-codegraph (preflight blast-radius) | `impact-analysis` | — | codegraph | backend-, frontend- |
| `bug-fix` | workflow | orchestrated-subsystem (investigate→RCA→fix→verify, any source) | `bug-fix` | `mh-rca` | codex-reviewer | backend-, frontend-, ponytail, quality-gates |
| `robust-test` | workflow | manual-owner-gated-test-protocol (targeted/sweep; one folder per bug; no source edits) | `robust-test` | — | — | backend-, frontend-, source-discovery, ponytail, quality-gates |
| `espresso-test` | workflow | agent-orchestrated-loop (review→fix→re-review until clean; blind coordinator; reuses `deep-review` + `mh-rca`/`mh-fix`/`mh-implementer`) | `espresso-test` | `mh-rca`, `mh-implementer` | — | backend-, frontend-, source-discovery, ponytail, quality-gates |
| `ui-spec` | workflow | orchestrated-sdd-fe (DOCX+mockups → specs/03-ui reuse-map) | `ui-spec` | — | codegraph | frontend-, ponytail, quality-gates |
| `technical-design` | workflow | orchestrated-sdd — **API-contract only** (→ specs/08,06,04; schema=owner, UI=`ui-spec`) | `technical-design` | `mh-rule-auditor` | codex-reviewer | backend-, frontend-, ponytail, quality-gates |
| `task-slicing` | workflow | orchestrated-sdd (→ specs/10,04, vertical slices; large modules) | `task-slicing` | — | — | backend-, frontend-, ponytail, quality-gates |
| `incremental-impl` | internal | orchestrated-wrapper — **internal per-task executor** (called BY `mh-implement`) | `incremental-impl` | `mh-implementer` | — | backend-, frontend-, ponytail, quality-gates |
| `dev-from-handoff` | workflow | manual-handoff-dev (owner docs → plan approval → bounded slices → receipt; no BA discovery) | `dev-from-handoff` | — | — | backend-, frontend-, source-discovery, artifact-policy, spec-driven-development, ponytail, quality-gates |
| `pm-orchestrator` | orchestrator | agent-orchestrated-pm (blind/stateless coordinator over a pluggable phase-recipe; gate-by-risk dispatch; ledger + context-manifest; reuses `deep-review`/`espresso-test`/`mh-rca`/`mh-fix`/`mh-implement`) | `pm-orchestrator` | `mh-rca`, `mh-implementer`, `mh-reviewer` | — | orchestrator-ledger, context-manifest, multi-agent-execution, quality-gates |
| `adapt` | orchestrator | agent-orchestrated-meta (blind coordinator over a 2-mode adapt pipeline; RCA+plan+fix/build+validate; owner approves every apply; reuses `mh-rca`+`mh-fix`+`harness_doctor`+`harness_backup`) | `adapt` | `mh-rca` | — | orchestrator-ledger, context-manifest, multi-agent-execution, quality-gates, ponytail |

**Reuse note:** `bug-fix` reuses `mh-rca` (follows the bug-trace playbook) + `/mh-fix`; `incremental-impl` is the **internal per-task executor** of `mh-implement`; `impact-analysis` wraps CodeGraph; `espresso-test` reuses `deep-review` (review engine) + the same `mh-rca`/`/mh-fix`/`mh-implementer` fix path as `bug-fix` — it is the self-driving loop over `mh-review`'s ≤3-round cycle, adding no new engine.
`dev-from-handoff` reuses `/mh-implement`, `/impact-analysis`, and targeted `robust-test` only after owner approval; it does not replace SDD requirement discovery.
`adapt` is the harness-machinery analogue of `bug-fix`: same RCA→plan→fix→verify shape + same `mh-rca`+`/mh-fix` reuse, but the "source" is `engine/workflows/**` not `worktrees/<slug>/{fe,be}`. It is the only workflow whose `allowed_writes` include harness machinery; six safety gates apply (owner-gated, POST-run, no-self-fix, pin-version, threshold, conflict-check).

**FE pipeline (owner decision 2026-06-16) — by OWNERSHIP, not phase:** the **owner** authors `02-requirements` + `07-schema` (agents NEVER author schema). **`/ui-spec`** turns DOCX + PNG mockups into a detailed `03-ui.md` reuse-map (multimodal + deep FE reuse-audit). **`/mh-implement` FE-mode** (`engine/skills/mh-implement/fe-flow.md`) CONSUMES that `03-ui.md` to build, folding `incremental-impl` in per task. `technical-design` is narrowed to the **API contract** (`08`, draft→owner-approves); `task-slicing` is for LARGE/cross-cutting modules (a normal FE feature slices internally from `03-ui`). These SDLC workflows are owner-gated/manual-only. The SDD workflows share `_shared/` (gate-check + module-state + envelope). Skills: capability (`mh-scaffold` `mh-implement` `mh-fix` `promote` `ponytail`) + orchestrator/entry (`mh-review` `robust-test` `espresso-test` `impact-analysis` `bug-fix` `ui-spec` `technical-design` `task-slicing`); `incremental-impl` is an internal executor (not a standalone owner entry).

**Robust-Test (owner-gated):** `engine/workflows/robust-test/` replaces the removed `progressive-test` and `super-test`.
It has `targeted` and `sweep` modes, writes one `bugs/BUG-NNN/` folder per captured bug candidate, triages
false positives, records RCA/fix-plan/retest notes, and produces `04-review-ready-bundle.md` for a later
high-reasoning review pass. It never self-launches other agents/executors and never edits source code. Legacy
runtime folders and alias skills are removed from active harness paths; old names are router aliases only.

**Espresso-Test (owner-gated):** `engine/workflows/espresso-test/` is the self-driving loop over
`mh-review`'s ≤3-round cycle. A **blind coordinator** (thin tier) spawns a reviewer (`review_tier`, runs
`deep-review`), then routes the findings file PATH to a stronger fixer (`fix_tier`, RCA + `/mh-fix` + fanned-out
`mh-implementer`), then re-reviews — looping until a round returns `verdict: ĐÓNG` (0 BLOCK/HIGH OPEN) or the
round cap (default 3) is hit. The coordinator reads NO output md, loads NO rules, and edits NO source; it only
routes paths + compact status and decides stop. Model tiers are passed at invoke — never baked into the
workflow. Where `robust-test` stops at a human-handoff bundle, `espresso-test` closes the audit→fix→audit loop
itself. **Autonomy:** the only owner-blocking moment is the round-0 pre-sweep question batch at invoke
(`ask_window: gate-only`); after that it is fire-and-forget. A business ambiguity becomes a `PROVISIONAL-FIXED`
decision with cited provenance (`DL-PROV-<n>` in `specs/<module>/06-decision-log.md`, mirrored to
`05-open-questions.md`) so the owner can confirm/correct later, OR — if closing it needs an irreversible-data/
migration op — a `PARKED-NEEDS-OWNER` finding while the loop continues on the rest. No mid-run questions, no
DEFERRED-Q deadlock, no rule invention without evidence.

**PM-Orchestrator (owner-gated):** `engine/workflows/pm-orchestrator/` generalizes the espresso
coordinator into an **always-on PM** that runs ANY task through a pluggable **phase-recipe** (presets `review` /
`espresso` / `bugfix` / `feature`, or custom). The same **blind, stateless coordinator** discipline applies: per
tick it re-reads its `00-pm-state.md` ledger (`engine/rules/orchestrator-ledger.md`), computes the next phase's
gate, dispatches ONE worker **from the main loop** (Workflow or depth-1 Agent — never fan-out into a worker that
re-fans-out), records the worker's compact blob + artifact PATH, and decides done. It reads NO output md, loads
NO rules, edits NO source; it transfers memory to workers **by reference** via a context-manifest
(`engine/rules/context-manifest.md`). **Gate-by-risk (LOCKED, plan sec.6.B):** auto-dispatch when `risk_tier ∈
{T0,T1}` ∧ the phase is read-only/reversible-worktree-bounded; HARD owner-confirm when `risk_tier ∈ {T2,T3}` ∧
`risk_class ∈ {clinical,billing,permission,migration,irreversible-data}`, OR the phase dispatches an owner-gated
workflow. `promote` is never dispatchable; dispatch `mh-implement`, never `incremental-impl`. The `espresso`
preset **reuses `engine/workflows/espresso-test/` verbatim** (no espresso file is modified). Tiers come from
`scripts/tier_policy.json` keyed by `risk_tier`. While a run is active the PM writes `.claude/.pm-run-active`
(contents = ledger path) so the invariants hook re-injects per turn; removed at run end. Stop enum `DONE |
CAP_HIT | BLOCKED | PARKED`. The first validation is a READ-ONLY `review`
preset (plan sec.6.D).

## How to add a workflow
1. Create `engine/workflows/<name>/` with its machinery (`.js` and/or `bin/lib/schemas`) + a `manifest.json`
   (`name`, `description`, `kind` = `workflow|internal|advisory`, optional `implementation_kind`, `entry_skill`,
   `public_entry`, `auto_route_allowed`, `agents`, `external_agents`, `skills_used`, `rules`).
2. Put its entry **skill** in the `engine/skills/` pool; reuse existing `agents`/`rules` by name (or add new
   ones to their pools first).
3. Add a row to the Workflows table above. `harness_doctor.py` will fail if a manifest reference is dangling.
4. **Don't reinvent gates/receipts/state** — compose `engine/workflows/_shared/` (`gate-check.py`, `validate-envelope.py`, `module-state.py`, `runtime-boundary.md`) and list them in the manifest's `uses_shared`. Add a fast-path for trivial inputs and a learning-loop close-out (→ `second-brain/`).
