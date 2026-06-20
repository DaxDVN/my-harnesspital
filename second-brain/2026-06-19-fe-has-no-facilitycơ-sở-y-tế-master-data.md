---
title: "FE has no facility/cơ-sở-y-tế master data"
date: "2026-06-19"
status: provisional
source: review-closeout
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/frontend
tags: [consultation, master-data, facility, frontend]
applies_tasks: [fix, implement, design, scaffold]
applies_globs: [myhospital-fe/**, worktrees/**/fe/**]
applies_keywords: [facility, cơ sở, external-facility, liên-viện, referral]
expires: ""
---

# What

FE useMasterData exposes no Facility/medical-facility (danh mục cơ sở y tế) list. Any feature needing to pick an external facility (liên-viện consultation invitee, referral, transfer-out) must add a BE master-data source first; it cannot be done FE-only — current code falls back to a free-text ExternalFacilityRef input.

# Evidence

- worktrees/ipd-consultation/fe src/modules/common/hooks/use-master-data.ts (no Facility key); invitation-form-sheet ExternalFacilityRef is free-text

# Why It Matters

Prevents scoping an external-facility combobox as a cheap FE-only fix when the underlying master data does not exist (would mislead an estimate / a /mh-fix pass).

# How To Apply

_See # What above._

# Boundaries

Internal Department/User pickers DO exist via useMasterData(['Department','User']); this only concerns external facilities.

# Promotion Recommendation

Promote to: engine/rules/frontend
Reason: (fill in before promoting)
