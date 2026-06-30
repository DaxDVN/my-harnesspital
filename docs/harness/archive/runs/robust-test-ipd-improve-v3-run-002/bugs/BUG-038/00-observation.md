# BUG-038 — TASK-322: Thêm option "giường kê thêm" (DM loại giường)

## Metadata

- status: **CONFIRMED** (option chưa có)
- severity: MED
- bug_class: bed-type-missing-extra-option
- scanner_candidate: yes
- scanner_candidate_tier: review-checklist
- flow: /bed-management/bed-types → Thêm loại giường → Phân loại
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T05:24Z

## 00 Observation

Trên trang `/bed-management/bed-types`, các loại giường hiện có Phân loại:
- GTC01 "Giường tự chọn phòng VIP" → "Giường tự chọn"
- HSTC "Hồi sức tích cực" → "Giường thường"
- N01, NK1, NKL1 → "Giường thường"

Expected per TASK-322: có thêm option "Giường kê thêm" (ngoài "Giường kế hoạch" và "Giường tự chọn"). Hiện tại chỉ có "Giường thường" (= kế hoạch, đăng ký BHYT) và "Giường tự chọn" (= dịch vụ thêm). "Giường kê thêm" chưa có. → **BUG CÒN**.

## 02 Triage

Verdict: CONFIRMED.

## Note

Spec §6.1: 2 loại = "Giường thường" (= BV đăng ký BHYT) + "Giường tự chọn" (= dịch vụ). TASK-322 muốn thêm option thứ 3 "Giường kê thêm" (VD: kê thêm giường phụ khi quá tải). Cần update spec + cấu hình loại giường.
