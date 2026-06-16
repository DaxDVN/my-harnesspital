# engine/rules/ — convention canon + policy (tool-neutral)

The **sole canon** for MyHospital conventions, read by every agentic tool. When a doc conflicts with **live code**, trust the code (some repo docs are stale).

## Files
| File | Role |
|---|---|
| `backend.md` | **CANON BE** — BaseService, no-transaction/lock, no-N+1, tenant/hospital scope, ErrorCodes, `[RequireAuth]`, migration discipline. |
| `frontend.md` | **CANON FE** — RQ-via-adapter, `useMasterData`, id-only refs, shadcn, no FE money/stock math, RHF+zod, EnhancedDataGrid. |
| `source-discovery.md` | CodeGraph-first + bounded `rg`/`fd`/`bat` policy (never broad-dump FE/BE). |
| `cross-tool-enforcement.md` | How the guard tripwire wires into Claude / Codex / opencode. |
| `worktree-workflow.md` | Worktree + Zellij orchestration; intent→command map. |

## Precedence
live code (`file:line`) > **these files (canon)** > `myhospital-be/CONVENTIONS.md` & `myhospital-fe/CLAUDE.md` (repo-local pointers, may lag).

## Known drift (repo doc vs canon — pending fix)
`myhospital-be/CONVENTIONS.md` is wrong in 5–6 spots (D1–D6): code prefix (LK/CL → MV/CS), SettingKeys path, `/types` endpoint claim, action names (lists `CanCreate`/`CanApprove` which don't exist — only `CanInsert`), `GetByIdAsync` helper, transaction wording. Corrected version staged at **`docs/harness/pending/CONVENTIONS.fixed.md`** → apply via BE worktree + PR, then demote `CONVENTIONS.md` to a thin pointer (kills drift permanently). Drift checker: `python scripts/convention_truth.py`.
