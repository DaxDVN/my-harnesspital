---
title: "Do not claim VERIFIED without running the real gate + the live user path"
date: "2026-06-21"
status: provisional
source: user-correction
scope: workspace
confidence: high
owner_confirmed: false
proposed_target: reject
tags: [verification, honesty, live-test, gate, overclaim]
applies_tasks: [implement, bug-fix, review, verification]
applies_globs: []
applies_keywords: [verify, verified, tested, done, proof, browser, persist]
expires: ""
---

# What

VERIFIED means: (1) the project real gate passed scoped to changed files, AND (2) the actual user path was exercised live (browser: do the action, see persistence, reload and re-read from backend) — NOT static checks plus assumption. Always split the report into VERIFIED vs NOT-VERIFIED and name the residual risk honestly. esbuild/Vite transpiles without type-checking, so undefined identifiers and type errors reach the browser; only a live run proves no crash.

# Evidence

- I tagged findings VERIFIED/ok based on root-tsconfig tsc + memory, then shipped a runtime crash and a silently-dropped param. Owner: lam an cau tha. Only after driving agent-browser end-to-end (login, real nav, fill, save, reload-from-BE) was the flow actually proven.

# Why It Matters

Overclaiming done erodes trust fast and ships defects the owner then finds. A test that did not run is not evidence.

# How To Apply

_See # What above._

# Boundaries

All implement/fix/review tasks. Live-browser proof especially for save/persist/re-render paths.

# Promotion Recommendation

Promote to: reject
Reason: (fill in before promoting)
