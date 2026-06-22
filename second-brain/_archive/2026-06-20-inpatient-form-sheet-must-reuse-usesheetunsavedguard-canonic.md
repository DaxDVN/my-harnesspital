---
title: "Inpatient form Sheet must reuse useSheetUnsavedGuard + canonical primitives"
date: "2026-06-20"
status: provisional
source: user-correction
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: reject
tags: [fe, sheet-modal, reuse]
applies_tasks: []
applies_globs: []
applies_keywords: []
expires: ""
---

# What

FE sheet modals: Sheet/SheetContent/SheetHeader/SheetTitle/SheetBody/SheetFooter, named *-form-sheet.tsx, wire useSheetUnsavedGuard(onOpenChange) -> guardedOnOpenChange on Sheet + onDirtyChange/formState.isDirty -> setIsDirty + requestClose on cancel + UnsavedChangesDialog + setIsDirty(false) before post-save close; submit via footer Button type=submit form={FORM_ID}; reuse DecimalNumberInput with field.onChange(v ?? undefined); computed/patient fields as read-only display text not Input.

# Evidence

- vital-signs create-dialog used plain onOpenChange, no guard, while 62/98 sheets use useSheetUnsavedGuard and VitalSignsForm already exposed onDirtyChange; DecimalNumberInput onChange should be field.onChange(v) not an invented commitFieldChange.

# Why It Matters

Reinventing close/guard/input behavior causes the bug class the owner hit (undefined helpers, missing guard, wrong invalidation keys, bad variants).

# How To Apply

_See # What above._

# Boundaries

UserComboBox/Radix overlays are the exception on inpatient detail (hard-freeze under React 19.2); use native there.

# Promotion Recommendation

Promote to: reject
Reason: (fill in before promoting)
