---
title: "ServiceStack: never re-declare base-payload fields with 'new' when the service reads the base type"
date: "2026-06-19"
status: provisional
source: harness-review
scope: backend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/backend
tags: []
applies_tasks: [fix, implement, review]
applies_globs: [worktrees/*/be/**, myhospital-be/**]
applies_keywords: [servicestack dto new shadow payload upcast]
expires: ""
---

# What

If a request DTO inherits a base payload AND the service method is typed to the BASE payload, re-declaring fields with 'new' in the derived request makes the JSON deserialize into the DERIVED slots while the service reads the BASE slots (upcast) → those fields are silently null/dropped at runtime. Build passes; bug only shows at runtime. Inherit the fields (no 'new'); put validation attributes on the base payload. Grep for 'public new ' in *Api.cs request DTOs.

# Evidence

- ShiftApi.cs UpdateShiftRequest new Code/Name/... → ShiftService.UpdateAsync(UpdateShiftPayload) reads base null slots (F-012); same pattern latent in ScheduleRuleApi

# Why It Matters

Prevents silent update/create field-drop bugs (rename shift Continue no-op, etc.) that pass build + typecheck.

# How To Apply

_See # What above._

# Boundaries

Only when the service signature is the base payload type; harmless if the service takes the derived type.

# Promotion Recommendation

Promote to: engine/rules/backend
Reason: (fill in before promoting)
