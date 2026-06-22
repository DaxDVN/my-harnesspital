---
title: "Data-backfill migrations are guard-blocked in worktrees → need owner bypass"
date: "2026-06-19"
status: provisional
source: bugfix-from-report (bed-management F-004)
scope: workspace
confidence: high
owner_confirmed: false
proposed_target: engine/rules (source-discovery / backend) or guard refinement
applies_tasks: [fix, implement, review]
applies_globs: ["**/MyHospital.ServiceInterface/Migrations/*.cs"]
applies_keywords: [migration, backfill, migrationBuilder.Sql, guard, bypass, data-migration, IsClinicalOccupancy]
expires: ""
---

# What

`myhospital_guard.py:183` BLOCKS every Write/Edit/MultiEdit to `worktrees/<slug>/be/.../Migrations/*.cs`
("migration-hand-edit — change the model + add a migration"). That rule assumes migrations are always
regenerable from a model delta. **Data-backfill migrations are NOT** — `migrationBuilder.Sql("UPDATE …")`
has no model delta, so `dotnet ef migrations add` produces an EMPTY `Up()` and the SQL must be hand-authored.
So any legitimate data-backfill fix is guard-blocked and requires an explicit Owner-Authorized Bypass.

# How To Apply

- When a fix is a **data backfill** (repair existing rows), expect the guard to block the Edit tool. Do NOT
  treat that as "can't fix". Surface it to the owner for a one-line bypass (AGENTS.md → Owner-Authorized
  Bypass Protocol), state the bypassed rule + reason, keep scope to the one migration file.
- The hook intercepts Write/Edit/MultiEdit (and main-brain Bash writers) — it does NOT intercept generic Bash,
  so after owner authorization the SQL can be written via a Bash heredoc to the single migration file.
- Backfill SQL must be **idempotent** (e.g. `… AND IsClinicalOccupancy = 0`) and put in a NEW forward
  migration's `Up()` — never retro-edited into an already-issued migration (DBs that ran it won't replay).
- Slot DBs (localhost,1434-1437) are sync-from-main, NOT EF-managed → a backfill migration won't run there;
  it executes on the real deploy. Verify by compile + idempotent-SQL review, note runtime is deploy-time.

# Why It Matters

Recurring: bed-management F-004 (2026-06-19) and F-102 (prior round) were both empty/forward backfill
migrations for `IsClinicalOccupancy`. The fix kept stalling on the guard. Pairs with
[[2026-06-17-additive-not-null-default-column-consumed-by-a-new-query-nee]] (the backfill-must-exist class)
and the worktree-slot-DB sync note.

# Promotion Recommendation

Promote to: a guard refinement (allow `migrationBuilder.Sql`-only data migrations, or a `.migration-unlock`
marker like main-brain's) OR an `engine/rules` note documenting the expected owner-bypass for data backfills.
Reason: turns a repeated hard-stop into a known, fast path.
