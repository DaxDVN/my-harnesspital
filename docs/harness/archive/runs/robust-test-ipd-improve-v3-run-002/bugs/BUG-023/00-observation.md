# BUG-023 — TASK-267: BN dịch vụ chỉ định NV → không fill đối tượng

## Metadata

- status: **NEEDS_OWNER_DECISION** (need create admission from dịch vụ row)
- severity: HIGH
- bug_class: admission-order-object-type-not-copied
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:06Z

## 00 Observation

Có NB "Dịch vụ" trong list (rows 4, 5, 6, 7) nhưng click row → action create admission chưa trigger được.
