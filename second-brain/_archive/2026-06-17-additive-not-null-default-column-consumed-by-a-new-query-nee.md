---
title: "Additive NOT NULL DEFAULT column consumed by a new query needs a backfill SQL"
date: "2026-06-17"
status: provisional
source: review-closeout
scope: backend
confidence: high
owner_confirmed: false
proposed_target: deep-review/checklist
tags: [migration, ef, backfill, data-migration, review]
applies_tasks: [review, fix, implement]
applies_globs: [**/Migrations/**, **/*.cs]
applies_keywords: [migration, defaultValue, NOT NULL, backfill, IsClinicalOccupancy]
expires: ""
---

# What

When a migration adds a NOT NULL column with a constant DEFAULT and a NEW query filters/counts on that column, the migration MUST also include migrationBuilder.Sql(...) to backfill existing rows to their correct value. defaultValue is schema-mechanics-safe but semantically wrong: all pre-migration rows get the default, blinding the new query on any upgrade DB. A D9 reviewer checking only schema mechanics will pass it — cross-check the consuming query.

# Evidence

- 20260617024136_AddBedClinicalOccupancyTierFkAndNullable.cs:18 defaultValue:false, no Sql() backfill; consumed at BedStayService.cs:1240,1315 (bed v3 F-102)

# Why It Matters

IsClinicalOccupancy added bit NOT NULL DEFAULT 0 with no backfill; the new one-stay guard + capacity/ratio count filter on it → all pre-migration Patient stays invisible on production upgrade (double-assign, undercount). Masked locally because slot DBs are sync-from-main, not EF-managed, so the migration never runs on dev/test.

# How To Apply

_See # What above._

# Boundaries

N/A for a brand-new column no query depends on yet, or a fresh InitialCreate DB with no existing rows.

# Promotion Recommendation

Promote to: deep-review/checklist
Reason: (fill in before promoting)
