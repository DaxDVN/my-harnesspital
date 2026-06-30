# BUG-006 — TASK-73: Bố cục "theo phòng/NV/ca" đưa ra ngoài bộ lọc

## Metadata

- status: **LIKELY FIXED** (visible at top, no need to enter filter dropdown)
- severity: MED
- bug_class: filter-view-tabs-moved
- scanner_candidate: no
- flow: /hospital-management/schedules
- actor: bvtest3
- route/url: /hospital-management/schedules
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T05:14Z

## 00 Observation

Expected: Bố cục "theo phòng/nhân viên/ca trực" nằm ngoài dropdown bộ lọc, có thể phân tab để UX tốt hơn.

Actual: Trên trang Lịch làm việc hiện tại, có 3 tab nằm NGOÀI dropdown filter: "Theo phòng" / "Theo nhân viên" / "Theo ca trực" (refs e59/e60/e61). Click "Theo ca trực" → view chuyển sang group theo ca. → BUG này có vẻ đã fix.

## 02 Triage

Verdict: LIKELY FIXED — chuyển sang "FIXED" nếu owner xác nhận đây là behavior mong muốn. Cần owner confirm trên UI thực tế.

Scanner promotion note: có thể promote thành rule "schedule page PHẢI có tabs Theo phòng/NV/ca trực ở top-level, không nằm trong filter dropdown".
