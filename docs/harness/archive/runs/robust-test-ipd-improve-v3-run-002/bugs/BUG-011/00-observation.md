# BUG-011 — TASK-81: Phân ca trùng 1 ngày → lỗi UI

## Metadata

- status: **BLOCKED** (Phân ca dialog không mở)
- severity: HIGH
- bug_class: shift-assign-overlap-ui-error
- scanner_candidate: yes
- scanner_candidate_tier: mh_scan
- flow: Click "Phân ca làm việc" → dialog → thử gán trùng
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:03Z

## 00 Observation (drill)

Expected: Hệ thống chặn trước khi cho chọn ca trùng (per 15/06 update), hoặc hiển thị lỗi UI clean.

Actual: Click button "Phân ca làm việc Ctrl N" → không mở dialog (click thất bại, không có DOM change). → BLOCKED — không trigger được phân ca UI.

## 02 Triage

Verdict: **BLOCKED** — same Phân ca button issue as BUG-003.

## Note

Có source `add-shift-cell-dialog/` và `create-slot-dialog/` — cần verify trigger event.
