---
title: "IValidatableObject.Validate must pass an object (not a string/collection) to NestedValidation"
date: "2026-06-19"
status: provisional
source: bug-fix
scope: backend
confidence: high
owner_confirmed: false
proposed_target: deep-review/checklist
tags: [consultation, validation, servicestack, IValidatableObject, backend, 500]
applies_tasks: [review, implement, fix, scaffold]
applies_globs: [**/MyHospital.Apis/**, worktrees/**/be/**]
applies_keywords: [IValidatableObject, ValidateNested, NestedValidation, TargetParameterCountException, Validate]
expires: ""
---

# What

A DTO Validate(ValidationContext) that calls NestedValidation.ValidateNested(<a string or a List<>>, name) crashes the whole request with HTTP 500 'TargetParameterCountException: Parameter count mismatch'. ValidateNested reflects over the value's properties; string.Chars and List<T>.Item are indexer properties whose GetValue(obj) needs an index arg. The == typeof(string) guard does NOT skip them (their PropertyType is char/T). Correct call for validating a request's nested children is NestedValidation.ValidateChildren(this).

# Evidence

- worktrees/ipd-consultation/be MyHospital.Apis/ConsultationApi.cs:104,196,298 → HTTP 500 TargetParameterCountException; NestedValidation.cs:54 reflects over string/List indexer

# Why It Matters

Prevents a class of silent 500s on create/upsert endpoints that look fine until the form actually submits; the error message names no field so it is hard to trace without reproducing.

# How To Apply

_See # What above._

# Boundaries

ValidateNested(<class DTO>, name) is fine (e.g. a nested Handover/Meta object). The bug only triggers when the passed value is a string or a collection. Hardened NestedValidation.cs now skips indexer properties, so the helper is defensive — but call sites should still use ValidateChildren(this).

# Promotion Recommendation

Promote to: deep-review/checklist
Reason: (fill in before promoting)
