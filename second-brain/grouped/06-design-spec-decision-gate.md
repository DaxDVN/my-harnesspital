---
title: "Rule Gate: Design genre and spec decision placement"
date: "2026-06-22"
status: provisional
source: grouped-generalization
scope: workspace
confidence: high
owner_confirmed: true
proposed_target: skill:clinical-ui-design + specs/<module>/06-decision-log.md
tags: [grouped, design, clinical-ui, spec-decision, module]
applies_tasks: [design, implement, review, scaffold, fix]
applies_globs: [worktrees/*/fe/**, specs/**]
applies_keywords: [design, clinical-ui, his, ui, mockup, spec, decision, table, map, workflow, density, module]
expires: ""
---

# Design Genre And Spec Decision Gate

Design work should choose the right clinical job/genre before layout details. Module-local business/design
decisions belong in specs, not global memory.

## Use When

- Designing/reviewing HIS/clinical screens.
- Choosing between table/form/map/timeline/queue/board/checklist/command-center layouts.
- Resolving a conflict between docs, mockups, and owner decisions.
- Capturing a decision that only applies to one module.

## Rule

- Start from the clinical job and real data, not generic SaaS/marketing UI defaults.
- Calm clinical UI must still have clear hierarchy, density, and task-specific affordances.
- Do not default to a table; choose the genre that matches the user's job.
- Variants should be different approaches to the same job, not unrelated feature bundles.
- Owner taste and mockups are evidence; reconcile them explicitly with written docs.
- Module-local decisions go to `specs/<module>/06-decision-log.md`, not `main-brain`.

## Why It Generalizes

This turns design notes from taste fragments into a reusable design decision process: job first, genre second,
layout third, then module decision logging.

## Archive Sources

- [`clinical-ui-v2-calm-not-bland`](../_archive/2026-06-18-clinical-ui-design-v2-calm-bland-generic-là-failure-mode-var.md)
- [`frontend-design-marketing-bias`](../_archive/2026-06-18-frontend-design-skill-bias-marketing-cần-clinical-variant-ch.md)
- [`clinical-ui-v3-real-data-owner-taste`](../_archive/2026-06-19-clinical-ui-design-v3-ground-vào-data-hệ-thống-thật-gu-là-củ.md)
- [`clinical-ui-v4-density-fresh-eyes`](../_archive/2026-06-19-clinical-ui-design-v4-constraint-quality-thêm-kỹ-thuật-legib.md)
- [`clinical-ui-v5-genre-first`](../_archive/2026-06-19-clinical-ui-design-v5-genre-first-sơ-đồmap-variantdesign-app.md)
- [`bed-reservation-mockup-decision`](../_archive/2026-06-19-bed-reservation-đặt-lịch-form-follows-mockup-lean-not-doc-te.md)
