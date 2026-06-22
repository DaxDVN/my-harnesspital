---
title: "deactivate-by-absence over collapsed multi-category payload drops untouched categories"
date: "2026-06-19"
status: provisional
source: review-closeout
scope: backend
confidence: high
owner_confirmed: false
proposed_target: deep-review/checklist
tags: []
applies_tasks: [fix, review, implement]
applies_globs: [myhospital-be/**, worktrees/*/be/**]
applies_keywords: [allergy, deactivate, IsActive, category, upsert, null-vs-empty, deactivate-by-absence]
expires: ""
---

# What

When a request carries several independently-nullable category lists and BE collapses them into ONE list then deactivates every existing active row whose id is absent from the combined list, editing ONE category (others sent null=untouched) wrongly DEACTIVATES the untouched categories. Root: null(=do-not-touch) vs [](=clear) intent lost after merge. FIX: keep per-category presence — only deactivate within categories whose request field is non-null. Prefer explicit per-category touched flags in the DTO->service contract over sentinel rows.

# Evidence

- worktrees/vital-signs F-003; VitalSignsManagementService.cs UpsertPatientAllergiesAsync + MedicalVisitApi.cs BuildPatientAllergies

# Why It Matters

Prevents silent clinical data loss (active drug allergy deactivated by a food-allergy-only edit).

# How To Apply

_See # What above._

# Boundaries

Only applies to merge/upsert paths using deactivate-by-absence across multiple categories; single-category or full-replace payloads unaffected.

# Promotion Recommendation

Promote to: deep-review/checklist
Reason: (fill in before promoting)
