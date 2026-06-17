# engine/ — the governing core + CANONICAL HOME for all harness assets

The **single, tool-neutral home** for everything the harness is made of: the rules every tool obeys, the
routing map, **and the executable assets (skills, agents, hooks, workflows) themselves**. Every coding tool
(Claude, Codex, opencode/mimocode, …) read from here; their own dirs (`.claude/` `.codex/` `.opencode/`)
hold config + pointers. **Wiring depth varies (see "How each tool reaches" below) — only Claude is fully
symlinked; Codex/opencode reach engine via `AGENTS.md` auto-load + guard, engine skills read as docs.**

Where this sits (3 knowledge tiers; engine = the doer):
- **`main-brain/`** — concise, gated source-of-truth (lessons + durable truths). Refers down here.
- **`engine/`** (here) — the rules/routing + the skills/agents/hooks/workflows. Shared law AND shared recipes.
- **`second-brain/`** — provisional learnings; promoted up to `main-brain/` or graduated into a new skill.

**Inventory — read `engine/REGISTRY.md` first:** every agent / skill / rule / workflow + who composes what.
Components are flat shared POOLS (`agents/` `skills/` `rules/`); each **workflow is ONE folder** in
`workflows/<name>/` (self-contained machinery + its own workflow-specific knowledge) that **composes** the
pools BY NAME via its `manifest.json` — no duplication.

## Layout
**Shared pools (referenced by name from workflows):**
- **`rules/`** — convention canon + policies. Precedence in `rules/README.md`.
  - `backend.md` · `frontend.md` — **CANON** (scope-split: FE work loads `frontend`, BE work loads `backend`)
  - `source-discovery.md` · `cross-tool-enforcement.md` · `worktree-workflow.md` — policies
- **`agents/`** — subagent defs (all `mh-` prefixed): `mh-reviewer` · `mh-implementer` · `mh-rule-auditor` · `mh-rca`
- **`skills/`** — see "two kinds" below: `mh-scaffold` `mh-implement` (FE-mode `fe-flow`) `mh-fix` `promote` (capability) + `mh-review` `agentflow` `impact-analysis` `bug-fix` `ui-spec` `technical-design` `task-slicing` (orchestrator/entry); `incremental-impl` = internal per-task executor of `mh-implement`
- **`hooks/`** — guard tripwire + SessionStart probe (`myhospital_guard.py`, `graphify_stale_check.py`)
- **`agent-shortcuts.md`** — intent→tool routing (auto-loaded; `@`-imported by `CLAUDE.md`)

**Workflows (ONE folder each — self-contained + `manifest.json`):**
- **`workflows/deep-review/`** — `workflow.js` + the review knowledge (`protocol.md`/`checklist.md`/`findings-schema.md`) + manifest. Entry skill: `/mh-review`.
- **`workflows/progressive-test/`** — the `.agentflow/` orchestrated subsystem (bin/lib/schemas/…) + manifest. Entry skill: `/agentflow`.
- **`workflows/impact-analysis/` · `bug-fix/` · `ui-spec/` · `technical-design/` · `task-slicing/` · `incremental-impl/`** — preflight · bug loop · **FE keystone `ui-spec`** (DOCX+mockups → `03-ui.md`) · **API-contract** `technical-design` (→ `08`) · slicing (large modules) · the **internal** per-task executor (`incremental-impl` is called BY `mh-implement`). Entry skills of the same name.
- **`workflows/_shared/`** — support (NOT a workflow): deterministic `gate-check.py` + `validate-envelope.py`/`envelope.schema.json` + `module-state.py` the SDLC workflows compose (`uses_shared`). No manifest; self-tested by `harness_doctor`.

## Skills come in TWO kinds (so `/agentflow` isn't "half-everything")
- **capability skill** — a standalone capability (emit a pattern / fix / promote): `mh-scaffold`, `mh-implement`, `mh-fix`, `promote`.
- **orchestrator/entry skill** — the invokable ENTRY that DRIVES one workflow: `mh-review` → `deep-review`, `agentflow` → `progressive-test`. It must be a skill (that's how Claude exposes the `/cmd`); it reads like a router because it orchestrates. The command name may differ from the workflow name; `manifest.json` + `REGISTRY.md` map them.

## How each tool reaches engine's assets
- **Claude:** `.claude/{skills,agents,hooks,workflows}` are **symlinks → `engine/…`** (proven). Hooks also pointable by path in `settings.json`.
- **Codex:** `AGENTS.md` → `engine/` knowledge; guard via `.codex/hooks.json` (**walk-up to root → works from a worktree cwd**; does NOT cover `apply_patch` file edits). Engine skills are read as **workflow DOCS, NOT callable slash-skills** (no project skill loader wired) — so route via the docs, not `/cmd`.
- **opencode / mimocode:** opencode-fork; `.opencode/opencode.json` carries `instructions: ["AGENTS.md", "engine/rules/*.md"]` + the global guard plugin; **mimocode auto-loads `AGENTS.md`**. (Per-skill pointers not wired — skills read as docs; subagent tool calls aren't guard-intercepted — see `engine/rules/cross-tool-enforcement.md`.)
- **Automation (neutral):** `scripts/` — `mh_scan` (scan), `convention_truth.py` (drift), `harness_doctor.py` (health), `worktree.py`.

## Precedence (source of truth)
live code (`file:line`) > **`engine/rules/*` (canon)** > repo docs (`myhospital-be/CONVENTIONS.md`, `myhospital-fe/CLAUDE.md` — may drift) > memos in `docs/harness/notes/`.

## One folder per workflow (the rule)
EVERY workflow = `engine/workflows/<function-name>/` with its machinery (`.js` and/or `bin/lib/schemas`) +
its OWN workflow-specific knowledge + a `manifest.json` (declares `entry_skill` + the `agents`/`rules` it
composes, BY NAME). Shared agents/skills/rules live in the pools and are **referenced, never duplicated**.
Inventory + the add-a-workflow recipe → `engine/REGISTRY.md`.

## NOT here
Source-of-truth knowledge / lessons → `main-brain/`. Learning buffer → `second-brain/`. Business specs →
`specs/`. Reference / guides / worklogs → `docs/` (harness history in `docs/harness/`). Per-tool config +
pointers → `.claude/` `.codex/` `.opencode/`. Runnable commands → `scripts/`.
