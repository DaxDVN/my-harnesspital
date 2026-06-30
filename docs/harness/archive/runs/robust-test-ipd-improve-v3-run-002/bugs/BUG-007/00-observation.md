# BUG-007 — TASK-74: Bỏ chế độ xem THEO THÁNG, đưa ra ngoài

## Metadata

- status: **LIKELY FIXED**
- severity: MED
- bug_class: schedule-view-mode-month-removed
- scanner_candidate: no
- flow: /hospital-management/schedules — top-right view mode
- actor: bvtest3
- route/url: /hospital-management/schedules
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T05:14Z

## 00 Observation

Expected: Bỏ chế độ xem THEO THÁNG; view mode (Tuần/Ngày) đưa ra ngoài để tiện view.

Actual: Trên schedule page, top-bar chỉ có 2 view mode: "Tuần" và "Ngày" (KHÔNG có "Tháng"). Filter bên phải có "Khoảng thời gian: Toàn thời gian / Hôm nay / Tuần này / 7 ngày tới / Tháng này / Lựa chọn khác" — "Tháng này" là date range, không phải view mode. → "Tháng" view mode đã được bỏ, view mode Tuần/Ngày nằm ngoài filter → BUG FIXED.

## 02 Triage

Verdict: LIKELY FIXED.
