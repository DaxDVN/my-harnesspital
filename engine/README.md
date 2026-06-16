# engine/ — the governing core + CANONICAL HOME for all harness assets

The **single, tool-neutral home** for everything the harness is made of: the rules every tool obeys, the
review protocol, the routing map, **and the executable assets (skills, agents, hooks, workflows)
themselves**. Every coding tool (Claude, Codex, opencode, …) uses the SAME files here — their own dirs
(`.claude/` `.codex/` `.opencode/`) hold only config + **pointers** into this folder. Add a new tool = add
pointers once; no per-tool copies to re-create or forget.

Where this sits in the harness (3 knowledge tiers; engine = the doer):
- **`main-brain/`** (the BRAIN) — concise, gated source-of-truth (lessons + durable truths). *Refers down here* and knows engine CAN do X, not each file's detail.
- **`engine/`** (here) — the rules/protocols/routing + the skills/agents/hooks/workflows. The shared law AND the shared recipes.
- **`second-brain/`** — provisional learnings; promoted up to `main-brain/` or graduated into a new `engine/skills/<x>`.

## Layout
**Knowledge / law (read by every tool by path):**
- **`rules/`** — convention canon + policies. Precedence in `rules/README.md`.
  - `backend-rules-conventions-patterns.md` · `frontend-rules-conventions-patterns.md` — **CANON** (scope-split: FE work loads frontend, BE work loads backend)
  - `source-discovery.md` · `cross-tool-enforcement.md` · `worktree-workflow.md` — policies
- **`review/`** — `mh-review` ≤3-round audit: `protocol.md` · `checklist.md` (D1–D10) · `findings-schema.md`
- **`agent-shortcuts.md`** — intent→tool routing (auto-loaded; `@`-imported by `CLAUDE.md`)

**Executable assets (each tool points here via symlink / native config):**
- **`skills/`** — the skills (recipes): `mh-scaffold`, `mh-implement`, `mh-fix`, `mh-review` (+ its `workflow.js`), `promote`
- **`agents/`** — subagent defs: `mh-reviewer`, `mh-implementer`, `myhospital-rule-auditor`
- **`hooks/`** — the guard tripwire + SessionStart probe (`myhospital_guard.py`, `graphify_stale_check.py`)
- **`workflows/`** — home for STANDALONE Workflow-tool scripts (skill-bound workflows live in their skill dir)

## How each tool reaches engine's assets
- **Claude:** `.claude/{skills,agents,hooks,workflows}` are **symlinks → `engine/…`** (discovery proven). Hooks also pointable by absolute path in `settings.json`.
- **Codex:** `AGENTS.md` (→ `engine/` knowledge) + `[[skills.config]] path=engine/skills/*` + symlink for agents; guard via `.codex/hooks.json` → the `.claude/hooks` symlink.
- **opencode:** `instructions: ["engine/rules/*", …]` (native) + guard plugin → the symlink. (Commands/agent formats differ — wire when used.)
- **Automation (neutral):** `scripts/` — `mh_scan` (scan), `convention_truth.py` (drift), `harness_doctor.py` (health), `worktree.py`.

## Precedence (source of truth)
live code (`file:line`) > **`engine/rules/*` (canon)** > repo docs (`myhospital-be/CONVENTIONS.md`, `myhospital-fe/CLAUDE.md` — pointers, may drift) > memos/worklogs in `docs/harness/notes/`.

## Workflows (rule vs skill vs workflow)
- **rule** = `engine/rules` (law) · **skill** = `engine/skills/<name>` (model-driven recipe) · **workflow** = a deterministic Workflow-tool `.js`.
- Workflow bound to ONE skill → beside it (`engine/skills/<skill>/workflow.js`); standalone/named → `engine/workflows/<name>.js`. A workflow only orchestrates over `engine/` canon — never embeds its own copy. Full rule: `engine/workflows/README.md`.

## NOT here
Source-of-truth knowledge / lessons → `main-brain/`. Learning buffer → `second-brain/`. Business specs →
`specs/`. Reference / guides / worklogs → `docs/` (harness history in `docs/harness/`). Per-tool config +
pointers → `.claude/` `.codex/` `.opencode/`. Runnable commands → `scripts/`.
