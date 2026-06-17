# mh-implement — Pre-flight discovery (B1)

Goal: never author what already exists, and copy the *right* pattern. Reuse is the cheapest correctness. Order:

## 1. CodeGraph + the /ui-spec reuse-map first (FE)
- **CodeGraph** — `cd myhospital-fe && codegraph explore "<area>"` / `codegraph node <symbol>` for live components/hooks/adapters + their callers. The real reuse/dependency engine; treat returned source as already read.
- For an FE feature with a spec: the **`/ui-spec` reuse-map** in `specs/<module>/03-ui.md` already classifies reuse/extend/create per UI element — consume it (don't re-derive).
- *(The legacy `*.generated.md` reuse catalogs + `npm run components:index` were **removed** — they never existed in `myhospital-fe`.)*

## 2. Code graph / bounded search
- If `.codegraph/` exists in the repo: `codegraph explore "<area>"` / `codegraph node <symbol>` to see live callers/usage. Treat CodeGraph-returned source as already read.
- Else bounded `rg -l` / `fd` for the exact symbol/area (never broad-dump FE). `engine/rules/source-discovery.md` is the full policy.

## 3. Exemplar selection — warehouse, GOOD parts only
Canonical refs (from `frontend.md`): `src/modules/warehouse/{adapters/warehouse-adapter.ts, warehouse-routing.tsx, pages/inventory/inventory-list-page.tsx, pages/inventory/inventory-form-sheet.tsx, components/*}`.

Audit `velvet/notes/myhospital-fe-convention-audit-2026-06-15.md §4` — warehouse is a **PARTIAL exemplar**:

| ✅ Copy | ❌ Do NOT copy |
|---|---|
| Routing: `lazy`+`Suspense(ContentLoader)`+`LayoutSelector`+Provider | Monolithic page (`inventory-list-page.tsx` ≈ 637 lines) — split wrapper + `components/*-content.tsx` |
| Mutation: `adapter.useXxx({successMessage, invalidateQueries:[[...]], onSuccess})` | `useState`-only context as data layer — data lives in RQ hooks / `useMasterData`, context only for cross-component coordination |
| Read: `useMasterData([Entity])` + `invalidateMasterDataEntity` | Schema inlined in page (`inventory-form-sheet.tsx:56`) — put schema in `forms/<x>-schema.ts` factory |
| Table: `useReactTable`+`EnhancedDataGrid`+`useMemo` cols | `models.ts` that only re-exports DTOs (add real `XxxModel` only if you need FE-extension fields) |
| Forms: RHF+`zodResolver`+dirty-guard | Hardcoded status string `'Doing'` (`inventory-form-sheet.tsx:188`) — use `Statuses.*` from `Constants.ts` |

## 4. Reuse precedence
`src/components/ui/*` → `src/modules/common/*` → `src/lib/*` → warehouse pattern. Wrap/promote a side-effectful shared component instead of duplicating it. If a needed DTO/hook/permission constant is missing → BE/API contract blocker (stop, do not hand-write).

## Output of B1
A 5-10 line note: which existing components/hooks/adapters you will reuse, which exemplar files you will mirror, and the one or two genuinely new pieces. This feeds the B2 convention contract.
