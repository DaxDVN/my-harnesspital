---
title: "Restart slot backend before regenerating FE DTOs after BE contract changes"
date: "2026-06-19"
status: provisional
source: bug-fix
scope: workspace
confidence: high
owner_confirmed: false
proposed_target: engine/rules/frontend.md
tags: []
applies_tasks: [Regenerating FE DTO/client after BE DTO changes]
applies_globs: [worktrees/*/be/**/*.cs, worktrees/*/fe/src/lib/dtos/generated-dtos.ts]
applies_keywords: [dto, ServiceStack, generated-dtos, client-generate, stale-backend]
expires: ""
---

# What

After editing BE ServiceStack request/response DTOs or custom types, rebuild and restart the slot backend before running npm run dtos:update/client generation.

# Evidence

- npm run dtos:update succeeded against localhost:5003 but generated DTOs missed newly added BE fields until the old MyHospital process on port 5003 was killed and restarted from the worktree.

# Why It Matters

DTO generation reads from the currently running slot backend; a stale process can make generation pass while producing stale FE contract.

# How To Apply

_See # What above._

# Boundaries

Applies to generated FE DTO/client work. Does not require restart when BE contract was not changed.

# Promotion Recommendation

Promote to: engine/rules/frontend.md
Reason: (fill in before promoting)
