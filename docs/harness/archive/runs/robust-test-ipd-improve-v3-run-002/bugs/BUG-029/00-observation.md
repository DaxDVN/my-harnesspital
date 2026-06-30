# BUG-029 — TASK-276: Nhập viện trực tiếp không có section TTNV

## Metadata

- status: **CONFIRMED** (no "Thông tin nhập viện" section; has "Thông tin đăng kí KCB" instead)
- severity: HIGH
- bug_class: inpatient-direct-missing-section
- flow: /medical-visits/inpatient/create
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:07Z

## 00 Observation (drill)

Trên form Tiếp nhận trực tiếp (`/medical-visits/inpatient/create`), các sections hiện có:
1. Thông tin hành chính
2. Thông tin người thân
3. **Thông tin đăng kí KCB** (chứa: "Điều trị ngoại trú dài ngày", "Bác sĩ chỉ định", "Tỷ lệ markup giá dịch vụ", "Hình thức đến", "Ngày dự kiến nhập viện", "Khoa nhận", "Lý do nhập viện", "Ghi chú đợt")
4. Bảo hiểm (Danh sách thẻ BHYT, BH thương mại)
5. Đính kèm file
6. Lịch sử nhập viện

**KHÔNG có section "Thông tin nhập viện"** như spec §3.3. Thay vào đó, form có "Thông tin đăng kí KCB" với một số field liên quan (Khoa nhận, Lý do nhập viện, Ngày dự kiến NV).

Theo TASK-276: "Nhập viện trực tiếp không có section thông tin nhập viện" → **BUG CÒN** (section "Thông tin nhập viện" vẫn không có).

## 02 Triage

Verdict: **CONFIRMED**.

## 03 RCA

Có thể:
- Spec thay đổi (UPDATED.md §3.1) chỉ giữ field "Thông tin đăng kí KCB" + form nhập viện chi tiết chuyển sang màn khác (sau khi save initial reception)
- Hoặc FE chưa implement đầy đủ §3.3 spec

## 04 Fix Plan

So sánh spec `Tài liệu Nội trú UPDATED.md` §3.1 vs §3.3. Nếu §3.3 yêu cầu section "Thông tin nhập viện" trong form Tiếp nhận trực tiếp, cần add section. Nếu spec đã redesign (chỉ "Thông tin đăng kí KCB" thì OK), owner confirm.
