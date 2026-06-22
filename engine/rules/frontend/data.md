# Frontend Data, Query, And Cache

- Server state belongs in generated adapter hooks and TanStack Query patterns already used by the module.
- Reference/master data should use `useMasterData(...)` when the entity is available there.
- Mutations that affect list/master data need the project invalidation pair: TanStack query invalidation plus master-data invalidation when applicable.
- Avoid per-row API calls and ad hoc reference-data fetching.
- Treat disabled queries carefully: `enabled: false` can still leave misleading loading state depending on wrapper usage.
- Do not compute authoritative money, stock, billing, insurance, posted, or balance totals in FE.
