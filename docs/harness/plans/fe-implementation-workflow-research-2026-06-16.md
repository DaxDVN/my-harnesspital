# FE Implementation Workflow — research + proposal (why FE takes a week, and how to cut it)

> **Date:** 2026-06-16 · **Author:** Claude (Opus, max-effort research) · **Type:** research + harness proposal (read-only investigation; this doc is the only artifact written)
> **Scope:** `myhospital-fe` (React 19 + TanStack Query v5 + ServiceStack generated client/DTOs + IndexedDB master-data cache + shadcn + RHF/zod + `EnhancedDataGrid`).
> **Method:** CodeGraph from inside `myhospital-fe/` + bounded `rg`/`fd`/`wc` + targeted Read. Every claim is `path:line` or a live count. Items I could not verify are flagged.
> **Builds on (does not duplicate):** `engine/skills/mh-implement/{SKILL,preflight,definition-of-done}.md`, `engine/skills/mh-scaffold/SKILL.md`, `engine/agents/mh-implementer.md`, `engine/rules/frontend.md`, `engine/workflows/deep-review/checklist.md` (D3/D7/D10), `engine/workflows/progressive-test/`, `scripts/mh_scan/`, `scripts/sgconfig/rules/`, memory `fe-live-conventions-vs-stale-docs`, plan `docs/harness/plans/agentic-harness-dev-fix-plan-2026-06-16.md`, pending diffs `docs/harness/pending/fe-main-repo-diffs-2026-06-16.md`.

---

## 0. TL;DR

BE is fast for this team because BE has a **deterministic path**: a Confirmed spec → `/mh-scaffold` emits the exact canonical shape → `mh_scan` (13 BE scanners) + `dotnet build` prove it. FE has **no equivalent deterministic path**: `/mh-implement` is a generic FE+BE orchestrator whose FE-specific pre-flight step **literally cannot run** (it depends on `npm run components:index`, a script that does not exist, producing catalog files that do not exist), whose deterministic floor **is half-disabled** (the ESLint pack that would catch FE-V1/V2/V4 in worktrees was never applied — `docs/harness/pending/fe-main-repo-diffs-2026-06-16.md`), and whose exemplar (warehouse) is a **partial** one where the two files you are told to copy are a 636-line monolith and a **1321-line** form sheet — and warehouse is *mild*: the repo has **124 module `.tsx` files over 600 lines** (largest 2,783), so "copy a similar page" means copying a monolith. The result: every FE feature is re-discovered from scratch across ~8 independent concern-axes (contract, master-data, cache-invalidation pair, form schema, permission, i18n, status, testid, routing-root, reuse), each with its own silent-failure trap — and several fail silently (e.g. **~49% of the 327 `useForm` call-sites have no `zodResolver`**, so validation is silently absent). The only thing that reliably catches mistakes is `tsc --noEmit` against a **77,496-line generated layer** plus a manual review.

The fix is **not** a new framework — it is to make the FE path as deterministic as the BE path: an **FE-mode of `/mh-implement`** (not a separate skill) with FE-specific gates, fed by a **working** reuse catalog and a **working** deterministic floor, that walks the 8 concern-axes in dependency order with a per-axis check that proves each is done. Recommendation in §5: **FE-mode of `mh-implement`**, plus 3 small new deterministic pieces (a contract-sync gate, an FE phase checklist, and fixing/replacing `components:index`).

---

## 1. GAP ANALYSIS — concrete, evidence-backed reasons FE takes a week

### 1.1 The generated layer is enormous and is the single load-bearing correctness gate

- `src/lib/server/generated-api-client.ts` = **51,813 lines**; `src/lib/dtos/generated-dtos.ts` = **20,940 lines**; `src/lib/dtos/Constants.ts` = **4,743 lines** (`wc -l`). Total ≈ **77,496 generated lines**.
- The contract flows BE → FE via `npm run dtos:update` (pull DTOs) + `npm run client:generate` (regen hooks) — both real scripts (`myhospital-fe/package.json`), both forbidden to hand-edit (`myhospital-fe/CLAUDE.md:3-26`, `engine/rules/frontend.md:395-408`).
- **Why it eats time:** any BE contract change that is not re-pulled leaves FE referencing renamed/removed fields. The only thing that catches it is `npx tsc --noEmit` against 77k lines — slow, and it surfaces as a wall of type errors far from the cause. There is **no gate today that asserts "the FE generated layer matches current BE"** before you start coding; drift is discovered mid-feature.

### 1.2 The FE pre-flight (reuse discovery) is non-functional — step 1 cannot run

`engine/skills/mh-implement/preflight.md:5-8` makes the FIRST pre-flight step "read `myhospital-fe/docs/components/component-inventory.generated.md` + `docs/reuse/reuse-catalog.generated.md` … (run `npm run components:index` … if stale/missing)." Reality:

- **Neither catalog file exists** (`ls` → "No such file or directory" for both). `myhospital-fe/docs/components/` contains only hand-written `ai-index.md` + `data-grid.md`.
- **`npm run components:index` is not a script** — `package.json` scripts are only `dev, dev:test, build, lint, format, preview, create:module, create:page, dtos:update, client:generate, test:e2e*`. There is no `components:index` and no `reuse:catalog`.
- This is referenced as a real command **11+ times** across the harness (`engine/rules/frontend.md:443,481,529-530`, `preflight.md:6`, `definition-of-done.md:17`, `mh-implement/SKILL.md:43`, `deep-review/checklist.md:75`). **Every one of those is a dead instruction today.**
- **Why it eats time:** the "reuse beats authoring" lever (preflight.md:3 — "reuse is the cheapest correctness") is the harness's #1 anti-week mechanism, and it is unavailable. The dev re-discovers existing components/hooks/adapters by hand (`rg`) every feature.

### 1.3 The FE deterministic floor is half-disabled in worktrees

The plan (`agentic-harness-dev-fix-plan-2026-06-16.md:48-49`, G2) names this exactly: the guard hook's FE rules originally only fired in the main repo (which is edit-forbidden), so they **never fired during real dev** (in `worktrees/<slug>/fe`). The build added (a) an `mh_scan` FE bridge (`scripts/mh_scan/scanners.py:273-300`, FE-V1/V2/V3 via `scripts/sgconfig/rules/*.yml`) and (b) guard advisory for worktrees — but the **ESLint pack that makes `npx eslint <file>` catch FE-V1/V2/banned-libs in a worktree was never applied** (`docs/harness/pending/fe-main-repo-diffs-2026-06-16.md:11-43` — "CHỜ BẠN APPLY"). So today the FE floor = `mh_scan` (ast-grep, 5 rules) + guard-advisory only; `eslint.config.js` does **not** carry the convention rules.
- **Why it eats time:** FE-V4 (`useForm` without `zodResolver`) is explicitly "not expressible as a stable lint rule" (pending-diffs:39-40) and FE-V1 (dead import) only errors via `tsc` or the unapplied ESLint rule. So most FE convention violations are caught **late** (manual review / runtime), not at write-time — the opposite of the shift-left principle the harness is built on (`mh-implement/SKILL.md:8`).

### 1.4 The exemplar is a partial one whose two "copy me" files are giant anti-patterns — and monolithic pages are endemic repo-wide

`engine/rules/frontend.md:113` and `preflight.md:17-26` warn warehouse is a **PARTIAL** exemplar. Live sizes (`wc -l`):
- `inventory-list-page.tsx` = **636 lines** (the "monolithic 600-line page" — confirmed, do NOT copy whole).
- `inventory-form-sheet.tsx` = **1321 lines** (the audit said ~600; it is **more than double**): inline zod schema at `:56`/`:64`, hardcoded status `'Doing'` at `:188`, direct `serviceStackClient.get(new GetInventoryDetailRequest(...))` detail fetch at `:306`.
- The GOOD parts (`warehouse-adapter.ts` = **9 lines** thin singleton `extends GeneratedApiClient`; `warehouse-routing.tsx` = 146 lines; `warehouse-context.tsx` = 169 lines, correctly RQ-backed via `useMasterData`, not useState-as-data) are fine.
- **Monoliths are endemic, not a warehouse quirk:** across `src/modules` there are **230 `.tsx` files >400 lines and 124 files >600 lines** (~13% of module files). The largest: `prescription-tab.tsx` **2,783**, `transfer-issue-form-sheet.tsx` **2,527**, `purchase-order-form-sheet.tsx` **2,523**, `confirm-admission-page.tsx` **2,481**, `inpatient-admission-form.tsx` **2,386**. Warehouse's 1321-line form is mid-pack. So "copy a similar existing page" almost always means copying a monolith.
- **Why it eats time:** the canonical instruction is "mirror warehouse," but a dev who opens the two headline files copies a 636/1321-line structure, then has to *un-bake* the anti-patterns (split the page, extract the schema to `forms/`, replace the inline status). The "copy-not-copy" table exists (preflight.md:19-26) but is prose the dev must hold in their head while reading ~1957 lines — and every other module offers an even bigger monolith to copy.

### 1.5 The week goes into ~8 independent concern-axes, each with a silent-failure trap

FE features are slow because each one re-solves **all** of these, and several fail *silently* (no compile error), so they surface only in review or runtime:

| # | Concern-axis | Live evidence | The trap that eats time |
|---|---|---|---|
| A | **Contract / DTO drift** | 77k generated lines; regen via `dtos:update`+`client:generate` | Stale FE client → wall of `tsc` errors far from cause; no pre-flight "is FE in sync?" gate (§1.1). Dead import `@/lib/dtos/dtos` in **3 real source files** (`user/context/user-context.tsx`, `system-management/context/system-management-context.tsx`, `examination/context/examination-context.tsx`) — `dtos.ts` does **not** exist, real path is `generated-dtos.ts` → **build-breaking** (FE-V1). |
| B | **Master-data wiring** | `useMasterData([Entity])` (`src/modules/common/hooks/use-master-data.ts`, large hook w/ IDB + API fallback + share-scope) | Devs write an ad-hoc query for a dropdown instead of `useMasterData` (BLOCK, `frontend.md:87`); or compare by name/code: **2 live offenders** `patient-admin-info-block.tsx:226` and `inpatient-admission-form.tsx:842` (`=== 'kinh'`, FE-V3) — DB renames → FE fails silently. |
| C | **Cache-invalidation PAIR** | rule: every list/master mutation invalidates BOTH `invalidateQueries` AND `invalidateMasterDataEntity(...)` (`frontend.md:85-86,178-196`) | Missing the master-data half → UI stale after mutation, **no error** — pure runtime bug, found only by clicking. |
| D | **Form schema (RHF/zod factory)** | **327** `useForm` call-sites, only **168** wired to `zodResolver` → **~49% of forms have NO resolver** (76 of them in `src/modules`). Schema factories: ~8 modules have a `forms/<x>-schema.ts` factory; most schemas are still inlined in the page. | FE-V4 is **rampant, not rare**: ~159 `useForm` call-sites ship without `zodResolver` → validation **silently absent**. Live offenders: `diagnostic-imaging/.../ent-endoscopy-page.tsx:166`, `bed-management/.../bed-stay-assign-form.tsx:254`, `bed-reservation-form.tsx:153`, `create-room-page.tsx:90`. And schema-inlined-in-page (warehouse `inventory-form-sheet.tsx:56,64`) gets copied. |
| E | **Permission gating** | `useUserPermissions().can(fn, action)` (`src/modules/common/hooks/use-user-permissions.ts`); names from `Functions.FunctionNames.*`/`Actions.*` in `Constants.ts` | Missing permission constant = contract blocker, not a fallback (`frontend.md:92,282-288`); devs hardcode `'CanUpdate'` or add a fallback (legacy anti-pattern). State-machine buttons must gate on BOTH status AND permission — easy to miss. |
| F | **i18n** | `src/i18n/messages/`; **304 files** use `useIntl`/`useTranslation` | 6 modules have ZERO i18n (memory `fe-live-conventions-vs-stale-docs:23`); devs hardcode VN text in migrated areas (WARN). Choosing `useIntl` vs `useTranslation` (tenant-renamable labels) is a per-string judgment. |
| G | **Status display** | `StatusBadge` + `STATUS_REGISTRY` (`src/components/ui/status/status-badge.tsx`, `src/lib/status/status-resolver.ts`); values from `Statuses.*` | Hardcoded status string (warehouse `inventory-form-sheet.tsx` `'Doing'`, `frontend.md:113`); inlined `<Badge>`+conditional class instead of `StatusBadge`. New status not added to `STATUS_REGISTRY` → renders raw. |
| H | **Routing-root + provider wiring** | 21 `*-routing.tsx` files; each ≈110 lines of repetitive `lazy`+named-export+`Suspense(ContentLoader)`+`LayoutSelector`+404 (e.g. `bed-management-routing.tsx:1-110`). Registered in `src/routing/app-routing-setup.tsx` (57 lines) by adding an `import` (line ~24) + `<Route path="x/*" element={<XRouting/>}/>` (line ~30+) | The per-module routing file is pure boilerplate (slow to hand-write correctly); registering a new module touches `app-routing-setup.tsx` — a **protected root** whose edits need explicit approval (`frontend.md:410-420`). So a new module **always** hits a guarded file + 110 lines of ceremony. |
| I | **EnhancedDataGrid table** | `EnhancedDataGrid` + `useReactTable` + `useMemo` cols (`frontend.md:332-346`) | Raw `<table>` bypass is a BLOCK for admin lists (`frontend.md:90`); columns/`useMemo`/`recordCount`/`isLoading`/toolbar shape is verbose and re-derived each list. |
| J | **Reuse misses + testid/E2E** | `data-testid` in only **27 files / 121 occurrences** across ~1161 files | Sparse testids → progressive-test/agent-browser E2E must hand-write fragile selectors (slow); reuse misses (rebuild an existing component) because the catalog (§1.2) is dead. |

### 1.6 Tooling rot increases friction at the edges

- `npm run create:page` is **broken** — `scripts/create-page.js` **does not exist** (`myhospital-fe/scripts/` has `create-module.js`, `update-dtos.js`, `generate-api-client.js`, helper `.py`/`.cjs`, but no `create-page.js`), yet `package.json` still lists `"create:page": "node scripts/create-page.js"`. (`create-module.js` itself is 206 lines and *functional* — validates name, kebab→Pascal, guards the `demo` template — but it scaffolds a whole module, not a page, and predates the live RQ-adapter conventions.) (FE-V9; pending fix `fe-main-repo-diffs-2026-06-16.md:46-58`.)
- Two convention docs are **stale and misleading** — `ARCHITECTURE-OVERVIEW.md` (bearer-not-cookie auth, `Infinity` cache vs real `staleTime:0`, Context+reducer vs real RQ-adapter, "no tests", dead `/demo` routes) and `BEST-PRACTICES-NEW-PAGE.md` (prescribes an abandoned Context+`useReducer` data layer) (`engine/rules/frontend.md:60`, memory `fe-live-conventions-vs-stale-docs:12-15`). A dev who trusts them builds the wrong architecture. Banners proposed but **not applied** (`fe-main-repo-diffs-2026-06-16.md:62-76`).
- 14 `.v2.bak` files committed under `retail/` (FE-V12) — noise.

### 1.7 What `/mh-implement` does NOT cover for FE (the precise delta)

`/mh-implement` (`engine/skills/mh-implement/SKILL.md`) is a solid **generic** orchestrator (B0 worktree → B1 reuse → B2 contract → B3 implement → B4 DoD → B5 self-review-diff), but for FE specifically it:

1. **Assumes a reuse catalog that does not exist** (B1 / preflight.md:5-8 → §1.2). No fallback when `components:index` is absent.
2. **Has no contract-sync pre-gate** — it says "FE+BE work → BE contract first, regen FE" (SKILL.md:20) but nothing verifies the FE generated layer is current before FE-only work; drift (§1.1) is found mid-build.
3. **Treats the 8 concern-axes as one undifferentiated "implement" step** (B3). There is no FE-specific ordering (contract → reuse → skeleton → data → forms → cross-cutting → validate) and no per-axis "done" check. The dev must remember all of A–J from a prose contract (B2).
4. **Its DoD floor's FE half is partly inert** — `npx eslint` carries no convention rules (ESLint pack unapplied, §1.3); `components:index` in B4 is dead. So B4 = `tsc` + `mh_scan` (5 ast-grep rules) only.
5. **No FE-specific reuse/skeleton gate** — `/mh-scaffold` exists with good FE templates (`mh-scaffold/SKILL.md:401-446`, FE-1..FE-4) but mh-implement only *mentions* calling it at B3 (SKILL.md:36); nothing enforces "scaffold the skeleton from the canonical shape rather than copying the 1321-line form sheet."
6. **No testid/E2E-readiness step** despite the FE E2E path (progressive-test/agent-browser) needing testids that are 97% absent (§1.5-J).

The review side already encodes the FE bug-classes deterministically (`deep-review/checklist.md` D3 line 35 = adapter/invalidation/EnhancedDataGrid/master-data-name-compare/useForm-resolver; D7 line 59 = generated-file + dead-import; D10 line 77 = component-reuse + monolith-page) — **but that is post-hoc review, not write-time guidance.** The asymmetry is the whole problem: FE has good *review* coverage and weak *authoring* coverage.

---

## 2. PROPOSED FE-IMPLEMENTATION WORKFLOW (step-by-step, gated)

Design principle (inherited from the convergence memo, `mh-implement/SKILL.md:8`): **shift-left** — make each concern-axis correct *at write-time* with a deterministic per-phase check, so review/runtime stops finding it. This is an **FE-mode of `/mh-implement`** (§5): same B0/B5 spine, FE-specialized B1–B4. Phases below replace the single generic B1–B4 with FE-specific F1–F8. Each phase: **input → do → pitfall prevented → done-check**.

### F0 — Scope & worktree (unchanged from mh-implement B0)
- **Input:** feature ask + (if exists) `specs/<module>/{02-requirements,03-ui,06-decision-log,08-api}.md`.
- **Do:** Session Start Protocol; confirm slug/slot; work in `worktrees/<slug>/fe` (never `myhospital-fe/` — guard BLOCK). Read Confirmed requirements as business source of truth.
- **Pitfall prevented:** editing main repo; inventing business rules.
- **Done-check:** worktree confirmed; requirements read or "greenfield, no spec" stated.

### F1 — Contract intake & DTO/client sync gate  *(NEW deterministic gate — fixes §1.1)*
- **Input:** the BE endpoints/DTOs/permissions this feature needs (from `08-api.md` or the BE worktree if FE+BE).
- **Do:** (a) FE+BE features → BE contract first, then `npm run dtos:update && npm run client:generate` in the worktree. (b) FE-only features → run the **contract-sync check** (§3, new): assert the generated layer is current and that every DTO/hook/permission-constant the feature references already exists in `generated-dtos.ts` / `generated-api-client.ts` / `Constants.ts`. If a needed symbol is **missing → STOP, report a BE/API contract blocker** (`frontend.md:62-63,403`); do NOT hand-write it.
- **Pitfall prevented:** mid-feature `tsc` avalanche from stale client; hand-written DTO workarounds; dead `@/lib/dtos/dtos` import (assert the import path resolves).
- **Done-check:** `npx tsc --noEmit` is GREEN on the untouched baseline *before* writing feature code (drift surfaces now, not later); every referenced DTO/hook/constant grep-confirmed present.

### F2 — Reuse discovery (exemplar + working catalog)  *(fixes §1.2)*
- **Input:** the UI surfaces + data the feature needs.
- **Do:** (1) ensure the reuse catalog exists — run the **fixed `components:index`** (§3, new/repaired) to (re)generate `docs/components/component-inventory.generated.md` + `docs/reuse/reuse-catalog.generated.md`; if the script still can't be added to `myhospital-fe`, fall back to the harness-side generator (§3). (2) Read both catalogs. (3) CodeGraph from inside the repo (`codegraph explore "<area>"` / `codegraph node <symbol>`) for live callers. (4) Pick the warehouse exemplar's **GOOD parts only** (adapter 9-line singleton, routing, mutation-hook config, table, RHF+zod) — **never** copy `inventory-list-page.tsx` (636 ln) or `inventory-form-sheet.tsx` (1321 ln) wholesale.
- **Pitfall prevented:** rebuilding an existing component/hook (§1.5-J); copying the monolith/inline-schema anti-patterns (§1.4).
- **Done-check:** a 5–10-line reuse note: which existing components/hooks/adapters will be reused, which exemplar files mirrored (GOOD parts), the 1–2 genuinely new pieces. (Same artifact as preflight.md:30, but now backed by a catalog that actually exists.)

### F3 — Scaffold the skeleton from canonical shapes  *(leans on /mh-scaffold; replaces broken create:page)*
- **Input:** the reuse note (F2) + module/feature name.
- **Do:** for any brand-new module/page/form/adapter, emit the canonical shape via **`/mh-scaffold`** FE templates (`mh-scaffold/SKILL.md:408-446`): module skeleton (FE-1, split `pages/<f>/<f>-list-page.tsx` wrapper + `pages/<f>/components/<f>-list-content.tsx`), list page (FE-2), form sheet (FE-3, schema in `forms/<f>-schema.ts` factory — NOT inline), adapter (FE-4, 9-line singleton). For routing, generate the `*-routing.tsx` boilerplate (lazy+named-export+Suspense(ContentLoader)+LayoutSelector+404, mirror `bed-management-routing.tsx`). **Provider/routing-root wiring (`app-routing-setup.tsx`) is a protected root → prepare the 2-line diff (import + `<Route>`), flag it for approval, do not silently edit** (`frontend.md:410-420`).
- **Pitfall prevented:** 110 lines of hand-written routing ceremony; copying the 1321-line form sheet; inline schema; fat adapter; touching a guarded root unannounced; using the broken `npm run create:page` (§1.6).
- **Done-check:** files exist in the canonical split layout; `forms/<f>-schema.ts` exists as a factory; routing file present; root-wiring diff prepared + flagged (not yet applied without approval).

### F4 — Data wiring (adapter hooks + useMasterData + invalidation pair)
- **Input:** the scaffolded adapter + the entities/lists the feature reads/writes.
- **Do:** server state via `adapter.useGetXxx()` / `adapter.useCreateXxx({successMessage, invalidateQueries:[['GetXxxRequests'],['GetMasterDataRequests']], onSuccess})`. Reference/dropdown data via `useMasterData([Entity])` — never an ad-hoc query. Every list/master mutation invalidates **BOTH** `invalidateQueries` AND `invalidateMasterDataEntity('Entity')`. Reference by **Id** (`find(x => String(x.Id) === value)`); business rules from BE flags (`IsDefault`/`Requires*`/`*Option`)/`Constants.ts` — **never** a name/code literal.
- **Pitfall prevented:** raw `fetch`/`axios`/`serviceStackClient` in UI (FE-V2, BLOCK); ad-hoc dropdown query (BLOCK); missing invalidation half → stale UI (§1.5-C); name-compare `=== 'kinh'` (FE-V3, §1.5-B); client-side N+1.
- **Done-check:** `python scripts/mh_scan --root worktrees/<slug>/fe --scope <changed> --format summary` → 0 FE-V2/FE-V3; grep the new mutations to confirm BOTH invalidation calls are present (this is the one that has no compile signal — make it an explicit check).

### F5 — Forms (RHF + zodResolver + schema factory)
- **Input:** the form fields + validation rules + i18n needs.
- **Do:** `forms/<f>-schema.ts`: `export const get<F>FormSchema = (t?) => z.object({...})` + inferred type. `useForm<<F>FormValues>({ resolver: zodResolver(get<F>FormSchema(t)) })` — **resolver required**. Create/edit in `<Sheet>`; destructive confirm in `<AlertDialog>`; reset on open/identity change; unsaved-change guard.
- **Pitfall prevented:** `useForm` without resolver (FE-V4 → silent no-validation, §1.5-D); inline schema (un-i18n-able, copied from warehouse); missing dirty-guard.
- **Done-check:** grep the form file → `zodResolver` present and wired to the `forms/` factory (FE-V4 has no lint rule — make it an explicit grep check, per pending-diffs:39); schema lives in `forms/`, not the page.

### F6 — Cross-cutting: permission · i18n · status · testid
- **Input:** the rendered surfaces + actions.
- **Do:** permission via `useUserPermissions().can(Functions.FunctionNames.X, Functions.Actions.CanUpdate)` — names from `Constants.ts`, no fallback (missing constant → blocker). State-machine buttons gate on BOTH status AND permission. i18n: `useIntl` for chrome/buttons/errors, `useTranslation` for tenant-renamable labels — no new hardcoded VN text; `handleApiError(error, intl, fallback)` for API errors. Status: `StatusBadge` + register new statuses in `STATUS_REGISTRY`; values from `Statuses.*`. **testid: add `data-testid` to every interactive element the E2E flow will drive** (per the module's selector convention).
- **Pitfall prevented:** hardcoded permission/`'CanUpdate'`/fallback (§1.5-E); hardcoded VN text (§1.5-F); hardcoded status string / raw `<Badge>` (§1.5-G); ungated state-machine button; **missing testids that make E2E slow/fragile** (§1.5-J — 97% of files have none).
- **Done-check:** grep → no new `=== '<status>'`, no hardcoded `'CanUpdate'`, permission names resolve in `Constants.ts`; new interactive elements carry `data-testid`; (manual) i18n keys added for new text.

### F7 — Validation floor (deterministic)  *(fixes §1.3; one button)*
- **Input:** the changed file set (`git -C worktrees/<slug>/fe diff --name-only <base>`).
- **Do, in the worktree:**
  1. `npx tsc --noEmit` (catches FE-V1 dead import + contract drift) — BLOCK on error.
  2. `npx eslint <changed> --no-fix` (scoped; **never `npm run lint`**) — **after the ESLint pack is applied** (§3) this catches axios/banned-libs/`@/lib/dtos/dtos`/raw-`fetch`.
  3. `python scripts/mh_scan --root worktrees/<slug>/fe --scope <changed> --format summary` (FE-V1 HIGH, FE-V2/V3).
  4. `fd -t f '\.(bak|orig|v2\.bak)$' <changed dir>` empty (FE-V12).
  5. If a generated file would change → `npm run dtos:update && npm run client:generate`, re-run (1).
  6. `npm run components:index` (the **fixed** one) if UI added.
- **Pitfall prevented:** every deterministic FE violation reaching review (shift-left); committed backups; stale catalog.
- **Done-check:** 0 type errors · 0 ESLint errors on changed files · 0 FE-V1/HIGH from `mh_scan` (WARN each fixed or justified w/ comment per `definition-of-done.md:24`) · no `.bak`.

### F8 — Self-review-diff + E2E
- **Input:** the diff.
- **Do:** (B5) run `mh-review` on **only the diff** (explicit file set = changed files) — reviewer D3/D7/D10 already carry the FE bug-classes (`checklist.md:35,59,77`); fix what it flags now. For visible UI, run the dev server + smoke login (`HMU`/`admin`/`123456`). For a real user flow, run the FE E2E path (`engine/workflows/progressive-test/` → agent-browser) — the testids added in F6 make this fast.
- **Pitfall prevented:** pushing regressions/convention drift to a later review round (the thing that makes review take 3+ rounds); shipping a flow that doesn't actually work in the browser.
- **Done-check:** self-review findings closed; UI verified in browser; E2E green (when the feature is a flow). Then summarize: files changed, contract items honored (A–J), validation commands run + results, residual risks.

---

## 3. REUSE vs NEW

### Reuse / extend (the bulk — do NOT replace)
- **`/mh-implement`** — keep its B0 (worktree) and B5 (self-review-diff) verbatim; FE-mode only specializes the middle (B1–B4 → F1–F8). Same skill file, an FE branch.
- **`/mh-scaffold`** — already has correct FE templates (FE-1..FE-4, `mh-scaffold/SKILL.md:401-446`); F3 *calls* it. No change needed beyond pointing F3 at it explicitly.
- **`mh-implementer` agent** — already FE-convention-aware (`engine/agents/mh-implementer.md:17`); reuse as the bounded sub-task worker for disjoint files in F3–F6.
- **`mh_scan` FE bridge + `scripts/sgconfig/rules/`** — reuse as the F4/F7 deterministic floor (FE-V1/V2/V3 already wired, `scanners.py:273-300`).
- **`deep-review/checklist.md` D3/D7/D10** — reuse as the F8 self-review dimensions; they already encode the FE bug-classes. The FE workflow's job is to make F1–F7 *prevent* what D3/D7/D10 *detect*.
- **`progressive-test/` + agent-browser** — reuse as the F8 E2E step.
- **`engine/rules/frontend.md`** — reuse as the convention source of truth for the B2/F-phase contracts.

### Genuinely NEW pieces worth adding (small, deterministic, high-leverage)
1. **Fix/replace `components:index` (+ reuse-catalog generator)** — *the single highest-value fix.* The catalogs are referenced 11+ times and don't exist (§1.2). Either restore a working `scripts/` generator in `myhospital-fe` (prepare as a diff — main repo is edit-forbidden) OR add a harness-side generator under `scripts/` that writes the two `.generated.md` files. Without this, F2 reuse-discovery stays dead and the #1 anti-week lever is unavailable.
2. **Contract-sync gate (F1)** — a small `scripts/` check that, given a list of referenced DTO/hook/permission symbols, greps `generated-dtos.ts`/`generated-api-client.ts`/`Constants.ts` and reports missing ones as a contract blocker, and asserts `@/lib/dtos/generated-dtos` resolves (no dead `@/lib/dtos/dtos`). Makes drift a *pre*-gate, not a mid-feature avalanche.
3. **Apply the pending ESLint pack** (`docs/harness/pending/fe-main-repo-diffs-2026-06-16.md:11-43`) — the F7 floor's ESLint half is inert until this lands. It is a prepared diff awaiting the owner. Until applied, F7 step 2 is a no-op and FE-V1/V2/V4 lean entirely on `tsc`+`mh_scan`+review.
4. **An FE phase checklist** (`engine/skills/mh-implement/fe-checklist.md` or a section) — the A–J concern-axis table (§1.5) as an explicit per-feature checklist with the done-check for each, so the dev/agent doesn't carry 8 axes in their head. This is the cheap "make the implicit explicit" win.
5. *(Optional, lower priority)* a **routing/provider-wiring helper** — since every new module hits the 110-line routing boilerplate + a guarded-root 2-line registration, a generator (part of `/mh-scaffold` F3) that emits both and flags the root diff.

What is **not** worth adding: a new state library, a new table abstraction, a parallel review system, or a from-scratch FE framework — the conventions and the review side are mature; the gap is authoring-time determinism, not new abstractions.

---

## 4. WHERE THE WEEK GOES — summary map (evidence → time sink)

| Failure mode | Evidence | Silent? | Phase that fixes it |
|---|---|---|---|
| Contract drift / stale FE client | 77k generated lines; no sync pre-gate (§1.1) | semi (late `tsc`) | F1 + new contract-sync gate |
| Dead `@/lib/dtos/dtos` import | 3 source files (user/system-management/examination context) | **build-break** | F1, F7 (tsc + mh_scan FE-V1) |
| Reuse miss (rebuild existing) | catalogs don't exist; `components:index` not a script (§1.2) | yes | F2 + new catalog generator |
| Copy the monolith/inline-schema | warehouse 636/**1321** ln; repo-wide **124 files >600 ln**, largest 2,783 (§1.4) | yes | F2/F3 (scaffold canonical, GOOD parts only) |
| Master-data name-compare | `patient-admin-info-block.tsx:226`, `inpatient-admission-form.tsx:842` (`=== 'kinh'`) | **yes** (DB rename) | F4 (mh_scan FE-V3) |
| Ad-hoc dropdown query | rule BLOCK `frontend.md:87` | yes | F4 (useMasterData) |
| Missing invalidation half | rule `frontend.md:85,178-196` | **yes** (stale UI) | F4 done-check (grep both calls) |
| useForm without resolver | **327 useForm / 168 zodResolver → ~49% none** (§1.5-D) | **yes** (no validation) | F5 done-check (grep resolver) |
| Hardcoded permission/status/VN text | §1.5-E/F/G | yes | F6 done-checks |
| Routing boilerplate + guarded-root registration | 21 routing files ~110 ln; `app-routing-setup.tsx` protected | no (compile) but slow | F3 (scaffold + flagged diff) |
| Sparse testids → slow E2E | `data-testid` in 27/1161 files | n/a | F6 (add testids) + F8 |
| Inert ESLint floor in worktree | pack unapplied (§1.3) | n/a | NEW piece #3 |
| Broken `create:page`, stale docs | §1.6 | n/a | F3 (use /mh-scaffold); banner diffs pending |

---

## 5. RECOMMENDATION — FE-mode of `mh-implement` (not a new skill)

**Pick: extend `/mh-implement` with an FE-mode (F1–F8), NOT a separate `/fe-implement` skill.**

**Why FE-mode wins:**
- **Shared spine, no fork drift.** B0 (worktree/Session-Start/spec-read) and B5 (self-review-diff) are identical for FE and BE; a separate skill would duplicate them and they would drift. mh-implement already *is* the FE+BE orchestrator (`SKILL.md:6`) — it just lacks an FE specialization in the middle.
- **The boundary doc is already there.** `mh-implement/SKILL.md:10-15` defines scaffold-vs-implement-vs-fix; adding "FE-mode vs BE-mode" inside implement is consistent with that, whereas a 4th top-level skill blurs the trigger surface the harness deliberately keeps small (`agent-shortcuts.md`).
- **FE+BE features need one orchestrator.** A feature that spans BE contract → regen → FE usage (SKILL.md:20, the common case) must be driven by one skill that does BE-mode then FE-mode in sequence. Two skills would force the user to hand off mid-feature.
- **Lower maintenance.** All the NEW pieces (§3) are deterministic scripts/checklists referenced *by* mh-implement; they don't need a new skill wrapper.

**Trade-offs (honest):**
- *Against FE-mode:* the SKILL.md grows and must branch clearly ("if FE: F1–F8; if BE: existing B-flow"). Mitigation: keep the FE phases in a sibling `engine/skills/mh-implement/fe-flow.md` (like `preflight.md`/`definition-of-done.md` already are), referenced from SKILL.md — same pattern, no bloat in the main file.
- *For a separate skill:* a dedicated `/fe-implement` would have a sharper trigger and a fully FE-tailored prose. But the cost (duplicated B0/B5, split FE+BE features, a new entry to remember) outweighs the marginal clarity, and the FE-flow doc gives the same tailoring without the fork.

**Concretely, to implement the recommendation (all inside `roast/`, no main-repo edits):**
1. Add `engine/skills/mh-implement/fe-flow.md` = the F1–F8 phases (§2) with per-phase done-checks + the A–J checklist (§1.5).
2. Branch `mh-implement/SKILL.md` B1–B4: "**FE work → follow `fe-flow.md` (F1–F8)**; BE work → the existing B-flow." Keep B0/B5 shared.
3. Land the 3 deterministic enablers (§3 #1 catalog generator, #2 contract-sync gate, #3 apply the pending ESLint pack) — without them F2/F1/F7 are partially inert.
4. Point F3 explicitly at `/mh-scaffold` FE templates; point F8 at `deep-review` D3/D7/D10 + `progressive-test`.

The net effect: FE gets the same property BE already has — *a Confirmed spec plus a deterministic, gated path*, where each of the 8 concern-axes is made correct at write-time and proven by a check, instead of re-discovered and caught late. That is what turns a week into a day.

---

## 6. Verification notes / unverifiable flags
- All `wc -l`, `rg`, `fd`, `ls`, and `package.json` facts above were run live against `myhospital-fe/` on 2026-06-15/16 checkout.
- The referenced FE audit `velvet/notes/myhospital-fe-convention-audit-2026-06-15.md` **does not exist on this Linux checkout** (the `velvet/` tree is gone); its content survives distilled in `engine/rules/frontend.md`, `mh-implement/preflight.md §3`, `deep-review/checklist.md` D3/D7/D10, and memory `fe-live-conventions-vs-stale-docs`. Treat audit V-numbers as cited via those live files, not the original.
- The `inventory-form-sheet.tsx` line numbers (inline schema `:56`/`:64`, status `'Doing'` `:188`, `serviceStackClient.get` `:306`, invalidation pair `:364-396`) and `invalidateMasterDataEntity` at `use-master-data.ts:21` (776-line hook) were independently re-confirmed by a second read pass against the live files.
- The `useForm`/resolver figures are **call-site** counts (327 total / 168 with `zodResolver` → ~49% without). A few of the ~159 resolver-less call-sites may be legitimate (forms with no validation needs); the named offenders (`ent-endoscopy-page.tsx:166`, `bed-stay-assign-form.tsx:254`, `bed-reservation-form.tsx:153`, `create-room-page.tsx:90`) are real. The earlier file-level ratio (82/91 files) and this call-site ratio are both accurate at their respective granularities.
- Dead `@/lib/dtos/dtos` references total ~6-8 hits including READMEs/i18n strings; the **3 build-relevant code imports** are `examination/context/examination-context.tsx`, `user/context/user-context.tsx`, `system-management/context/system-management-context.tsx`.
