---
title: "FE custom onError must route through handleApiError, not raw error.message — or forced-i18n breaks"
date: "2026-06-17"
status: provisional
source: review-closeout
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/frontend
tags: [frontend, i18n, error-handling, onError, toast, mutation]
applies_tasks: [review, implement, fix]
applies_globs: [myhospital-fe/**, worktrees/**]
applies_keywords: [onError, showErrorToast, error.message, handleApiError, FORCE_I18N_CODES, i18n, toast]
expires: ""
---

# What

A mutation that overrides onError and calls showErrorToast(error.message) shows the RAW BE message and bypasses the FORCE_I18N_CODES whitelist (error-handler.ts), so owner-decision codes (e.g. SHIFT.FIXED_SHIFT_TIME_LOCKED) display English/internal text instead of the confirmed VN i18n string. error.message = raw BE Message; error.code = the i18n key. Route non-special branches through handleApiError(error, intl, fallback) instead.

# Evidence

- shift-form-sheet.tsx:360-383 onError -> showErrorToast(error.message); FORCE_I18N_CODES whitelist in error-handler.ts:68-73; api-error.ts:31 message=raw BE

# Why It Matters

Prevents user-facing raw/English error text for codes the team explicitly localized; keeps custom branches (e.g. AFFECTED_SLOTS_REQUIRE_CONFIRM) while restoring forced-i18n.

# How To Apply

_See # What above._

# Boundaries

Only when a mutation sets disableErrorToast + custom onError. Mutations using the adapter default onError already honor FORCE_I18N_CODES (e.g. use-roster-mutations).

# Promotion Recommendation

Promote to: engine/rules/frontend
Reason: (fill in before promoting)
