---
title: "Rule Gate: Freshness before diagnosis"
date: "2026-06-22"
status: provisional
source: grouped-generalization
scope: workspace
confidence: high
owner_confirmed: true
proposed_target: engine/rules/quality-gates + worktree setup docs + FE/BE freshness guards
tags: [grouped, freshness, generated-artifacts, runtime-state, worktree, dto, db]
applies_tasks: [fix, implement, review, test, worktree-creation, db-setup]
applies_globs: [worktrees/**, myhospital-fe/**, myhospital-be/**]
applies_keywords: [freshness, stale, dto, client, generated, migrate-data, slot-db, schema, seed, sql, redis, env, node_modules, restart]
expires: ""
---

# Freshness Before Diagnosis

Before blaming source code, prove the runtime inputs are fresh enough for the diagnosis.

## Use When

- FE bug touches API data, generated DTO/client, forms, query params, or stale contract symptoms.
- BE/schema work touches migrations, slot DB, seed data, SQL, or model changes.
- Build/start/test fails after branch/worktree/master changes.
- Browser/API smoke shows missing schema, missing dependency, env/startup failure, or old backend behavior.

## Rule

- Generated contract freshness: if BE DTO/API may affect FE, restart the slot BE, then run DTO/client generation,
  then retry the repro before editing FE.
- DB freshness: if model/schema/migration changed or slot DB shape is suspect, use the approved slot DB refresh
  path such as `make migrate-data`; do not run DB refresh blindly on every start.
- Environment freshness: verify required local env, SQL/Redis/runtime dependencies, and `node_modules` before
  treating startup/build errors as code regressions.
- Seed/data freshness: confirm seed CSV exists/tracked, target table state matches command semantics, and restored
  data did not skip reshaped tables.
- Test environment freshness: full BE test suite needs live SQL; otherwise use targeted runnable subsets and mark
  SQL-dependent tests as environment-skipped.

## Not Enough

This gate does not prove business/data correctness. It only prevents diagnosing against stale/generated/runtime
state. After freshness passes, still apply correctness and verification gates.

## Archive Sources

- [`be-full-test-suite-needs-live-sql`](../_archive/2026-06-17-be-full-test-suite-needs-live-sql-validate-batches-via-the-i.md)
- [`clone-real-server-data`](../_archive/2026-06-17-clone-real-server-data-to-local-dev-dbs.md)
- [`worktree-slot-dbs-sync-from-main`](../_archive/2026-06-17-worktree-slot-dbs-are-sync-from-main-not-ef-migration-manage.md)
- [`seed-table-command-skips-non-empty`](../_archive/2026-06-18-seed-table-command-skips-non-empty-tables-and-gitignore-can.md)
- [`slot-db-may-miss-feature-schema`](../_archive/2026-06-18-slot-db-may-miss-an-entire-feature-schema-not-just-the-lates.md)
- [`fe-bug-fix-needs-be-up-dtosupdate`](../_archive/2026-06-19-fe-bug-fix-needs-be-up-dtosupdate-first-migrations-may-run-f.md)
- [`restart-slot-backend-before-dtos`](../_archive/2026-06-19-restart-slot-backend-before-regenerating-fe-dtos-after-be-co.md)
- [`slot-db-ef-history-drift`](../_archive/2026-06-19-slot-db-ef-migration-history-drift-apply-additive-migration.md)
- [`new-worktree-db-setup-migrate-data`](../_archive/2026-06-20-new-worktree-db-setup-defaults-to-make-migrate-data.md)
- [`directorybuildprops-local-sdk`](../_archive/2026-06-20-directorybuildprops-local-sdk-workaround-must-stay-out-of-gi.md)
- [`slot-infra-recovery`](../_archive/2026-06-20-slot-infra-recovery-after-crash-sql-redis-be-and-resolve-master-instance.md)
- [`worktree-be-env`](../_archive/2026-06-20-worktree-be-env-needs-internal-token-and-bff-bridge-local-co.md)
- [`worktree-node-modules-drift`](../_archive/2026-06-21-worktree-node-modules-drift-when-master-adds-fe-deps.md)
