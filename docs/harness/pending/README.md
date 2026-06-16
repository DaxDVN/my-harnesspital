# Pending — enforcement LIFTED to harness (Stage 4 NOT applied to projects)

> **Decision 2026-06-16:** the user chose **not** to push these changes into `myhospital-fe`/`myhospital-be`. Their **enforcement was lifted to the harness layer** so they take effect **without modifying the projects**. The staging worktree `harness-stage4` was removed; the real repos are untouched. The diffs below are kept only as **optional owner-discretion project hygiene** — not required for the harness.

## Where each Stage-4 effect now lives (harness layer)
| Stage-4 item | Enforced by (harness, no project change) | Project edit still needed? |
|---|---|---|
| no `axios` import | **ast-grep `mh-no-axios-import`** (`scripts/sgconfig/rules/`) → `mh_scan` | **No** (lifted here) |
| no raw `fetch` in UI | ast-grep `mh-no-raw-fetch` → `mh_scan` | No |
| no dead `@/lib/dtos/dtos` | ast-grep `mh-dead-dtos-import` + guard advisory | No |
| no banned libs (zustand/jotai/redux/mobx/react-icons/react-modal) | guard advisory (edit-time) | No |
| master-data name-compare | ast-grep `mh-masterdata-name-compare` | No |
| stale FE docs (`ARCHITECTURE-OVERVIEW`, `BEST-PRACTICES-NEW-PAGE`) | noted in `harness/rules/frontend-rules-conventions-patterns.md` + memory `fe-live-conventions-vs-stale-docs` | No (banner unnecessary) |
| `CONVENTIONS.md` drift | `harness/rules/backend-rules-conventions-patterns.md` is **CANON**; `convention_truth` flags the drift | No (canon supersedes) |
| committed `.v2.bak` | `mh_scan` / DoD flags committed `.bak` | Optional cleanup |
| broken `create:page` | replaced by `/mh-scaffold` | Optional cleanup |
| `components.json rsc:true` | `/mh-scaffold` emits correct components regardless | Optional (shadcn-CLI only) |
| 38 missing-auth endpoints | `mh_scan auth_coverage` (BLOCK gate) | **Owner decision** — see `auth-triage-2026-06-16.md` |

## Optional — if you ever DO want to apply to the projects
`fe-main-repo-diffs-2026-06-16.md` (FE config/cleanup) + `CONVENTIONS.fixed.md` (BE doc) are kept as ready diffs — apply via a worktree + PR. The ast-grep/guard/canon floor already catches the violations regardless, so this is hygiene, not enforcement.

## Auth (38 endpoints) — still owner-driven
`auth-triage-2026-06-16.md` — NOT auto-applied (payment-webhook / OTP endpoints would break if blindly locked). The `auth_coverage` scanner is the durable gate; fix per-Api with the owner.
