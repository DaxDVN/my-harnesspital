---
name: mh-scaffold
description: Emit CANONICAL MyHospital code patterns (BE + FE) — copy-paste-ready templates for BE listing/service/error/detail endpoints AND FE module skeleton, list page, form sheet, and adapter. Prevents convention violations at the source (BE V3/V4/V8; FE dead-dtos-import V1, raw fetch V2, master-data name-compare V3, form-without-resolver V4). Replaces the broken `npm run create:module`/`create:page`. Trigger on "scaffold new endpoint/service/listing/error path", "new BE API", "scaffold module/page/list/form", "new FE page", "/mh-scaffold".
---

# mh-scaffold — canonical MyHospital BE pattern emitter

Emits copy-paste-ready templates anchored to **live exemplars** (verified file:line). Each template
has a DO/DON'T block cross-referenced to the audit violation it prevents.

## Boundary — scaffold vs implement vs fix
- **`/mh-scaffold` (this)** — emit ONE canonical pattern to paste (a single endpoint / service / error-path / module / list / form / adapter). No orchestration, no reuse-scan, no DoD gate. Use when you need the *correct shape* for one new thing, or start a file from scratch.
- **`/mh-implement`** — build/extend a whole **feature** end-to-end (worktree → reuse-discovery → convention-contract → code → DoD gate → self-review-diff). It **calls this skill** at B3 when it needs a fresh skeleton.
- **`/mh-fix`** — fix a known **bug** (repro-first, minimal blast radius), not build new.

> Rule of thumb: *one pattern to paste → scaffold · a feature to build → implement · a bug to fix → fix.*

> **Safety**: this skill emits patterns for you to place inside a worktree
> (`worktrees/<slug>/be`). It never edits `myhospital-be/` directly — that is a
> hard `BLOCK` in AGENTS.md.

After placing generated code in your worktree file, run:

```
python scripts/mh_scan --scope <yourfile> --format summary
```

---

## How to use this skill

Tell Claude which template you need (one or more):

1. **listing-endpoint** — paginated GET with `[FilterField]` + `ParseAllFilters`
2. **service** — `XService : BaseService<T>, IXService` + DI registration
3. **error-path** — add a grouped constant in `ErrorCodes.cs` then throw it
4. **detail-endpoint** — single-record GET with not-found guard

You can combine: "scaffold listing-endpoint + service for Appointment".

---

## Template 1 — listing-endpoint

> Prevents **V4** (44 % of listing endpoints still use `ParseStringEquality` directly).
> Exemplar: `myhospital-be/MyHospital.Apis/InvoiceApi.cs:22-53` (InvoiceApi)
> and `myhospital-be/MyHospital.Apis/CashierApi.cs:18-33` (CashierApi).

### DO — declarative pattern

```csharp
// ─── File: MyHospital.Apis/XyzApi.cs ───────────────────────────────────────

using Microsoft.AspNetCore.Mvc;
using MyHospital.Apis.Helpers;
using MyHospital.ServiceInterface.Attributes;
using MyHospital.ServiceInterface.Interfaces;
using MyHospital.Utilities;
using MyHospital.Utilities.Constants;
using ServiceStack;
using F = MyHospital.Apis.GetXyzListRequest.F;

namespace MyHospital.Apis;

// ── Request DTO ─────────────────────────────────────────────────────────────
// One [FilterField] attribute per filterable field.
// FilterType options: String | Number | Date | Boolean | Enum (+ enumSource)
[FilterField(F.Q,          FilterType.String)]
[FilterField(F.Status,     FilterType.Enum, "Statuses.Xyz")]     // optional
[FilterField(F.DateFrom,   FilterType.Date)]                     // optional
[FilterField(F.DateTo,     FilterType.Date)]                     // optional
[SortFields(nameof(XyzEntity.CreatedAt), nameof(XyzEntity.Name))] // optional
[ServiceStack.Route("/xyz", "GET")]
[RequireAuth(Functions.FunctionNames.XyzManagement, Functions.Actions.CanView)]
[Tag(Functions.FunctionNames.XyzManagement)]
public class GetXyzListRequest : ODataRequest, IGet, IReturn<PagingDataSource<XyzListItem>>
{
    /// <summary>Constant field names — the single source of truth for filter keys.</summary>
    public static class F
    {
        public const string Q        = "q";
        public const string Status   = "Status";
        public const string DateFrom = "DateFrom";
        public const string DateTo   = "DateTo";
    }
}

// ── Api handler ─────────────────────────────────────────────────────────────
// Thin: no Db access here. All data access goes in IXyzService.
public class XyzApi : BaseApi
{
    [FromServices] public required IXyzService XyzService { get; set; }

    public async Task<PagingDataSource<XyzListItem>> Get(GetXyzListRequest request)
    {
        var f = request.ParseAllFilters();   // ← single declarative parse call

        var (count, items) = await XyzService.GetListAsync(
            q:        f.GetString(F.Q),
            statuses: f.GetList(F.Status),
            dateFrom: f.GetDate(F.DateFrom)?.StartDate,
            dateTo:   f.GetDate(F.DateTo)?.EndDate,
            orderBy:  request.ValidatedOrderBy(),
            skip:     request.Skip,
            top:      request.Top);

        return new PagingDataSource<XyzListItem>
        {
            Count        = count,
            ListOfObject = items,
        };
    }
}
```

### DON'T — legacy manual parsing (V4)

```csharp
// BAD — calls ParseStringEquality / ParseContains individually per field.
// This pattern exists in ~44 % of listing endpoints (CTApi, MRIApi, LabTestApi…).
// Do NOT copy it for new endpoints.
var q      = request.ParseStringEquality("q");
var status = request.ParseStringEquality("Status");
var date   = request.ParseStringEquality("DateFrom");
```

**Rule**: every new listing endpoint MUST use `[FilterField]` attributes on the DTO
plus a single `request.ParseAllFilters()` call in the handler. Legacy manual calls
are permitted only when touching existing files that already use them — do not
introduce them in new code.

**Verify**: `python scripts/mh_scan --scope XyzApi.cs --format summary`

---

## Template 2 — service

> Prevents **V7** gap (BedService has no `IBedService` interface; cross-module callers bind to
> concrete class — `Configure.AppHost.cs:94`). New cross-module services MUST have an interface.
> Exemplar: `myhospital-be/MyHospital.ServiceInterface/PatientService.cs:14`
> and `myhospital-be/MyHospital.ServiceInterface/BillingService.cs:16`.

### DO — service + interface + DI registration

```csharp
// ─── File: MyHospital.ServiceInterface/Interfaces/IXyzService.cs ────────────

namespace MyHospital.ServiceInterface.Interfaces;

/// <summary>
/// Required when this service is injected by any OTHER module or Api class.
/// (If truly package-internal only, the interface is optional — see note below.)
/// </summary>
public interface IXyzService
{
    Task<(int Count, List<XyzListItem> Items)> GetListAsync(
        string? q, List<string>? statuses,
        DateTime? dateFrom, DateTime? dateTo,
        string? orderBy, int? skip, int? top);

    Task<XyzEntity?> GetByIdAsync(long id);

    // Add mutation methods as needed
}
```

```csharp
// ─── File: MyHospital.ServiceInterface/XyzService.cs ────────────────────────

using Microsoft.EntityFrameworkCore;
using MyHospital.ServiceInterface.Interfaces;
using MyHospital.ServiceInterface.Models;
using MyHospital.Utilities;

namespace MyHospital.ServiceInterface;

public class XyzService : BaseService<XyzEntity>, IXyzService
{
    // Inject extra dependencies alongside MyHospitalContext.
    // Pass db to base; DO NOT store db in a local field — use this.Db.
    public XyzService(MyHospitalContext db) : base(db) { }

    // ── internal-only constructor (testing only) ──────────────────────────
    internal XyzService(
        MyHospitalContext db,
        CustomCredential.CustomUserSession session) : base(db, session) { }

    public async Task<(int Count, List<XyzListItem> Items)> GetListAsync(
        string? q, List<string>? statuses,
        DateTime? dateFrom, DateTime? dateTo,
        string? orderBy, int? skip, int? top)
    {
        // GetAllByTenantAndHospital() applies TenantId + HospitalId filters automatically
        // (BaseService.cs:204). Never add .Where(x => x.TenantId == ...) yourself.
        var query = GetAllByTenantAndHospital()
            .AsNoTracking();

        if (!string.IsNullOrWhiteSpace(q))
            query = query.Where(x => x.Name.Contains(q));

        if (statuses?.Count > 0)
            query = query.Where(x => statuses.Contains(x.Status));

        if (dateFrom.HasValue)
            query = query.Where(x => x.CreatedAt >= dateFrom.Value);

        if (dateTo.HasValue)
            query = query.Where(x => x.CreatedAt <= dateTo.Value);

        // orderBy string comes from request.ValidatedOrderBy() (already whitelist-validated)
        if (!string.IsNullOrEmpty(orderBy))
        {
            // Apply EF ordering from validated string; for complex sort use a switch.
            // Example: query = query.OrderBy(x => x.CreatedAt);
        }

        // ApplyPaginationAsync: clamps top (default 100, max 500) — BaseService.cs:964
        var (count, items) = await ApplyPaginationAsync(query, skip, top);

        return (count, items.Select(MapToListItem).ToList());
    }

    public async Task<XyzEntity?> GetByIdAsync(long id)
    {
        return await GetAllByTenantAndHospital()
            .AsNoTracking()
            .FirstOrDefaultAsync(x => x.Id == id);
    }

    private static XyzListItem MapToListItem(XyzEntity e) => new()
    {
        Id   = e.Id,
        Name = e.Name,
        // …
    };
}
```

```csharp
// ─── File: MyHospital/Configure.AppHost.cs (find the services block) ────────
// Add ONE line in ConfigureServices / the IHostingStartup ConfigureServices method:

services.AddScoped<IXyzService, XyzService>();

// WRONG (V7 gap): services.AddScoped<XyzService>();
// A concrete-only registration means cross-module callers can't rely on the interface.
// Use concrete-only ONLY for purely internal services with no cross-module callers.
```

**When is an interface required?** If ANY other Api or Service outside `XyzService.cs`
will inject this service — it MUST have `IXyzService`. If it is 100 % internal to one
file (e.g., a private strategy helper), concrete-only is acceptable.

**Verify**: `python scripts/mh_scan --scope XyzService.cs --format summary`

---

## Template 3 — error-path

> Prevents **V3** (12 literal-string `throw new BusinessException("SOME.LITERAL", ...)` calls
> bypass the FE i18n contract — `ClaudeAnalyzeService.cs:30,34`, `PrescriptionHoldService.cs:186+`).
> Exemplar: `myhospital-be/MyHospital.Utilities/ErrorCodes.cs:1-28` (format + group pattern).

### Step 1 — add a group in ErrorCodes.cs

```csharp
// ─── File: MyHospital.Utilities/ErrorCodes.cs ───────────────────────────────
// Append a new static class inside ErrorCodes. Format: MODULE.ERROR_TYPE (SCREAMING_SNAKE).
// Client uses these as i18n keys — never change a value once the FE ships it.

public static class ErrorCodes
{
    // … existing groups …

    // ── Xyz ─────────────────────────────────────────────────────────────
    public static class Xyz
    {
        public const string NotFound       = "XYZ.NOT_FOUND";
        public const string InvalidStatus  = "XYZ.INVALID_STATUS";
        public const string DuplicateName  = "XYZ.DUPLICATE_NAME";
        // Add only codes that map to a real FE-visible user-facing error.
    }
}
```

### Step 2 — throw it in service / handler code

```csharp
// DO — constant reference, never a string literal
throw new BusinessException(ErrorCodes.Xyz.NotFound, "Không tìm thấy Xyz");

// Also available (static factory, same result):
throw BusinessException.NotFound(ErrorCodes.Xyz.NotFound, $"Xyz id={request.Id} not found");
```

### DON'T — string literal (V3)

```csharp
// BAD — string literal bypasses the FE contract and is not exported by /types/typescript-const.
throw new BusinessException("XYZ.NOT_FOUND", "...");           // ← literal string
throw new BusinessException("XyzNotFound", "...");             // ← camelCase, wrong format
throw new BusinessException("PINotFound", "...");              // ← real example from audit
```

**Rule**: every `new BusinessException(...)` MUST pass `ErrorCodes.<Group>.<Constant>` as the
first argument — never a string literal. The constant MUST exist in `ErrorCodes.cs`.

**Verify**: `python scripts/mh_scan --scope XyzService.cs --format summary`

---

## Template 4 — detail-endpoint

> Prevents **V14** (detail handlers returning `null` instead of throwing — `LabTestApi.cs:335`,
> `InpatientAdmissionOrderApi.cs:160,165`).
> Exemplar: `myhospital-be/MyHospital.Apis/InvoiceApi.cs:103-107` (InvoiceApi detail).

```csharp
// ─── File: MyHospital.Apis/XyzApi.cs (add to the same Api class) ────────────

[ServiceStack.Route("/xyz/{Id}", "GET")]
[RequireAuth(Functions.FunctionNames.XyzManagement, Functions.Actions.CanView)]
[Tag(Functions.FunctionNames.XyzManagement)]
public class GetXyzDetailRequest : IGet, IReturn<XyzDetailResponse>
{
    public long Id { get; set; }
}

// … inside XyzApi class …

public async Task<XyzDetailResponse> Get(GetXyzDetailRequest request)
{
    var entity = await XyzService.GetByIdAsync(request.Id);

    // DO: throw BusinessException.NotFound on null — never return null from a detail handler
    if (entity == null)
        throw new BusinessException(ErrorCodes.Xyz.NotFound, $"Xyz với Id={request.Id} không tồn tại");

    return MapToDetailResponse(entity);
}

private static XyzDetailResponse MapToDetailResponse(XyzEntity e) => new()
{
    Id   = e.Id,
    Name = e.Name,
    // …
};
```

### DON'T — return null (V14)

```csharp
// BAD — ServiceStack wraps null in a 200 OK response; FE cannot distinguish "not found"
// from "empty result". Real examples: LabTestApi.cs:335, InpatientAdmissionOrderApi.cs:160.
var result = await XyzService.GetByIdAsync(request.Id);
return result;            // ← returns null silently

// ALSO BAD — null! cast suppresses compiler warning but still returns null at runtime
return result ?? null!;
```

**Verify**: `python scripts/mh_scan --scope XyzApi.cs --format summary`

---

## Quick reference — action constants and entity CodePrefix

**Actions** (Functions.cs:312-318) — use exactly these names with `[RequireAuth]`:

| Action | Constant |
|---|---|
| Read / list / detail | `Functions.Actions.CanView` |
| Create / insert | `Functions.Actions.CanInsert` — NOT `CanCreate` (audit D4) |
| Update / edit | `Functions.Actions.CanUpdate` |
| Delete | `Functions.Actions.CanDelete` |
| Import (bulk upload) | `Functions.Actions.CanImport` |
| Export (download) | `Functions.Actions.CanExport` |

There is no `CanCreate`, no `CanApprove` in `Functions.Actions` — audit D4 confirmed these do NOT exist.

**Entity CodePrefix** (live values from `static CodePrefix` on each entity model):

| Module | Prefix |
|---|---|
| MedicalVisit | `MV` |
| MedicalVisitClinicalService | `CS` |
| MedicalVisitDiagnosticImagingService | `DI` |
| Billing | `BI` |
| Invoice | `IV` |
| Patient | `PT` |
| LabTestSample | `LS` / LabTestSpecimen `LP` |
| RetailOrder | `RS` |
| MedicalRecord (EMR) | `EMR` |
| DepartmentTransferRequest | `CK` |

These live as `public static string CodePrefix = "XX"` on the entity class, not in a central `CodePrefixes.cs`.
Use `CreateUniqueCodeAsync(entity)` (BaseService.cs:702) — never generate codes manually (audit V15).

---

# FE templates (React) — canonical MyHospital FE shapes

> Anchored to the **warehouse** module — but warehouse is a PARTIAL exemplar (FE audit §4):
> copy its data/routing/table/form patterns, NOT its monolithic 600-line pages / `useState`-only
> context / inline schema. Canon: `engine/rules/frontend.md`.
> Place code in `worktrees/<slug>/fe`, then `python scripts/mh_scan --root worktrees/<slug>/fe --scope <file> --format summary`.

## FE-1 — module skeleton (replaces broken `npm run create:module`/`create:page`, audit V9)

```text
src/modules/<module>/
  adapters/<module>-adapter.ts   # singleton: class X extends GeneratedApiClient { constructor(){ super(); } } ; export const xAdapter = new X()
  forms/<feature>-schema.ts      # get<Feature>FormSchema(t?) => z.object({...})  (FACTORY, not inline in the page)
  pages/<feature>/<feature>-list-page.tsx           # thin wrapper (Container)
  pages/<feature>/components/<feature>-list-content.tsx  # logic here — SPLIT, not a 600-line monolith
  context/<module>-context.tsx   # ONLY for cross-component coordination (selection/gate); data lives in RQ hooks, NOT here
  lib/models.ts                  # only if FE-extension fields are needed; else import DTOs from '@/lib/dtos/generated-dtos'
  <module>-routing.tsx           # lazy + Suspense(ContentLoader) + LayoutSelector (+ Provider if context exists)
  index.ts
```
❌ never `import … from '@/lib/dtos/dtos'` — dead path, real one is `@/lib/dtos/generated-dtos` (FE-V1, build-breaking).

## FE-2 — list page (EnhancedDataGrid + useMasterData)
Exemplar `src/modules/warehouse/pages/inventory/inventory-list-page.tsx` (but SPLIT wrapper/content):
- Reference data: `const { data, isLoading } = useMasterData(['<Entity>'])` — never a raw query for dropdown/reference lists.
- Columns: `useMemo<ColumnDef<T>[]>(() => […], [intl, …])`; Table: `useReactTable({ columns, data, getCoreRowModel: getCoreRowModel() })` → `<EnhancedDataGrid table={table} recordCount=… isLoading=… toolbar={…} />`.
- Mutations: `adapter.useXxx({ successMessage, invalidateQueries: [['Get<Entity>Requests'], ['GetMasterDataRequests']], onSuccess })` **plus** `invalidateMasterDataEntity('<Entity>')` (both halves).
- Reference by Id: `find(x => String(x.Id) === value)`. ❌ no name/code compare like `=== 'kinh'` (FE-V3) — use `IsDefault`/flags.
- ❌ no raw `<table>` for admin lists; ❌ no `fetch()`/axios in UI (FE-V2).

## FE-3 — form sheet (RHF + zod factory)
Exemplar `src/modules/warehouse/pages/inventory/inventory-form-sheet.tsx` (but put the schema in `forms/`, not inline):
- `forms/<feature>-schema.ts`: `export const get<Feature>FormSchema = (t?) => z.object({…}); export type <Feature>FormValues = z.infer<ReturnType<typeof get<Feature>FormSchema>>;`
- `const form = useForm<<Feature>FormValues>({ resolver: zodResolver(get<Feature>FormSchema(t)) })` — **resolver REQUIRED** (FE-V4: imaging forms shipped without it).
- Create/edit in `<Sheet>`; destructive confirm in `<AlertDialog>`; reset on open/identity change; unsaved-change guard.
- Status → `StatusBadge` + `STATUS_REGISTRY`; permission → `useUserPermissions().can(fn, action)`; i18n → `useIntl`/`useTranslation`.

## FE-4 — adapter (singleton)
```ts
import { GeneratedApiClient } from '@/lib/server/generated-api-client';
class <Module>Adapter extends GeneratedApiClient { constructor() { super(); } }
export const <module>Adapter = new <Module>Adapter();
```
Use inherited generated hooks (`adapter.useGet…`, `adapter.useCreate…`); add a custom method only for real business logic. ❌ no `fetch`/`axios`/manual `JsonServiceClient`/bearer — auth is cookie `ss-id` already (FE-V2).

**Verify any FE file**: `python scripts/mh_scan --root worktrees/<slug>/fe --scope <file> --format summary`

---

## Safety

This skill emits template code for the user to paste into a worktree file
(`worktrees/<slug>/be` or `worktrees/<slug>/fe`). It never edits `myhospital-be/` or
`myhospital-fe/` directly — both are main branches, zero code edits ever (AGENTS.md hard BLOCK).

Convention source of truth: `engine/rules/backend.md` (BE),
`engine/rules/frontend.md` (FE).
Audit evidence: `velvet/notes/myhospital-be-conventions-audit-2026-06-15.md` (BE),
`velvet/notes/myhospital-fe-convention-audit-2026-06-15.md` (FE).
