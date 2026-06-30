# BUG-022 — TASK-266: Khoa nhận vs khoa chuyển (sai 2 chiều)

## Metadata

- status: **NEEDS_OWNER_DECISION** (data hiện tại không có KKB → Ngoại scenario)
- severity: HIGH
- bug_class: department-receive-vs-transfer-mismatch
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:06Z

## 00 Observation

DS tiếp nhận: cả Khoa chuyển và Khoa nhận đều = "Khoa nội" cho mọi NB. Cần test với NB chuyển từ KKB sang khoa khác.
