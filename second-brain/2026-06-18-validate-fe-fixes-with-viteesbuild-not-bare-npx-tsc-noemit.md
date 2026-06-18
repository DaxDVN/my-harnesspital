---
title: "Validate FE fixes with vite/esbuild, not bare 'npx tsc --noEmit'"
date: "2026-06-18"
status: provisional
source: bug-fix
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/frontend
tags: []
applies_tasks: [fix, implement, test]
applies_globs: [worktrees/*/fe/**, myhospital-fe/**]
applies_keywords: [tsc, vite, esbuild, typecheck, syntax, frontend]
expires: ""
---

# What

A missing closing brace (superRefine left getBedTypeFormSchema unclosed) gave 'npx tsc --noEmit' exit 0 (false green) but vite/esbuild rejected it ('Unexpected export', Pre-transform error) and the page crashed at runtime. Bare 'npx tsc --noEmit' in an FE worktree can resolve no/incorrect tsconfig and false-pass. Validate FE edits with vite build / esbuild transform, or curl the module through the running vite dev server; the project's real check is 'tsc && vite build'.

# Evidence

- worktrees/fix-bug-noi-tru/fe/src/modules/bed-management/forms/bed-type-form-schema.ts:45 — esbuild 'Unexpected export', tsc exit 0

# Why It Matters

Prevents shipping a syntactically broken FE file that typecheck falsely passes and that crashes the module at runtime; prevents trusting a subagent's 'tsc 0 errors' self-report.

# How To Apply

_See # What above._

# Boundaries

FE/vite worktrees; not BE (dotnet build is authoritative there).

# Promotion Recommendation

Promote to: engine/rules/frontend
Reason: (fill in before promoting)
