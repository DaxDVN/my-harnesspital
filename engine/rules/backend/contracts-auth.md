# Backend API, DTO, Auth, And Error Contracts

- Request DTOs should use ServiceStack route/interface markers and generated-client-friendly typed contracts.
- Internal endpoints require project auth/permission attributes unless a nearby approved exception exists.
- Do not introduce `dynamic`, `JObject`, anonymous JSON, or untyped dictionaries in API contract layers.
- Reuse existing permission constants and ErrorCodes before adding new ones.
- Use `BusinessException`/`ErrorCodes` for business validation, not generic exceptions/null not-found behavior.
- FE+BE contract changes require BE build, FE DTO/client regeneration, then FE validation.
