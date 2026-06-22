---
title: "Slot-DB EF migration-history drift: apply additive migration surgically, not via database update"
date: "2026-06-19"
status: provisional
source: conversation
scope: backend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/backend.md
tags: []
applies_tasks: []
applies_globs: []
applies_keywords: []
expires: ""
---

# What

Worktree slot DBs are cloned from real data, so __EFMigrationsHistory is out of sync (only a few rows stamped; most migration .cs files not recorded). 'make migrate-up' (dotnet ef database update) then tries to replay InitialCreate and fails with 'There is already an object named Account' (Err 2714). For an ADDITIVE migration: dotnet ef migrations add (generates file), then apply its columns surgically via 'docker exec mssql-hospital-wt<N> /opt/mssql-tools18/bin/sqlcmd' -> SET QUOTED_IDENTIFIER ON (required, table has filtered index/computed col) + idempotent ALTER TABLE ADD + INSERT the migration id into __EFMigrationsHistory. Non-destructive. make migrate-data (full remake) is the heavier sanctioned alternative but its restore skips reshaped tables.

# Evidence

- _No specific evidence cited._

# Why It Matters

database update cannot be used on these slot DBs; blindly running migrate-data risks reshaped-table data loss. Surgical ALTER+stamp applies one additive migration safely without touching other data or the pre-existing drift.

# How To Apply

_See # What above._

# Boundaries

_No specific boundaries noted._

# Promotion Recommendation

Promote to: engine/rules/backend.md
Reason: (fill in before promoting)
