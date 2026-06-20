---
title: "New worktree DB setup defaults to make migrate-data"
date: "2026-06-20"
status: provisional
source: user-correction
scope: workflow:worktree
confidence: high
owner_confirmed: false
proposed_target: main-brain
tags: []
applies_tasks: [worktree-creation, db-setup, migration]
applies_globs: []
applies_keywords: [worktree, migrate-data, PendingModelChangesWarning, sync-db, slot-db]
expires: ""
---

# What

Owner decision: new worktree creation should default to running make migrate-data CONFIRM=yes in the BE worktree.

# Evidence

- _No specific evidence cited._

# Why It Matters

This regenerates EF migrations from the current model and avoids PendingModelChangesWarning caused by stale committed migrations during the older sync-db flow.

# How To Apply

_See # What above._

# Boundaries

Use sync-db only when explicitly requested as the older copy-main-data plus committed-migration fallback. migrate-data may dirty regenerated migration files because that is the intended workflow.

# Promotion Recommendation

Promote to: main-brain
Reason: (fill in before promoting)
