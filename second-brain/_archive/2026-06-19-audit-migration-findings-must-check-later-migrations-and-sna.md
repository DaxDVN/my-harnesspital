---
title: "audit migration findings must check later migrations and snapshot"
date: "2026-06-19"
status: provisional
source: bug-fix
scope: backend
confidence: high
owner_confirmed: false
proposed_target: deep-review/checklist
tags: [migration, audit, false-positive, ef]
applies_tasks: [review, bugfix, backend]
applies_globs: [**/Migrations/*.cs, **/MyHospitalContextModelSnapshot.cs]
applies_keywords: [migration, audit, snapshot, filtered-index, missing-table, missing-column]
expires: ""
---

# What

Before accepting a migration finding from an audit report, verify the full migration chain after the cited migration plus MyHospitalContextModelSnapshot.

# Evidence

- _No specific evidence cited._

# Why It Matters

A report that only inspects the original feature migration can be false-positive when a later generated migration already adds the missing table, column, index, or filter.

# How To Apply

_See # What above._

# Boundaries

Do not create a new migration until later migrations and the snapshot have been checked.

# Promotion Recommendation

Promote to: deep-review/checklist
Reason: (fill in before promoting)
