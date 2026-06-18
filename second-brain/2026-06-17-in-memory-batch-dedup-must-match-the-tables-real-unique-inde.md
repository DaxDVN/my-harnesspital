---
title: "In-memory batch dedup must match the table's real unique index, else silent data loss"
date: "2026-06-17"
status: provisional
source: review-closeout
scope: backend
confidence: high
owner_confirmed: false
proposed_target: deep-review/checklist
tags: [backend, dedup, unique-index, batch, silent-data-loss, shift]
applies_tasks: [review, implement, fix]
applies_globs: [myhospital-be/**, worktrees/**]
applies_keywords: [dedup, HashSet, batch, unique, index, skip, SkippedCodes, continue]
expires: ""
---

# What

Before adding an in-memory dedup that 'continue'/skips batch rows, confirm the dedup key matches a real UNIQUE index on that table. SHIFT-16 deduped Shift templates on (DepartmentId,RoomId) but the table is unique only on (Tenant,Hospital,Dept,Code) and (...,Name) — so multiple shift templates per dept+room are legitimate, and the dedup silently dropped them (log + SkippedCodes only). True dups were already blocked by Code/Name dedup, so the new key added zero protection and only false-blocked valid rows.

# Evidence

- ShiftService.cs:296-311 SHIFT-16 dedup on (DepartmentId,RoomId) vs UK_Shift_Code/UK_Shift_Name only (MyHospitalContextModelSnapshot.cs:15053-15058)

# Why It Matters

Prevents silent data-loss-by-skip that contradicts schema cardinality; a dedup that doesn't mirror a UK index either does nothing or drops valid records.

# How To Apply

_See # What above._

# Boundaries

Applies to batch create/update paths that skip-on-duplicate. If a UK index does cover the key, dedup is correct. Surfacing a typed SkippedDetail/reason to the user is the min mitigation if silent skip is intended.

# Promotion Recommendation

Promote to: deep-review/checklist
Reason: (fill in before promoting)
