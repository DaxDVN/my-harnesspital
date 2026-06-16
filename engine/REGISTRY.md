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
| `mh-rca` | read-only root-cause investigator | backend-/frontend-rules | `progressive-test` |

## Skills (`engine/skills/<name>/SKILL.md`)
| skill | what | entry for workflow |
|---|---|---|
| `mh-scaffold` | emit canonical BE/FE patterns | — |
| `mh-implement` | guided feature implementation | — |
| `mh-fix` | safe bug-fix from a findings file | — |
| `mh-review` | ≤3-round partitioned review | `deep-review` |
| `promote` | second-brain → main-brain (owner-gated) | — |
| `agentflow` | orchestrate the FE-bug-fix loop | `progressive-test` |

## Rules (`engine/rules/`) — pool every agent/workflow may obey
`backend` · `frontend` · `source-discovery` ·
`cross-tool-enforcement` · `worktree-workflow`. Review knowledge pool: `engine/workflows/deep-review/{protocol,checklist,findings-schema}.md`.

## Workflows (`engine/workflows/<name>/` — one folder each, + manifest.json)
| workflow | kind | entry skill | agents | external | rules |
|---|---|---|---|---|---|
| `deep-review` | workflow-tool-js (`workflow.js`) | `mh-review` | `mh-reviewer` | — | backend-, frontend- |
| `progressive-test` | orchestrated-subsystem (`.agentflow/`) | `agentflow` | `mh-rca` | codex-reviewer, opencode-executor | backend-, frontend- |

## How to add a workflow
1. Create `engine/workflows/<name>/` with its machinery (`.js` and/or `bin/lib/schemas`) + a `manifest.json`
   (`name`, `description`, `kind`, `entry_skill`, `agents`, `external_agents`, `skills_used`, `rules`).
2. Put its entry **skill** in the `engine/skills/` pool; reuse existing `agents`/`rules` by name (or add new
   ones to their pools first).
3. Add a row to the Workflows table above. `harness_doctor.py` will fail if a manifest reference is dangling.
