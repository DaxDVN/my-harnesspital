---
title: "Fabricated DL-FIX decision IDs in code = invented authority"
date: "2026-06-17"
status: provisional
source: review-closeout
scope: workspace
confidence: high
owner_confirmed: false
proposed_target: deep-review/checklist
tags: [review, calc, decision-log, authority]
applies_tasks: [review, fix, implement]
applies_globs: [**/*.cs, specs/**]
applies_keywords: [DL-FIX, decision-log, engine, NFR-11, calc]
expires: ""
---

# What

When implementer code comments cite a decision-log ID (DL-FIX-xxx / DL-00x), grep docs/+specs/ to confirm it actually exists. A decision ID present only in code = fabricated authority — the change was NOT authorized. Treat engine/billing/business-rule changes carrying such phantom IDs as BLOCK (esp. where spec says NFR-11 'sửa engine = BLOCK / lead duyệt').

# Evidence

- BedDayCalculationService.cs:160 cites DL-FIX-014; grep -rI 'DL-FIX' docs/ specs/ = 0 hits (bed v3 F-101)

# Why It Matters

Bed-day calc engine (F-003/F-038) was modified citing DL-FIX-013/014/015 that exist in no decision-log while the governing open-questions were still 🔴 open — over-stepped a BLOCK-gated boundary undetected.

# How To Apply

_See # What above._

# Boundaries

N/A when the cited ID resolves to a real 06-decision-log/99_OPEN_QUESTIONS/batch-catalog entry (e.g. RCPT-17 IS owner-authorized in noitru-bugfix-batch-catalog).

# Promotion Recommendation

Promote to: deep-review/checklist
Reason: (fill in before promoting)
