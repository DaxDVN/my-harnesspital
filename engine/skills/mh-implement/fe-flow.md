# mh-implement — FE flow (F0–F8)

> The **FE-specialized** middle of `/mh-implement`. When the target is `myhospital-fe`, the SKILL routes
> here instead of the generic B1–B4. The **B0 worktree spine** and **B5 self-review-diff** are shared with
> the BE path — they are *not* re-done here (F0 == B0, F8 == B5 specialized). Source of this flow:
> `docs/harness/plans/fe-implementation-workflow-research-2026-06-16.md` (the FE-week gap analysis).
>
> **Why FE needs its own gated flow:** BE has a deterministic path (Confirmed spec → `/mh-scaffold` → `mh_scan`
> + `dotnet build`). FE does not — a feature is re-discovered across ~8 independent concern-axes (contract,
> reuse, skeleton, master-data, invalidation pair, form schema, permission/i18n/status/testid, validation),
> several of which **fail silently** (no compile error). These 9 gated phases make each axis correct at
> write-time and prove it with a per-phase done-check, so `mh-review` converges in ≤3 rounds.

## INPUT — the UI spec drives F2 onward
The primary input is **`specs/<module>/03-ui.md`** (the **UI.md** produced by the `/ui-spec` workflow; it is
also written by `/technical-design`). Its **REUSE MAP** (which existing components/hooks/adapters to reuse,
which exemplar parts to mirror, the genuinely-new pieces) **drives F2–F6 — do not re-derive reuse**; consume
the UI.md reuse map. If no `03-ui.md` exists (greenfield, no spec) state that and fall back to live discovery
in F2. Other business source of truth: `specs/<module>/{02-requirements,06-decision-log,08-api}.md`.

## EXECUTION MODEL — per-task = the incremental-impl mechanics
Each phase's edits run as an **`incremental-impl` task**: bounded by the task's **file-allowlist**, validated
per task, and **`PLAN_MISMATCH` → STOP** (file missing · code differs from `01-source-audit` · allowlist
insufficient · needs an API not in `08-api.md` · a missing design decision surfaces) — write the mismatch +
envelope, set `module-state BLOCKED_PLAN`, route back to `/task-slicing`. **Do NOT improvise** outside the
allowlist. `incremental-impl` is the internal executor invoked *by* this flow; you do not enter it separately.
**Boundary enforcement (deterministic — after each task's edits):**
`git -C worktrees/<slug>/fe diff --name-only <base> | python engine/workflows/_shared/allowlist-check.py --stdin --allow '<task allowlist globs>' --forbid '**/generated-*,**/app-routing-setup*'` — **exit 2 = the worker edited OUTSIDE its allowlist → STOP, revert the out-of-scope edits, `PLAN_MISMATCH`** (never accept overreach; it is context-rot + scope-creep). Convention canon for every phase: `engine/rules/frontend.md`.

---

## F0 — Scope & worktree  *(== B0; shared spine)*
- **Input:** the feature ask + (if present) `specs/<module>/{02-requirements,03-ui,06-decision-log,08-api}.md`.
- **Do:** Session Start Protocol (`python scripts/worktree.py list`, confirm slug/slot); work in
  `worktrees/<slug>/fe` — **never** `myhospital-fe/` (guard BLOCK). Read Confirmed requirements as the
  business source of truth; FE+BE feature → BE contract first, regen FE (F1), then FE usage.
- **FE pitfall prevented:** editing the main repo; inventing business rules.
- **Done-check:** worktree confirmed; `03-ui.md` + requirements read, or "greenfield, no spec" stated.

## F1 — Contract intake & DTO/client sync gate
- **Input:** the DTOs / hooks / permission-constants this feature needs (from `08-api.md`, or the BE worktree if FE+BE).
- **Fixing an FE bug (not greenfield build):** BE must be **running** + run **`npm run dtos:update`** FIRST, then re-check the bug against fresh DTOs before touching FE code (`engine/rules/frontend.md` → "FE bug-fix prerequisite"). A schema change needed mid-fix → running migrations on the slot DB is allowed if data is restorable (**`make migrate-data`**, `engine/rules/backend.md` → "Running migrations"); never the real DB.
- **Do:** (a) FE+BE → land the BE contract first, then `npm run dtos:update && npm run client:generate` **in the
  worktree**. (b) FE-only → assert the generated layer (`generated-dtos.ts` / `generated-api-client.ts` /
  `Constants.ts`) already carries every referenced symbol, and that `@/lib/dtos/generated-dtos` resolves
  (**never** the dead `@/lib/dtos/dtos`, FE-V1). A needed DTO/hook/permission **missing → STOP, report a
  BE/API contract blocker** (`frontend.md` "Generated Artifact Rules") — do NOT hand-write or work around it.
  - **Contract-sync = the `tsc`-on-baseline done-check below** (no separate tool, no main-fe edit): a stale
    client surfaces as type errors. Regen, when needed, happens **in the worktree** (`dtos:update` /
    `client:generate` — guard-allowed there); never regen against `myhospital-fe/` directly.
- **FE pitfall prevented:** the mid-feature `tsc` avalanche from a stale client; hand-written DTO workarounds;
  the build-breaking dead `@/lib/dtos/dtos` import.
- **Done-check:** `npx tsc --noEmit` is **GREEN on the untouched baseline** *before* writing feature code
  (drift surfaces now, not later); every referenced DTO/hook/constant grep-confirmed present.

## F2 — Reuse discovery  *(consume the UI.md REUSE MAP)*
- **Input:** the UI surfaces + data the feature needs **+ the REUSE MAP from `03-ui.md`**.
- **Do:** take the reuse decisions from the UI.md reuse map as given (do not re-derive them). Confirm each
  named reuse target still exists (bounded `rg`/CodeGraph for live callers). Pick the **warehouse exemplar's
  GOOD parts only** (adapter 9-line singleton, routing, mutation-hook config, `EnhancedDataGrid` table,
  RHF+`zodResolver`) — **never** copy `inventory-list-page.tsx` (~636 ln) or `inventory-form-sheet.tsx`
  (~1321 ln) wholesale, and beware: ~124 module files exceed 600 lines, so "copy a similar page" usually
  means copying a monolith.
  - The reuse source is the **UI.md reuse map** (`03-ui.md`, preferred) + **CodeGraph** / bounded `rg`. *(The
    legacy `*.generated.md` catalogs + `npm run components:index` were **removed** — they never existed in fe.)*
  - If `03-ui.md` is absent or incomplete for the changed visible surface, create the same reuse matrix locally
    before coding: `UI element/surface/action → semantic role → existing component/pattern (file:line) →
    decision REUSE|EXTEND|CREATE-NEW → why`. This matrix is required for every new/changed visible form, list,
    filter, dialog/sheet, action cluster, and control group. Do not implement a hand-rolled component/control
    until the matrix shows no suitable existing pattern.
- **FE pitfall prevented:** rebuilding an existing component/hook; copying the monolith / inline-schema
  anti-patterns.
- **Done-check:** the reuse matrix exists and every CREATE-NEW row has a search-backed reason; plus a 5–10-line
  summary (= `preflight.md` output, now driven by the UI.md map): components/hooks/adapters reused, exemplar GOOD
  parts mirrored, the 1–2 genuinely new pieces.

## F3 — Scaffold the canonical skeleton  *(calls `/mh-scaffold`)*
- **Input:** the reuse note (F2) + module/feature name.
- **Do:** for any brand-new module/page/form/adapter emit the canonical shape via **`/mh-scaffold`** FE
  templates (FE-1..FE-4): module skeleton (split `pages/<f>/<f>-list-page.tsx` wrapper +
  `pages/<f>/components/<f>-list-content.tsx`), list page (FE-2), form sheet (FE-3, **schema in
  `forms/<f>-schema.ts` factory — NOT inline**), adapter (FE-4, 9-line singleton). Generate the
  `*-routing.tsx` boilerplate (lazy + Suspense(ContentLoader) + LayoutSelector + 404; mirror
  `bed-management-routing.tsx`). **`app-routing-setup.tsx` is a protected root → prepare the 2-line diff
  (import + `<Route>`) and flag it for approval; do NOT silently edit it** (`frontend.md` "File Ownership").
  Do not use the broken `npm run create:page`/`create:module`.
- **FE pitfall prevented:** 110 lines of hand-written routing ceremony; copying the 1321-line form sheet;
  inline schema; a fat adapter; editing a guarded root unannounced.
- **Done-check:** files exist in the canonical split layout; `forms/<f>-schema.ts` exists as a factory;
  routing file present; the root-wiring diff is prepared + flagged (not applied without approval).

## F4 — Data wiring (adapter hooks + useMasterData + the invalidation pair)
- **Input:** the scaffolded adapter + the entities/lists the feature reads/writes.
- **Do:** server state via `adapter.useGetXxx()` / `adapter.useCreateXxx({ successMessage,
  invalidateQueries:[['GetXxxRequests'],['GetMasterDataRequests']], onSuccess })`. Reference/dropdown data via
  **`useMasterData([Entity])`** — never an ad-hoc query. Every list/master mutation invalidates **BOTH**
  `invalidateQueries` **AND** `invalidateMasterDataEntity('Entity')`. Reference by **Id**
  (`find(x => String(x.Id) === value)`); business rules from BE flags (`IsDefault`/`Requires*`/`*Option`) /
  `Constants.ts` — **never** a name/code literal (no `=== 'kinh'`).
- **FE pitfall prevented:** raw `fetch`/`axios`/`serviceStackClient` in UI (FE-V2, BLOCK); ad-hoc dropdown
  query (BLOCK); the **missing invalidation half → stale UI with no error** (silent); name-compare (FE-V3,
  silent on DB rename); client-side N+1.
- **Done-check:** `python scripts/mh_scan --root worktrees/<slug>/fe --scope <changed> --format summary` →
  0 FE-V2/FE-V3; **grep the new mutations to confirm BOTH invalidation calls are present** (no compile signal
  exists for this — make it an explicit check).

## F5 — Forms (RHF + zodResolver + schema factory)
- **Input:** the form fields + validation rules + i18n needs.
- **Do:** `forms/<f>-schema.ts`: `export const get<F>FormSchema = (t?) => z.object({...})` + inferred
  `<F>FormValues`. `useForm<<F>FormValues>({ resolver: zodResolver(get<F>FormSchema(t)) })` — **resolver
  REQUIRED**. Create/edit in `<Sheet>`; destructive confirm in `<AlertDialog>`; reset on open/identity
  change; unsaved-change guard. For each visible field/control/action, use the component/pattern selected in
  the F2 reuse matrix; if coding reveals the selected component cannot fit, update the matrix with evidence
  before creating/wrapping a new one.
- **FE pitfall prevented:** `useForm` without resolver (FE-V4 → **validation silently absent**; ~half of the
  repo's call-sites have no resolver); inline schema (un-i18n-able, copied from warehouse); missing
  dirty-guard.
- **Done-check:** **grep the form file → `zodResolver` present and wired to the `forms/` factory** (FE-V4 has
  no lint rule — make this an explicit grep check); schema lives in `forms/`, not the page.

## F6 — Cross-cutting: permission · i18n · status · testid
- **Input:** the rendered surfaces + actions.
- **Do:** permission via `useUserPermissions().can(Functions.FunctionNames.X, Functions.Actions.CanUpdate)` —
  names from `Constants.ts`, **no fallback** (missing constant → blocker); state-machine buttons gate on
  **BOTH status AND permission**. i18n: `useIntl` for chrome/buttons/errors, `useTranslation` for
  tenant-renamable labels — **no new hardcoded VN text**; `handleApiError(error, intl, fallback)` for API
  errors. Status: `StatusBadge` + register new statuses in `STATUS_REGISTRY`; values from `Statuses.*` — no
  hardcoded status string, no raw `<Badge>`. **testid: add `data-testid` to every interactive element the E2E
  flow (F8) will drive.** For Sheet/Dialog/Drawer flows, make the overlay content targetable: accessible
  title/labels are required, icon-only controls need `aria-label`, and the content wrapper needs a stable
  anchor (`data-slot` in shared primitives, or a feature-specific `data-testid` in feature code).
- **FE pitfall prevented:** hardcoded permission/`'CanUpdate'`/fallback; hardcoded VN text; hardcoded status /
  raw `<Badge>`; an ungated state-machine button; **missing testids/overlay anchors that make E2E slow/fragile
  or make agent-browser evidence look falsely empty** (~97% of files have none today).
- **Done-check:** grep → no new `=== '<status>'`, no hardcoded `'CanUpdate'`, permission names resolve in
  `Constants.ts`; new E2E-driven interactive elements carry `data-testid`; overlay flows can be scoped by
  `[role="dialog"]`/`[role="alertdialog"]` plus a stable wrapper anchor; (manual) i18n keys added for new text.

## F7 — Deterministic validation floor  *(one button, in the worktree)*
- **Input:** the changed file set (`git -C worktrees/<slug>/fe diff --name-only <base>`).
- **Do, in the worktree** (dev/build/test/regen are guard-ALLOWED here):
  1. `npx tsc --noEmit` — catches FE-V1 dead import + contract drift; **BLOCK** on error.
  2. `npx eslint <changed> --no-fix` (scoped; **never `npm run lint`**).
  3. `python scripts/mh_scan --root worktrees/<slug>/fe --scope <changed> --format summary` (FE-V1 HIGH, FE-V2/V3).
  4. `fd -t f '\.(bak|orig|v2\.bak)$' <changed dir>` empty (FE-V12 — no committed backups).
  5. a generated file would change → `npm run dtos:update && npm run client:generate` **in the worktree**, re-run (1).
  - ⚠ **owner-decision (touches main fe — bypass/worktree/owner):** the **pending ESLint pack**
    (`docs/harness/pending/fe-main-repo-diffs-2026-06-16.md`, the research's leverage fix #3) is what makes
    step 2's `eslint` catch axios/banned-libs/`@/lib/dtos/dtos`/raw-`fetch`. It edits `myhospital-fe`'s
    `eslint.config.js` → owner's call; **until applied, step 2 is largely a no-op** and FE-V1/V2/V4 lean on
    `tsc` (1) + `mh_scan` (3) + the F4–F6 grep done-checks. Do not apply it from this flow.
- **FE pitfall prevented:** every deterministic FE violation reaching review (shift-left); committed backups.
- **Done-check:** 0 type errors · 0 ESLint errors on changed files · 0 FE-V1/HIGH from `mh_scan` (each WARN
  fixed or justified with a comment per `definition-of-done.md`) · no `.bak`.

## F8 — Self-review-diff + E2E  *(== B5; shared spine)*
- **Input:** the diff.
- **Do:** run `mh-review` on **only the diff** (explicit file set = changed files) — reviewer D3/D7/D10 already
  carry the FE bug-classes; fix what it flags **now**, do not push regressions to a later round. For visible
  UI, self-review must compare the final diff back to the F2 reuse matrix: every visible element/surface/action
  either uses the selected exemplar/pattern or has an updated, evidence-backed CREATE-NEW rationale. Then run the
  dev server + smoke login (`bvtest3` / `lynkhanh9822@gmail.com` / `12.[s7HXZQ;NfAoF`). For a real user flow, run the FE E2E path
  (`engine/workflows/progressive-test/` → agent-browser) — the testids added in F6 make this fast.
- **FE pitfall prevented:** pushing regressions/convention drift to a later review round (the thing that makes
  review take 3+ rounds); shipping a flow that does not actually work in the browser.
- **Done-check:** self-review findings closed; UI verified in browser; E2E green (when the feature is a flow).
  Then summarize: files changed, the concern-axes honored (contract · master-data · invalidation pair · form
  schema · permission · i18n · status · testid), validation commands run + results, residual risks.

---

## What this flow ORCHESTRATES (does NOT duplicate)
- **`/mh-implement` B0/B5** — the worktree spine + self-review-diff (F0/F8 are these, specialized).
- **`/mh-scaffold`** (FE-1..FE-4) — F3 *calls* it for canonical skeletons; this flow never re-defines templates.
- **`incremental-impl`** mechanics — the per-task allowlist + validation + `PLAN_MISMATCH`→STOP envelope.
- **`mh-implementer`** subagent — bounded disjoint-file workers inside the worktree for F3–F6.
- **`mh_scan`** + `scripts/sgconfig/rules/` — the F4/F7 deterministic floor (FE-V1/V2/V3).
- **`engine/workflows/deep-review`** D3/D7/D10 — the F8 self-review dimensions (this flow *prevents* what they *detect*).
- **`engine/workflows/progressive-test`** + agent-browser — the F8 E2E step.

## ⚠ Owner-decision — ONE residual that touches `myhospital-fe`
Resolved in-harness: **contract-sync** is just the F1 `tsc`-on-baseline check (worktree regen, no main-fe edit);
the phantom **`components:index`** + `*.generated.md` catalogs were **removed** (reuse = UI.md map + CodeGraph).
The ONE remaining fe-side enhancement (NOT implemented — needs owner bypass / their own edit):
- **Apply the pending ESLint pack** (`docs/harness/pending/fe-main-repo-diffs-2026-06-16.md`) — edits
  `myhospital-fe/eslint.config.js` so F7 step 2 catches axios/banned-libs/`@/lib/dtos/dtos`/raw-`fetch`. **Until
  applied, the deterministic floor still holds** via `tsc` (F7.1) + `mh_scan` ast-grep (F7.3) + the F4–F6 grep
  done-checks — the flow self-operates without it.

## Safety
Worktree-only edits; honor the guard (no git-history mutation, no recursive delete, no new deps, no editing
generated files). Missing DTO/constant/permission → **stop, report a BE/API contract blocker** (F1). Ambiguous
business rule → route to `specs/<module>/05-open-questions.md`, do not invent it. `PLAN_MISMATCH` → STOP +
`BLOCKED_PLAN`, route to `/task-slicing`.
