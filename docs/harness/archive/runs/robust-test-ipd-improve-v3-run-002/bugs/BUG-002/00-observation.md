# BUG-002 — TASK-67: Hủy lịch Pending không hoạt động

## Metadata

- status: **BLOCKED** (no slot detail panel with Hủy button found in 5 min)
- severity: HIGH
- bug_class: schedule-cancel-pending-state
- scanner_candidate: yes
- scanner_candidate_tier: mh_scan
- flow: Click vào slot pending → Hủy lịch → nhập lý do → xác nhận
- actor: bvtest3
- route/url: /hospital-management/schedules (no slot-detail trigger found)
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:01Z

## 00 Observation (drill)

Expected: Khi click Hủy lịch trên slot Pending → button đổi từ "Gửi yêu cầu" → "Xác nhận hủy lịch".

Actual: Schedule grid (`/hospital-management/schedules`) chỉ hiển thị Ca sáng với BS names, KHÔNG có button Hủy/Gửi yêu cầu trên cell. Click "Phân ca làm việc" button → không mở dialog. Có code `reject-slot-dialog.tsx` + `submit-for-review-side-panel.tsx` trong source nhưng trigger UI không tìm thấy. → BLOCKED — không trigger được slot detail panel với action Hủy.

## 02 Triage

Verdict: **BLOCKED** — schedule UI không có entry point rõ ràng để trigger Hủy lịch action. Source có reject-slot-dialog nhưng cách trigger cần owner manual test.

## 03 RCA

Có thể click vào Ca sáng cụ thể (không phải cell "+ Thêm ca") sẽ mở slot-detail-side-panel. Cần test thủ công.

## 04 Fix Plan

N/A — defer.
