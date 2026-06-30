# BUG-020 — TASK-263: NB chờ NV vẫn lưu mới được (Re-open)

## Metadata

- status: **NEEDS_OWNER_DECISION** (need scenario: pick "Chờ NV" row → new admission)
- severity: HIGH
- bug_class: admission-double-save-allowed
- flow: /medical-visits/inpatient → click row "Chờ nhập viện" → Tiếp nhận
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:06Z

## 00 Observation

Có NB ở trạng thái "Chờ nhập viện" (rows 2,3,4,5) nhưng click row không trigger rõ action.

## 02 Triage

Verdict: NEEDS_OWNER_DECISION.
