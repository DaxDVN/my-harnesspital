---
title: "Rule Gate: Correct boundary and data integrity"
date: "2026-06-22"
status: provisional
source: grouped-generalization
scope: workspace
confidence: high
owner_confirmed: true
proposed_target: engine/rules/backend + engine/rules/frontend + deep-review/checklist + scanners
tags: [grouped, correctness, boundary, data-integrity, business-rule]
applies_tasks: [fix, implement, review, test, scaffold]
applies_globs: [worktrees/**, myhospital-be/**, myhospital-fe/**]
applies_keywords: [boundary, correctness, data, migration, backfill, dto, servicestack, tenant, audit, timezone, validation, error, dbcontext, dedup]
expires: ""
---

# Correct Boundary And Data Integrity Gate

Put rules at the boundary where the behavior is actually created, and make data transformations match the real
database/API/business contract.

## Use When

- Touching migrations, backfills, seed SQL, DTOs, validators, services, upsert/deactivate flows, tenant/audit
  scope, permissions, time/date logic, or expected error paths.
- Reviewing suggested "optimization" or "cleanup" around EF, ServiceStack, batch dedup, or shared write paths.

## Rule

- Migration/data changes must preserve historical rows, not only future inserts.
- Audit a migration claim against the full chain and snapshot before accepting it.
- In-memory uniqueness, deactivate-by-absence, and payload merge semantics must match the real persistence model.
- DTO/service contracts must not hide fields through inheritance shadowing or wrong validation target types.
- Business rules belong where the business action occurs, not wherever the UI or earlier workflow happens to pass.
- Shared write paths must preserve tenant/hospital scope and audit stamps.
- Time/day logic must use the business timezone bucket, not accidental UTC/local conversions.
- Expected errors need explicit boundaries; do not let expected empty-state errors become global failure toasts.
- Async/query state must be gated by the actual enable/business condition, not only library status flags.
- Do not parallelize EF work over a shared `DbContext`.

## Why It Generalizes

These notes are all the same failure class: the code compiles but the rule is attached to the wrong layer or the
data shape differs from the real contract.

## Archive Sources

- [`additive-not-null-needs-backfill`](../_archive/2026-06-17-additive-not-null-default-column-consumed-by-a-new-query-nee.md)
- [`guard-blocks-migration-backfill`](../_archive/2026-06-17-guard-blocks-all-migrationscs-edits-additive-data-backfill-n.md)
- [`in-memory-dedup-real-index`](../_archive/2026-06-17-in-memory-batch-dedup-must-match-the-tables-real-unique-inde.md)
- [`servicestack-dto-new-shadowing`](../_archive/2026-06-17-servicestack-re-declaring-an-inherited-dto-property-with-new.md)
- [`shift-on-duty-boundary`](../_archive/2026-06-17-shift-on-duty-enforcement-binds-at-the-service-order-path-no.md)
- [`audit-parallel-ef-unsafe`](../_archive/2026-06-19-audit-parallelize-sequential-ef-queries-with-taskwhenall-is.md)
- [`calendar-day-local-timezone`](../_archive/2026-06-19-calendar-day-business-logic-must-bucket-in-hospital-local-tz.md)
- [`deactivate-by-absence-category-scope`](../_archive/2026-06-19-deactivate-by-absence-over-collapsed-multi-category-payload.md)
- [`guard-data-backfill-bypass`](../_archive/2026-06-19-guard-blocks-data-backfill-migration-edits-needs-owner-bypass.md)
- [`ivalidatableobject-target-object`](../_archive/2026-06-19-ivalidatableobjectvalidate-must-pass-an-object-not-a-stringc.md)
- [`new-baseservice-tenant-audit`](../_archive/2026-06-19-new-baseservice-write-paths-recurringly-bypass-tenant-scope.md)
- [`servicestack-never-redeclare-base`](../_archive/2026-06-19-servicestack-never-re-declare-base-payload-fields-with-new-w.md)
- [`sql-seed-go-batches`](../_archive/2026-06-19-sql-seed-scripts-must-not-use-t-sql-variables-across-go-batc.md)
- [`react-query-enabled-false-pending`](../_archive/2026-06-18-disabled-react-query-enabledfalse-keeps-ispendingtrue-guard.md)
- [`tanstack-auto-reset-data-ref`](../_archive/2026-06-20-tanstack-table-autoreset-plus-unstable-data-ref-infinite-rerender-loop.md)
- [`expected-query-errors-no-toast`](../_archive/2026-06-21-expected-query-errors-latest-x-404-on-empty-must-opt-out-of.md)
