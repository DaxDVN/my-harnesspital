# engine/workflows/ — one folder per workflow

Canonical home for **named, standalone** Workflow-tool scripts. Like all harness assets they live in
`engine/`; Claude discovers them via the `.claude/workflows` → `engine/workflows` symlink (the Workflow
tool resolves `{name: "<x>"}` to `<x>.js`). Running `.js` workflows is a **Claude Code feature** (Codex/
opencode don't execute them), but the files still live here in `engine/` so there is one source.

This folder ALSO hosts **orchestrated multi-agent subsystems** — self-contained workflow dirs with their
own `bin/`/`lib/`/`schemas/` driven by a Claude orchestrator skill (e.g. `progressive-test/`, run by the
`/agentflow` skill: a Claude-orchestrated OpenCode/mimo + Opus-RCA + Codex-gate FE-bug-fix loop over file
artifacts + envelopes). Same principle: one canonical source under `engine/`, every tool points in.

## One folder per workflow (the rule)
EVERY workflow = a folder `engine/workflows/<name>/` containing its machinery (`.js` and/or `bin/lib/schemas`)
+ a **`manifest.json`** that declares, BY NAME, the shared parts it composes: `entry_skill`, `agents`,
`external_agents`, `skills_used`, `rules`. The entry **skill** lives in the `engine/skills/` pool; the
**agents/rules** are referenced from their pools — **never duplicated** into the workflow folder. A single
bare named `.js` (invoked by `{name}`) may sit flat as `engine/workflows/<name>.js`.
**Inventory of everything → `engine/REGISTRY.md`.** Examples: `deep-review/` (workflow.js + manifest),
`progressive-test/` (`.agentflow/` subsystem + manifest).

## Rules every workflow obeys
1. **Orchestrate, don't legislate.** A workflow fans out agents and loops/verifies; it reads the rules
   from `engine/` (canon, `workflows/deep-review/checklist.md`, `workflows/deep-review/findings-schema.md`) — it must **never embed its
   own copy**. Duplicated rules are the #1 way the harness drifts: two sources of truth that diverge.
2. **`export const meta` is a pure literal** (`name`, `description`, `phases`). `name` = the resolve key.
3. **Deterministic control flow only.** Use a workflow when the loop/fan-out/verify should be *code*
   (loop-until-dry, adversarial verify, pipeline). If a step needs judgment, that's a skill or an agent.
4. **No file writes from the script** — workflows return structured data; the *caller* writes files
   (e.g. mh-review's audit `.md` under `docs/audit/`).
5. **Honor the guard + safety rules** — no git history mutation, never touch `myhospital-fe|be` or
   `worktrees/` (audit/read-only stays read-only).

## Current workflows
- `deep-review/` — `workflow.js` + review knowledge (`protocol`/`checklist`/`findings-schema.md`) + manifest. Entry skill: `/mh-review`.
- `progressive-test/` — `.agentflow/` orchestrated subsystem (bin/lib/schemas) + manifest. Entry skill: `/agentflow`.
- `impact-analysis/` — CodeGraph-backed preflight blast-radius (READ-ONLY). Entry skill: `/impact-analysis`.
- `bug-fix/` — investigate→RCA→fix→verify from any source; `mh-rca` follows the bug-trace playbook. Entry skill: `/bug-fix`.
- `ui-spec/` — **FE keystone**: DOCX + PNG mockups → detailed `specs/<m>/03-ui.md` reuse-map (multimodal + deep FE reuse-audit). Entry skill: `/ui-spec`. Feeds the FE dev workflow.
- `technical-design/` (**API-contract only**: `08`; schema=owner, UI=`/ui-spec`) · `task-slicing/` (large/cross-cutting modules) · `incremental-impl/` (**internal** per-task executor of `/mh-implement`). Entry skills of the same name.

> **FE dev pipeline:** owner authors `02-requirements`+`07-schema` → `/ui-spec` → `03-ui.md` → `/mh-implement` FE-mode (`engine/skills/mh-implement/fe-flow.md`; folds `incremental-impl` per task).

## Shared support — `_shared/` (NOT a workflow)
`_shared/` holds the deterministic primitives the SDLC workflows compose — `gate-check.py` (real gates),
`validate-envelope.py` + `envelope.schema.json` (the ONE receipt), `module-state.py` (per-module SDLC
state). No `manifest.json` (so `check_registry` skips it); each self-tests under `harness_doctor`. A
workflow lists what it uses in its manifest's `uses_shared`. Contract: `_shared/README.md`.
(Inventory → `engine/REGISTRY.md`.)
