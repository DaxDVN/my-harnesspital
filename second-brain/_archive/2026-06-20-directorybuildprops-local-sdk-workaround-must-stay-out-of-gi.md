---
title: "Directory.Build.props local SDK workaround must stay out of git"
date: "2026-06-20"
status: provisional
source: user-correction
scope: backend
confidence: high
owner_confirmed: false
proposed_target: main-brain
tags: [local-config, dotnet, msbuild, skip-worktree, main-repo]
applies_tasks: [fix, implement, test, any]
applies_globs: [myhospital-be/Directory.Build.props]
applies_keywords: [Directory.Build.props, AllowMissingPrunePackageData, skip-worktree, local-only, dotnet, SDK]
expires: ""
---

# What

When Directory.Build.props is modified only to make this local machine run .NET SDK 10.0.108, keep it local-only with git skip-worktree and do not commit or push it.

# Evidence

- Conversation 2026-06-20: owner said Directory.Build.props is local-only; git ls-files -v shows S Directory.Build.props

# Why It Matters

Prevents a machine-specific MSBuild workaround from entering shared main history while preserving local ability to run make server.

# How To Apply

_See # What above._

# Boundaries

Only applies to local environment workarounds. If the team intentionally decides the MSBuild property is a shared project requirement, unskip and commit via normal review.

# Promotion Recommendation

Promote to: main-brain
Reason: (fill in before promoting)
