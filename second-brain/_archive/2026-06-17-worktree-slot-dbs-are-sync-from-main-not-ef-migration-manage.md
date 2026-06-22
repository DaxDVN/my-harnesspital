---
title: "Worktree slot DBs are sync-from-main, NOT EF-migration-managed — apply schema via direct DDL, not 'ef database update'"
date: "2026-06-17"
status: provisional
source: bug-fix
scope: backend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/backend
tags: [backend, ef-migration, worktree, dev-db]
applies_tasks: [fix, implement]
applies_globs: [worktrees/**, myhospital-be/**]
applies_keywords: [migration, ef database update, schema, column, slot db, sqlcmd, 2714]
expires: ""
---

# What

Worktree slot DBs (localhost,1434-1437, reset via wt-sync-db from the main DB) have a __EFMigrationsHistory that does NOT match the migration files, and the app does NOT auto-migrate on startup. 'dotnet ef database update' therefore replays from InitialCreate and fails with error 2714. To make a new migration's schema live on a slot DB for testing, apply the column DDL directly (guarded ALTER/CREATE via docker exec sqlcmd, with -I for QUOTED_IDENTIFIER) and keep the generated migration file for the real deploy pipeline.

# Evidence

- ef database update on worktrees/fix-bug-noi-tru/be tried to apply 20260616075932_InitialCreate -> SqlException 2714 (object already exists)

# Why It Matters

Prevents a failed/half-applied ef database update and wasted time when a BE schema change must be live on a worktree slot DB.

# How To Apply

_See # What above._

# Boundaries

Slot DBs only; the main/prod DB is migration-managed and the migration file applies normally there. ALTER on tables with filtered indexes needs sqlcmd -I.

# Promotion Recommendation

Promote to: engine/rules/backend
Reason: (fill in before promoting)
