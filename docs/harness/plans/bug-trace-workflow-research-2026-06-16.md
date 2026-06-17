# Bug-Trace / Root-Cause-Investigation Workflow — research + proposal

> Status: research proposal (2026-06-16). Read-only investigation; no source touched.
> Purpose: make the **investigation front-half** of `/bug-fix` concrete, ORDERED, and tied to real
> files in this repo — replacing the black-box "RCA via the mh-rca agent" step with a layered,
> cheap-first playbook. It does NOT rebuild `mh-rca` or `progressive-test`; it *feeds* them.
>
> All `file:line` citations were verified against the live checkout unless flagged `UNVERIFIED`.

---

## 0. Why this is needed (the gap)

`engine/skills/bug-fix/SKILL.md` step 2 ("REPRODUCE") and step 3 ("RCA → spawn the mh-rca agent")
are correct as *orchestration* but give the investigator no **system-specific procedure**. The
`mh-rca` agent (`engine/agents/mh-rca.md`) is told to "investigate the TARGETED source — CodeGraph
first, then bounded rg. Find the real root cause" — but *which layer first*, *what to check*, and
*what a result means* is left to improvisation. This document supplies that procedure, grounded in
how THIS stack actually moves data.

This playbook is the body of **bug-fix step 2 (REPRODUCE)** and **step 3 (RCA)**. Everything
downstream (FIX-PLAN, CODEX gate, FIX via `/mh-fix`, VERIFY) is unchanged.

---

## 1. The two facts that make this codebase special (read first)

Two architectural realities dominate every FE bug here. Internalize them before triaging.

### Fact A — Success is the body `Code === "SUCCESS"`, NOT the HTTP status

The standard envelope is `{ Code, Message, Data }` (PascalCase). **Success is `Code === "SUCCESS"`,
NOT the HTTP status code.** A business error (validation, not-found, conflict, forbidden) may arrive
**either** as **HTTP 200 with a non-SUCCESS `Code`** (handled by `checkResponse` → throws `ApiError(...,200)`)
**or** — when the `BusinessException` carries an HTTP status, `StandardResponsePlugin` overrides the status
(`StandardResponsePlugin.cs:81,:133`) — as a **real 4xx/5xx** (handled by `wrapInfrastructureError`).
*(Correction 2026-06-17: an earlier draft said the BE "always returns HTTP 200"; that is no longer true.
Status MAY be 200 or a real error code — so the reliable signal is the body `Code`, never the status line.)*

- `myhospital-fe/src/lib/server/servicestack-client.ts:15-18` — documents "All API responses return
  HTTP 200 with structure `{ Code, Message, Data }`; `Code = "SUCCESS"` means success".
- `servicestack-client.ts:97-185` — `checkResponse()`: if `Code !== ErrorCodes.Success` it throws
  `ApiError(..., 200)` (note the hard-coded `200` at `:130` and `:170`). It also auto-handles
  `Unauthorized`/`UserNotLoggedIn` (→ `handleUnauthorized()`, redirect to login, `:204-223`) and
  `Forbidden` (→ dispatch `API_FORBIDDEN_EVENT`, `:118-122`).
- `servicestack-client.ts:262-344` — `wrapInfrastructureError()`: the *other* path, for real non-200
  HTTP (nginx 502, raw ServiceStack `ResponseStatus`, "Failed to fetch"). It tries `responseBody.Code`
  first, then `ResponseStatus.errorCode`, then a `"NNN - reason"` status-line regex, then network-error.

**Triage consequence:** "Network tab shows 200 OK" does **NOT** mean the call succeeded. You MUST read
the **response body `Code`**. A green 200 with `Code: "SomeError"` is a *handled business error*, and
the real message is in `Message`. This single fact reorders the whole network-layer investigation.

### Fact B — Reference/list data is served from an IndexedDB cache, not the network

Most dropdowns, lookups, names, **and permissions** do not hit the API on each render — they come from
an IndexedDB-backed master-data cache via `useMasterData(...)`. The cache can go stale independently
of the server, and a "wrong data" bug is very often a *stale-cache* bug, not a BE bug.

- `myhospital-fe/src/modules/common/hooks/use-master-data.ts:166-181` — documents the flow:
  IDB lookup first → API fallback for missing entities → save back to IDB → filter → return.
- `use-master-data.ts:374-407` — initial mount reads each entity from IDB (`idbStorage.getEntities`);
  found → `cached`, missing → fetched from API via TanStack Query (`:417-429`).
- `use-master-data.ts:21-25` — `invalidateMasterDataEntity(entityName, force=true)` dispatches the
  `masterdata:entity-invalidated` CustomEvent; the listener (`:341-356`) calls `refreshEntity`.
- `use-master-data.ts:277-336` — `refreshEntity`: always re-fetches from **API** (not IDB), with a
  **global lock** (`globalRefreshing`, `:41`) and a **3s cooldown** (`REFRESH_COOLDOWN_MS = 3000`,
  `:45`, `:285-296`). **If the API returns empty, it skips notify to avoid wiping UI data** (`:319-322`).
- `use-master-data.ts:464-554` — `filterActiveRows`: hospital/tenant + `IsActive` + `ShareScope`
  filtering. A row can be present in IDB but **filtered out** of the returned data (wrong hospital,
  inactive, share-scope mismatch). This is a distinct failure mode from "missing from cache".
- **Permissions ride on this same cache:** `use-user-permissions.ts:12` does
  `useMasterData(['UserRolePermission'])`. So a "missing permission / button greyed out" bug can be a
  *stale `UserRolePermission` in IndexedDB*, not a BE/seed problem.

The IndexedDB store itself: `myhospital-fe/src/lib/storage/idb-storage.ts`.
- DB name `myhospital-db` (`:16`); version from `VITE_INDEXEDDB_VERSION` (`:17`).
- **Hospital-switch wipe:** `checkHospitalChange()` (`:37-61`) and `dropIfHospitalChanged()` (`:91-99`)
  **delete the entire DB** when the stored hospital id differs from the current one. (Relevant when a
  bug only repros after switching hospital or re-login.)
- `saveEntities` only writes to **stores that already exist** (`:384-390`); a *new* entity needs to be
  added to `ENTITY_STORES` + `DB_VERSION` bumped, else it silently never caches (`:374` doc).

### Fact B' — Two SEPARATE caches, do not confuse them

There are two distinct IndexedDB-backed layers and a memory layer:

1. **Master-data entity cache** — `useMasterData` → `idbStorage.getEntities/saveEntities`, keyed by
   `row.Id` in per-entity object stores (`idb-storage.ts:394-403`). Invalidated by
   `invalidateMasterDataEntity`.
2. **TanStack Query persisted cache** — the `REQUESTS` object store, written by the
   `PersistQueryClientProvider` persister. **Only queries whose key is in `customQueryConfig` are
   persisted** (`query-provider.tsx:147-158` `shouldDehydrateQuery`), and today that list is just
   `["GetAllHospitalsByUserRequest"]` (`config/query.config.ts:35-47`). Everything else lives only in
   RAM with `staleTime: 0` / `gcTime: 5min` (`query.config.ts:14-18`) — i.e. **refetched on every
   mount**, never persisted.
3. **In-memory React Query cache** — default `staleTime: 0`, so normal queries are always "stale" and
   refetch on mount/reconnect (`query.config.ts:18`, `:27`, `:30`).

**Triage consequence:** a stale value that *survives a full page reload / browser restart* is almost
certainly the **master-data IDB cache** or a `customQueryConfig` persisted query — NOT a normal RQ
query (those are gone after `gcTime`). A stale value that *disappears on reload* is the in-memory RQ
cache (missing invalidation).

---

## 2. Triage front-door — pick the prime suspect (CHEAP + HIGH-YIELD first)

Given a symptom, start at the cheapest check that most often localizes it. Do **one** of these first,
not all. The goal is to assign a *prime-suspect layer*, then run that layer's playbook (§3).

| Symptom pattern | Prime suspect (start here) | First cheap check | §3 layer |
|---|---|---|---|
| Mutation succeeds but the list/dropdown doesn't update until reload | RQ cache / master-data not invalidated | Did the mutation call BOTH `invalidateQueries` AND `invalidateMasterDataEntity`? (grep the form) | L2 / L3 |
| Wrong name / label / category shown; "old" value after someone edited master data elsewhere | Stale master-data in IndexedDB | DevTools → Application → IndexedDB → `myhospital-db` → entity store: is the row stale? `window.__idbLogs.summary()` | L3 |
| Value wrong even after full page reload / next day | Persisted cache (master-data IDB or `customQueryConfig`) | Clear IndexedDB, reload — does it fix? | L3 |
| Button missing / "no permission" but user should have it | Stale `UserRolePermission` in IDB **or** BE seed | IndexedDB `UserRolePermission` store has the row? `can()` args correct? | L3 / L6 |
| Error toast with a specific message | BE business rule (HTTP 200 + `Code`) | Network tab → **response body `Code`/`Message`** (NOT the 200 status) | L4 → L5 |
| Generic "Máy chủ đang gặp sự cố" / 500 / "Failed to fetch" | BE exception or infra | BE console/logs + Network status code | L5 / L6 |
| Field saved as null / wrong shape / "Cannot read property X" | Contract drift (DTO ≠ BE) or id/name mismatch | `npx tsc --noEmit`; compare request payload to `generated-dtos.ts` | L4 |
| `find(... === 'someName')` returns nothing after a rename | id/name mismatch (FE-V3) | grep the component for `.find(... === '` (mh_scan FE-V3) | L1/L3 |
| Page crash / infinite re-render / blank | UI render/state (hooks, refs) | React error overlay + console; React DevTools render count | L1 |
| Selected dropdown shows id instead of label, or "[object Object]" | id-vs-object referencing in the form | Inspect form value: is it an `Id` string or the whole object? | L1/L3 |

Heuristic ordering when truly unsure: **L4 network/contract first** (one Network-tab glance tells you
FE-only vs BE-only vs contract — see §4), then branch.

---

## 3. Layered investigation playbook

Layers are ordered **outside-in along the data path**: UI render → RQ cache → IndexedDB master-data →
network/contract → BE service/validation → DB. Each step: **the check · how to run it · what
positive/negative means · where to go next.** Investigation is **read-only** (mirrors `mh-rca` and the
audit rounds in `engine/workflows/deep-review`). Fixes happen only later via `/mh-fix` in a worktree.

### L1 — UI render / component state

**Check:** Is the bug a pure render/state problem (stale closure, missing `useEffect` dep, ref not
reset, wrong derived value, infinite re-render) with the *correct* data already in hand?

**How:**
- React error overlay + browser console first.
- React DevTools → Components: inspect the component's props/state and the `useMasterData`/`useQuery`
  result it received. If `data` is already correct here, the bug is L1 (render), not data.
- For infinite-render/crash: watch the render count. `use-master-data.ts:640-705` documents a real
  historical infinite-loop class ("70+ renders in 500ms, crashing the app") caused by using the
  unstable `apiQuery` object reference in deps — if you touched a master-data consumer, suspect ref
  stability.
- Form id/object bug: inspect the RHF field value. Convention is **reference by `Id` string**, not the
  object (`engine/rules/frontend.md:223-226`). A dropdown showing `[object Object]` or not matching =
  the form stored the object, or compared `String(x.Id) === formValue` wrong.

**Positive (data correct in component, render wrong):** root cause is L1 — fix is local
(deps/refs/derivation). Likely `DIRECT_PATCH`.
**Negative (data arriving is already wrong):** descend to L2.

### L2 — TanStack Query cache (in-memory + invalidation)

**Check:** Is the displayed data a *stale RQ query result* because a mutation didn't invalidate it?

**How:**
- Grep the mutation site for the **invalidation pair**. Every mutation that changes list/master data
  must call BOTH `invalidateQueries` (RQ) **and** `invalidateMasterDataEntity(...)` (master-data) —
  this is a BLOCK rule (`engine/rules/frontend.md:85-88`, `:178-196`). A mutation with `onSuccess` but
  missing one half is "almost always a cache bug" (`frontend.md:194`).
- There are **no React Query Devtools** wired in this app (verified: no `ReactQueryDevtools` import in
  `src/`). Inspect RQ state instead via component props (React DevTools) or by reading the query keys
  the adapter uses (e.g. `['GetInventoryRequests']`, `['GetMasterDataRequests']`).
- Remember `staleTime: 0` (`query.config.ts:18`): a normal query refetches on the **next mount**. So a
  stale value that *clears when you navigate away and back* but not *in place after a mutation* = a
  missing `invalidateQueries` (no in-place refetch), confirmed.

**Positive (missing/incorrect `invalidateQueries`):** root cause L2. Fix = add the correct query keys
to the mutation hook config. Usually `DIRECT_PATCH`, but if the entity is master-data it's really L3.
**Negative (invalidation present and fires):** if data is a reference/lookup entity, descend to L3;
otherwise the stale data came from the server → L4/L5.

### L3 — IndexedDB master-data cache (the big FE trap)

**Check:** Is `useMasterData` returning stale/missing/over-filtered rows from IndexedDB?

**How (in order):**
1. **Open the cache.** DevTools → **Application → IndexedDB → `myhospital-db`** → the entity store
   (store name = entity name, e.g. `MasterDisease`, `UserRolePermission`). Rows are keyed by `Id`
   (`idb-storage.ts:399-403`). Read the actual cached row.
2. **Read the op log.** In the console: `window.__idbLogs.summary()` for stats,
   `window.__idbLogs.getErrors()` for failed IDB ops, `window.__idbLogs.export()` to copy a full
   trace (ring buffer, 500 entries; `idb-logger.ts:56`, global registered at `idb-logger.ts:275`).
   Gated by `VITE_DEBUG_INFO=true`. There is also an in-app **IndexedDB debug panel**
   (`src/components/dev/idb-debug-panel.tsx`) and a network **debug-info panel**
   (`src/components/dev/debug-info-panel.tsx`, mounted when `VITE_DEBUG_INFO === 'true'`,
   `:577`), which taps every HTTP response via `setDebugInfoTap` (`debug-info-tap.ts`,
   wired in `servicestack-client.ts:240`).
3. **Decide which failure mode:**
   - **Stale row in store** (store has an outdated value) → an upstream mutation didn't call
     `invalidateMasterDataEntity('Entity')`, OR the cooldown/empty-guard suppressed the refresh
     (`use-master-data.ts:285-322`: 3s cooldown; **empty API response is intentionally NOT written**,
     so the old row persists). Confirm: trigger `invalidateMasterDataEntity('Entity')` (or wait out
     cooldown / re-login) — if it corrects, that's the cause.
   - **Row missing from store** → either never fetched, or the **store doesn't exist** (`saveEntities`
     skips unknown stores, `idb-storage.ts:384-390`). Check `ENTITY_STORES` in
     `src/lib/dtos/Constants.ts` includes the entity and `VITE_INDEXEDDB_VERSION` was bumped.
   - **Row present in store but absent from returned `data`** → **filtered out** by `filterActiveRows`
     (`use-master-data.ts:464-554`): wrong `HospitalId`/`TenantId`, `IsActive === false`, or
     `ShareScope` (`All`/`Partial` via `EntityHospitalShare`) excludes it. Confirm by comparing the
     cached row's `HospitalId`/`TenantId`/`IsActive`/`ShareScope` against the current
     `user.hospital.id` / `user.tenant.id`.
   - **Stale after hospital switch** → expected DB-drop didn't run, or ran and re-fetched wrong scope
     (`idb-storage.ts:37-61`, `:91-99`).
4. **id/name compare (FE-V3).** If business logic selects a master-data row by a **name/code string
   literal** (`masterData.X.find(e => e.Name === 'Kinh')`), a DB rename makes it silently fail. This
   is a BLOCK convention (`frontend.md:221-229`) and is deterministically flagged by `mh_scan` FE-V3.
   Fix is to use a BE flag (`IsDefault`, …) or select by `Id`.

**Positive:** root cause is L3 — classify by failure mode above. Missing-invalidation → often
`DIRECT_PATCH`. Filtering/scope or store-version issues → `CODEX_REQUIRED` (touches shared cache
behavior). FE-V3 name-compare → `DIRECT_PATCH` to flag/Id.
**Negative (cache faithfully holds what the server sent, and it's wrong):** the server sent wrong data
→ L4/L5.

### L4 — Network / contract (the FE↔BE boundary)

**Check:** What did the server actually return, and does the wire shape match the generated contract?

**How:**
1. **Read the response body, not the status.** DevTools → Network → the call → Response. Per **Fact
   A**, a **200 with `Code !== "SUCCESS"`** is a handled business error; the human-facing reason is in
   `Message`. A real non-200 (4xx/5xx) goes through `wrapInfrastructureError`
   (`servicestack-client.ts:262-344`) and maps to a friendly VN message by status
   (`friendlyMessageForStatus`, `:27-37`).
2. **401/403 special paths:** a `401`/`Unauthorized`/`UserNotLoggedIn` triggers auto-logout +
   redirect (`:113-115`, `:204-223`, `:282-284`) — if the app "randomly logs out", look here and at
   the `ss-id` cookie. `403`/`Forbidden` fires `API_FORBIDDEN_EVENT` and suppresses the error toast
   (`query-provider.tsx:31`, `:62`). Auth is **cookie-based (`ss-id`, `credentials:'include'`)** — no
   bearer token (`servicestack-client.ts:55-57`); a missing/expired `ss-id` cookie (Application →
   Cookies) explains 401s.
3. **Contract drift detection:** run `npx tsc --noEmit` from `myhospital-fe/` — catches FE code using
   a DTO field/hook that the generated client no longer has (and the dead `@/lib/dtos/dtos` import,
   FE-V1). Compare the request payload / response shape in the Network tab to the type in
   `src/lib/dtos/generated-dtos.ts`. The three generated files are **read-only** and regenerated, never
   hand-edited (`engine/rules/frontend.md:395-408`, `myhospital-fe/CLAUDE.md`): if a field/hook/constant
   is *missing*, that's a **BE/API contract blocker**, not something to patch in FE. Regenerate with
   `npm run dtos:update && npm run client:generate` only when scope allows.
4. **Reproduce the call in isolation:** replay the request (Network → Copy as fetch, or re-trigger the
   action). If the same payload yields the same bad response independent of UI state → it's BE (L5),
   not FE.

**Positive (response is correct, FE mishandles it):** root cause is FE — go back up to L3/L2/L1.
**Positive (response is wrong / shape mismatch):** contract drift or BE bug → L5; if the field simply
doesn't exist in the generated DTO, it's contract drift → BE-first (`CODEX_REQUIRED` / `HUMAN_DECISION`
if it implies a contract change).
**Negative (call never sent, or raw `fetch`/`axios` used):** a raw `fetch`/`axios`/manual
`JsonServiceClient` in a component bypasses the adapter (BLOCK; FE-V2 / no-axios). Find it via mh_scan
(`mh-no-raw-fetch-*`, `mh-servicestackclient-in-component`, `no-axios-import-*` in
`scripts/sgconfig/rules/`).

### L5 — BE service / validation

**Check:** Does the BE endpoint compute/return the wrong thing, or throw?

**How:**
- Map the request DTO name (from the Network call / `generated-api-client.ts` method) to its `*Api`
  class, then to the `*Service`. The lifecycle is endpoint DTO → thin `*Api : BaseApi` (validates via
  `ValidationHelper.Validate`, calls the service) → `*Service : BaseService<T>` (business logic +
  data) → returns DTO; `StandardResponsePlugin` wraps it into `{ Code, Message, Data }`.
  *(BE file:line evidence — see §3-BE below, populated from the BE trace.)*
- A thrown `BusinessException(code, message)` becomes the non-SUCCESS `{ Code, Message }` the FE sees
  (`engine/rules/backend.md:142-150`). So map the FE's `Code` straight to `ErrorCodes.<Module>.<Reason>`
  in the BE to find the exact `throw`.
- **Where to look server-side at runtime:** see the BE observability findings in §3-BE (console / log
  sink / request-logs). *(Populated from the BE trace; if no durable sink exists, the cheapest BE
  observability is a focused failing test, below.)*
- **Deterministic BE bug-classes** (run `just mh-scan`, scanners in `scripts/mh_scan/scanners.py`):
  `error_code_literal` (V3, HIGH), `raw_exception` (`throw new Exception`, V12, HIGH),
  `swallow_catch` (V11), `new_transaction` (V6), `hard_delete` (V10), `redundant_softdelete` (V9),
  `contract_dict` (`Dictionary<string,object>`/`dynamic` at contract layer, V13),
  `magic_status` (V16), `manual_codegen` (V15), `fat_api` (Db access in `*Api.cs`, V8),
  `legacy_listing` (V4), `missing_hospital_scope`. These map straight to the BE convention rules and
  often *are* the root cause for a class of BE bugs.
- **Tenant-scope trap:** a "data missing for this user/hospital" bug can be a tenant/hospital scoping
  issue — `BaseService.GetAllByTenant*` **hard-fails** (`InvalidOperationException`) when
  **`EffectiveTenantId == 0`** (`BaseService.cs:159`; `EffectiveTenantId` defaults to
  `CurrentSession.CurrentTenantId`, `:38`). Confirm the session has the expected tenant/hospital.

**Positive (BE logic/throw wrong):** root cause L5. Fix in BE (worktree) — usually `CODEX_REQUIRED`
(business rule / data / multi-file). Write a failing NUnit test first (see §4 / §3-BE).
**Negative (BE returns correct data from what's in the DB):** descend to L6.

### L6 — Database

**Check:** Is the data itself wrong/missing in SQL Server, or a query/filter excluding it?

**How:**
- Query the DB directly for the row(s) the endpoint should return (the SQL slot per worktree is in the
  slot map, `AGENTS.md`). Remember the **global soft-delete filter** (`DeletedAt == null`) is applied
  by `MyHospitalContext` (`backend.md:120-129`) — a row with `DeletedAt` set is invisible to normal
  queries by design. Check `DeletedAt`, `IsActive`, `TenantId`, `HospitalId`, and any unique-index /
  `ShareScope` columns.
- For a "duplicate allowed / duplicate blocked wrongly" bug: the service's duplicate check must mirror
  the **DB unique index scope exactly** including `DeletedAt IS NULL` (`backend.md:281-283`).
- Permissions: the row lives in the table behind `UserRolePermission`; a genuinely missing permission
  is a **seed/data** issue (not an FE fallback — adding an FE fallback is a BLOCK,
  `frontend.md:281-288`).

**Positive (data wrong/missing in DB):** root cause L6 — data fix or a BE write-path bug that produced
bad data. Often `HUMAN_DECISION` (is the data wrong, or is the rule wrong?).
**Negative (DB correct, BE query correct, FE correct):** re-examine assumptions — the symptom may be a
different call/entity than assumed; restart triage with sharper evidence (`MORE_EVIDENCE`).

---
## 3-BE — Backend lifecycle + observability reference (cited by L5/L6)

> Evidence from the BE CodeGraph/rg trace. **Line numbers are as reported by that trace and were not
> each independently re-verified by me** — the *patterns* are corroborated by `engine/rules/backend.md`;
> spot-check exact lines when wiring this in. The file paths and behaviors are reliable.

**Request lifecycle (endpoint → service → DB → response):**
- `MyHospital.Apis/BaseApi.cs:9-21` — `BaseApi : Service`; exposes `GetCurrentSession` (reads
  `CustomUserSession` via `SessionAs<CustomUserSession>()`) to every `*Api`.
- `MyHospital.Apis/DepartmentApi.cs:208-238` — canonical thin Api: `ValidationHelper` validates the DTO
  (`:210`) → `GetCurrentSession` for tenant/hospital (`:214`) → calls
  `DepartmentService.Upsert...(..., session.CurrentTenantId, session.CurrentHospitalId, ...)` (`:231-235`)
  → returns the domain object, which `StandardResponsePlugin` wraps.
- `MyHospital.ServiceInterface/DepartmentService.cs:34-36` — service queries via
  `GetAllByTenantAndHospital()` (tenant+hospital filter), then persists (`AddAsync*`/`UpdateAsync*`).
- `MyHospital.ServiceInterface/BaseService.cs` — helper surface used everywhere: `GetAllByTenant()`
  (`:137-149`), `GetAllByTenant<T>()` (`:153-168`), `GetAllByTenantAndHospital()` (`:204-250`),
  `AddAsync` (`:399-425`, runs `PreProcess` + `CreateUniqueCodeAsync`), `UpdateAsync` (`:349-370`),
  `DeleteAsync` (soft-delete, `:304-317`), `CreateUniqueCodeAsync<T>` (`proc_CodeGeneratorAsync`,
  `:694-734`), `ApplyPaginationAsync<T>` (`:964-994`).

**Response wrapping + error mapping (how a `throw` becomes the FE's `{ Code, Message }`):**
- `MyHospital/StandardResponsePlugin.cs` — global response filter: success (status < 400) → wrap as
  `{ Code = SUCCESS, Message = "Success", Data = dto }` (`:118-126`); an `HttpError` → wrap as
  `{ Code = errorCode, Message, Data = null, ResponseStatus }` (`:76-90`); serialized PascalCase with
  nulls (`:138`). This is the BE side of **Fact A**.
- `MyHospital/Configure.AppHost.cs:318-341` — `ServiceExceptionHandlers`: unwraps `BusinessException`
  (possibly nested) → `HttpError(StatusCode, ErrorCode, Message)` (`:321-325`); `ValidationException`
  /`ArgumentException` → `HttpError(BadRequest, Common.InvalidRequest, …)` (`:328-337`); else default
  500.
- `MyHospital.Utilities/BusinessException.cs` — carries `ErrorCode` + `StatusCode` (`:15`,`:20`); ctor
  defaults to 400 (`:22`); factories `NotFound`→404 (`:32-34`), `Conflict`→409 (`:37-39`),
  `Forbidden`→403 (`:43-45`).
- `MyHospital.Utilities/ErrorCodes.cs` — `public const string` codes shaped `"{MODULE}.{ERROR_TYPE}"`
  (e.g. `Department.NotFound`, `Department.DuplicateCode`, `:355-362`; globals `Success`/`Unauthorized`/
  `Forbidden`, `:11-13`). **The FE's `Code` is exactly one of these constants** — grep the BE for it to
  land on the precise `throw`.

**Runtime observability (where to LOOK server-side):**
- **Request logs DO exist:** `MyHospital/Configure.RequestLogs.cs:13` registers ServiceStack's
  `RequestLogsFeature` with a **`SqliteRequestLogger`**, `EnableResponseTracking`,
  `EnableRequestBodyTracking`, `EnableErrorTracking`; a `RequestLogsHostedService` flushes every ~3s
  (`:23-34`). So failing requests (with body + error) are captured to a SQLite request-log DB and are
  viewable via ServiceStack's `/requestlogs` admin endpoint.
- **`NOT FOUND`: the SQLite DB file path** — no explicit `dbPath` in `Configure.RequestLogs.cs` or
  `appsettings*.json` (ServiceStack default; treat as unconfirmed until checked at runtime).
- **Per-service logging:** services use injected `ILogger<T>` → ASP.NET Core console / configured sink
  (`appsettings.json` `Logging.LogLevel.Default = Information`). Example `ILogger<DepartmentApi>` used
  for import failures (`DepartmentApi.cs:203`, logged at `:311/:350/:389`).
- **DebugContext:** per-request debug payload is attached to the envelope when `Debug.Enabled=true`
  (`StandardResponsePlugin.cs:129`; currently false). This is the BE counterpart to the FE
  `debug-info-panel`.
- **Cheapest BE observability when no console access:** a focused failing NUnit test (below).

**Tenant/hospital scope HARD-FAIL (a "data missing" bug can be a 500, not an empty list):**
- `MyHospital.ServiceInterface/BaseService.cs:159-163` — `GetAllByTenant<T>()` **throws
  `InvalidOperationException`** when `EffectiveTenantId == 0` on a tenant-scoped entity (same in
  `GetAllByTenantAndHospital<T>()`, `:265-272`). It does **not** silently return empty. **Triage:** if
  the FE shows a generic 500 / "Máy chủ đang gặp sự cố" on a list/detail call, suspect a missing
  `CurrentTenantId`/`CurrentHospitalId` in the session (un-scoped session, bad auth) *before* assuming
  the DB is empty.

**Tests (where to write a failing one + how to run):**
- Framework **NUnit** (`MyHospital.Tests/MyHospital.Tests.csproj:15-17`). Self-host integration
  pattern in `MyHospital.Tests/IntegrationTest.cs:8-43` (`AppSelfHostBase` + `JsonServiceClient`).
- Run focused: `dotnet test MyHospital.Tests/MyHospital.Tests.csproj --filter "FullyQualifiedName~<TestClass>"`
  (from `myhospital-be/`). Put a regression test for an L5/L6 root cause here asserting the corrected
  behavior / `ErrorCode`.

**Contract export (= where drift originates):**
- `MyHospital/Configure.AppHost.cs:302-311` — RawHttpHandlers register `/types/typescript-const`
  (`:304-306`) and `/types/typescript-types` (`:309-311`); handlers
  `TypeScriptConstantsHandler.cs` / `TypeScriptTypesHandler.cs`. `TypeScriptGeneratorHostedService`
  (`Configure.AppHost.cs:192`, dev-only) regenerates at startup. **Drift = BE DTO/const changed but FE
  not re-pulled** (`npm run dtos:update && npm run client:generate`); detected on the FE by
  `npx tsc --noEmit` (§L4).

---

## 4. Fast bisection — FE-only vs BE-only vs contract-mismatch

One Network-tab observation usually decides the bisection. Do this **before** deep-diving a layer.

```
Open DevTools → Network, reproduce the action, click the failing/relevant request.

(1) Was a request even sent?
      NO  → FE-only. UI/state never called the adapter, OR a raw fetch/axios bypass.
            → L1/L2, and mh_scan FE-V2/no-axios.
      YES → continue.

(2) Read the RESPONSE BODY (not the HTTP status — Fact A).
      Code === "SUCCESS" and Data is CORRECT
            → FE-only. BE did its job; FE mis-caches/mis-renders/over-filters it.
            → L3 (master-data/IDB) → L2 (RQ invalidation) → L1 (render).
      Code === "SUCCESS" but Data is WRONG / missing fields
            → BE-only (logic) OR contract drift. Go to (3).
      Code !== "SUCCESS"  (HTTP 200 business error)  OR real 4xx/5xx
            → BE-only. The BE rejected/failed. Map Code → ErrorCodes.<Module> → the throw (L5),
              then L6 if it's a data issue.

(3) Does the wire shape match the generated DTO?
      Run `npx tsc --noEmit` (FE) + eyeball Response vs src/lib/dtos/generated-dtos.ts.
      Field FE expects is ABSENT on the wire / type differs
            → CONTRACT MISMATCH (drift). BE changed and FE wasn't regenerated, or vice-versa.
              BE is source of truth: fix BE contract first, then `npm run dtos:update &&
              npm run client:generate`. Never hand-edit the 3 generated files.
      Shapes match but value wrong
            → BE-only logic (L5) → maybe L6.
```

Corollaries:
- **Survives full reload?** → persisted layer (master-data IDB or a `customQueryConfig` query), not a
  normal RQ query. Strongly implies FE cache (L3), not BE.
- **Only after hospital-switch / re-login?** → IDB drop/rescope path (`idb-storage.ts:37-99`).
- **Same payload reproduced in isolation still fails?** → BE-only (L5/L6), removes FE from suspicion.

---

## 5. Evidence to capture at each step (so the fix is provable + a regression test can be written)

Capture as you go; this is what `mh-rca` records in its `evidence_supporting_root_cause` and what the
fix's VERIFY step (and a regression test) will assert against. Save artifacts under
`docs/session-notes/` and screenshots under `docs/testing/screenshots/` (workspace file-org rules).

| Layer | Capture |
|---|---|
| Symptom | Exact steps, expected vs observed, env (slot/worktree, hospital `bvtest3`, user), screenshot. |
| L1 render | Component name + the prop/state value that's wrong vs the data it received; render-count if loop. |
| L2 RQ | The mutation site + its `invalidateQueries` keys (present/absent); whether refetch fires. |
| L3 IDB | The cached row JSON from Application→IndexedDB; `window.__idbLogs.export()`; which failure mode (stale / missing / filtered-out / store-missing); the entity name + key. |
| L4 network | Request payload + **full response body incl. `Code`/`Message`**; HTTP status; `npx tsc --noEmit` output if drift suspected; `ss-id` cookie presence for 401. |
| L5 BE | The `*Api`→`*Service` path + the exact `throw`/branch; the `ErrorCodes.*` constant; any server log line / test output. |
| L6 DB | The query + the actual row(s) incl. `DeletedAt`/`IsActive`/`TenantId`/`HospitalId`/unique-index cols. |

**Regression-test target:** the layer of the root cause dictates where the test goes —
- L1/L2/L3 (FE) → a component/hook test or an `agent-browser`/`progressive-test` E2E reproducing the
  exact UI step (the same harness that found E2E bugs).
- L4 contract → a typecheck + a generated-artifact presence assertion.
- L5/L6 (BE) → a focused **NUnit** test in `MyHospital.Tests` asserting the corrected
  behavior/`ErrorCode` (run command in §3-BE).

---

## 6. Exit — confirmed root cause + verdict (feeds the fix half)

The investigation ends by emitting the SAME verdict set `mh-rca` already produces
(`engine/agents/mh-rca.md`, `engine/skills/bug-fix/SKILL.md` step 3), so nothing downstream changes:

- **`DIRECT_PATCH`** — root cause is small, local, low-risk, high-confidence. Typical: L1 render/dep,
  L2 missing `invalidateQueries`, L3 missing `invalidateMasterDataEntity` or FE-V3 name→Id, a literal
  error code (mh_scan V3). `requires_codex_review: false`.
- **`CODEX_REQUIRED`** — touches data/API/schema/state/business-rule/multi-file/shared behavior.
  Typical: L3 filtering/scope or store-version change, L4 contract change, any L5 business-logic fix,
  L6 write-path fix. `requires_codex_review: true`.
- **`MORE_EVIDENCE`** — the prime-suspect layer's checks were inconclusive (e.g. couldn't read the
  response body, no server log, can't reproduce). State exactly which evidence in §5 is missing. (Maps
  to bug-fix's `NEEDS_MORE_EVIDENCE` gate.)
- **`HUMAN_DECISION`** — L6 "is the data wrong or is the rule wrong?", or a business/product call. Not
  a code fix.

The exit record must name: the **root-cause layer (L1–L6)**, the **failure mode**, the **evidence**
(§5), and the **verdict** — exactly the inputs `mh-rca` writes into its RCA artifact and the FIX-PLAN
consumes.

---

## 7. How this plugs into the existing `bug-fix` workflow (no duplication)

This playbook **is the body of two existing steps** in `engine/skills/bug-fix/SKILL.md` /
`engine/workflows/bug-fix/README.md` — it adds procedure, not new orchestration:

| bug-fix step | What this playbook adds | Reuses (unchanged) |
|---|---|---|
| **2. REPRODUCE** | §2 triage front-door (pick prime-suspect layer) + §4 fast bisection to confirm FE/BE/contract before deep work. | The E2E reproduction path stays **`progressive-test`** (`engine/workflows/progressive-test/WORKFLOW.md`): agent-browser writes `01-bug-packet.json`. BE/API repro = the failing request/test. |
| **3. RCA** | §3 layered playbook (L1–L6: check · how · pos/neg · next) + §5 evidence + §6 verdict. This *is* the "investigate the targeted source" instruction `mh-rca` was missing. | **`mh-rca` agent** does the read-only investigation and writes the RCA artifact + verdict. This doc is the *procedure mh-rca follows*; the agent contract is unchanged. Optional `/impact-analysis` for HIGH-risk. |
| 4–8 (FIX-PLAN → CODEX → FIX → VERIFY) | unchanged. §6's verdict maps 1:1 onto FIX-PLAN's "requires-Codex?" gate; §5's evidence becomes the regression scenario. | **`/mh-fix`** applies the fix in a worktree (allowlist + self-review-diff); VERIFY reruns validation / agent-browser. |

**Reuse, explicitly:**
- **`mh-rca`** (read-only RCA, `Read/Grep/Glob/Bash`) is still the investigator. This playbook should
  live where `mh-rca` (and the bug-fix RCA step) can load it — e.g. referenced from
  `engine/agents/mh-rca.md` "Do → investigate the TARGETED source" and from `bug-fix/README.md` step 3
  — so the agent runs §2→§3→§6 instead of improvising. No new agent.
- **`progressive-test`** remains the only E2E reproduction/retest mechanism (agent-browser via OpenCode
  wrappers). This playbook does not touch browser automation; it consumes `01-bug-packet.json` as L-layer
  evidence and feeds `02-rca-plan.json`.
- **`mh_scan`** (`scripts/mh_scan/`, `scripts/sgconfig/`) is the deterministic detector cited inside
  L3/L4/L5 — the investigator runs it to confirm a bug-class rather than eyeballing.
- The **learning loop** (`bug-fix/SKILL.md` §"Learning loop") is unchanged: when a root cause is a
  recurring class, promote it to the cheapest layer that would have caught it (guard/ESLint/ast-grep →
  `engine/rules/*` → deep-review checklist → `second-brain/`).

### Suggested wiring (proposal, not yet applied — owner decides)
1. Add this file as the canonical "investigation procedure" and reference it from
   `engine/agents/mh-rca.md` (step "Do → investigate the TARGETED source") and
   `engine/workflows/bug-fix/README.md` step 3.
2. Keep it tool-neutral (plain `.md`) like `engine/workflows/deep-review/*` so Codex/opencode RCA can
   follow the same L1–L6 order and emit the same verdict.
3. No code, no new skill, no new agent — purely a procedure that the existing read-only RCA step obeys.
