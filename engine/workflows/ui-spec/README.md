# ui-spec (W6-FE) — the FE-discovery keystone, INTO specs/<module>/03-ui.md

Entry skill: `/ui-spec` (`engine/skills/ui-spec/`). Owner-invoked. **Writes only `specs/` — READ-ONLY on source code.**

Turns a **business DOCX + PNG mockups + the owner's requirements** into a **detailed `specs/<module>/03-ui.md`** that maps every UI element to **REUSE / EXTEND / CREATE-NEW**, maximizing reuse of what the FE codebase already has. This `03-ui.md` is the **foundation/input of the FE dev workflow** — detailed enough that `mh-implement` (FE-mode) builds the page without guessing. It exists because, per `docs/harness/plans/fe-implementation-workflow-research-2026-06-16.md`, **reuse discovery is the #1 FE pain**: agents re-create components that already exist, and fall into the "exemplar trap" (copying the warehouse page wholesale, including its anti-patterns).

## Reuses (does NOT rebuild)
- The **SDD** `specs/<module>/03-ui.md` — this IS the UI artifact (not a parallel ui-design file). The owner's `02-requirements` / `07-schema` are the **input**, authored by the owner.
- **CodeGraph** (`cd myhospital-fe && codegraph explore "<need>"` / `codegraph node <symbol>`) — the FE reuse/dependency engine. **The CLI works from inside the repo.**
- *(No `*.generated.md` reuse catalogs / `components:index` — removed; CodeGraph above is the reuse engine.)*
- The **warehouse exemplar** — GOOD parts only (see the rubric + `engine/rules/frontend.md` "Warehouse is a PARTIAL exemplar").
- The shared primitives — `gate-check.py`, `module-state.py`, the envelope schema + `validate-envelope.py` (`engine/workflows/_shared/`).

## Inputs → Outputs
**IN:** the business DOCX (`rga` for `.docx/.pdf`) + the PNG mockup images + the owner's `specs/<module>/{02-requirements,07-schema}`.
**OUT:** a detailed `specs/<module>/03-ui.md` (routes/screens/states + forms + loading/error/empty + testid strategy + FE state plan + the reuse map), any mockup-vs-business **open questions** appended to `specs/<module>/05-open-questions.md`, and the round envelope.

## The 5 steps (in depth)

### STEP 0 — input gate (deterministic, before any work)
```bash
python engine/workflows/_shared/gate-check.py <module> --require 02-requirements --no-blocking 05-open-questions
```
Exit `2` → **STOP**: `02-requirements` missing/stub → `REQUIRES_SPEC_DISCOVERY` (owner authors requirements first); a `BLOCKING*` line in `05` → `REQUIRES_BA_DECISION`. Also STOP with `BLOCKED_NO_MOCKUPS` if the owner provided no mockup images — there is nothing to inventory. Fail-closed on the gate.

### 1 — Intake
Read the DOCX + the owner's `02-requirements` / `07-schema`. Enumerate the screens/flows in scope. You are mapping the **UI surface** onto existing FE assets; you do **not** re-derive the business rules or the schema.

### 2 — View mockups (MULTIMODAL — read the PNGs directly)
Open **each** mockup PNG with the **Read tool** (it renders images visually). Do not guess from filenames. Extract a **UI-needs inventory** — for every screen capture every: region/section · component · state (loading/error/empty/disabled/read-only) · field (label, type, required marker) · table/grid (columns, row actions) · form/modal/sheet · filter (incl. saved-filter affordances) · status display · action button · permission-gated element.

### 3 — Deep FE reuse-audit (per UI-need)
For each UI-need, search the FE in this order and stop at the first solid match:
1. **CodeGraph** — `cd myhospital-fe && codegraph explore "<need / component / hook>"`, then `codegraph node <symbol>` to read the verbatim source + callers. This is the primary reuse engine; treat its returned source as already read.
2. **shadcn / common / lib** — `src/components/ui/*` → `src/modules/common/*` → `src/lib/*`.
3. **Warehouse exemplar** — only the GOOD patterns (see rubric).
Then a **bounded** `rg -l` for an exact symbol in a known small scope. **Never broad-scan all of FE and dump output.**

**Fan-out for large modules:** spawn `Explore` (or `general-purpose`) subagents **partitioned by UI region** (e.g. list-page reviewer, create-form reviewer, filter-modal reviewer) so each does a deep CodeGraph+catalog pass on its slice in parallel. The parent owns the merge + the final reuse map (recall comes from partition, like `deep-review`). Each subagent must cite `file:line` and is read-only.

### 4 — Reuse map (the table)
One row per UI-need: **UI element → REUSE | EXTEND | CREATE-NEW → evidence (`file:line`) → notes (props/variants/hooks to pass)**.

| UI element | Class | Evidence (`file:line`) | Notes (props / variant / hook) |
|---|---|---|---|
| Status pill on the list | REUSE | `src/components/ui/status/status-badge.tsx:…` | pass `status`; register new status in `STATUS_REGISTRY` |
| Admin list grid | REUSE | `src/components/ui/enhanced-data-grid.tsx:…` | `toolbar`, `recordCount`, `isLoading`; do NOT raw-`<table>` |
| "Approve" button | EXTEND | warehouse capability hook `…use-inventory-capabilities.ts:…` | gate on status **and** `useUserPermissions().can(...)` |
| Bespoke triage panel | CREATE-NEW | (none — CodeGraph + both catalogs + shadcn show no match) | new `components/<x>.tsx`; reuse `Container`/`Card` shell |

#### REUSE-classification rubric (pick the cheapest tier that fits)
- **REUSE** — an existing component/hook/pattern works as-is. Cite `file:line` + props. Preference order `src/components/ui/*` → `src/modules/common/*` → `src/lib/*` → warehouse.
- **EXTEND** — existing thing is ~80% right; add a prop/variant or wrap it. Cite the base + the exact delta. **Never** copy-and-edit a private fork.
- **CREATE-NEW** — only after CodeGraph + both catalogs + shadcn confirm no match; state explicitly why nothing fits. CREATE-NEW is the **last resort**, the whole point of this workflow is to shrink it.

### 5 — Output `specs/<module>/03-ui.md` (detailed)
Write the contract section per UI screen (keep the template's stable `UI-00x` IDs + requirement trace), and ALSO include:
- **Routes / screens / states** — each screen, its mode (create/edit/read-only/list), and its loading / error / empty / disabled states.
- **Forms** — per field: label → bound DTO field → component (shadcn/Kendo) → validation + where the error shows. Note RHF + `zodResolver` + a schema factory `getXxxFormSchema(t?)`; `Sheet` for create/edit, `AlertDialog` for destructive.
- **testid / selector strategy** — stable `data-testid`s so the FE-dev + agent-browser E2E can target elements.
- **FE STATE PLAN** — which **adapter** + generated **hooks** (`adapter.useXxx({successMessage, invalidateQueries, onSuccess})`), which **`useMasterData([ENTITY])`** entities, and the **mutation invalidation pair** (`invalidateQueries: [...]` **and** `invalidateMasterDataEntity('Entity')`) for every mutation. Resolve reference data by `Id`/BE-flag — never name/code compare (FE-V3). Permissions via `Functions.FunctionNames.*`.
- **The reuse map** (step 4).

These must respect `engine/rules/frontend.md` (RQ-via-adapter, `useMasterData`, id-only, shadcn, RHF+zod, `EnhancedDataGrid`, `StatusBadge`/`STATUS_REGISTRY`, permissions, i18n via `useIntl`/`useTranslation`). Generated DTO/client/`Constants.ts` are read-only.

## Mockup-vs-business flag (NEVER a silent assumption)
A mockup that **implies a business rule absent from the DOCX** or **contradicts** it (a `*` required marker, a computed/derived badge, a hidden subtotal, an implied state transition) → an **Open Question** in `specs/<module>/05-open-questions.md` (tag `BLOCKING` if it gates the UI contract), resolved via the DOCX/BA, never auto-resolved. This mirrors the `03-ui.md` template's source-precedence note: **mockups are UI evidence, not business authority.**

## How `03-ui.md` feeds the FE dev workflow
The reuse map + FE state plan are exactly what `mh-implement` (FE-mode) / `incremental-impl` need to implement without re-discovering: REUSE rows → import-and-use; EXTEND rows → the precise delta; CREATE-NEW rows → the only net-new components. Chaining is via the envelope `next_recommended_workflow: mh-implement` (FE-dev mode). (If the module also needs schema/API design, `/technical-design` consumes the same `03-ui.md` as its UI-contract input.)

## Close-out (envelope + state + learning)
- `rounds/<id>/ui-spec.envelope.json` (shared schema: `artifact_type: ui-spec`, `module: <module>`, `next_recommended_workflow: mh-implement`, `content_sha256` of `03-ui.md`) → `python engine/workflows/_shared/validate-envelope.py rounds/<id>/ui-spec.envelope.json --payload specs/<module>/03-ui.md`.
- `python engine/workflows/_shared/module-state.py <module> --set DESIGN --by ui-spec` (the UI contract is part of design).
- **Learning loop:** a recurring **reuse-miss** (CodeGraph/catalogs keep failing to surface an existing component, so it gets re-created) → `second-brain/` note for `/promote` — promote to the cheapest layer (catalog refresh → `engine/rules/frontend.md` reuse note → checklist).

## Boundaries
- **Owner-invoked**; never self-invoke.
- **Writes only `specs/`** (`03-ui.md`, `05-open-questions.md`, the round envelope, the state marker). **READ-ONLY on source code.**
- **Never authors schema or business rules** — the owner owns `02-requirements`/`07-schema`; a mockup-implied rule becomes an Open Question, not an assumption.
- Never edits `myhospital-fe/` · `myhospital-be/` · `worktrees/` · `main-brain/`; never broad-scans FE; honor the guard (no git history mutation, no recursive delete, no dependency installs, no hand-editing generated files).

## Status
Scaffold + wiring + contract. The **multimodal mockup-read + the CodeGraph/catalog reuse-audit are REAL**; the **reuse-map quality is UNPROVEN** → first real run = owner gate. **Input-dependency: the owner's `specs/<module>/02-requirements` + the mockup PNGs must be provided first.**
