---
title: "FE label fix via t() fallback is a NO-OP when the key exists in vi.json — must edit vi.json"
date: "2026-06-19"
status: provisional
source: conversation
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/frontend.md
tags: []
applies_tasks: []
applies_globs: []
applies_keywords: []
expires: ""
---

# What

MyHospital FE renders labels with t('KEY','Vietnamese fallback'). Displayed text = src/i18n/messages/vi.json.ts[KEY] IF that key exists, ELSE the inline fallback. So changing ONLY the fallback string in a component is a SILENT NO-OP whenever the key already exists in vi.json with a (stale) value — the screen keeps showing the old vi.json text even though the component code looks correct. This bit the bed-management label work repeatedly: bed-types COL_CODE/COL_NAME/ACTION_EDIT/BADGE_SELF_SELECT, bed-stay popup TITLE_ASSIGN/TITLE_RELEASE/RELEASE_BED_BUTTON/RELEASE_ENDED_AT_LABEL, STARTED_AT_LABEL/ENDED_AT_LABEL — all had correct fallbacks but wrong vi.json overrides. vi.json.ts is the i18n SOURCE (hand-maintained, EDITABLE — NOT one of the 3 generated files: generated-dtos/Constants/generated-api-client).

# Evidence

- _No specific evidence cited._

# Why It Matters

To change a displayed label: update vi.json[KEY] (and keep the fallback in sync), not just the fallback. When auditing/fixing labels, grep vi.json for the KEY first; reconcile its value to the doc. VERIFY by render/screenshot, not by reading the component — a code-correct label can still render wrong via a stale vi.json override. Earlier 'do not edit vi.json' guidance was wrong for label fixes.

# How To Apply

_See # What above._

# Boundaries

_No specific boundaries noted._

# Promotion Recommendation

Promote to: engine/rules/frontend.md
Reason: (fill in before promoting)
