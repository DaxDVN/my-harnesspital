---
title: "Worktree node_modules drift when master adds FE deps"
date: "2026-06-21"
status: provisional
source: harness-review
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/frontend
tags: [worktree, node_modules, npm, build, frontend, drift]
applies_tasks: [fix, implement, test, review]
applies_globs: [worktrees/**/fe/**]
applies_keywords: [npm install, build, node_modules, jsep, bwip-js, worktree]
expires: ""
---

# What

A worktree FE gets its own node_modules at creation; when master later ADDS a dependency to package.json and re-installs, existing worktrees do NOT auto-update — their node_modules go stale (dep declared but not installed) and a full  fails on the new dep's import (often in out-of-scope files like EMR/form-builder), even though the feature code is clean. Fix: run  in the worktree FE before trusting . This is NOT a per-feature bug; multiple worktrees share the gap.

# Evidence

- 2026-06-21: ipd-consultation/fe + vital-signs/fe both missing jsep@^1.4.0 + bwip-js@^4.11.1 (declared, not installed); master myhospital-fe had them; npm run build failed on those imports until npm install

# Why It Matters

Prevents misdiagnosing a stale-deps build failure as a feature/code bug, and prevents a false NO-GO on the FE build gate.

# How To Apply

_See # What above._

# Boundaries

Only the build gate / dev runtime for pages importing the new dep; tsc + per-file esbuild still pass since types resolve. The guard hook blocks the main session's npm install — needs owner bypass or .

# Promotion Recommendation

Promote to: engine/rules/frontend
Reason: (fill in before promoting)
