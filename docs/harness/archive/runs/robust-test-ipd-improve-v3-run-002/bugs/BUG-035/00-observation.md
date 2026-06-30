# BUG-035 — TASK-307: QL giường: chỉ "Tự chọn" (bỏ label "Tiêu chuẩn BHYT")

## Metadata

- status: **CONFIRMED** (vẫn hiển thị cả 2 label)
- severity: MED
- bug_class: bed-type-label-shows-both
- scanner_candidate: yes
- scanner_candidate_tier: review-checklist
- flow: /bed-management/ward-map
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T05:24Z

## 00 Observation

Trên ward-map (`/bed-management/ward-map`):
- Phòng Nội Bệnh 01 (PNB01): 3 giường (K.101, K.102, K.103) → hiển thị "Trống / Tự chọn"
- Phòng nội trú 01 (PNT0): 2 giường (01, 02) → hiển thị "Trống / Tiêu chuẩn (BHYT)"

Cả 2 label đều hiển thị cùng lúc. Expected theo TASK-307: chỉ hiển thị "Tự chọn", bỏ "Tiêu chuẩn BHYT". → **BUG CÒN**.

## 02 Triage

Verdict: CONFIRMED.

## Note

Spec §6.1 nói rõ: "Giường tự chọn = giường dịch vụ thêm của bệnh viện, không đăng ký với BHYT" → label BHYT không cần hiển thị nếu giường đó là tự chọn. UI hiện tại vẫn dùng "Tiêu chuẩn (BHYT)" cho phòng PNT0.
