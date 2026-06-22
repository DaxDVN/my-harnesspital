---
title: "Guard blocks all Migrations/*.cs edits — additive data-backfill needs owner bypass"
date: "2026-06-17"
status: provisional
source: implementation-discovery
scope: backend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/backend
tags: [migration, guard, backfill, ef]
applies_tasks: [fix, implement]
applies_globs: [worktrees/*/be/**/Migrations/*.cs, myhospital-be/**/Migrations/*.cs]
applies_keywords: [migration, backfill, data-migration, guard, bypass, migrationBuilder.Sql]
expires: ""
---

# What

The guard hook BLOCKS every Edit/Write to worktrees/*/be/**/Migrations/*.cs (rule migration-hand-edit), including a legit data-backfill migrationBuilder.Sql() line in an uncommitted, never-deployed migration. EF's canonical data-backfill pattern (scaffold then hand-add .Sql()) therefore cannot be done by an agent without an Owner-Authorized Bypass — surface it to the owner, do NOT silently skip.

# Evidence

- .claude/hooks/myhospital_guard.py rule 'migration-hand-edit'; blocked F-102 backfill in 20260617024136_AddBedClinicalOccupancyTierFkAndNullable.cs

# Why It Matters

An additive NOT NULL DEFAULT column consumed by a new query needs a backfill; if the fix is guard-blocked and silently skipped, the BLOCK-severity data bug ships. Must escalate to owner bypass.

# How To Apply

_See # What above._

# Boundaries

Schema scaffolds SHOULD still be regenerated via dotnet ef migrations add (the block is correct for schema hand-edits); it just over-blocks legitimate data-only .Sql() lines.

# Promotion Recommendation

Promote to: engine/rules/backend
Reason: (fill in before promoting)
