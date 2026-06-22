---
title: "FE field/component: survey-then-reuse the canonical, never hand-roll"
date: "2026-06-21"
status: provisional
source: user-correction
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: reject
tags: [fe, reuse, convention, survey-first, field, component]
applies_tasks: [fe, implement, bug-fix, review]
applies_globs: [**/*.tsx]
applies_keywords: [reuse, convention, field, datepicker, number, label, sheet, header]
expires: ""
---

# What

Before writing ANY FE field/component, survey how the system already does it (grep across many instances) and reuse it. MyHospital FE canonical map: date+time = DatePicker(date)+TimeInput24(time) bound to one ISO (nurse-handover pattern, with a time-of-day ref); numbers = masked text+inputMode (components/ui/quantity-input, or DecimalNumberInput maxDecimalPlaces=0 for integers) NEVER input type=number; labels = FormLabel inside FormItem; inpatient patient header = PatientInfoBar+StatusBadge; sheet = modal Sheet + useSheetUnsavedGuard + UnsavedChangesDialog; DecimalNumberInput onChange = field.onChange(v ?? undefined). Non-reuse is the ROOT CAUSE of a whole bug class. If caught not reusing once, audit the WHOLE feature surface, not just that field.

# Evidence

- Owner blamed the vital-signs form repeatedly; EVERY bug traced to hand-rolling instead of reusing: commitFieldChange vs field.onChange, Top vs ODataRequest top, bad invalidateQueries key, variant=link, .IsActive nonexistent, hand-rolled patient header vs PatientInfoBar+StatusBadge, missing useSheetUnsavedGuard, raw label vs FormLabel, native datetime-local vs DatePicker+TimeInput24, raw type=number vs masked input.

# Why It Matters

Hand-rolled controls reinvent value/onChange contracts, prop names, query-key shapes the canonical already gets right, producing crashes, dropped params, wrong invalidation, and drift.

# How To Apply

_See # What above._

# Boundaries

FE worktrees. Exception only with current empirical evidence a canonical cannot apply.

# Promotion Recommendation

Promote to: reject
Reason: (fill in before promoting)
