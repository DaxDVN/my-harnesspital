---
title: "ServiceStack: re-declaring an inherited DTO property with 'new' silently drops it when the service reads via the BASE type"
date: "2026-06-17"
status: provisional
source: bug-fix
scope: backend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/backend
tags: [backend, servicestack, dto, inheritance, shadowing]
applies_tasks: [fix, implement, review]
applies_globs: [myhospital-be/**, worktrees/**]
applies_keywords: [servicestack, DTO, new, shadow, base, property, confirm flag, deserialize]
expires: ""
---

# What

In a ServiceStack request DTO inheriting a payload base, re-declaring a base property with 'new' (C# shadowing) makes TWO properties. Deserialization sets the DERIVED one (runtime type = the request), but if the service method takes the BASE type and reads via direct typed access (payload.X), it reads the never-set BASE prop -> value silently lost. Reflection merges (PopulateWithNonDefaultValues) use the runtime type so they still work, which MASKS the bug — only direct typed reads break, and it compiles fine. Fix: don't 'new'-shadow an inherited property the service reads by base-typed direct access; inherit it (for a plain flag, don't re-declare at all).

# Evidence

- ShiftApi.cs UpdateShiftRequest:103 'public new bool ConfirmAffectedSlots' shadowed UpdateShiftPayload.ConfirmAffectedSlots; UpdateAsync(UpdateShiftPayload payload) read the base prop (always false) -> eternal 400 SHIFT.AFFECTED_SLOTS_REQUIRE_CONFIRM (SHIFT-18)

# Why It Matters

Prevents a class of silent 'flag never takes effect' bugs (confirm/force flags) where FE sends the value, deserialization binds it to the shadow, but the service reads the unset base prop.

# How To Apply

_See # What above._

# Boundaries

Only bites when (a) the DTO uses 'new' to shadow an inherited prop AND (b) the service reads it via a base-typed param with direct access (not reflection). 'new' + validation attrs on fields merged via reflection is fine.

# Promotion Recommendation

Promote to: engine/rules/backend
Reason: (fill in before promoting)
