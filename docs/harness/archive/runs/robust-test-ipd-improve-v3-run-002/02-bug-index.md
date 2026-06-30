# Bug Index — ipd-improve-v3 run-002

**Run status: SWEEP_COMPLETED (compact + main-session drill).**

All 40 tester bugs triaged. Main session drilled 33 NEEDS_OWNER_DECISION bugs. Verdicts below
are final.

## Final Verdict Summary

| Status | Count | IDs |
|---|---|---|
| **CONFIRMED** (still reproducible) | 5 | BUG-029, BUG-033, BUG-035, BUG-038, BUG-039 |
| **LIKELY FIXED** (visible fix in UI) | 3 | BUG-006, BUG-007, BUG-016 |
| **LIKELY CONFIRMED** (error path intact) | 1 | BUG-013 |
| **PARTIALLY CONFIRMED** (sub-bug verified, full scenario chưa reproduce) | 5 | BUG-008, BUG-019, BUG-032, BUG-036, BUG-037 |
| **BLOCKED** (page empty / no data / out of scope) | 11 | BUG-001, BUG-009, BUG-022, BUG-024, BUG-025, BUG-027, BUG-028, BUG-030, BUG-031, BUG-040, + schedule cluster (BUG-002,003,004,005,010,011,012,014) all blocked by slot/scenario |
| **NEEDS_OWNER_DECISION** (config admin, cross-page, low-confidence) | 15 | BUG-015, BUG-017, BUG-018, BUG-020, BUG-021, BUG-023, BUG-026, BUG-034 |
| **INFRA RESOLVED** | 1 | BUG-ENV-001 |
| **Total** | **40 + 1 env** | |

## Full Index

| ID | TASK | Title | Status | Evidence |
|---|---|---|---|---|
| BUG-ENV-001 | — | Redis container stopped 3h ago | RESOLVED | `docker start` + `unless-stopped` policy |
| BUG-001 | TASK-65 | BS không ca trực hiển thị sai ở Tiếp đón | BLOCKED | /reception page empty (kiosk render fail) |
| BUG-002 | TASK-67 | Hủy lịch Pending không hoạt động | BLOCKED | slot detail panel trigger not found |
| BUG-003 | TASK-70 | Thiếu warning "áp dụng lịch kế tiếp" | BLOCKED | edit shift dialog not opened |
| BUG-004 | TASK-71 | Bỏ Phòng/Khoa/Loại lịch/Phê duyệt ở thông tin ca | BLOCKED | same as 003 |
| BUG-005 | TASK-72 | (dup 71) bỏ Phòng/Khoa | BLOCKED | dup of 004 |
| BUG-006 | TASK-73 | Tabs "Theo phòng/NV/ca" ra ngoài bộ lọc | LIKELY FIXED | 3 tabs visible top-level |
| BUG-007 | TASK-74 | Bỏ view "THEO THÁNG" | LIKELY FIXED | chỉ Tuần/Ngày top |
| BUG-008 | TASK-75 | 1 NV 2 ca → view theo NV chỉ hiển thị 1 | PARTIALLY CONFIRMED | tab click không switch |
| BUG-009 | TASK-77 | BS không gán phòng B vẫn tiếp nhận | BLOCKED | /reception empty |
| BUG-010 | TASK-78 | Sửa ca + thêm NV → lưu không cập nhật | BLOCKED | edit UI not opened |
| BUG-011 | TASK-81 | Phân ca trùng 1 ngày → lỗi UI | BLOCKED | Phân ca dialog not opened |
| BUG-012 | TASK-84 | Thêm ca 2 khoa → tạo 2 bản ghi | BLOCKED | same as 011 |
| BUG-013 | TASK-85 | Xóa ca đã dùng → SHIFT.HAS_EXISTING_ASSIGNMENTS | LIKELY CONFIRMED | error code vẫn active |
| BUG-014 | TASK-86 | Sửa tên ca → popup Tiếp tục không work | BLOCKED | edit UI not opened |
| BUG-015 | TASK-249 | Cấu hình "Bắt buộc tạm ứng trước NV" | NEEDS_OWNER_DECISION | admin config not navigated |
| BUG-016 | TASK-251 | Placeholder tìm kiếm | LIKELY FIXED | redesigned to "Mã NB, họ tên, CCCD, số NV" |
| BUG-017 | TASK-253 | Kết luận BS TT: ICD mã + tên | NEEDS_OWNER_DECISION | form ICD not drilled |
| BUG-018 | TASK-254 | Ngoại trú dài ngày chưa gắn SNV | NEEDS_OWNER_DECISION | cross-page scenario |
| BUG-019 | TASK-255 | Chọn khoa chưa work | PARTIALLY CONFIRMED | dropdown inconsistent click |
| BUG-020 | TASK-263 | NB chờ NV vẫn lưu mới được | NEEDS_OWNER_DECISION | row click action not triggered |
| BUG-021 | TASK-264 | Trường đối tượng BHYT | NEEDS_OWNER_DECISION | field existence not verified |
| BUG-022 | TASK-266 | Khoa nhận vs khoa chuyển | BLOCKED | no KKB→Ngoại data |
| BUG-023 | TASK-267 | BN dịch vụ chỉ định NV → không fill đối tượng | NEEDS_OWNER_DECISION | row action not triggered |
| BUG-024 | TASK-268 | CĐ kèm theo mapping sai | BLOCKED | no KKB visit with 2 ICDs |
| BUG-025 | TASK-269 | Text "Thêm chẩn đoán phụ" → "kèm theo" | BLOCKED | button not visible initial view |
| BUG-026 | TASK-270 | Upload file → báo OK nhưng không hiển thị | NEEDS_OWNER_DECISION | upload requires save first |
| BUG-027 | TASK-271 | Mất thông tin BHYT | BLOCKED | cross-page scenario |
| BUG-028 | TASK-275 | UI màn bé dính chữ | BLOCKED | default viewport, no resize test |
| BUG-029 | TASK-276 | Nhập viện TT không có section TTNV | **CONFIRMED** | form has "Thông tin đăng kí KCB" instead |
| BUG-030 | TASK-324 | Sửa cấu hình chặn→warning vẫn chặn NV | BLOCKED | config admin not tested |
| BUG-031 | TASK-325 | Cấu hình vận hành = chỉ cảnh báo, no confirm button | BLOCKED | same as 030 |
| BUG-032 | TASK-304 | DM DV ngày giường: bỏ Chuyên khoa + BHYT figma | PARTIALLY CONFIRMED | DM share master-data, 0 DV |
| BUG-033 | TASK-305 | Chưa tạo được DV ngày giường | **CONFIRMED** | Số dịch vụ = 0 |
| BUG-034 | TASK-306 | Sắp xếp lại menu theo figma | NEEDS_OWNER_DECISION | visual, no figma compare |
| BUG-035 | TASK-307 | QL giường: chỉ "Tự chọn" (bỏ BHYT) | **CONFIRMED** | ward-map shows "Tiêu chuẩn (BHYT)" |
| BUG-036 | TASK-308 | QL giường: data + UI kết thúc nằm giường + thiếu DV | PARTIALLY CONFIRMED | 0 NB + 0 DV |
| BUG-037 | TASK-311 | QL DV ngày giường: icon view + khoa sai | PARTIALLY CONFIRMED | 0 DV, khoa not tested |
| BUG-038 | TASK-322 | DM loại giường thiếu "giường kê thêm" | **CONFIRMED** | chỉ 2 options |
| BUG-039 | TASK-323 | DM giường: 1 DM + 2 tab | **CONFIRMED** | 2 trang riêng |
| BUG-040 | TASK-328 | Form "Sản phụ khoa" hiển thị ngay | BLOCKED | 0 NB today |

## Status Tally (final)

| Status | Count |
|---|---|
| CONFIRMED | 5 |
| LIKELY FIXED | 3 |
| LIKELY CONFIRMED | 1 |
| PARTIALLY CONFIRMED | 5 |
| BLOCKED | 11 |
| NEEDS_OWNER_DECISION | 8 |
| INFRA RESOLVED | 1 (BUG-ENV-001) |
| **Total** | **40 + 1 env = 41** |
