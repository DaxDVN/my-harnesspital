# engine/rules/ — convention canon + policy (tool-neutral)

The **sole canon** for MyHospital conventions, read by every agentic tool. When a doc conflicts with **live code**, trust the code (some repo docs are stale).

## Files
| File | Role |
|---|---|
| `backend.md` | **CANON BE** — BaseService, no-transaction/lock, no-N+1, tenant/hospital scope, ErrorCodes, `[RequireAuth]`, migration discipline. |
| `frontend.md` | **CANON FE** — RQ-via-adapter, `useMasterData`, id-only refs, shadcn, no FE money/stock math, RHF+zod, EnhancedDataGrid. |
| `backend/*.md` | Compact BE quick/topic cards selected by `python scripts/rule_card.py be "<task>"`; use before opening full `backend.md`. |
| `frontend/*.md` | Compact FE quick/topic cards selected by `python scripts/rule_card.py fe "<task>"`; use before opening full `frontend.md`. |
| `source-discovery.md` | CodeGraph-first + bounded `rg`/`fd`/`bat` policy (never broad-dump FE/BE). |
| `ponytail.md` | Minimal-correct-diff discipline: avoid over-building without weakening safety/validation. |
| `quality-gates.md` | Evidence gates: reuse proof, fix plan, regression map, adjudication, validation, scanner promotion. |
| `preflight-confirmation.md` | Natural-language route prediction + owner confirmation before workflow/agent/source-edit execution. |
| `cross-tool-enforcement.md` | How the guard tripwire wires into Claude / Codex / opencode. |
| `worktree-workflow.md` | Worktree lifecycle policy; intent→command map. Terminal/session control is owner-manual and outside harness. |
| `memory-policy.md` | Lazy-loaded memory/learning tiers, recall, capture, promotion policy. |
| `artifact-policy.md` | Lazy-loaded artifact paths, date folders, audit round versioning. |
| `session-boot-details.md` | Lazy slot map, browser smoke login, and bootloader reference details. |
| `spec-driven-development.md` | Lazy-loaded requirement/design/spec change-control protocol. |
| `graphify.md` | Lazy-loaded docs/specs graph policy and trust model. |
| `multi-agent-execution.md` | Lazy-loaded subagent/worker orchestration policy. |

## Precedence
live code (`file:line`) > **these files (canon)** > `myhospital-be/CONVENTIONS.md` & `myhospital-fe/CLAUDE.md` (repo-local pointers, may lag).

Daily source work should load the package quick/topic cards first. Open the full FE/BE canon only when the cards
do not cover the task, the change is high-risk, or local evidence conflicts.

## Known drift (repo doc vs canon — pending fix)
`myhospital-be/CONVENTIONS.md` is wrong in 5–6 spots (D1–D6): code prefix (LK/CL → MV/CS), SettingKeys path, `/types` endpoint claim, action names (lists `CanCreate`/`CanApprove` which don't exist — only `CanInsert`), `GetByIdAsync` helper, transaction wording. Corrected version staged at **`docs/harness/pending/CONVENTIONS.fixed.md`** → apply via BE worktree + PR, then demote `CONVENTIONS.md` to a thin pointer (kills drift permanently). Drift checker: `python scripts/convention_truth.py`.
