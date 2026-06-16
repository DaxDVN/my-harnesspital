# MyHospital Backend Review Rules, Conventions, and Patterns

Purpose: compact backend-only guardrails for CodeRabbit-like review of `myhospital-be`.

Scope: review and implement backend code only. Do not use `myhospital-fe` except when a task explicitly spans BE-FE contract sync after backend changes.

## Technology Stack and Project Shape

Verified from current project files, not assumed:

- Solution: `myhospital-be/MyHospital.sln`.
- Runtime target in current `*.csproj`: `net10.0` for `MyHospital`, `MyHospital.Apis`, `MyHospital.ServiceInterface`, `MyHospital.Utilities`, `Community.OData.Linq`, and tests. `FirebaseAdmin` targets `netstandard2.1`.
- Web framework: ServiceStack `10.0.6`.
- Data: EF Core / SQL Server `10.0.8`, `EFCore.BulkExtensions.SqlServer 10.0.1`.
- Host project: `MyHospital` (`Configure.AppHost.cs`, DI, response wrapping, TypeScript export endpoints).
- API project: `MyHospital.Apis` (ServiceStack request DTOs and thin `*Api : BaseApi` classes).
- Service/data project: `MyHospital.ServiceInterface` (`BaseService<T>`, EF entities under `Models/`, `MyHospitalContext`, services, interfaces, migrations).
- Utilities project: `MyHospital.Utilities` (`BusinessException`, `ErrorCodes`, constants, validation helpers, shared typed DTOs).
- Tests: `MyHospital.Tests` with NUnit.

Current package harness: `myhospital-be/CONVENTIONS.md` is the backend convention source. There is no package-level `myhospital-be/AGENTS.md` in this checkout.

## Source-of-Truth Hierarchy

For backend review, apply this order:

1. Current user/task instruction and explicit affected-file boundaries, but only within hard harness boundaries.
2. Active feature spec/task files if the task names them.
3. `myhospital-be/CONVENTIONS.md` as the canonical backend convention source.
4. Current source code patterns near the touched files.

If a requested change conflicts with `CONVENTIONS.md` or a forbidden backend harness rule, stop instead of inventing a workaround. Existing source deviations are lead-approved legacy unless the task explicitly targets them.
If the current task explicitly conflicts with a `BLOCK`/forbidden rule, use the stop protocol
instead of treating the instruction as an override.

## Severity Model

Use this model before approving risky backend changes.

- `BLOCK`: stop review/implementation. The change violates a hard rule or creates a known data/auth/contract risk.
- `WARN`: continue only with the least risky option and explicit rationale in the review.
- `INFO`: normal convention guidance; enforce unless the immediate local pattern is more specific.

When uncertain between `BLOCK` and `WARN`, treat it as `BLOCK`.

## Mandatory Rules and Forbidden Actions

Block these changes in new backend code:

- Missing tenant/hospital scoping for `TenantBase` or `Base` entities.
- Querying inside loops, per-row lookups, per-item code generation, or batch APIs that call single-item methods with their own database checks.
- More than one query per table per endpoint unless the extra query is a documented legacy/approved pattern.
- New DB transactions, `BeginTransactionAsync`, `IDbContextTransaction`, `IProcessLockService`, or app-level locks.
- Hard-delete of tenant/audited entities (`Db.Remove`) instead of soft-delete.
- Manual migration edits, migration history rewrites, or hand-written generated artifacts.
- Missing `[RequireAuth]` on internal request DTOs, `[AllowAnonymous]` on internal endpoints, custom auth/session bypass, or ad hoc role checks in handlers.
- Generic exceptions or null returns for not-found behavior where the endpoint should throw `BusinessException` + `ErrorCodes`.
- Weak FE-facing contracts: `dynamic`, `JObject`, `Dictionary<string, object>`, anonymous JSON contracts, or untyped settings payloads in DTO/API contract layers.
- New packages, package version changes, `*.csproj`, `.sln`, or config changes without explicit approval.
- Direct `Db.SaveChangesAsync()` paths in new service code when `AddAsync`, `UpdateAsync`, `DeleteAsync`, `FlushAsync`, or batch helpers fit.

Warn on:

- New `FunctionName`, status, setting key, ErrorCodes group, or magic-string-looking literal where an existing constant may apply.
- `IgnoreQueryFilters()`.
- Duplicate checks that do not exactly match database unique-index scope and soft-delete filter.
- Touching legacy direct-save, process-lock, billing, BHYT/insurance, pricing, auth, base service, base entity, or context behavior.
- Skipped focused tests for workflow/state/data-access changes.

## Canonical API Pattern

Request DTOs:

- Name as `<Verb><Resource>Request`; list requests are typically `<Resource>ListsRequest`, `Get<Resource>ListRequest`, or `Query<Resource>Request`.
- Use ServiceStack route/interface markers: `[Route]`, `IGet`/`IPost`/`IPut`/`IDelete`, and `IReturn<T>`.
- New internal DTOs should carry `[RequireAuth(Functions.FunctionNames.<X>, Functions.Actions.<CanY>)]` and `[Tag(Functions.FunctionNames.<X>)]` unless the nearby API has a lead-approved exception.
- Use DataAnnotations for basic validation: `[Required]`, `[Range]`, `[StringLength]`, etc.

API classes:

- Keep `*Api : BaseApi` thin.
- Inject dependencies via `[FromServices] public required I<Resource>Service Service { get; set; }`, not constructor injection.
- Validate request DTOs with `ValidationHelper.Validate(request)` before service calls when the local API pattern does so.
- Throw `new BusinessException(ErrorCodes.<X>.ValidationFailed, result.GetFirstError())` for validation failures.
- Return DTO/entity/list response directly. `StandardResponsePlugin` wraps successful and error responses into `{ Code, Message, Data }`.

References: `MyHospital.Apis/DepartmentApi.cs`, `MyHospital.Apis/CashierApi.cs`, `MyHospital.Apis/InvoiceApi.cs`, `MyHospital.Apis/BaseApi.cs`, `MyHospital/StandardResponsePlugin.cs`.

## Canonical Service Pattern

- Business logic belongs in `*Service : BaseService<T>`, not in API methods.
- Cross-module service calls should go through `I<Resource>Service` interfaces registered by DI/autowire or explicit registration.
- Prefer existing helpers on `BaseService<T>`:
  - `GetAllByTenant()`
  - `GetAllByTenant<T>()`
  - `GetAllByTenantAndHospital()`
  - `GetAllByTenantAndHospital<T>()`
  - `AddAsync`, `UpdateAsync`, `DeleteAsync`, `DeleteRangeAsync`, `FlushAsync`
  - `BatchAddAsync`, `BatchUpdateAsync`
  - `CreateUniqueCodeAsync`
  - `ApplyPaginationAsync`
- Use `CurrentSession.CurrentTenantId`, `CurrentSession.CurrentHospitalId`, and `CurrentSession.UserAuthId` from `BaseService<T>`.

References: `MyHospital.ServiceInterface/BaseService.cs`, `MyHospital.ServiceInterface/DepartmentService.cs`, `MyHospital.ServiceInterface/BillingService.cs`, `MyHospital/Configure.AppHost.cs`.

## Model, Tenant, Soft Delete, and Audit Rules

Base hierarchy:

- `TrackingBase`: `Id`, `CreatedAt/By`, `UpdatedAt/By`, `DeletedAt/By`, `LanguageCode`.
- `TenantBase`: adds `TenantId`.
- `Base`: adds `HospitalId`.

Tenant/hospital scoping:

- `TenantBase` entities require tenant scope.
- `Base` entities require tenant + hospital scope.
- Use `GetAllByTenant*` helpers. They hard-fail when a tenant-scoped query lacks `CurrentTenantId`.
- Do not use raw `Db.<Set>.Where(...)` or `Db.Set<T>()` for tenant entities if it bypasses helper scoping.

Soft delete and audit:

- `MyHospitalContext` applies a global query filter for `TrackingBase.DeletedAt == null`.
- Do not add redundant `.Where(x => x.DeletedAt == null)`.
- Use `DeleteAsync(entity)` / `DeleteRangeAsync` for soft-delete. `SoftDelete<T>` is private in `BaseService<T>`, so callers must not try to call it.
- Do not manually set `CreatedAt`, `CreatedBy`, `UpdatedAt`, `UpdatedBy`, `TenantId`, or `HospitalId` unless following a local force/legacy pattern such as `AddAsyncForce` or explicit background/import logic.
- `SaveChangesAsync` also has a safety net converting hard deletes on `TrackingBase` into soft deletes, but reviewers should still block new hard-delete intent.

References: `MyHospital.ServiceInterface/Models/Base.cs`, `MyHospital.ServiceInterface/Models/MyHospitalContext.cs`, `MyHospital.ServiceInterface/Partial/MyHospitalContext.cs`, `MyHospital.ServiceInterface/BaseService.cs`.

## Auth and Permission Rules

- Use ServiceStack auth plus project `[RequireAuth]`; do not create custom auth providers, sessions, permission checks, or handler-level role gates.
- Verified action constants are exactly: `CanView`, `CanInsert`, `CanUpdate`, `CanDelete`, `CanImport`, `CanExport`, `CanShare`.
- There is no verified `CanApprove` or `CanCreate`; approval-like workflows usually reuse `CanUpdate` or a more specific existing `FunctionName`.
- Reuse existing `Functions.FunctionNames.*` before adding a new permission function.
- If adding a new function/action is unavoidable, require seed/permission update and reviewer rationale.

References: `MyHospital.Utilities/Constants/Functions.cs`, `MyHospital.Apis/DepartmentApi.cs`, `myhospital-be/CONVENTIONS.md`.

## BusinessException and ErrorCodes

- Use `BusinessException.NotFound`, `.Conflict`, `.Forbidden`, or `new BusinessException(code, message)`.
- Error codes must be constants grouped under `ErrorCodes.<Module>.<Reason>`.
- Reuse `ErrorCodes.Common.*` when appropriate.
- Do not throw `new Exception(...)` for business validation/not-found/conflict.
- Do not return `null` from an endpoint as not-found behavior; the API layer should translate missing service results into `BusinessException`.
- `ServiceExceptionHandlers` maps `BusinessException` to `HttpError`; `StandardResponsePlugin` wraps it.

References: `MyHospital.Utilities/BusinessException.cs`, `MyHospital.Utilities/ErrorCodes.cs`, `MyHospital/Configure.AppHost.cs`, `MyHospital/StandardResponsePlugin.cs`.

## OData Listing and Pagination

Canonical list DTO:

- Inherit `ODataRequest`.
- Implement `IGet, IReturn<PagingDataSource<T>>` or a response class derived from `PagingDataSource<T>`.
- Declare `[FilterField(F.X, FilterType.Y)]`.
- Declare `[SortFields(...)]` for allowed sort fields.
- Define nested `static class F` for filter names.

Canonical list handling:

- `var f = request.ParseAllFilters()`.
- Use typed reads: `f.GetString`, `f.GetLong`, `f.GetBool`, `f.GetDate`, `f.GetList`.
- Use `request.ValidatedOrderBy()` for sorting.
- Use `ApplyPaginationAsync(query, request.Skip, request.Top)` in services, or return `{ Count, ListOfObject }` with equivalent count/page semantics.
- Default pagination helper caps `Top` defensively.

Forbidden for new listing APIs:

- `[AutoQueryDb]`.
- Ad hoc query-string-only filter parameters.
- Hard-coded `[FilterField("Name", ...)]` when a nested `F` constant is practical.
- Legacy `ParseStringEquality` for new list endpoints.

References: `MyHospital.Apis/CashierApi.cs`, `MyHospital.Apis/InvoiceApi.cs`, `MyHospital.Apis/ODataHelper/ODataRequest.cs`, `MyHospital.Apis/ODataHelper/QuerySchemaAttributes.cs`, `MyHospital.Apis/ODataHelper/PagingDataSource.cs`, `MyHospital.ServiceInterface/BaseService.cs`.

## Data Access, N+1, and Query Budget

Review for "one query per table per endpoint":

- Load all needed rows with one query per table.
- Use `Contains`/`IN`, then `ToDictionary`, `ToLookup`, or `HashSet` for in-memory lookup.
- Enrich paged results in memory after batch loading related tables.
- Never run database queries inside `foreach`.
- Batch endpoints should validate all rows against preloaded state, then write in one path; they must not call single-item create/update methods when those methods query/generate codes one row at a time.

Good pattern examples:

- `BillingService.GetInvoiceListAsync` pages invoices, batch-loads patients/visits/allocations, then enriches in memory.
- `CommercialInsuranceQueryService.GetGuaranteesAsync` loads paged guarantees, then batch-loads patient/company/billing maps.

Legacy caveat: some existing services still query directly or hit multiple tables repeatedly. Treat those as lead-approved local history unless the task touches them; do not expand the pattern.

References: `MyHospital.ServiceInterface/BillingService.cs`, `MyHospital.ServiceInterface/CommercialInsuranceQueryService.cs`, `myhospital-be/CONVENTIONS.md`.

## Transactions and Locking

Project convention: no new transactions and no new locks.

Required design alternatives:

- Write-order strategy: write the most important parent/state first, then dependents.
- Idempotent operations: rerun should not double-apply effects.
- Derived/computed values at query time instead of duplicate persisted totals when possible.

Legacy exceptions exist, including `IProcessLockService` registration and transaction paths in inventory/prescription areas. Reviewers should warn when a task edits these paths and block any new transaction/lock introduction outside explicit human-approved migration work.

References: `myhospital-be/CONVENTIONS.md`, `MyHospital/Configure.AppHost.cs`, `MyHospital.ServiceInterface/BatchAdjustmentService.cs`, `MyHospital.ServiceInterface/TransferService.cs`, `MyHospital.ServiceInterface/Prescription/PrescriptionHoldService.cs`.

## Constants, Status, Money, and Code Generation

Constants:

- No magic strings/numbers in new business logic.
- Permission functions/actions: `Functions.cs`.
- Error codes: `ErrorCodes.cs`.
- Setting keys: `Commons.SettingKeys` or module setting-key classes.
- Code prefixes: `CodePrefixes.cs` or entity static `CodePrefix`.
- Status/type/mode constants: `MyHospital.Utilities/Constants/<Module>.cs`.
- Filter names: nested `static class F` on request DTOs.

Status:

- Prefer existing PascalCase status constants such as `Pending`, `Approved`, `InProgress`.
- Do not introduce upper snake-case status strings unless an existing exported constant requires it.

Money and quantity:

- For monetary rounding, use `Math.Round`/`decimal.Round` with `MidpointRounding.AwayFromZero`.
- Avoid bare `Math.Round` for money because default banker's rounding can change healthcare/billing totals.
- Quantity rounding should also be explicit; use three decimals where the domain requires quantity precision.

Code generation:

- Entities that need auto codes expose a public static `CodePrefix` or `CodePrefixes`.
- `BaseService.CreateUniqueCodeAsync` invokes `proc_CodeGeneratorAsync`.
- Do not roll custom code generators unless an existing approved module already has one and the task explicitly uses that module.

References: `MyHospital.Utilities/Constants/Functions.cs`, `MyHospital.Utilities/Constants/CodePrefixes.cs`, `MyHospital.ServiceInterface/BaseService.cs`, `MyHospital.ServiceInterface/CodeGeneration/CodePrefixRegistry.cs`, `MyHospital.ServiceInterface/Models/Payment/Invoice.cs`, `MyHospital.ServiceInterface/Pricing/PricingResolver.cs`.

## BE-FE Contract Sync and Type Export

Backend is the source for FE DTO/constants export:

- `/types/typescript-types` exports C# DTO/utility interfaces.
- `/types/typescript-const` exports constants, entity stores, and query schema from `[FilterField]` / `[SortFields]`.
- `Configure.AppHost.cs` registers both raw handlers.
- `TypeScriptGeneratorHostedService` fetches both endpoints in development.

Review rules:

- Every shape the FE needs must be a concrete C# class/record/enum/static constant.
- Avoid `dynamic`, `JObject`, `Dictionary<string, object>`, and `object` fields in FE-facing DTOs.
- JSON settings need a typed class used for deserialize + validation, with setting keys as constants.
- When changing backend DTOs/constants that FE consumes, require BE first, then regenerate FE DTO/client artifacts in the cross-package workflow.

References: `MyHospital/Configure.AppHost.cs`, `MyHospital/Services/TypeScriptTypesHandler.cs`, `MyHospital/Services/TypeScriptConstantsHandler.cs`, `MyHospital/Services/TypeScriptConstantsGenerator.cs`, `myhospital-be/CONVENTIONS.md`.

## Data Access and DI Patterns

- ServiceStack API classes use property injection via `[FromServices]`.
- Service classes use constructor injection.
- `Configure.AppHost.cs` explicitly registers special services and autowires classes that implement an `I<ClassName>` interface.
- If a service does not match `I<ClassName>`, add explicit DI registration rather than relying on autowire.
- Do not introduce repository wrappers for normal EF access; `BaseService<T>` is the repository-like base.

References: `MyHospital/Configure.AppHost.cs`, `MyHospital.Apis/DepartmentApi.cs`, `MyHospital.ServiceInterface/DepartmentService.cs`.

## Migrations and Generated Artifacts

- Do not edit existing migration files or `MyHospitalContextModelSnapshot` manually.
- Do not hand-write migrations; generate new migrations only through EF CLI when model changes require it.
- Existing migration history under `MyHospital.ServiceInterface/Migrations/` currently includes initial create, stored procedures, and model snapshot files.
- Do not modify generated TypeScript output, generated DTO/client artifacts, generated catalogs, `*.csproj`, `.sln`, or config files unless the current task explicitly allows it.
- Schema changes need matching model configuration, unique-index filter, FK delete behavior, and migration review.

Model configuration rules:

- Unique indexes for soft-deletable entities must include a `DeletedAt IS NULL` filter.
- FK delete behavior should be `DeleteBehavior.Restrict` unless existing local configuration proves otherwise.
- Duplicate checks in services must match the database unique-index scope exactly, including `TenantId`, `HospitalId`, nullable dimensions, and the soft-delete filter.

References: `MyHospital.ServiceInterface/Models/MyHospitalContext.cs`, `MyHospital.ServiceInterface/Partial/MyHospitalContext.cs`, `MyHospital.ServiceInterface/Migrations/`.

## Reuse and Discovery Rules

Before proposing backend code changes:

- Search with `rg` / `rg --files`.
- Check `BaseService<T>` for tenant/audit/code/pagination helpers.
- Check `ValidationHelper` for request validation.
- Check `Functions.cs`, `ErrorCodes.cs`, constants folders, and existing module status classes before adding constants.
- Check nearby APIs/services for file shape and method naming.
- For BHYT/insurance/coverage, search `MyHospital.ServiceInterface/Insurance/` and `CommercialInsurance*Service` first; do not re-derive benefit logic.
- For Excel/import/background tasks, mirror the Department import pattern: read bytes and session data before `Task.Run`, then create a fresh DI scope inside.

Discovery limitation from this extraction: `myhospital-be/docs/reuse/reuse-catalog.generated.md` is missing. This is not a blocker, but reviewers should not rely on that optional catalog unless it exists in a later workspace state.

## Validation Expectations

Docs-only backend rule extraction:

- Confirm the Markdown file exists.
- Run focused `rg`/read checks.
- Do not run `dotnet build` or `dotnet test` unless the task changes code or explicitly asks for it.

Backend code changes:

- Build from `myhospital-be/`: `dotnet build MyHospital.sln` or the changed project.
- Run focused NUnit tests when behavior/data access/workflow changes.
- For schema changes, generate migration with `dotnet ef migrations add <Name> --project MyHospital.ServiceInterface --startup-project MyHospital`; never hand-edit migration files.
- Report exact validation commands and failures/residual risk.

## Automated Review Guardrails

Flag as `BLOCK`:

- New endpoint request DTO lacks `[RequireAuth]` or uses a non-existing action like `CanCreate`.
- API method contains business workflow logic that belongs in service.
- Service query uses `Db.<Set>` / `Db.Set<T>()` on `TenantBase`/`Base` entity without helper scoping.
- Query appears inside `foreach` or per-row branch.
- Batch method calls single-item create/update repeatedly.
- New transaction, process lock, or direct app lock.
- New hard delete of tracked tenant entity.
- Business not-found path returns `null` or throws generic exception.
- Listing endpoint uses `ParseStringEquality` instead of declarative `[FilterField]` + `ParseAllFilters`.
- New DTO exposes weak `object`/`dynamic`/`Dictionary<string, object>` contract.
- New unique index omits `DeletedAt IS NULL`.
- New FK uses cascade delete on tenant/audited data.
- Migration/generated artifacts were manually edited.

Flag as `WARN`:

- Existing legacy path is touched and still uses direct `SaveChangesAsync`, `IgnoreQueryFilters`, transactions, locks, or direct `Db` queries.
- New constant/function/error group may duplicate an existing one.
- A duplicate check cannot mirror DB uniqueness exactly.
- Tests are skipped for a non-doc behavior change.
- The code changes billing, BHYT/insurance, cost-price, auth/session, `BaseService`, `TrackingBase` hierarchy, or `MyHospitalContext`.

Flag as `INFO`:

- Naming/style consistency issues around request/service/entity names.
- Thin API and service-boundary hygiene.
- Missing `SortFields` on a list endpoint where sorting is supported.

## Known Legacy Exceptions and How to Treat Them

Do not auto-clean these during unrelated reviews:

- Existing direct `Db.SaveChangesAsync()` calls in services and some APIs.
- Existing transaction/process-lock paths in warehouse/prescription areas.
- Existing direct `Db.Patients`, `Db.Billings`, `Db.Set<T>()`, or `IgnoreQueryFilters()` uses.
- Existing manual `ParseStringEquality` list APIs.
- Existing weak/dynamic contracts in older master-data/settings/dynamic-form paths.
- Existing generic exceptions in older service code.

Reviewer posture: preserve behavior when a task touches a legacy path, flag risk as `WARN`, and only require convention migration when explicitly in scope. For new code, enforce current conventions strictly.

## Open Risks / Human Confirmation Areas

- Stack mismatch: backend harness says `.NET 8`/ServiceStack 8/EF 8, while project files show `.NET 10`/ServiceStack 10/EF 10.
- Some convention prose says use `SoftDelete<T>`, but `BaseService<T>.SoftDelete<T>` is private in current code; caller-safe rule is to use `DeleteAsync` / `DeleteRangeAsync`.
- `CONVENTIONS.md` says all `TenantBase` entities scope by `TenantId + HospitalId`, but `TenantBase` itself only has `TenantId`; apply hospital scope only when the entity has `HospitalId` (`Base`).
- Optional reuse catalog is missing.
- Existing source deviations are not cleanup targets. Ask a human before converting broad legacy patterns.

## Useful Source References

- `AGENTS.md`
- `CLAUDE.md`
- `myhospital-be/CONVENTIONS.md`
- `myhospital-be/MyHospital/Configure.AppHost.cs`
- `myhospital-be/MyHospital/StandardResponsePlugin.cs`
- `myhospital-be/MyHospital/Services/TypeScriptTypesHandler.cs`
- `myhospital-be/MyHospital/Services/TypeScriptConstantsHandler.cs`
- `myhospital-be/MyHospital.Apis/BaseApi.cs`
- `myhospital-be/MyHospital.Apis/DepartmentApi.cs`
- `myhospital-be/MyHospital.Apis/CashierApi.cs`
- `myhospital-be/MyHospital.Apis/InvoiceApi.cs`
- `myhospital-be/MyHospital.Apis/ODataHelper/ODataRequest.cs`
- `myhospital-be/MyHospital.Apis/ODataHelper/QuerySchemaAttributes.cs`
- `myhospital-be/MyHospital.Apis/ODataHelper/PagingDataSource.cs`
- `myhospital-be/MyHospital.ServiceInterface/BaseService.cs`
- `myhospital-be/MyHospital.ServiceInterface/Models/Base.cs`
- `myhospital-be/MyHospital.ServiceInterface/Models/MyHospitalContext.cs`
- `myhospital-be/MyHospital.ServiceInterface/Partial/MyHospitalContext.cs`
- `myhospital-be/MyHospital.ServiceInterface/DepartmentService.cs`
- `myhospital-be/MyHospital.ServiceInterface/BillingService.cs`
- `myhospital-be/MyHospital.ServiceInterface/CommercialInsuranceQueryService.cs`
- `myhospital-be/MyHospital.ServiceInterface/CommercialInsuranceCommandService.cs`
- `myhospital-be/MyHospital.ServiceInterface/CodeGeneration/CodePrefixRegistry.cs`
- `myhospital-be/MyHospital.Utilities/ValidationHelper.cs`
- `myhospital-be/MyHospital.Utilities/BusinessException.cs`
- `myhospital-be/MyHospital.Utilities/ErrorCodes.cs`
- `myhospital-be/MyHospital.Utilities/Constants/Functions.cs`
- `myhospital-be/MyHospital.Utilities/Constants/CodePrefixes.cs`
