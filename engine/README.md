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
  - `source-discovery.md` · `ponytail.md` · `quality-gates.md` · `preflight-confirmation.md` · `cross-tool-enforcement.md` · `worktree-workflow.md` — policies
- **`agents/`** — subagent defs (all `mh-` prefixed): `mh-reviewer` · `mh-implementer` · `mh-rule-auditor` · `mh-rca`
- **`skills/`** — see "two kinds" below: `mh-scaffold` `mh-implement` (FE-mode `fe-flow`) `mh-fix` `promote` `ponytail` (capability) + `mh-review` `robust-test` `impact-analysis` `bug-fix` `ui-spec` `technical-design` `task-slicing` (orchestrator/entry); `incremental-impl` = internal per-task executor of `mh-implement`
- **`hooks/`** — guard tripwire + prompt/session probes (`myhospital_guard.py`, `learning_trigger.py`, `preflight_trigger.py`, `graphify_stale_check.py`)
- **`router/` + `scripts/harness_router.py` + `scripts/harness_preflight.py` + `scripts/codex_preflight.py`** — read-only dry-run router and owner confirmation card for intent/risk/lifecycle/files-to-load decisions.
- **`docs/harness/evals/` + `scripts/harness_eval.py` + `scripts/harness_lifecycle_eval.py`** — eval/cost ledger validation (P4) for lifecycle promotion evidence.
- **`workflows/LIFECYCLE.md` + `scripts/harness_workflow_governance.py`** — workflow taxonomy/deprecation governance (P5).
- **`scripts/harness_runtime_contract.py` + `scripts/harness_ready.py`** — runtime-boundary scan and one-shot readiness gate (P6/P7).
- **`agent-shortcuts.md`** — lazy shortcut reference for human-readable aliases; no longer auto-loaded by `CLAUDE.md`.

**Workflows (ONE folder each — self-contained + `manifest.json`):**
- **`workflows/deep-review/`** — `workflow.js` + the review knowledge (`protocol.md`/`checklist.md`/`findings-schema.md`) + manifest. Entry skill: `/mh-review`.
- **`workflows/robust-test/`** — owner-gated targeted/sweep testing. It writes one folder per captured bug plus a review-ready bundle; no autonomous agent handoff and no source edits.
- **`workflows/impact-analysis/` · `bug-fix/` · `ui-spec/` · `technical-design/` · `task-slicing/` · `incremental-impl/` · `dev-from-handoff/`** — preflight · bug loop · **FE keystone `ui-spec`** (DOCX+mockups → `03-ui.md`) · **API-contract** `technical-design` (→ `08`) · slicing (large modules) · the **internal** per-task executor (`incremental-impl` is called BY `mh-implement`) · owner handoff docs → approved dev slices. Entry skills of the same name.
- **`workflows/_shared/`** — support (NOT a workflow): deterministic `gate-check.py` + `validate-envelope.py`/`envelope.schema.json` + `runtime-boundary.md` + `module-state.py` the SDLC workflows compose (`uses_shared`). No manifest; self-tested by `harness_doctor`.

## Skills come in TWO kinds
- **capability skill** — a standalone capability (emit a pattern / fix / promote / minimize a diff): `mh-scaffold`, `mh-implement`, `mh-fix`, `promote`, `ponytail`.
- **orchestrator/entry skill** — the invokable ENTRY that DRIVES one workflow: `mh-review` → `deep-review`, `robust-test` → `robust-test`. It must be a skill (that's how Claude exposes the `/cmd`); it reads like a router because it orchestrates. The command name may differ from the workflow name; `manifest.json` + `REGISTRY.md` map them.

## How each tool reaches engine's assets
- **Claude:** `.claude/{skills,agents,hooks,workflows}` are **symlinks → `engine/…`** (proven). Hooks also pointable by path in `settings.json`.
- **Codex:** `AGENTS.md` → `engine/` knowledge; guard via `.codex/hooks.json` (**walk-up to root → works from a worktree cwd**; does NOT cover `apply_patch` file edits). Engine skills are read as **workflow DOCS, NOT callable slash-skills** (no project skill loader wired) — so route via the docs, not `/cmd`.
- **opencode / mimocode:** opencode-fork; `.opencode/opencode.json` carries a thin bootloader (`AGENTS.md` + `engine/rules/README.md`) + the global guard plugin; **mimocode auto-loads `AGENTS.md`**. (Per-skill pointers not wired — skills read as docs; subagent tool calls aren't guard-intercepted — see `engine/rules/cross-tool-enforcement.md`.)
- **Automation (neutral):** `scripts/` — `mh_scan` (scan), `convention_truth.py` (drift), `harness_doctor.py` (health), `worktree.py`. Terminal/session control is intentionally not part of the harness.

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
