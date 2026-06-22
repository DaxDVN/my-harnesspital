---
title: "SQL seed scripts must not use T-SQL variables across GO batches"
date: "2026-06-19"
status: provisional
source: bug-fix
scope: backend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/backend
tags: [seed, sql, sqlcmd, go, database]
applies_tasks: [fix, implement, test]
applies_globs: [worktrees/**/be/Database/*.sql, myhospital-be/Database/*.sql]
applies_keywords: [seed, sqlcmd, GO, @Now, batch, scope]
expires: ""
---

# What

When a SQL seed script uses GO batch separators, T-SQL variables declared before GO are out of scope in later batches; use literals/GETUTCDATE() per batch or SQLCMD variables, and verify sqlcmd output for mid-script errors.

# Evidence

- worktrees/fix-bug-noi-tru/be/Database/seed-fix-bug-noi-tru-slot3.sql: @Now declared before GO caused sqlcmd error 137 while later batches still printed Seed complete

# Why It Matters

Prevents partial seed application with misleading success output and missing test data.

# How To Apply

_See # What above._

# Boundaries

Applies to SQL scripts executed by sqlcmd or tools that treat GO as a batch separator; does not apply to a single uninterrupted SQL batch.

# Promotion Recommendation

Promote to: engine/rules/backend
Reason: (fill in before promoting)
