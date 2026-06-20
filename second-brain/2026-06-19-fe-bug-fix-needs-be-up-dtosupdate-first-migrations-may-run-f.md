---
title: "FE bug fix needs BE up + dtos:update first; migrations may run freely if data restorable via make migrate-data"
date: "2026-06-19"
status: provisional
source: user-correction
scope: workspace
confidence: high
owner_confirmed: false
proposed_target: main-brain
tags: [fe-bug, dtos, migration, migrate-data, data-safety, fix-flow]
applies_tasks: [fix, implement, test]
applies_globs: [myhospital-fe/**, worktrees/**, engine/rules/**]
applies_keywords: [FE, bug, dtos:update, migration, migrate-data, backup, restore, schema, slot-db]
expires: ""
---

# What

Two owner rules now in canon + fix-flow assets. (1) FE BUG FIX: before fixing any FE bug, the matching BE must be RUNNING and you MUST run npm run dtos:update (then client:generate if changed) first; re-check repro on fresh DTOs — symptom gone => stale generated artifacts, not FE code. (2) MIGRATIONS: full authority to RUN migrations on a worktree slot DB when a fix needs schema change, BUT current data must be restorable (backup + re-insert). Preferred: make migrate-data (backup-data -> db-clear -> migrate-remake -> migrate-up -> restore-data; CONFIRM=yes non-interactive). Caveat: restore-data SKIPS reshaped tables -> re-seed (make seed-tables) + report what restored. Never the real/shared DB. Hand-EDITING migration files still forbidden (regenerate via EF CLI).

# Evidence

- engine/rules/frontend.md FE bug-fix prerequisite + engine/rules/backend.md Running migrations; myhospital-be/Makefile migrate-data

# Why It Matters

Most FE bugs are stale-contract symptoms; fixing FE against stale DTOs hides the real cause. Migrations were over-blocked; owner authorizes running them as long as data is recoverable, removing a workflow stall while keeping the slot DB safe.

# How To Apply

_See # What above._

# Boundaries

Slot DB only, never real/shared source DB. migrate-data restore skips reshaped tables. Applies to fix-flow (/mh-fix, /bug-fix, bugfix-from-report) + FE work in /mh-implement; wired into AGENTS.md allowed-list, frontend.md, backend.md, mh-fix, bug-fix, mh-implementer, mh-rca, fe-flow.

# Promotion Recommendation

Promote to: main-brain
Reason: (fill in before promoting)
