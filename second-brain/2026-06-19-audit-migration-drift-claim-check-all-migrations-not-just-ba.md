---
title: "Audit migration-drift claim: check ALL migrations, not just baseline"
date: "2026-06-19"
status: provisional
source: harness-review
scope: backend
confidence: high
owner_confirmed: false
proposed_target: deep-review/checklist
tags: []
applies_tasks: [review, fix]
applies_globs: [**/Migrations/**]
applies_keywords: [migration, drift, column missing, table missing, EF]
expires: ""
---

# What

An audit finding of 'entity column/table missing from migration DDL' (claimed BLOCKS-MERGE) is often a FALSE POSITIVE when a feature spans MULTIPLE migrations: a later additive migration supplies it. Grep ALL migration files for the column/table name before trusting the finding; verify MODEL + SNAPSHOT + ALL-MIGRATIONS together.

# Evidence

- 20260618135109_AddIpdConsultationDrugRecords.cs:14,22 creates RecordType + ConsultationRecordDrug; deep-audit F-001/F-002 cited only 20260615151512

# Why It Matters

Prevents a stale-read reviewer (reads only the baseline migration, misses a follow-up AddColumn/CreateTable) from blocking merge on a non-existent drift.

# How To Apply

_See # What above._

# Boundaries

Does NOT apply when there is genuinely one migration, or when snapshot disagrees with all migrations (then drift is real).

# Promotion Recommendation

Promote to: deep-review/checklist
Reason: (fill in before promoting)
