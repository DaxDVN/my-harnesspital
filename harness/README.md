# harness/ — tool-neutral harness knowledge

This folder is the **single, tool-neutral home** for MyHospital harness knowledge. Every agentic coding tool (Claude, Codex, opencode, Cursor, …) reads these files **by path** — nothing here is Claude-specific. Tool-specific *wiring* lives in each tool's own dir; this folder is the shared *truth* they all point at.

## Layout
- **`rules/`** — convention canon + policies (what every tool checks code against). Precedence in `rules/README.md`.
  - `backend-rules-conventions-patterns.md` · `frontend-rules-conventions-patterns.md` — **CANON**
  - `source-discovery.md` · `cross-tool-enforcement.md` · `worktree-workflow.md` — policies
- **`review/`** — the `mh-review` ≤3-round audit knowledge, tool-neutral:
  - `protocol.md` (runbook) · `checklist.md` (10 dimensions D1–D10) · `findings-schema.md` (findings interchange format)

## How each tool wires in (all point HERE)
- **Dispatcher:** `AGENTS.md` (repo root) — the cross-tool entry every tool reads; routes to this folder.
- **Claude:** `.claude/skills/` (mh-review / mh-implement / mh-fix / mh-scaffold drivers), `.claude/agents/`, `.claude/hooks/myhospital_guard.py` → read `harness/`.
- **Codex:** `.codex/` (hooks/config) → reads `AGENTS.md` → `harness/`.
- **opencode:** `.opencode/` + `scripts/opencode/myhospital-guard.js` → `harness/`.
- **Automation (neutral, any tool runs):** `scripts/` — `python scripts/mh_scan` (deterministic scan FE+BE), `scripts/convention_truth.py` (doc-drift), `scripts/harness_doctor.py` (health), `scripts/worktree.py`.

## Precedence (source of truth)
live code (`file:line`) > **`harness/rules/*` (canon)** > repo docs (`myhospital-be/CONVENTIONS.md`, `myhospital-fe/CLAUDE.md` — pointers, may drift) > memos/worklogs in `docs/harness/`.

## NOT here
Reference docs / worklogs / plans → `docs/harness/`. Business specs → `specs/`. Per-tool wiring → `.claude/` `.codex/` `.opencode/`. Automation → `scripts/`.
