---
title: "mimo executor retries provider 400"
date: "2026-06-17"
status: provisional
source: bug-fix
scope: workflow:super-test
confidence: medium
owner_confirmed: false
proposed_target: skill
tags: [opencode, mimo, retry, executor, agent-browser]
applies_tasks: [test, implement, review]
applies_globs: [engine/workflows/**]
applies_keywords: [opencode, mimo, retry, 400, non-retryable]
expires: ""
---

# What

OpenCode/MiMo executor wrappers should retry only the provider's specific Request Error status 400 / non-retryable failure after a short sleep, instead of failing immediately.

# Evidence

- engine/workflows/_shared/opencode-retry.sh:12-69

# Why It Matters

This converts a flaky upstream request choke into one bounded retry and prevents the whole run from dying on a transient provider-side 400.

# How To Apply

_See # What above._

# Boundaries

Does not apply to app-level 4xx/5xx, browser automation failures, or real validation errors.

# Promotion Recommendation

Promote to: skill
Reason: (fill in before promoting)
