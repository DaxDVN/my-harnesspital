---
title: "Slot DB may miss an entire feature schema, not just the latest migration"
date: "2026-06-18"
status: provisional
source: bug-fix
scope: workspace
confidence: high
owner_confirmed: false
proposed_target: engine/rules/backend
tags: [backend, worktree, sqlserver, migration, validation]
applies_tasks: [fix, review, implement, test]
applies_globs: [worktrees/**/be/**]
applies_keywords: [slot-db, schema, migration, browser-smoke, consultation, sqlcmd]
expires: ""
---

# What

Before browser/API smoke for a feature worktree that added migrations, verify the slot DB has the feature's baseline tables. If the whole module schema is absent, applying only the newest additive DDL is insufficient; run the module seed/schema bootstrap or sync the DB from a baseline that includes those migrations.

# Evidence

- docker exec mssql-hospital-wt2 sqlcmd: INFORMATION_SCHEMA.TABLES LIKE '%Consultation%' returned 0 rows while the worktree app exposed consultation DTOs

# Why It Matters

Prevents wasting time on DDL for one migration and then misclassifying browser smoke failures as code bugs when the slot DB lacks all feature tables.

# How To Apply

_See # What above._

# Boundaries

Only applies to worktree slot databases; production/main migration pipeline should still use generated EF migrations.

# Promotion Recommendation

Promote to: engine/rules/backend
Reason: (fill in before promoting)
