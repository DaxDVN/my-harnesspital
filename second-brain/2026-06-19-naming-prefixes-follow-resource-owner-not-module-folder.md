---
title: "Naming prefixes follow resource owner, not module folder"
date: "2026-06-19"
status: provisional
source: user-correction
scope: workspace
confidence: high
owner_confirmed: false
proposed_target: engine/rules/frontend
tags: [naming, inpatient, frontend, backend, schema]
applies_tasks: [review, implement, fix]
applies_globs: [worktrees/*/fe/**, worktrees/*/be/**, myhospital-fe/**, myhospital-be/**]
applies_keywords: [inpatient, naming, prefix, schema, model, DTO, component, resource-owner]
expires: ""
---

# What

For FE/BE naming, use prefixes like Inpatient only when the resource has an inpatient-specific lifecycle/API/status/permission; do not add or remove prefixes just because a file lives under an inpatient module folder.

# Evidence

- docs/session-notes/2026-06-19/inpatient-module-screens-fix-bug-noi-tru-fe.md section 8

# Why It Matters

Prevents misleading model/component/schema names and avoids unnecessary BE schema/DTO churn when resource ownership is actually MedicalVisit, Bed, DepartmentTransfer, or pharmacy-specific.

# How To Apply

_See # What above._

# Boundaries

Generated DTOs/constants and persisted table/entity renames require a dedicated compatibility/migration plan; local FE component names can be shorter when folder context is sufficient.

# Promotion Recommendation

Promote to: engine/rules/frontend
Reason: (fill in before promoting)
