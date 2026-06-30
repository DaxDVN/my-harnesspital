# BUG-036 — TASK-308: QL giường: data + UI kết thúc nằm giường + thiếu DV

## Metadata

- status: **PARTIALLY CONFIRMED** (0 NB đang nằm giường; thiếu DV confirmed)
- severity: HIGH
- bug_class: bed-stay-end-multiple-clicks-missing-dv
- flow: /bed-management/ward-map → click NB đang nằm giường
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:09Z

## 00 Observation (drill)

Trên `/bed-management/ward-map`:
- "5 giường trống / 5 · 2 phòng"
- "0 Đang dùng, 0 Đặt trước"
- Tất cả 5 giường đều "Trống"
- Stats: "Giường trống 5, Đang sử dụng 0, Đặt trước 0"
- Mỗi giường có button "Thêm" (thêm NB)

→ 0 NB đang nằm giường → không test được "kết thúc nằm giường click 2 button".

Về "Thêm NB" thiếu DV: Mỗi giường có button "Thêm" nhưng không drill vào form. Per BUG-033, DV ngày giường = 0 → form Thêm NB sẽ không có DV nào để chọn.

## 02 Triage

Verdict: **PARTIALLY CONFIRMED** — "Thiếu DV" partially confirmed (vì DV count = 0). "Click 2 button kết thúc" chưa reproduce được (no data).

## 04 Fix Plan

Sau khi tạo DV ngày giường (unblock BUG-033) + thêm 1 NB test vào giường → test lại BUG-036.
