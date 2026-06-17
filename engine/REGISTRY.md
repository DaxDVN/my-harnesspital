# engine/ REGISTRY — what exists + who composes what

The single index of the harness's composable parts. **Read THIS to know the inventory.** Components are
flat shared POOLS (`agents/` `skills/` `rules/` `review/`); **workflows COMPOSE them by name** via each
`engine/workflows/<name>/manifest.json` (no duplication). Relationships are many-many. `harness_doctor.py
check_registry` validates that every manifest reference resolves to a real pool file.

## Agents (`engine/agents/<name>.md`)
| agent | role | rules it works against | used by workflow(s) |
|---|---|---|---|
| `mh-reviewer` | single-dimension code reviewer (D1–D10) | backend-/frontend-rules, deep-review/checklist | `deep-review` |
| `mh-implementer` | bounded convention-safe implementer | backend-/frontend-rules | (skill `mh-implement`) |
| `mh-rule-auditor` | read-only BLOCK/WARN rule auditor | backend-/frontend-rules | (ad-hoc) |
| `mh-rca` | read-only root-cause investigator — follows the **bug-trace playbook** (`docs/harness/plans/bug-trace-workflow-research-2026-06-16.md`) | backend-/frontend-rules | `progressive-test`, `bug-fix` |
| `mh-batch-rca` | read-only **BATCH** cluster-RCA (Opus, max effort) — clusters bugs by root cause → prioritized repair batches | backend-/frontend-rules | `super-test` |

## Skills (`engine/skills/<name>/SKILL.md`)
| skill | what | entry for workflow |
|---|---|---|
| `mh-scaffold` | emit canonical BE/FE patterns | — |
| `mh-implement` | guided feature implementation | — |
| `mh-fix` | safe bug-fix from a findings file | — |
| `mh-review` | ≤3-round partitioned review | `deep-review` |
| `promote` | second-brain → main-brain (owner-gated) | — |
| `agentflow` | orchestrate the FE-bug-fix loop | `progressive-test` |
| `impact-analysis` | preflight blast-radius (CodeGraph) | `impact-analysis` |
| `bug-fix` | investigate→RCA→fix→verify (any source) | `bug-fix` |
| `ui-spec` | DOCX+mockups → detailed `03-ui.md` reuse-map (FE keystone) | `ui-spec` |
| `technical-design` | **API-contract** draft (schema=owner, UI=`/ui-spec`) | `technical-design` |
| `task-slicing` | vertical slices → `10-plan` (large modules) | `task-slicing` |
| `incremental-impl` | **internal** per-task executor (called BY `mh-implement`) | `incremental-impl` |
| `super-test` | LAUNCHER for MiMo-led harvest (Claude is NOT the orchestrator) | `super-test` |

## Rules (`engine/rules/`) — pool every agent/workflow may obey
`backend` · `frontend` · `source-discovery` ·
`cross-tool-enforcement` · `worktree-workflow`. Review knowledge pool: `engine/workflows/deep-review/{protocol,checklist,findings-schema}.md`.

## Shared workflow primitives (`engine/workflows/_shared/`) — support, not a workflow
Deterministic pieces the SDLC workflows compose so gates/receipts/state are ONE implementation (no `manifest.json`, so `check_registry` skips it; each self-tests under `harness_doctor`). Full contract: `engine/workflows/_shared/README.md`.
| primitive | what | composed by (`uses_shared`) |
|---|---|---|
| `envelope.schema.json` + `validate-envelope.py` | the ONE round-receipt schema + validator (drift-detecting) | every workflow that emits a receipt |
| `gate-check.py` | deterministic SDD precondition gate (exit 2 = STOP) | technical-design · task-slicing · incremental-impl |
| `module-state.py` | per-module SDLC state on `00-module-state.md` (`DISCOVERY→DESIGN→DESIGN_REVIEW→SLICED→IMPLEMENTING→VERIFYING→DONE` + `BLOCKED_*`) | technical-design · task-slicing · incremental-impl |

**Fast-path (C8):** trivial + local + no-contract change skips the chain → `/mh-implement` or `/mh-fix` direct.

## Workflows (`engine/workflows/<name>/` — one folder each, + manifest.json)
| workflow | kind | entry skill | agents | external | rules |
|---|---|---|---|---|---|
| `deep-review` | workflow-tool-js (`workflow.js`) | `mh-review` | `mh-reviewer` | — | backend-, frontend- |
| `progressive-test` | orchestrated-subsystem (`.agentflow/`) | `agentflow` | `mh-rca` | codex-reviewer, opencode-executor | backend-, frontend- |
| `impact-analysis` | orchestrated-codegraph (preflight blast-radius) | `impact-analysis` | — | codegraph | backend-, frontend- |
| `bug-fix` | orchestrated-subsystem (investigate→RCA→fix→verify, any source) | `bug-fix` | `mh-rca` | codex-reviewer | backend-, frontend- |
| `ui-spec` | orchestrated-sdd-fe (DOCX+mockups → specs/03-ui reuse-map) | `ui-spec` | — | codegraph | frontend- |
| `technical-design` | orchestrated-sdd — **API-contract only** (→ specs/08,06,04; schema=owner, UI=`ui-spec`) | `technical-design` | `mh-rule-auditor` | codex-reviewer | backend-, frontend- |
| `task-slicing` | orchestrated-sdd (→ specs/10,04, vertical slices; large modules) | `task-slicing` | — | — | backend-, frontend- |
| `incremental-impl` | orchestrated-wrapper — **internal per-task executor** (called BY `mh-implement`) | `incremental-impl` | `mh-implementer` | — | backend-, frontend- |
| `super-test` | orchestrated-mimo-led (harvest → batch-RCA → repair; sibling of progressive-test) | `super-test` | — | opencode-executor, claude-opus-batch-rca, codex-reviewer | backend-, frontend- |

**Reuse note:** `bug-fix` reuses `mh-rca` (follows the bug-trace playbook) + `/mh-fix`; `incremental-impl` is the **internal per-task executor** of `mh-implement`; `impact-analysis` wraps CodeGraph.

**FE pipeline (owner decision 2026-06-16) — by OWNERSHIP, not phase:** the **owner** authors `02-requirements` + `07-schema` (agents NEVER author schema). **`/ui-spec`** turns DOCX + PNG mockups into a detailed `03-ui.md` reuse-map (multimodal + deep FE reuse-audit). **`/mh-implement` FE-mode** (`engine/skills/mh-implement/fe-flow.md`) CONSUMES that `03-ui.md` to build, folding `incremental-impl` in per task. `technical-design` is narrowed to the **API contract** (`08`, draft→owner-approves); `task-slicing` is for LARGE/cross-cutting modules (a normal FE feature slices internally from `03-ui`). The SDD workflows share `_shared/` (gate-check + module-state + envelope). Skills: capability (`mh-scaffold` `mh-implement` `mh-fix` `promote`) + orchestrator/entry (`mh-review` `agentflow` `impact-analysis` `bug-fix` `ui-spec` `technical-design` `task-slicing`); `incremental-impl` is an internal executor (not a standalone owner entry).

**Super-Test (MiMo-led — Topology B):** `engine/workflows/super-test/` — OpenCode/MiMo DRIVES module-level exploratory **bug-harvesting** (agent-browser sweep → bug-catalog/coverage-map/bypass-log/blocked-flows), then file-hands-off to **Opus 4.8** for BATCH cluster-RCA + Codex gate + MiMo repair + targeted & module-sweep retest. Sibling of `progressive-test` (harvest-first, NOT fix-first). Reuses progressive-test's agent-browser + `_shared/{envelope,validate-envelope,allowlist-check}`. **Claude/Opus is a CALLED specialist, never the orchestrator.** Entry: launcher skill `/super-test` → `bin/sweep` (the executor — **opencode OR mimo-code** — drives; `bin/_executor-lib.sh` auto-picks). **Full chain wired (M1+M2+M3):** `sweep` (harvest) → `call-opus-batch-rca` (`mh-batch-rca` Opus) → `call-codex-review` → `repair` (allowlist-enforced via `_shared/allowlist-check.py`) → `retest --targeted` → `retest --sweep` → `supertest final-report`. State machine on `00-super-test-state.md`. UNPROVEN e2e — first real run = owner gate.

## How to add a workflow
1. Create `engine/workflows/<name>/` with its machinery (`.js` and/or `bin/lib/schemas`) + a `manifest.json`
   (`name`, `description`, `kind`, `entry_skill`, `agents`, `external_agents`, `skills_used`, `rules`).
2. Put its entry **skill** in the `engine/skills/` pool; reuse existing `agents`/`rules` by name (or add new
   ones to their pools first).
3. Add a row to the Workflows table above. `harness_doctor.py` will fail if a manifest reference is dangling.
4. **Don't reinvent gates/receipts/state** — compose `engine/workflows/_shared/` (`gate-check.py`, `validate-envelope.py`, `module-state.py`) and list them in the manifest's `uses_shared`. Add a fast-path for trivial inputs and a learning-loop close-out (→ `second-brain/`).
