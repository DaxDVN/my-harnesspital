---
title: "Self-test the fix new edge cases, not just the original bug"
date: "2026-06-21"
status: provisional
source: bug-fix
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: reject
tags: [fix, self-test, edge-case, datepicker, regression]
applies_tasks: [bug-fix, implement]
applies_globs: []
applies_keywords: [fix, regression, edge-case, datepicker, time, merge]
expires: ""
---

# What

After a fix, test the NEW code paths edge cases — not only that the original symptom is gone and that it compiles. Combining a date-only DatePicker with a TimeInput24 into one ISO needs a time-of-day ref so a date pick preserves the time. Verify the new control end-to-end (pick backdated date keeps time, type date/time preserves the other, save persists).

# Evidence

- Switching MeasuredAt to DatePicker+TimeInput24 fixed the convention but INTRODUCED a new bug: picking a date reset the time to 00:00 (date-only picker emits midnight from both calendar and text input). Caught only by live-testing the new control; fixed with a time-of-day ref.

# Why It Matters

A fix is new code and ships its own bugs; tsc-clean plus original-bug-gone is not enough.

# How To Apply

_See # What above._

# Boundaries

FE fixes that swap or combine controls.

# Promotion Recommendation

Promote to: reject
Reason: (fill in before promoting)
