# task-slicing (W8) — vertical slices INTO specs/<module>/10-plan.md

Entry skill: `/task-slicing`. Turns approved design into an implementable, executor-safe plan.

## Reuses (does NOT rebuild)
- The **SDD** `specs/<module>/10-plan.md` + `04-traceability.md` (these ARE the plan artifacts).
- **`/impact-analysis`** for per-slice blast-radius/risk.

## Inputs → Outputs
IN: `specs/<module>/{07-schema,08-api,03-ui,02-requirements,09-test-cases,01-source-audit}`.
OUT: `specs/<module>/10-plan.md` (strategy + slices + task-breakdown + per-task allowlist + per-task validation + dependency-order + rollback) + `04-traceability` update + envelope.

## Executor-overreach guard (feeds W9)
Per-task **file-allowlist** + per-task **validation** + dependency order + a "no vague task" rule → the executor (`/mh-implement` via `incremental-impl`) edits only the allowlist, runs the named validation, and STOPs on plan-mismatch.

## Gate / status
STOP if design ambiguous / `08` API contract incomplete / unresolved `05` question. Scaffold + contract;
slicing-quality UNPROVEN → owner gate. **Needs `specs/<module>/07,08` populated first.**
