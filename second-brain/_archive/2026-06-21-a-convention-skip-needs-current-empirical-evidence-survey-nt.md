---
title: "A convention-skip needs CURRENT empirical evidence; survey N/total not one exemplar"
date: "2026-06-21"
status: provisional
source: user-correction
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: reject
tags: [evidence, assumption, survey, convention, cascade]
applies_tasks: [fe, implement, review, bug-fix]
applies_globs: []
applies_keywords: [exception, assumption, freeze, survey, convention, evidence]
expires: ""
---

# What

Two rules. (1) Never use a past root-cause as a blanket excuse to skip a convention — re-test THAT specific claim empirically now; a justified exception requires current evidence, and a high-confidence memory note that contradicts new evidence must be corrected. (2) For convention questions, measure adoption across the whole population (count N/total over all instances, e.g. all *-form-sheet.tsx) rather than arguing from one exemplar or intuition. When a premise is retracted, re-examine every decision that relied on it (cascade).

# Evidence

- I justified native datetime-local + skipping KeyboardShortcutsHelp with a stale claim Radix Popover freezes this page — never re-tested. Live test showed DatePicker Popover works fine (35-day calendar, ~10 commits, no freeze); the real freeze was an already-fixed re-render loop. Separately, comparing to ONE exemplar (unit-form-sheet) missed gaps; surveying ALL 57 form-sheets revealed FormLabel 79%, type=number only 9/57.

# Why It Matters

Stale assumptions and single-exemplar comparisons let real convention violations survive and get rationalized as deliberate exceptions.

# How To Apply

_See # What above._

# Boundaries

FE convention/reuse decisions; generalizes to any claimed exception.

# Promotion Recommendation

Promote to: reject
Reason: (fill in before promoting)
