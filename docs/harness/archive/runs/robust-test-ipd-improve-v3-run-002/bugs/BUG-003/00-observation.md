# BUG-003 — TASK-70: Thiếu warning "khoảng TG mới áp dụng lịch kế tiếp"

## Metadata

- status: **BLOCKED** (no edit shift dialog open in 5 min)
- severity: LOW
- bug_class: shift-time-update-warning-missing
- scanner_candidate: no
- flow: Click shift → Chỉnh sửa ca → đổi thời gian → check warning
- actor: bvtest3
- route/url: /hospital-management/schedules
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:02Z

## 00 Observation (drill)

Expected: Khi cập nhật thời gian của ca, hiển thị warning "Khoảng thời gian mới sẽ được áp dụng trong lịch làm việc kế tiếp".

Actual: Schedule grid không có action Chỉnh sửa trực tiếp. Các cell có "+ Thêm ca" button. Click "Phân ca làm việc" top button → không mở dialog. Cần tìm entry point để edit shift. Có thể phải click vào Ca sáng tên (e.g., "BS. Administrator") để mở detail.

## 02 Triage

Verdict: **BLOCKED** — không trigger được edit shift UI trong 5 min. Cần manual test.

## 04 Fix Plan

N/A — defer.
