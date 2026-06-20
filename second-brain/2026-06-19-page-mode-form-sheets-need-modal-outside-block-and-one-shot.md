---
title: "Page-mode form sheets need modal outside block and one-shot hydration"
date: "2026-06-19"
status: provisional
source: bug-fix
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/frontend.md
tags: [frontend, sheet, modal, unsaved-guard, prefill, dirty-form]
applies_tasks: [fix, implement, review]
applies_globs: [worktrees/*/fe/src/**/*.tsx]
applies_keywords: [sheet, modal, drawer, pageMode, unsaved, prefill, form.reset, isDirty]
expires: ""
---

# What

For editable pageMode Sheet forms, outside/background interactions can unmount the form before useSheetUnsavedGuard runs if the Sheet is non-modal. Async detail/prefill effects can also reset over user input if they run after the user starts typing.

# Evidence

- _No specific evidence cited._

# Why It Matters

Use modal/outside-interaction blocking or route/page-level guards for pageMode form sheets. Hydrate form values once per open/entity, do not form.reset when the form is dirty, render loading until initial detail/prefill is ready, and include non-RHF local state such as staged uploads in dirty tracking.

# How To Apply

_See # What above._

# Boundaries

Verified on consultation record/invitation sheets; apply to FE sheet/modal/drawer forms with async prefill/detail and unsaved guard.

# Promotion Recommendation

Promote to: engine/rules/frontend.md
Reason: (fill in before promoting)
