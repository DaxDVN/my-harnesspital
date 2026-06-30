# BUG-017 — TASK-253: Kết luận BS tuyến trước: ICD hiển thị cả mã và tên

## Metadata

- status: **NEEDS_OWNER_DECISION** (form create ICD dropdown not drilled)
- severity: MED
- bug_class: icd-display-format-wrong
- flow: /medical-visits/inpatient/create → Kết luận BS tuyến trước
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:05Z

## 00 Observation (drill)

Trên form Tiếp nhận trực tiếp (`/medical-visits/inpatient/create`), không thấy section "Kết luận BS tuyến trước" rõ ràng (có thể là "Thông tin đăng kí KCB" → "Bác sĩ chỉ định"). ICD dropdown chưa drill.

## 02 Triage

Verdict: NEEDS_OWNER_DECISION.
