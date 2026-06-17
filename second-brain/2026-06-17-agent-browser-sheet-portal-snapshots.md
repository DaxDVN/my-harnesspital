---
title: "agent-browser Sheet portal snapshots"
date: "2026-06-17"
status: promoted
source: conversation
scope: workflow:super-test
confidence: high
owner_confirmed: true
proposed_target: engine/rules/frontend + workflow:super-test
tags: [agent-browser, mimo, sheet, portal, accessibility]
applies_tasks: [test, review, implement]
applies_globs: [engine/workflows/**, worktrees/*/fe/src/components/ui/sheet.tsx]
applies_keywords: [agent-browser, mimo, sheet, portal, accessibility, snapshot, data-slot]
expires: ""
---

# What

agent-browser snapshot -i can see form fields inside portal-rendered Sheet dialogs; if Sheet evidence appears missing, first check wrong selectors/truncation. In this FE, SheetContent currently lacks data-slot=sheet-content, so selector-scoped evidence using [data-slot=sheet-content] returns no match; [role=dialog] works.

# Evidence

- engine/workflows/super-test/bin/agent-browser-evidence:90

# Why It Matters

Prevents MiMo/Super-Test from treating screenshot-only evidence as necessary or misdiagnosing portal overlays as an accessibility traversal bug.

# How To Apply

_See # What above._

# Boundaries

Does not prove every custom virtualized/offscreen field appears in AX snapshots; offscreen, aria-hidden, inert, unnamed custom controls, and max-output truncation still require scoped snapshot/eval/screenshot fallback.

# Promotion Recommendation

Promote to: skill
Reason: Promoted by owner request on 2026-06-17 into `engine/rules/frontend.md`,
`engine/skills/mh-implement/fe-flow.md`, and `engine/workflows/super-test/protocol/harvest-sweep.md`.
