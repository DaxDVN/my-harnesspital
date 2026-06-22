# incremental-impl (W9) — wrap /mh-implement, one task/slice at a time

Entry skill: `/incremental-impl`. The ONLY code-editing SDLC workflow. Thin wrapper — does NOT rebuild.

## Reuses (does NOT rebuild)
- **`/mh-implement`** skill (+ `mh-implementer` subagent) — already does worktree + convention preflight +
  reuse discovery + allowlist-bounded edits + validation + self-review-diff. W9 just feeds it ONE task + captures an envelope.
- **`robust-test targeted`** / **`/bug-fix`** for FE verify + any bug found. **`/impact-analysis`** for high-risk tasks.

## Inputs → Outputs
IN: ONE approved task from `specs/<module>/10-plan.md`. OUT: `rounds/<id>/{01-task-implementation,02-validation,03-e2e?,04-completion}` + envelope.

## Plan-mismatch policy (no improvising)
file missing · code differs from audit · allowlist insufficient · needs an API not in `08-api` · validation
reveals a missing design decision → STOP, write PLAN_MISMATCH, route back to `task-slicing`/`technical-design`.

## Boundaries / status
Edits only via `/mh-implement` in a worktree (never main fe/be), allowlist-bounded. Thin wrapper over proven
`/mh-implement`; wrapper wiring UNPROVEN → owner gate. **Needs an approved `10-plan.md` (from `/task-slicing`).**
