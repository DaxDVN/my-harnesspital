# BUG-004 — TASK-71: Bỏ Phòng/Khoa/Loại lịch/Phê duyệt ở thông tin ca

## Metadata

- status: **BLOCKED** (no slot detail panel opened)
- severity: MED
- bug_class: shift-detail-overflow
- scanner_candidate: no
- flow: Click shift → panel "Chi tiết lịch làm việc"
- actor: bvtest3
- route/url: /hospital-management/schedules
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:02Z

## 00 Observation (drill)

Same as BUG-003 — không trigger được shift detail panel. → BLOCKED.

## 02 Triage

Verdict: **BLOCKED** — same blocker as BUG-003.

## Note

Spec §6 định nghĩa "thông tin ca" trong slot-detail-side-panel.tsx (theo source structure). Cần owner manual verify hoặc sửa UI để mở được detail panel.
