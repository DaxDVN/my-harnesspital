# BUG-015 — TASK-249: Cấu hình "Bắt buộc tạm ứng trước khi nhập viện"

## Metadata

- status: **NEEDS_OWNER_DECISION** (cấu hình admin page not navigated)
- severity: MED
- bug_class: payment-config-missing-flag
- flow: Cấu hình thanh toán (admin)
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:05Z

## 00 Observation

Trên DS tiếp nhận, cột "TT Thanh toán" hiển thị "Đã tạm ứng" / "Chờ thanh toán". Có cả 2 trạng thái → config có thể đang chạy ở mode warning (cho phép tạo NV khi chưa tạm ứng, hiển thị cảnh báo). Cấu hình nằm trong admin module.

## 02 Triage

Verdict: NEEDS_OWNER_DECISION — không navigate tới cấu hình admin để verify flag.
