# Backend Quick Rule Card

Use this before opening the full `engine/rules/backend.md`.

## Always

- Source discovery: CodeGraph in the BE repo first, then bounded exact search.
- Business logic belongs in services, API classes stay thin.
- Tenant/hospital scope is mandatory for tenant/hospital entities.
- Prefer existing `BaseService<T>` helpers and current service patterns before adding new helpers.
- Do not hand-edit EF migrations or generated artifacts.
- No new package/config/solution changes without explicit approval.
- Report actual validation. For BE service/API work, prefer `dotnet build` plus targeted request/test evidence.

## Load Topic Cards

- Service/data/query/scope: `engine/rules/backend/service-data.md`
- API/DTO/auth/error contracts: `engine/rules/backend/contracts-auth.md`
- Migrations/schema/seed/backfill: `engine/rules/backend/migrations.md`
- Validation/test expectations: `engine/rules/backend/validation-tests.md`

Open the full `engine/rules/backend.md` only when these cards conflict with local evidence, the task is high-risk,
or the selected topic cards do not cover the change.
