---
name: mh-implement
description: Guided, convention-safe FEATURE implementation for a MyHospital module (FE/BE), in a worktree. Shift-left harness — loads the live conventions BEFORE writing code, reuses existing patterns, and self-reviews its own diff so mh-review converges fast. Use when building a new page/feature/module or extending one. Trigger "/mh-implement", "implement feature X", "build page/module Y", "triển khai feature".
---

# mh-implement — orchestrator (DEV side)

> Full runbook. `SKILL.md` is the token-light discovery stub for this skill.

Companion to **`mh-review`**. Where mh-review *finds* issues after the fact, mh-implement *prevents* them at write-time (shift-left = the strongest lever for ≤3-round convergence, per `docs/harness/notes/review-harness-feasibility-2026-06-16.md` §7.2). For **bug-fixing** use **`mh-fix`** instead — different stance (repro-first vs reuse-first).

## Boundary — scaffold vs implement vs fix
- **`/mh-implement` (this)** — build/extend a whole **feature** (multi-file; needs reuse + DoD + self-review). **Calls `/mh-scaffold`** at B3 when it needs a fresh canonical skeleton.
- **`/mh-scaffold`** — emit ONE canonical pattern to paste (single endpoint/service/page/form). No orchestration. Use standalone when you only need the *shape*, not a feature.
- **`/mh-fix`** — fix a known **bug** (repro-first), not build new.

> Rule of thumb: *feature → implement (uses scaffold) · one pattern → scaffold · bug → fix.*

## Mode — FE vs BE (the middle branches; B0/B5 are shared)
- **FE target (`myhospital-fe`) → follow [fe-flow.md](./fe-flow.md) (F0–F8).** It specializes B1–B4 into 9 FE
  gates (contract-sync · reuse · scaffold · data-wiring · forms · cross-cutting · deterministic floor), each
  with its silent-failure pitfall + a per-phase done-check. FE work **consumes `specs/<module>/03-ui.md`** —
  the UI.md from the **`/ui-spec`** workflow, whose **REUSE MAP** drives F2 onward (do not re-derive reuse).
- **BE target (`myhospital-be`) → the existing B1–B4 below.**
- **FE+BE feature** → BE contract first (B-flow), `npm run dtos:update && npm run client:generate`, then the FE side via `fe-flow.md`.

Bundle docs in this folder: **[preflight.md](./preflight.md)** (reuse discovery), **[definition-of-done.md](./definition-of-done.md)** (the gate), **[fe-flow.md](./fe-flow.md)** (the FE-specialized F0–F8 path). Live convention source of truth: `engine/rules/frontend.md` (FE) + `backend.md` (BE). FE reality spine (memory `fe-live-conventions-vs-stale-docs` + audit `velvet/notes/myhospital-fe-convention-audit-2026-06-15.md`): RQ-via-adapter + `useMasterData` + id-only + shadcn. **Do NOT trust `ARCHITECTURE-OVERVIEW.md` / `BEST-PRACTICES-NEW-PAGE.md` — both stale (audit V10).**

## B0 — Scope & worktree
Follow the Session Start Protocol: `python scripts/worktree.py list`, confirm slug/slot, **work in `worktrees/<slug>/fe|be`** — never edit `myhospital-fe/` or `myhospital-be/` directly (guard hook enforces). If a spec module exists, read `specs/<module>/{02-requirements,03-ui,06-decision-log,08-api}.md` — Confirmed requirements + decisions are the business source of truth. FE+BE work → BE contract first, regen FE DTO/client, then FE usage.

> **B1–B4 below are the BE / generic path. For an FE target use [fe-flow.md](./fe-flow.md) (F1–F8) instead** — same B0/B5 spine, FE-specialized middle with per-axis gates.

## B1 — Pre-flight discovery (anti-reinvent) — see [preflight.md](./preflight.md)
Mandatory before writing. Reuse beats authoring. In short: **CodeGraph** (`codegraph explore/node` from the fe repo) + (for an FE feature) the **`/ui-spec` reuse-map** in `specs/<module>/03-ui.md` + bounded `rg` for the target area, and pick the **warehouse exemplar — its GOOD parts only**:
- ✅ COPY: routing (`lazy`+`Suspense`+`LayoutSelector`+Provider), mutation hooks `adapter.useXxx({successMessage, invalidateQueries, onSuccess})`, table (`useReactTable`+`EnhancedDataGrid`+`useMemo` cols), shadcn UI, RHF+`zodResolver`+dirty-guard.
- ❌ DO NOT COPY (audit §4): monolithic 600+-line page files, `useState`-only context as a data layer, schema inlined in the page, `models.ts` that only re-exports DTOs.

## B2 — Convention contract (shift-left) — print BEFORE coding
Emit a short per-task contract = the subset of rules that apply, so you bind yourself up front. Always include the spine, plus whatever the task touches:
- Server state via the module **adapter** (`extends GeneratedApiClient`); **no `fetch`/`axios`/manual `JsonServiceClient`/bearer** in UI (cookie `ss-id` already). Reference/dropdown data via **`useMasterData([Entity])`** — never an ad-hoc query.
- Every list/master mutation invalidates **both** `invalidateQueries` **and** `invalidateMasterDataEntity(...)`.
- **Reference by Id**, not name/code: `find(x => String(x.Id) === value)`. Business rules from **BE flags / generated `Constants.ts`** (`IsDefault`/`Requires*`/`*Option`), never hardcoded strings (audit V3 — e.g. no `=== 'kinh'`).
- Tables → `EnhancedDataGrid`; forms → RHF + `zodResolver` + schema factory `getXxxFormSchema(t?)` in `forms/`; status → `StatusBadge`+`STATUS_REGISTRY`; permission → `useUserPermissions().can(...)`; i18n → `useIntl`/`useTranslation` (no new hardcoded VN text).
- **No FE money/stock/cost/posted/balance computation.** No new global-state lib. No edits to routing roots / providers / generated files / configs without approval.

## B3 — Implement
Build against the contract, reusing what B1 found. Apply `engine/rules/ponytail.md`: use the smallest correct
diff that preserves MyHospital conventions; do not add abstractions, dependencies, or "future-ready" scaffolding
unless the current task requires them. For a brand-new skeleton (module / list-page / form-sheet / adapter /
routing) use **`/mh-scaffold`** — it emits the canonical FE+BE shapes (replaces the broken
`npm run create:page`/`create:module`, audit V9). For independent bounded sub-tasks, delegate to the
**`mh-implementer`** subagent (Agent tool) — one per disjoint file/scope, in the SAME worktree. Keep page files
split (wrapper + `components/*-content.tsx`), not monolithic.

## B4 — Definition-of-Done gate — see [definition-of-done.md](./definition-of-done.md)
Run the deterministic floor + types/lint:
- `python scripts/mh_scan --root worktrees/<slug>/fe --scope <changed...> --format summary` — the unified FE+BE scanner; FE rules flag dead `@/lib/dtos/dtos` import (FE-V1, HIGH), raw `fetch()` (FE-V2), master-data name-compare like `=== 'kinh'` (FE-V3), `serviceStackClient.*` in a component.
- `npx tsc --noEmit` (from the worktree fe) — catches FE-V1 + contract drift.
- scoped `npx eslint <changed> --no-fix` — **never `npm run lint`**.
- regen DTO/client if contract changed.

Fix every HIGH/BLOCK before B5; advisory WARN each fixed or justified (audit §6 exception, with a comment).

## B5 — Self-review-diff (M3)
Before handing off, self-review **only your diff**. Use `git -C worktrees/<slug>/<fe|be> diff --name-only <base>` to list changed files, then check the relevant D1-D10 checklist dimensions manually plus deterministic scanners. Do **not** invoke the full partitioned `mh-review` workflow here unless the owner explicitly asks for a review/audit or the router selected a review workflow. Fix what the scoped self-review flags now. Then summarize: files changed, contract items honored, validation commands run + results, residual risks.

## Safety
Worktree-only edits; honor the guard hook (no git history mutation, no recursive delete, no new deps, no editing generated files). Report actual validation run (Validation Contract). If a required DTO/constant/permission is missing → **stop, report a BE/API contract blocker** (do not hand-write or work around). If a business rule is ambiguous → route to `specs/<module>/05-open-questions.md`, do not invent it.

## Learning loop
After review/validation closes the feature, promote any new/recurring mistake to the cheapest layer (`engine/workflows/deep-review/protocol.md §7`): guard/ESLint/ast-grep (deterministic) → `engine/rules/*` (convention) → `engine/workflows/deep-review/checklist.md` "Known bug-classes" → auto-memory.
