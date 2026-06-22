---
title: "UI deep audit must require semantic reuse matrix"
date: "2026-06-19"
status: provisional
source: harness-review
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: deep-review/checklist
tags: [frontend, ui-review, deep-review, semantic-reuse, component-reuse]
applies_tasks: [review, fix, implement, test]
applies_globs: [worktrees/*/fe/src/**/*.tsx, myhospital-fe/src/**/*.tsx]
applies_keywords: [consultation, component, pattern, reuse, semantic, UI, widget, surface, layout, modal, sheet, control]
expires: ""
---

# What

For visible FE audit/implementation/fix, do not mark D3/D10 clean from code presence alone. Require a semantic reuse matrix for every changed UI element/surface/action: semantic role -> existing live exemplar component/pattern -> actual implementation/decision. Date/time pickers and sheet layout are examples, not the rule itself.

# Evidence

- docs/audit/2026-06-19/full-audit-consultation.md:54-56 marked consultation UI CLEAN without proving component/pattern reuse per UI element. Later manual code review found multiple semantic reuse misses: document sheet surface pattern, typed create flow, and date/time control pattern.

# Why It Matters

Prevents agents from rebuilding or hand-rolling UI that already has a system component/pattern. Build, mh-scan, and spec-conformance can pass while FE code still violates the system's reuse conventions.

# How To Apply

For any visible UI work, ask for or produce the matrix before coding/reviewing. If a row has no cited exemplar and no CREATE-NEW rationale, the D3/D10 cell is UNATTESTED, not CLEAN.

# Boundaries

The matrix is about coding pattern/reuse, not business truth. Business specs decide what fields/actions exist; live FE code and frontend canon decide which component/pattern should implement them.

# Promotion Recommendation

Promote to: deep-review/checklist
Reason: (fill in before promoting)
