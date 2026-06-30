# BUG-039 — TASK-323: DM loại giường + giường → 1 DM "giường" + 2 tab

## Metadata

- status: **CONFIRMED** (vẫn 2 trang riêng)
- severity: MED
- bug_class: bed-catalog-not-unified
- scanner_candidate: no
- flow: Menu Quản trị → DM giường
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T05:24Z

## 00 Observation

Trong menu hiện tại, có 2 route riêng:
- `/bed-management/bed-types` — DM loại giường
- `/bed-management/beds` — DM giường (chưa visit)

Expected per TASK-323: gộp thành 1 DM "Danh mục giường" với 2 tab (Loại giường + Giường) như cách "DM loại DV / DV" đã làm. Hiện tại 2 trang riêng → **BUG CÒN**.

## 02 Triage

Verdict: CONFIRMED.
