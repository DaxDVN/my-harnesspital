# MyHospital Frontend Rules, Conventions, and Review Patterns

This document is a frontend-only audit artifact for `myhospital-fe`.
It is meant to seed compact, CodeRabbit-like review prompts. It is not a replacement
for the live harness. The package-level executor source in this checkout is
`myhospital-fe/CLAUDE.md`.

## Scope

- Analyze and review frontend code only under `myhospital-fe/`.
- Do not inspect or infer backend implementation except through the root harness and
  frontend generated contract files.
- Do not modify application code, generated files, package files, configs, or catalogs
  when performing docs-only extraction.
- Generated FE artifacts are read-only:
  - `src/lib/dtos/generated-dtos.ts`
  - `src/lib/dtos/Constants.ts`
  - `src/lib/server/generated-api-client.ts`

## Technology Stack And Project Shape

Verified by `AGENTS.md` and `package.json`.

- React 19, TypeScript 5.9, Vite 7.2, ESM package (`"type": "module"`), app version `9.3.4`.
- Server state: TanStack Query v5 plus persisted query client. No Redux/Zustand/Jotai/MobX.
- Data layer: ServiceStack (`@servicestack/client`) through `src/lib/server/generated-api-client.ts`
  and module adapters extending `GeneratedApiClient`.
- Forms: `react-hook-form`, `@hookform/resolvers`, `zod`.
- Routing: `react-router` / `react-router-dom` v7.
- UI: shadcn-style `src/components/ui/*`, Radix, Kendo React grids/inputs, Tailwind 4,
  lucide-react for new icons.
- i18n: `react-intl` plus the project `useTranslation` layer.

Canonical module shape, from `src/modules/warehouse/`:

```text
src/modules/<module>/
  adapters/
  forms/
  pages/<feature>/
  components/
  context/
  lib/
  <module>-routing.tsx
```

## Source-Of-Truth Hierarchy

Use this order during reviews:

1. Current user/task instruction, but only within hard harness boundaries.
2. Architect task plan in `roast/docs/tasks/`, when present.
3. Specs under `roast/specs/<module>/`, especially `api.md`, `design.md`, `requirements.md`.
4. `myhospital-fe/CLAUDE.md`.
5. Existing source code, with warehouse as the first pattern reference.
6. Reuse discovery: **CodeGraph** (`codegraph explore/node`) + (for an FE feature with a spec) the **`/ui-spec` reuse-map** in `specs/<module>/03-ui.md`. *(The legacy `*.generated.md` catalogs + `npm run components:index` were removed — they never existed in `myhospital-fe`.)*

**Stale project docs — do NOT trust:** `myhospital-fe/ARCHITECTURE-OVERVIEW.md` and `myhospital-fe/BEST-PRACTICES-NEW-PAGE.md` predate the live app (audit V10: bearer-vs-cookie auth, Infinity-vs-`staleTime:0`, Context+reducer-vs-RQ-adapter, dead `demo`/`samples`). **This canon + live code override them** — the warning is recorded here at the harness layer instead of editing those project files. See memory `fe-live-conventions-vs-stale-docs`.

If generated DTOs/client disagree with `api.md`, stop and report the contract mismatch.
Do not compensate in FE by hand-writing DTOs, constants, hooks, or request types.
If the current task explicitly conflicts with a `BLOCK`/forbidden rule, use the stop protocol
instead of treating the instruction as an override.

## Severity Model

Use the root harness model.

- `BLOCK`: do not implement. Report the violated rule, exact file/symbol, why it matters,
  and a safe alternative.
- `WARN`: continue only with the least risky option and record the rationale in the final response.
- `INFO`: normal project convention. Follow it unless local source proves a more specific pattern.

Treat uncertainty between `BLOCK` and `WARN` as `BLOCK` until the harness or a human clarifies.

## Mandatory Rules And Forbidden Actions

### BLOCK

- Editing generated DTO, constants, or generated API client by hand.
- Adding direct UI network access (`fetch`, `axios`, manual `JsonServiceClient`, manual bearer auth)
  outside existing approved legacy paths.
- Missing either half of the mutation invalidation pair:
  `invalidateQueries` for TanStack cache and `invalidateMasterDataEntity(...)` for master-data cache.
- Querying master/reference entities ad hoc instead of `useMasterData(...)`.
- Client-side N+1 query/API calls per row/item.
- Adding global state libraries or changing provider/routing/cache roots without explicit approval.
- New tabular admin/list UI that bypasses `EnhancedDataGrid`.
- Computing authoritative financial, inventory, posted, cost, balance, or stock totals in FE.
- Permission fallback logic when generated permission constants are missing.
- Duplicating a side-effectful reusable component/hook identified by the component inventory.
- Running `npm run lint`, because it applies global ESLint fixes.

### WARN

- Creating a presentational component when a similar shared/module-local component exists.
- Keeping a reusable module-local component local because extraction is out of scope.
- Hard-coded user-facing text in areas that already use i18n.
- Custom sizing or styling where the design-system default works.
- Skipping browser/dev-server verification for visible UI changes.
- Docs or script updates that keep the harness accurate.

### INFO

- Prefer warehouse module shape when the target module lacks a local pattern.
- Prefer named exports for lazy-routed cross-module pages.
- Prefer `cn()` for conditional class names.

## Canonical Warehouse Inventory References

> ⚠️ **Warehouse is a PARTIAL exemplar** (FE audit `velvet/notes/myhospital-fe-convention-audit-2026-06-15.md` §4). COPY: routing (`lazy`+`Suspense`+`LayoutSelector`+Provider), mutation hooks `adapter.useXxx({successMessage, invalidateQueries, onSuccess})`, `useReactTable`+`EnhancedDataGrid`+`useMemo` columns, shadcn UI, RHF+`zodResolver`+dirty-guard. **DO NOT copy:** monolithic 600+-line page files (split wrapper + `components/*-content.tsx`), `useState`-only context used as a data layer (data belongs in RQ hooks / `useMasterData`), schema inlined in the page (put it in `forms/<x>-schema.ts`), `models.ts` that only re-exports DTOs, or the hardcoded `'Doing'` status string at `inventory-form-sheet.tsx:188` (use `Statuses.*`).

Treat these files as the first implementation reference, then verify broader project patterns with `rg`:

- `src/modules/warehouse/adapters/warehouse-adapter.ts`
- `src/modules/warehouse/warehouse-routing.tsx`
- `src/modules/warehouse/context/warehouse-context.tsx`
- `src/modules/warehouse/pages/inventory/inventory-list-page.tsx`
- `src/modules/warehouse/pages/inventory/inventory-form-sheet.tsx`
- `src/modules/warehouse/components/inventory-filter-modal.tsx`
- `src/modules/warehouse/components/delete-inventory-dialog.tsx`
- `src/modules/warehouse/components/inventory-selector.tsx`
- `src/modules/warehouse/hooks/use-inventory-capabilities.ts`
- `src/modules/warehouse/lib/inventory-source-resolver.ts`

Observed inventory patterns:

- List shell uses `Container` with full-height flex/overflow containment.
- List data comes through `useMasterData(...)`, then memoized maps and filtered lists.
- Vietnamese client-side search uses `fuzzyMatchVietnamese`.
- Advanced filters use `UserScreenFilter` master data, `Filter.ScreenCodes.*`, save/default/delete mutations,
  `invalidateQueries: [['GetMasterDataRequests']]`, and `invalidateMasterDataEntity('UserScreenFilter')`.
- Inventory create/update use generated hooks on `warehouseAdapter` with
  `invalidateQueries: [['GetInventoryRequests'], ['GetMasterDataRequests']]` and master-data invalidation.
- Warehouse context stores selected inventory per hospital/user in local storage and exposes
  `useWarehouse`, `useWarehouseOptional`, and dirty-guard registration.
- Inventory capability checks are pure helpers/hooks, not scattered button-specific booleans.

## Data Access And Adapter Pattern

New module adapters should be singleton classes extending `GeneratedApiClient`.

Reference:

```ts
import { GeneratedApiClient } from '@/lib/server/generated-api-client';

class WarehouseAdapter extends GeneratedApiClient {
  constructor() {
    super();
  }
}

export const warehouseAdapter = new WarehouseAdapter();
```

Verified adapter pattern exists across many modules:
`accounting`, `auth`, `bid-management`, `cashier`, `common`, `diagnostic-imaging`,
`examination`, `hospital-management`, `inpatient-reception`, `master-data-management`,
`reception`, `warehouse`, `warehouse-transaction`, `user`, etc.

Use generated hooks/methods from the adapter. `GeneratedApiClient` owns:

- `MutationHookConfig`
- `successMessage`
- `errorMessage`
- `invalidateQueries`
- `disableSuccessToast`
- `disableErrorToast`
- default `queryClient.invalidateQueries(...)` behavior in mutation `onSuccess`
- `handleApiError(...)` integration for error toasts

The ServiceStack client is cookie-authenticated (`ss-id`) with `credentials = 'include'`.
Do not set bearer tokens in FE.

## Mutation Invalidation Pair

Every successful mutation that changes list/master data must invalidate both:

1. TanStack query cache via generated hook config `invalidateQueries`.
2. Master-data cache via `invalidateMasterDataEntity('EntityName')`.

Canonical inventory examples:

- `inventory-form-sheet.tsx`: create/update inventory invalidates `GetInventoryRequests`,
  `GetMasterDataRequests`, `Inventory`, and `InventoryCategory`.
- `inventory-list-page.tsx`: filter mutations invalidate `GetMasterDataRequests` and
  `UserScreenFilter`; toggle active invalidates generated query keys and `Inventory`.
- `inventory-filter-modal.tsx`: saved filter creation invalidates `GetMasterDataRequests`
  and `UserScreenFilter`.

Reviewer guardrail: a mutation with `onSuccess` but no `invalidateQueries` and no
`invalidateMasterDataEntity` is almost always a cache bug. If a mutation intentionally does not
affect cached entities, require a comment or rationale.

## Master Data

Use `useMasterData([ENTITY_NAME], options?)` for reference data and shared tenant/hospital-scoped
entities. The hook handles:

- IndexedDB lookup and API fallback.
- Active/inactive filtering.
- tenant/hospital/share-scope filtering.
- `User` enrichment from `Profile`.
- `masterdata:entity-invalidated` events.
- singleton handling for shared entities like `UserScreenFilter`.

Reference helpers:

- `src/modules/common/hooks/use-master-data.ts`
- `src/modules/common/hooks/use-user-permissions.ts`
- `src/modules/common/hooks/use-setting.ts`
- `src/modules/common/hooks/use-default-vat.ts`

Do not add a separate API call for dropdown/reference lists if the entity is available as master data.

**No name/code string compare against master data (BLOCK — FE-V3).** Resolve defaults and business rules
by BE flag or `Id`, never by comparing a name/code literal — the DB can rename and the FE fails silently.

```ts
// BAD (FE-V3): masterData.MasterEthnicity.find(e => e.EthnicityName?.toLowerCase() === 'kinh')  // patient-admin-info-block.tsx:225
// GOOD: masterData.MasterEthnicity.find(e => e.IsDefault)                                       // flag from BE
// Reference selection by Id, not object: find(x => String(x.Id) === formValue)
```
Use the BE flags (`IsDefault`, `RequiresCitizenId`, `RequiresTransferInfo`, `HealthInsuranceOption`,
`CommercialInsuranceOption`, `IsForeign`) and generated `Constants.ts` enums. `mh_scan` flags the literal
`=== '<x>'`-inside-`.find()` shape as `FE-V3`.

## OData And Pagination

Use `buildODataParams(...)`, `buildPagination(...)`, and `ODataFilters` from
`src/lib/utils/odata-utils.ts`.

Preferred examples:

- `ODataFilters.eq('Status', status)`
- `ODataFilters.in('Status', statusList)`
- `ODataFilters.and(...)`
- `buildODataParams({ filter, top: pageSize, skip, count: true })`

Reviewer guardrails:

- Flag string-concatenated `$filter`, especially with user text.
- Flag unbounded `$top` values used to avoid pagination.
- List screens must either use master-data intentionally or page/filter through API with count.
- Query params are normalized by generated client/utils for IndexedDB cache compatibility.

Known direct `$filter` strings exist in legacy/common internals and a few screens. New code should use
the helpers unless there is a verified existing local pattern and no user input risk.

## Status Values And Status Display

Use `StatusBadge` for status display and `STATUS_REGISTRY` for status semantics.

References:

- `src/components/ui/status/status-badge.tsx`
- `src/lib/status/status-resolver.ts`
- `src/lib/status/status-tones.ts`
- `src/lib/dtos/Constants.ts` (`Statuses`)

Rules:

- Status values are PascalCase strings from generated constants where available.
- Add new statuses to `STATUS_REGISTRY`.
- `StatusBadge` may override label for domain/i18n context.
- Tone override is only for dual-domain cases where the same raw status has different page meaning.
- Do not inline `Badge` plus conditional class names for status values.

## Permissions

Use `useUserPermissions().can(functionName, action)`.

Preferred source:

- `Functions.FunctionNames.*` from `src/lib/dtos/Constants.ts`.
- Generated action constants if available; current code often uses string literals like `'CanUpdate'`
  as legacy.

Reviewer guardrails:

- State-machine action buttons must gate on both workflow status and permission.
- Missing permission constants are a contract blocker, not a reason to fallback to another permission.
- Existing fallbacks such as `can('DisposalProcess', 'CanUpdate') || canApprovalUpdate` and
  `(Functions.FunctionNames as any).TransferIssueReturnReceive ?? 'TransferIssueReturnReceive'`
  should be treated as legacy exceptions, not patterns for new work.

## i18n And User-Facing Text

Use:

- `useIntl` for fixed chrome, buttons, validation, errors, and generic UI text.
- `useTranslation` for tenant-renamable entity field labels.
- `handleApiError(error, intl, fallback)` for API errors.

Rules:

- New user-facing text should follow the local i18n pattern of the touched area.
- Hard-coded Vietnamese exists in warehouse and legacy pages; preserve when not in scope, but avoid
  expanding it in migrated areas.
- `disableErrorToast: true` is allowed only when the UI renders a specific alternate error state,
  such as a persistent conflict/lock banner.
- Do not disable generated-client error toast and then show the same generic toast manually.

## Forms

Preferred pattern:

- Create/edit surfaces use `Sheet`.
- Destructive confirmation uses `AlertDialog`.
- `react-hook-form` plus `zodResolver`.
- Schema should be a factory `getXxxFormSchema(t?)` when validation messages need i18n injection.
- Reset form on open/edit identity changes.
- Use unsaved-change guard for sheets when relevant.

Form/widget/surface reuse is a coding convention, not a visual preference:

- Before creating or wiring any visible UI element, classify its semantic role and search for the existing
  component or live-code pattern that already owns that role. Examples of semantic roles: date input,
  date-time input, master-data selector, user selector, product selector, diagnosis selector, status badge,
  list/grid shell, saved filter, tab/segmented view switcher, right-side CRUD sheet, document/workflow sheet,
  destructive confirmation, attachment uploader, read-only patient summary, typed create action.
- Reuse the existing component/pattern for that semantic role. Falling back to raw HTML, generic `Input`, or
  a hand-rolled local control is allowed only after CodeGraph/bounded search finds no suitable shared or
  module-local pattern, and the code/review notes state why. Existing legacy deviations are exceptions to
  preserve, not examples to copy.
- The required implementation artifact is a small reuse matrix for every new/changed visible surface:
  `UI element → semantic role → chosen existing component/pattern (file:line) → actual implementation`.
  A feature with no such matrix has not satisfied FE discovery, even if it builds.
- CTA-specific create flows must preserve the semantic type chosen by the CTA. Do not expose a generic type
  selector that lets the user silently switch to another document/entity kind unless a live module pattern
  explicitly supports a generic "create any type" flow.
- Choose the sheet/dialog/page surface by matching an existing surface class, not by copying classes by
  appearance. Small CRUD forms use the right-sheet pattern; large document/workflow forms can use page-mode
  sheets, but inside the normal app shell they should follow the shell-aware page pattern unless the intended
  behavior is to cover the entire viewport.

Overlay/testability contract:

- Sheet/Dialog/Drawer content must be discoverable by both accessibility and automation. Prefer accessible
  names first (`SheetTitle`, labels, `aria-label` on icon-only buttons), then add stable automation anchors
  only where the flow needs them.
- For shared overlay primitives, the content wrapper should expose a stable container selector such as
  `data-slot="sheet-content"` / `data-slot="dialog-content"`. For feature-owned overlays, add a
  feature-specific `data-testid` on the content wrapper when E2E/agent-browser will drive the flow.
- Do not diagnose "portal/overlay is invisible to agent-browser" from a single failed selector snapshot.
  Verify with `agent-browser snapshot -i -c`, then a semantic scoped snapshot such as
  `agent-browser snapshot -s '[role="dialog"], [role="alertdialog"]' -c`, then DOM attrs (`aria-hidden`,
  `inert`, visibility) and screenshot only as fallback.
- Avoid blanket `data-testid` on every field. If a field has a good accessible label, agent-browser can use
  the snapshot/ref or label. Add test ids for ambiguous icon buttons, repeated row actions, virtualized rows,
  and key flow anchors.

Inventory-specific notes:

- `inventory-form-sheet.tsx` currently keeps an inline schema and direct detail fetch for race avoidance.
  Treat this as an existing implementation exception, not a new-code pattern.
- Other current forms still use exported schema constants. The harness preference for new work is schema factories.

Allowed `as any` exceptions from harness:

- `zodResolver(schema) as any`
- dynamic RHF `register('field' as any)`
- ServiceStack envelope cast immediately after `mutateAsync`

Flag broad unsanctioned `as any` or `as Record<string, unknown>` in new code.

## Tables, Lists, Filters, And Layout

Admin/list data should use `EnhancedDataGrid` from `src/components/ui/enhanced-data-grid.tsx`.

Canonical list shell:

- `Container className="h-full flex flex-col overflow-hidden"`
- table area contained with `flex-1 min-h-0 overflow-hidden`
- `EnhancedDataGrid` with inline `toolbar={...}`
- toolbar search input and action buttons inside the grid toolbar
- `recordCount`, `isLoading`, pagination/table state from TanStack Table as needed

Do not create raw `<table>` list pages for admin data. Raw tables are acceptable only for existing
small detail/expanded/import-preview/form-builder contexts, as seen in warehouse transaction expanded rows
and import components.

For pages with many user-adjustable filters, reuse the saved filter pattern:

- `UserScreenFilter`
- `Filter.ScreenCodes.*`
- `useMasterData(['UserScreenFilter'])`
- save/default/delete mutations through adapter
- invalidate both `GetMasterDataRequests` and `UserScreenFilter`

Tabs/view modes should use `src/components/ui/tabs` or an existing segmented control, not hand-rolled
button tab bars.

## Routing

Module routing pattern:

- `lazy(...)`
- named export mapping: `.then((m) => ({ default: m.NamedExport }))`
- `<Suspense fallback={<ContentLoader />}>`
- nested under `<LayoutSelector>`
- module provider wrapper when needed, e.g. `WarehouseProvider`

References:

- `src/modules/warehouse/warehouse-routing.tsx`
- `src/modules/warehouse-transaction/transaction-routing.tsx`
- `src/modules/hospital-management/hospital-management-routing.tsx`
- `src/modules/master-data-management/master-data-management-routing.tsx`

Do not touch routing roots or provider hierarchy without explicit architect approval.

## Reuse And Discovery Rules

Before adding UI/components/hooks/adapters:

1. Use **CodeGraph** (`codegraph explore/node` from the fe repo) for live components/hooks/adapters + callers.
2. For an FE feature with a spec, consume the **`/ui-spec` reuse-map** in `specs/<module>/03-ui.md`.
3. Search source with bounded `rg`.
4. Prefer `src/components/ui/*`, `src/modules/common/*`, `src/lib/*`, then warehouse patterns.
5. Reuse/wrap/promote side-effectful module components instead of duplicating behavior.

Catalog facts from the audit:

- Component inventory indexed 1019 files, including shared/common and module-local components.
- Reuse catalog indexed 376 reuse files, including adapters, hooks, schemas, list pages, and form sheets.
- Both catalogs are generated; do not edit them by hand.

## Generated Artifact Rules

Always ignore these generated FE files during code review, static analysis, type check reviews, or linting. Do not report styling or convention violations in them.

Never hand-edit:

- `src/lib/dtos/generated-dtos.ts`
- `src/lib/dtos/Constants.ts`
- `src/lib/server/generated-api-client.ts`

If a DTO, constant, endpoint, hook, or permission is missing:

1. Stop and report a BE/API contract blocker.
2. Ask for BE contract change and regeneration.
3. Regenerate with `npm run dtos:update && npm run client:generate` only when the task scope allows it.
4. Verify the generated artifact now has the type/hook/constant.

## File Ownership And Forbidden Package Changes

Do not change without explicit approval:

- `src/App.tsx`
- `src/routing/app-routing.tsx`
- `src/routing/app-routing-setup.tsx`
- global providers/cache/context roots
- non-generated `src/lib/server/*`
- package/dependency files
- Vite/TS/ESLint configs
- generated catalogs
- BHYT, billing, cost-price, or authoritative financial surfaces

Never add these packages/patterns:

- `axios`
- `zustand`, `jotai`, `redux`, `mobx`
- `@tanstack/react-router`
- `react-icons`
- `react-modal`

## Validation Expectations

Docs-only extraction:

- Confirm the Markdown exists.
- Run focused `rg`/read checks.
- Do not run build/test/lint unless the task explicitly asks; no application code changed.

UI/code changes:

- Reuse-check via **CodeGraph** + the `/ui-spec` reuse-map before adding UI (the `components:index` script was removed — it never existed).
- Run `npx tsc --noEmit` from `myhospital-fe/` (catches the dead `@/lib/dtos/dtos` import, FE-V1).
- Run the deterministic floor: `python scripts/mh_scan --root worktrees/<slug>/fe --scope <changed> --format summary` (FE-V1/V2/V3 via ast-grep pack in `scripts/sgconfig/`).
- Run scoped ESLint only, e.g. `npx eslint src/path/to/file.tsx --fix`.
- Never run `npm run lint`.
- For visible UI changes, run dev server and verify in browser.
- Run E2E only when the task involves E2E behavior.

DTO/client regeneration:

- `npm run dtos:update`
- `npm run client:generate`
- Then validate both generated presence and impacted FE compile/type behavior.

FE bug-fix prerequisite — BE up + fresh DTOs FIRST (BLOCK):

- **Before fixing any FE bug, the matching BE must be running and you MUST run `npm run dtos:update` first** (then `npm run client:generate` if the client changed). Many FE bugs are stale-contract symptoms (DTO/enum/field drift after a BE change) — fixing FE against stale generated artifacts hides the real cause or "fixes" the wrong layer.
- Order: start BE for the worktree slot → `npm run dtos:update` (+ `client:generate`) → re-check whether the bug still reproduces against fresh DTOs → only then fix FE. If the symptom disappears after regen, the bug was stale generated artifacts, not FE code.
- Applies to the fix-flow (`/mh-fix`, `/bug-fix`, `bugfix-from-report`) and FE work in `/mh-implement`. BE need not be edited if the contract is already correct — but it must be **running** and DTOs **freshly regenerated** before the FE fix is judged.

## Common Automated Review Checks

Use these as reviewer guardrails:

- Does every mutation that changes master/list data include both `invalidateQueries` and
  `invalidateMasterDataEntity`?
- Is every new network call routed through a module adapter/generated hook?
- Is any `fetch`, `axios`, manual `JsonServiceClient`, bearer token, or direct `Authorization` header introduced?
- Are generated DTOs/constants/client untouched?
- Are missing DTOs/hooks/permissions treated as blockers instead of local workarounds?
- Are dropdown/reference lists using `useMasterData` instead of ad hoc query calls?
- Are OData filters built with `ODataFilters`/`buildODataParams`, not string concat?
- Does list/admin data use `EnhancedDataGrid` with correct loading/count/toolbar behavior?
- Are raw tables limited to detail/preview contexts rather than primary list pages?
- Are status values rendered with `StatusBadge` and registered in `STATUS_REGISTRY`?
- Are state-machine buttons gated by both status and permission?
- Are permission names from `Functions.FunctionNames` where available?
- Are hard-coded permission fallbacks avoided?
- Is `useTranslation` used for tenant-renamable entity labels and `useIntl`/messages for fixed chrome?
- Are API errors handled by generated-client defaults or `handleApiError` when custom UI is needed?
- Is `disableErrorToast` paired with a concrete alternate error state?
- Are forms using RHF + zod, `Sheet`, `AlertDialog`, and unsaved guards when needed?
- Do Sheet/Dialog/Drawer flows have accessible labels and stable overlay anchors (`data-slot` or scoped
  `data-testid`) so agent-browser evidence can target the active dialog?
- Are new forms using schema factories when validation messages need i18n?
- Is there any client-side N+1 query/API call per row?
- Are authoritative financial/inventory/posted totals coming from BE rather than FE calculations?
- Did the change read component/reuse catalogs and search with `rg` before adding new reusable code?
- Are existing legacy exceptions preserved without being expanded?

## Known Legacy Exceptions And How To Treat Them

Existing deviations are lead-approved unless the current task changes that path. Preserve behavior,
but do not copy the deviation into new code.

- Direct fetch-like paths:
  - result viewers fetch external content (`src/components/result-viewers/*`).
  - query provider fetches metadata (`src/providers/query-provider.tsx`).
  - retail adapters/log paths use raw fetch.
  - common upload uses `apiForm`.
  - inventory form uses `serviceStackClient.get(new GetInventoryDetailRequest(...))` for detail refresh.
- `use client` directives exist in Vite code. Do not add new ones.
- Raw `<table>` exists in detail/expanded/import-preview/form-builder contexts. Do not use raw tables
  for new admin list pages.
- Some current permissions use string actions or fallbacks. New code should use generated constants
  where available and block if a required constant is missing.
- Some forms keep inline zod schemas or exported schema constants. New work should prefer schema factories.
- Some warehouse/transaction helpers compute display/warning values from cached inventory data. New
  authoritative stock/cost/posted/balance logic requires human/BE confirmation.

## Open Risks And Human-Confirmation Areas

- Financial, BHYT, inventory posting, cost-price, and balance logic are high risk. Confirm with human/BE
  before adding or changing any authoritative calculation.
- Permission constants may lag BE. Missing constants are blockers.
- Some warehouse transaction permission fallbacks are known legacy. Reviewers should not normalize by
  adding more fallbacks.
- Inventory form's direct detail fetch solves a race with master-data cache. Replacing it requires
  behavior verification, not a mechanical refactor.
- Generated catalogs may be stale. If a UI/code task depends on reuse decisions, run the catalog scripts
  before implementation.

## Useful Source References

Root/workspace:

- `AGENTS.md`
- `CLAUDE.md`

Frontend harness:

- `myhospital-fe/CLAUDE.md`

Discovery:

- **CodeGraph** per-repo index (`codegraph explore/node`) — the FE reuse/dependency engine
- the `/ui-spec` reuse-map in `specs/<module>/03-ui.md` (for an FE feature with a spec)

Core source:

- `myhospital-fe/package.json`
- `myhospital-fe/src/lib/server/generated-api-client.ts`
- `myhospital-fe/src/lib/server/servicestack-client.ts`
- `myhospital-fe/src/lib/server/error-handler.ts`
- `myhospital-fe/src/lib/utils/odata-utils.ts`
- `myhospital-fe/src/lib/status/status-resolver.ts`
- `myhospital-fe/src/components/ui/status/status-badge.tsx`
- `myhospital-fe/src/modules/common/hooks/use-master-data.ts`
- `myhospital-fe/src/modules/common/hooks/use-user-permissions.ts`
- `myhospital-fe/src/modules/common/adapters/common-adapter.ts`

Warehouse canonical:

- `myhospital-fe/src/modules/warehouse/adapters/warehouse-adapter.ts`
- `myhospital-fe/src/modules/warehouse/warehouse-routing.tsx`
- `myhospital-fe/src/modules/warehouse/context/warehouse-context.tsx`
- `myhospital-fe/src/modules/warehouse/pages/inventory/inventory-list-page.tsx`
- `myhospital-fe/src/modules/warehouse/pages/inventory/inventory-form-sheet.tsx`
- `myhospital-fe/src/modules/warehouse/components/inventory-filter-modal.tsx`
- `myhospital-fe/src/modules/warehouse/components/inventory-selector.tsx`
- `myhospital-fe/src/modules/warehouse/hooks/use-inventory-capabilities.ts`
- `myhospital-fe/src/modules/warehouse/lib/inventory-source-resolver.ts`
