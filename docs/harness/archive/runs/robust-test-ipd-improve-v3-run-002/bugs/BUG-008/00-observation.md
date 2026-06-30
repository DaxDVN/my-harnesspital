# BUG-008 — TASK-75: 1 NV 2 ca → View theo NV chỉ hiển thị 1

## Metadata

- status: **PARTIALLY CONFIRMED** (tab click handler has issue)
- severity: HIGH
- bug_class: schedule-by-employee-tab-not-switching
- scanner_candidate: yes
- scanner_candidate_tier: mh_scan
- flow: /hospital-management/schedules → tab "Theo nhân viên"
- actor: bvtest3
- route/url: /hospital-management/schedules
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:03Z

## 00 Observation (drill)

Expected: Tab "Theo nhân viên" switch view → BS có nhiều ca (BS. Administrator có ≥6 Ca sáng ở Phòng khám nội 101) hiển thị tất cả.

Actual: 
- Tab "Theo nhân viên" tồn tại (ref e60), `aria-selected="false"`
- Click @e60 thất bại với "Could not locate element with role=tab name=Theo nhân viên"
- Click qua JS `target.click()` thì aria-selected vẫn false
- Click qua `agent-browser find text "Theo nhân viên" click` không có kết quả
- View KHÔNG switch sang Theo nhân viên — vẫn ở "Theo phòng"

→ **Tab click handler có bug** (không switch được sang tab "Theo nhân viên" qua bất kỳ cách nào). Có thể cần keyboard nav (arrow keys).

Vì không switch được tab → không verify được "1 NV 2 ca hiển thị 1" sub-bug.

## 02 Triage

Verdict: **PARTIALLY CONFIRMED** — bug tab click (chính) reproducible; bug sub-task (1 NV 2 ca) chưa verify được.

## 03 RCA

Source: `fe/src/modules/hospital-management/pages/schedule/schedule-page.tsx` likely dùng Radix Tabs với onValueChange, nhưng click event không trigger. Có thể:
- Component dùng `onMouseDown` không phải `onClick`
- Component keyboard-only (chỉ Tab + Enter)
- Race condition với React state update

## 04 Fix Plan

Kiểm tra `schedule-page.tsx` Tabs component — nếu Radix Tabs default thì cần dùng keyboard hoặc thêm onClick handler.
