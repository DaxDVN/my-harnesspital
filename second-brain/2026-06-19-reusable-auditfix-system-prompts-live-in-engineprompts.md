---
title: "Reusable audit+fix system prompts live in engine/prompts/"
date: "2026-06-19"
status: provisional
source: conversation
scope: workspace
confidence: high
owner_confirmed: false
proposed_target: engine/rules/backend
tags: [prompts, audit, bugfix, reuse, engine]
applies_tasks: [review, fix, any]
applies_globs: [engine/prompts/**, docs/tasks/full-worktree-audit-*, docs/audit/**]
applies_keywords: [audit, system prompt, orchestrator, findings, fix report, merge-gate]
expires: ""
---

# What

Reusable copy-paste system prompts live in engine/prompts/. deep-audit-orchestrator.md = SELF-CONTAINED deep-audit prompt: hand it + just a slug/tên module (vital-signs, Hội chẩn, noi-tru-3modules) → it resolves the preset from its built-in §11 MODULE REGISTRY and starts immediately, no external file. Has static+dynamic build/test layer, D1-D10, bug-classes, fix-ready FIX PACKET schema, DoD; §10 MODULE BLOCK contract is only for NEW modules not yet in the registry (then append a preset). bugfix-from-report.md = Opus-xhigh investigate+fix prompt wired to /bug-fix, mh-rca, /mh-fix, /impact-analysis. Output → docs/audit/<YYYY-MM-DD>/full-audit-<scope>.md (date-folder). The old 3 docs/tasks/full-worktree-audit-prompt-*.md instance files were DELETED 2026-06-19 (content absorbed into §11 registry incl. the 42-item BA-FINAL list).

# Evidence

- engine/prompts/{deep-audit-orchestrator,bugfix-from-report,README}.md created 2026-06-19

# Why It Matters

Stops the 3-near-duplicate-prompt drift; edit orchestrator once -> every audit inherits. Adds dynamic test layer (audits were static-only -> missed runtime bugs) + fix-ready findings so the downstream Opus fixer needs no re-investigation.

# How To Apply

_See # What above._

# Boundaries

Not skills/auto-invoked; owner hands them to an external agent manually. Audit prompt is read-only on code but RUNS build/test/scanner/e2e.

# Promotion Recommendation

Promote to: engine/rules/backend
Reason: (fill in before promoting)
