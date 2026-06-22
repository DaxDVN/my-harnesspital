---
title: "E2E browser tester subagents should not capture screenshots by default"
date: "2026-06-20"
status: provisional
source: conversation
scope: workflow:super-test
confidence: high
owner_confirmed: false
proposed_target: skill
tags: [e2e, agent-browser, super-test, screenshot, owner-pref]
applies_tasks: [test, review]
applies_globs: []
applies_keywords: [e2e, agent-browser, screenshot, tester, sweep]
expires: ""
---

# What

When spawning a sonnet E2E/agent-browser tester subagent for MyHospital flows, do NOT instruct per-screen screenshots. Owner finds it unnecessary overhead. Screenshot only as targeted evidence for a specific logged bug.

# Evidence

- _No specific evidence cited._

# Why It Matters

Owner directive 2026-06-20 'từ giờ bảo agent không cần chụp screenshot nữa'. Cuts tester runtime + tokens.

# How To Apply

_See # What above._

# Boundaries

Still allowed: a targeted screenshot as evidence for a specific bug.

# Promotion Recommendation

Promote to: skill
Reason: (fill in before promoting)
