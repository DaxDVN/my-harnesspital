---
title: "Rule Gate: Canonical reuse before new code"
date: "2026-06-22"
status: provisional
source: grouped-generalization
scope: workspace
confidence: high
owner_confirmed: true
proposed_target: engine/rules/ponytail + frontend/backend reuse checklist + scanners
tags: [grouped, reuse, ponytail, convention, component, pattern]
applies_tasks: [fix, implement, review, test, design, scaffold]
applies_globs: [worktrees/**, myhospital-fe/**, myhospital-be/**]
applies_keywords: [reuse, convention, canonical, hand-roll, component, field, form, sheet, label, error-handler, naming, pattern]
expires: ""
---

# Canonical Reuse Gate

Before creating or hand-rolling code, survey the project for the canonical pattern and reuse it unless current
evidence proves it cannot fit.

## Use When

- Adding/changing FE fields, forms, sheets, labels, headers, tables, error handling, or query patterns.
- Adding/changing BE helpers, services, naming, DTO/resource patterns, validators, or shared behavior.
- Reviewing code that looks locally correct but may bypass a project convention.

## Rule

- Survey the relevant population, not one exemplar. Record current evidence such as `N/total` or cited files.
- Reuse existing project component/helper/pattern first. Extend it if the gap is small.
- Create new code only when reuse is unsafe or impossible, and state why.
- If one hand-rolled instance is found, audit the surrounding feature for the same class.
- Do not invent missing master data, resource ownership, naming prefix, error contract, or display model when the
  project already has a canonical owner/source.

## Why It Generalizes

Most case-specific FE bugs were not unique bugs; they were local rewrites of already-solved contracts: value
format, `onChange`, i18n, unsaved guard, query key, patient display, or error handling.

## Archive Sources

- [`fe-custom-onerror-handleapierror`](../_archive/2026-06-17-fe-custom-onerror-must-route-through-handleapierror-not-raw.md)
- [`controlled-draft-input-focus-sync`](../_archive/2026-06-19-controlled-draft-input-must-guard-its-value-sync-useeffect-w.md)
- [`fe-no-facility-master-data`](../_archive/2026-06-19-fe-has-no-facilitycơ-sở-y-tế-master-data.md)
- [`fe-label-fallback-no-op`](../_archive/2026-06-19-fe-label-fix-via-t-fallback-is-a-no-op-when-the-key-exists-i.md)
- [`naming-prefixes-resource-owner`](../_archive/2026-06-19-naming-prefixes-follow-resource-owner-not-module-folder.md)
- [`page-mode-form-sheets`](../_archive/2026-06-19-page-mode-form-sheets-need-modal-outside-block-and-one-shot.md)
- [`patientheaderdto-display-fields`](../_archive/2026-06-19-patientheaderdto-carries-precomputed-display-fields-prefer-over-recompute.md)
- [`ui-deep-audit-reuse-matrix`](../_archive/2026-06-19-ui-deep-audit-must-verify-live-widgets-and-layout-patterns.md)
- [`inpatient-form-sheet-reuse`](../_archive/2026-06-20-inpatient-form-sheet-must-reuse-usesheetunsavedguard-canonic.md)
- [`fe-field-component-survey`](../_archive/2026-06-21-fe-fieldcomponent-survey-then-reuse-the-canonical-never-hand.md)
