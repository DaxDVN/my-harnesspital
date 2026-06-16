# engine/workflows/ — standalone Workflow-tool scripts

Canonical home for **named, standalone** Workflow-tool scripts. Like all harness assets they live in
`engine/`; Claude discovers them via the `.claude/workflows` → `engine/workflows` symlink (the Workflow
tool resolves `{name: "<x>"}` to `<x>.js`). Running `.js` workflows is a **Claude Code feature** (Codex/
opencode don't execute them), but the files still live here in `engine/` so there is one source.

This folder ALSO hosts **orchestrated multi-agent subsystems** — self-contained workflow dirs with their
own `bin/`/`lib/`/`schemas/` driven by a Claude orchestrator skill (e.g. `agentflow-opencode/`, run by the
`/agentflow` skill: a Claude-orchestrated OpenCode/mimo + Opus-RCA + Codex-gate FE-bug-fix loop over file
artifacts + envelopes). Same principle: one canonical source under `engine/`, every tool points in.

## Which folder a workflow goes in
- **Bound to one skill** (it IS that skill's engine) → keep it in the skill dir:
  `engine/skills/<skill>/workflow.js` (e.g. `mh-review/workflow.js`). Do **not** move it here.
- **Standalone / reusable / invoked by name** → `engine/workflows/<name>.js`.

## Rules every workflow obeys
1. **Orchestrate, don't legislate.** A workflow fans out agents and loops/verifies; it reads the rules
   from `engine/` (canon, `review/checklist.md`, `review/findings-schema.md`) — it must **never embed its
   own copy**. Duplicated rules are the #1 way the harness drifts: two sources of truth that diverge.
2. **`export const meta` is a pure literal** (`name`, `description`, `phases`). `name` = the resolve key.
3. **Deterministic control flow only.** Use a workflow when the loop/fan-out/verify should be *code*
   (loop-until-dry, adversarial verify, pipeline). If a step needs judgment, that's a skill or an agent.
4. **No file writes from the script** — workflows return structured data; the *caller* writes files
   (e.g. mh-review's audit `.md` under `docs/audit/`).
5. **Honor the guard + safety rules** — no git history mutation, never touch `myhospital-fe|be` or
   `worktrees/` (audit/read-only stays read-only).

## Current workflows
- `agentflow-opencode/` — orchestrated subsystem (FE-bug-fix loop; `/agentflow` skill). Envelope-native, hybrid-triage.
- _(no standalone `.js` yet)_ — `engine/skills/mh-review/workflow.js` is skill-bound and stays in its skill dir.
