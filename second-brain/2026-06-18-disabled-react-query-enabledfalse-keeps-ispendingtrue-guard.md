---
title: "Disabled React Query (enabled:false) keeps isPending=true → guard loading UI on the gate, not isPending"
date: "2026-06-18"
status: provisional
source: bug-fix
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/frontend
tags: []
applies_tasks: [fix, implement]
applies_globs: [worktrees/*/fe/**, myhospital-fe/**]
applies_keywords: [react-query enabled isPending isLoading spinner department-gate]
expires: ""
---

# What

When a list query is gated with enabled:!!someId, React Query keeps isPending=true while disabled (no data, not fetching). Wiring the loading spinner to isPending then shows an INFINITE spinner whenever the gate is unmet (e.g. no department selected). Gate the loading UI on the SAME condition (isLoading={isPending && !!someId}) so the unmet-gate state renders an empty/prompt ('Chọn khoa') instead of spinning forever.

# Evidence

- room-list-page.tsx:231-233 enabled:!!currentDepartmentId + :383 isLoading={isPending} → infinite 'Đang tải...' spinner when no department selected

# Why It Matters

Prevents infinite-spinner dead-ends on department/tenant-gated list pages; pairs with the DepartmentId=0 enabled-guard fix (which stops the 400 but exposes this spinner).

# How To Apply

_See # What above._

# Boundaries

FE React Query list pages with enabled-gated queries; not relevant where the query is always enabled.

# Promotion Recommendation

Promote to: engine/rules/frontend
Reason: (fill in before promoting)
