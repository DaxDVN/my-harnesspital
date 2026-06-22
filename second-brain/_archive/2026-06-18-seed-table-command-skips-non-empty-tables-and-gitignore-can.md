---
title: "Seed table command skips non-empty tables and gitignore can hide seed CSVs"
date: "2026-06-18"
status: provisional
source: implementation-discovery
scope: backend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/backend
tags: [seed, database, csv, gitignore]
applies_tasks: [fix, implement, test]
applies_globs: [worktrees/**/be/MyHospital.ServiceInterface/SeedData/**, myhospital-be/MyHospital.ServiceInterface/SeedData/**]
applies_keywords: [seed, csv, slot, db, table-specific, non-empty, gitignore]
expires: ""
---

# What

The CSV seed command inserts a table only when that table is empty; table-specific seed does not append rows to non-empty tables. Also verify gitignore before assuming a new seed CSV will be tracked.

# Evidence

- worktrees/fix-bug-noi-tru/be/MyHospital.ServiceInterface/Commands/SeedMasterDataCommand.cs: existingCount > 0 returns 0; .gitignore ignores local/ShiftAssignment.csv

# Why It Matters

Prevents false confidence when preparing deterministic fixtures for a live slot DB and prevents losing ignored seed files.

# How To Apply

_See # What above._

# Boundaries

Applies to MyHospital CSV seed loader; direct SQL append scripts have different behavior.

# Promotion Recommendation

Promote to: engine/rules/backend
Reason: (fill in before promoting)
