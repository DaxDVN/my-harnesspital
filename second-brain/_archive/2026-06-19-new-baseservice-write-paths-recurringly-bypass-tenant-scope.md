---
title: "new BaseService write paths recurringly bypass tenant-scope helper + skip audit stamps"
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
applies_keywords: [GetAllByTenantAndHospital, Db.Set, tenant-scope, SetCreatedAudit, SetUpdatedAudit, PreProcess, AddRangeAsync, audit-stamp]
expires: ""
---

# What

In new code on a BaseService subclass, two convention bugs recur together on WRITE paths: (1) raw Db.<Set>.Where(... manual TenantId==.. && HospitalId==..) instead of GetAllByTenantAndHospital<T>() — works now but drifts if scoping logic changes; (2) entity mutations (esp. AddRangeAsync batch inserts + in-place updates) skip PreProcess/SetCreatedAudit/SetUpdatedAudit, leaving Created/Updated audit columns null. The READ path in the same method often uses the helper correctly, making the write-path omission easy to miss.

# Evidence

- vital-signs F-001/F-002/F-003 (round-2) = F-001/F-002/F-003 (round-1, MiMoCode) — same bugs flagged by 2 independent audits; VitalSignsManagementService.cs CorrectVitalSignsAsync/UpsertPatientAllergiesAsync

# Why It Matters

Prevents tenant-scope drift (cross-hospital leak risk) + null audit trail on clinical records; both were missed by the first audit pass and only caught on re-review.

# How To Apply

_See # What above._

# Boundaries

Internal-only entities with no API (e.g. VitalSignsHistory) may legitimately use direct Db access; applies to tenant-scoped entities on BaseService subclasses.

# Promotion Recommendation

Promote to: deep-review/checklist
Reason: (fill in before promoting)
