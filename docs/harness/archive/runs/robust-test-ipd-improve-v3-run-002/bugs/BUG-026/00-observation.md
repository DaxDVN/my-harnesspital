# BUG-026 — TASK-270: Upload file → báo OK nhưng không hiển thị

## Metadata

- status: **NEEDS_OWNER_DECISION** (form create chưa save nên file section disabled)
- severity: HIGH
- bug_class: file-upload-display-broken
- flow: /medical-visits/inpatient/create → "Đính kèm file"
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:06Z

## 00 Observation

Form có section "Đính kèm file" với text "Lưu hồ sơ tiếp nhận trước khi đính kèm tài liệu." → file upload bị disable cho đến khi save. Cần save form trước rồi mới test upload.
