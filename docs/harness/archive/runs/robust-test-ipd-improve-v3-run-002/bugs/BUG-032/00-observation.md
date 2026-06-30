# BUG-032 — TASK-304: DM DV ngày giường: bỏ Chuyên khoa + BHYT theo figma

## Metadata

- status: **PARTIALLY CONFIRMED** (DM ngày giường dùng chung DM dịch vụ; 0 DV)
- severity: MED
- bug_class: bed-day-service-form-not-matching-figma
- flow: /master-data-management/services
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:09Z

## 00 Observation (drill)

DM DV ngày giường nằm ở `/master-data-management/services` (chung DM dịch vụ), với:
- Nhóm dịch vụ "Ngày giường" (NG) — 1 nhóm
- Loại dịch vụ: "Ngày giường ngoại khoa" (NGNK) + "Ngày giường nội khoa" (NGNK) — 2 loại
- DV ngày giường: 0 DV (Số dịch vụ = 0, Số phòng = 0, Người thực hiện = 0)

DM ngày giường đang share với DM DV chung (master-data-management), không có page config riêng "Danh mục dịch vụ ngày giường" với fields riêng. Bug TASK-304 nói "bỏ thông tin Chuyên khoa, Riêng với BHYT không sử dụng component cũ, thay đổi như figma" — cần drill vào form Thêm DV ngày giường để verify fields.

## 02 Triage

Verdict: **PARTIALLY CONFIRMED** — DM ngày giường không có trang riêng (dùng chung master-data-management). Bug BUG-033 (chưa tạo được DV) → 0 DV → không thể verify form fields. Owner nên test thủ công tạo DV ngày giường.

## Note

Cấu trúc hiện tại: DM dịch vụ → Nhóm "Ngày giường" → Loại "Ngày giường ngoại/nội khoa" → DV. Form DV có thể có fields BHYT riêng (theo TASK-304).
