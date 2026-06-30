# BUG-037 — TASK-311: QL DV ngày giường: icon view + bỏ view detail + khoa sai

## Metadata

- status: **PARTIALLY CONFIRMED** (DM ngày giường 0 DV; khoa filter chưa verify)
- severity: HIGH
- bug_class: bed-day-service-view-icon-missing
- flow: /master-data-management/services (DM ngày giường)
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:09Z

## 00 Observation (drill)

Trên `/master-data-management/services`, loại "Ngày giường ngoại khoa" + "Ngày giường nội khoa" có column "Thao tác" với 0 rows (no DV to have icons). Không thể verify icon view vì không có DV.

Khoa filter: hiện tại chỉ hiển thị 1 khoa (Khoa nội) trong table. Không có NB ngày giường để test khoa filter.

## 02 Triage

Verdict: **PARTIALLY CONFIRMED** — icon view / khoa filter chưa test được vì 0 DV. Unblock BUG-033 trước.
