# Backend Service, Data, And Scope

- Put business logic in `*Service : BaseService<T>`, not in API methods.
- Use existing BaseService helpers for tenant/hospital-scoped reads and writes.
- Do not bypass tenant/hospital scope for `TenantBase` or `Base` entities.
- Avoid queries in loops and batch APIs that call single-row methods with their own database checks.
- Use soft-delete paths for tenant/audited entities; do not introduce hard-delete intent.
- Keep query budget explicit when touching shared/listing endpoints.
