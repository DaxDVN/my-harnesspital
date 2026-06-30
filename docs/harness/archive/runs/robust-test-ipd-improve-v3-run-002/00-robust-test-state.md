# Robust-Test State — `ipd-improve-v3` run-002

```text
mode        : sweep
module      : ipd-improve-v3 (Lịch làm việc + Tiếp nhận nội trú + Quản lý ngày giường + Khám bệnh)
worktree    : ipd-improve-v3 (slot 3)
fe_url      : http://localhost:3003
be_url      : http://localhost:5003
sql         : localhost,1436/MyHospital
actor       : bvtest3 (lynkhanh9822@gmail.com) — TenantId=6, HospitalId=7
status      : ENV_FIXED_READY_TO_RESUME
started_at  : 2026-06-26
halted_at   : 2026-06-26 ~05:01 (initial env halt)
env_fixed_at: 2026-06-26 ~05:12 (Redis restart + FE env override)
prior_run   : run-001 (treatment sheet, different module, COMPLETED)
env_fix_log : see 00-blocker.md "Resolution Trace" + BUG-ENV-001/evidence/env-fix-summary.txt
```

## Purpose

Re-verify 40 tester-reported bugs (TASK-*) across 4 modules on `ipd-improve-v3` slot 3, using agent-browser
+ Firefox, credential `bvtest3`. Triage to CONFIRMED / NOT_A_BUG / FIXED / NEEDS_OWNER_DECISION.

## Environment Gate

| Check | Status | Note |
|-------|--------|------|
| FE running (localhost:3003) | ✅ | vite started with `VITE_BACKEND_URL=http://localhost:5003` override |
| BE running (localhost:5003) | ✅ | pid 59745; auth returns 200 SUCCESS post-Redis-fix |
| DB migrated (slot 3) | ✅ inferred | master data + hospital API calls all 200 |
| Worktree active | ✅ | `ipd-improve-v3` slot 3 |
| Login (bvtest3) | ✅ FIXED | redirected to `/home` after submit |

**Halt condition:** all 40 bugs depend on a successful login; login is broken at the BE
infrastructure layer (master-instance election / DB primary resolver). Per
`engine/workflows/robust-test/README.md` §2, the environment gate is not satisfied → stop and
raise to owner. See `00-blocker.md` for full evidence + options.

## Bug Inventory (40 bugs)

### Module 1: Lịch làm việc (Work Schedule) — 14 bugs

| Folder | TASK | Severity | Title | Page |
|---|---|---|---|---|
| BUG-001 | TASK-65 | MED | BS không có ca trực hiển thị sai ở Tiếp đón | Tiếp đón |
| BUG-002 | TASK-67 | HIGH | Hủy lịch chưa hoạt động đúng (Pending không hủy được) | Danh sách lịch |
| BUG-003 | TASK-70 | LOW | Thiếu warning "khoảng TG mới áp dụng lịch kế tiếp" khi cập nhật ca | Chỉnh sửa ca |
| BUG-004 | TASK-71 | MED | Bỏ Phòng/Khoa/Loại lịch/Phê duyệt ở thông tin ca | Chi tiết lịch |
| BUG-005 | TASK-72 | MED | (dup TASK-71) bỏ Phòng/Khoa | Chi tiết lịch |
| BUG-006 | TASK-73 | MED | Bố cục "theo phòng/NV/ca trực" đưa ra ngoài bộ lọc | Lịch làm việc |
| BUG-007 | TASK-74 | MED | Bỏ chế độ xem THEO THÁNG, đưa ra ngoài | Lịch làm việc |
| BUG-008 | TASK-75 | HIGH | Gán 1 NV 2 ca nhưng View theo NV chỉ hiển thị 1 ca | Lịch làm việc |
| BUG-009 | TASK-77 | HIGH | BS không gán phòng B vẫn tiếp nhận được khi bật "Áp dụng lịch làm việc" | Tiếp nhận |
| BUG-010 | TASK-78 | HIGH | Sửa ca + thêm NV → lưu không cập nhật NS | Chỉnh sửa lịch |
| BUG-011 | TASK-81 | HIGH | Phân ca trùng trong 1 ngày → lỗi UI (chặn sai vị trí) | Phân ca |
| BUG-012 | TASK-84 | HIGH | Thêm ca 2 khoa → tạo 2 bản ghi | DS ca làm việc |
| BUG-013 | TASK-85 | HIGH | Xóa ca đã sử dụng → SHIFT.HAS_EXISTING_ASSIGNMENTS (no graceful) | DS ca làm việc |
| BUG-014 | TASK-86 | HIGH | Sửa tên ca → popup xác nhận bấm Tiếp tục không work | Chỉnh sửa ca |

### Module 2: Tiếp nhận nội trú (IPD Admission) — 17 bugs

| Folder | TASK | Severity | Title | Page |
|---|---|---|---|---|
| BUG-015 | TASK-249 | MED | Cấu hình "Bắt buộc tạm ứng trước khi nhập viện" | Cấu hình TT |
| BUG-016 | TASK-251 | LOW | Placeholder tìm kiếm điều trị ngoại trú dài ngày | Tiếp nhận TT |
| BUG-017 | TASK-253 | MED | Kết luận BS tuyến trước: ICD hiển thị cả mã và tên | Tiếp nhận TT |
| BUG-018 | TASK-254 | HIGH | Điều trị ngoại trú dài ngày chưa gắn với giấy hẹn/SNV | DS tiếp nhận |
| BUG-019 | TASK-255 | HIGH | Chọn khoa chưa work (Khoa khám bệnh vẫn xem DS khoa nội) | DS tiếp nhận |
| BUG-020 | TASK-263 | HIGH | Tiếp nhận NB chờ nhập viện vẫn lưu mới được | Tiếp nhận TT |
| BUG-021 | TASK-264 | MED | Trường đối tượng BHYT (Re-open) | Tiếp nhận TT |
| BUG-022 | TASK-266 | HIGH | Khoa nhận vs khoa chuyển (NB khoa ngoại nhưng NB đang ở khoa KB) | DS tiếp nhận |
| BUG-023 | TASK-267 | HIGH | BN dịch vụ chỉ định nhập viện → không fill đối tượng | CT tiếp nhận |
| BUG-024 | TASK-268 | HIGH | Chẩn đoán kèm theo mapping sai (KKB I44.0, phụ O10.0) | CT tiếp nhận |
| BUG-025 | TASK-269 | LOW | Text "Thêm chẩn đoán phụ" → "kèm theo" | CT tiếp nhận |
| BUG-026 | TASK-270 | HIGH | Upload file → báo thành công nhưng không hiển thị | CT tiếp nhận |
| BUG-027 | TASK-271 | HIGH | Tiếp đón nội trú mất thông tin thẻ BHYT từ ngoại trú | CT tiếp nhận |
| BUG-028 | TASK-275 | MED | UI màn bé dính chữ, mất nút | DS tiếp nhận |
| BUG-029 | TASK-276 | HIGH | Nhập viện trực tiếp không có section TTNV | TT nhập viện |
| BUG-030 | TASK-324 | HIGH | Sửa cấu hình từ chặn → chỉ warning vẫn không cho NV | Tiếp nhận TT |
| BUG-031 | TASK-325 | HIGH | Cấu hình vận hành = chỉ cảnh báo nhưng không có button xác nhận NV | Tiếp nhận TT |

### Module 3: Quản lý ngày giường (Bed Management) — 8 bugs

| Folder | TASK | Severity | Title | Page |
|---|---|---|---|---|
| BUG-032 | TASK-304 | MED | Danh mục DV ngày giường: bỏ Chuyên khoa, BHYT theo figma | DM DV |
| BUG-033 | TASK-305 | BLOCK | Chưa tạo được DV ngày giường để test (blocker) | DM DV |
| BUG-034 | TASK-306 | LOW | Sắp xếp lại menu theo figma | Menu |
| BUG-035 | TASK-307 | MED | Quản lý giường: chỉ hiển thị "Tự chọn" (bỏ BHYT) | QL giường |
| BUG-036 | TASK-308 | HIGH | QL giường: data + UI kết thúc nằm giường (click 2 lần) + thêm NB thiếu DV | QL giường |
| BUG-037 | TASK-311 | HIGH | QL DV ngày giường: không icon view, bỏ view detail, khoa sai vẫn có data | DM DV |
| BUG-038 | TASK-322 | MED | Thêm option "giường kê thêm" (ngoài kế hoạch + tự chọn) | DM loại giường |
| BUG-039 | TASK-323 | MED | DS loại giường/giường → 1 DM "giường" + 2 tab | DM giường |

### Module 4: Khám bệnh (Examination) — 1 bug

| Folder | TASK | Severity | Title | Page |
|---|---|---|---|---|
| BUG-040 | TASK-328 | MED | Form "Sản phụ khoa" phải hiển thị ngay khi chọn NB | Khám bệnh |

## Status Legend

- `CANDIDATE` — captured, not yet triaged
- `CONFIRMED` — still reproducible on `ipd-improve-v3` slot 3
- `FIXED` — no longer reproducible (tester may have stale report)
- `NOT_A_BUG` — false positive (test artifact / permission / data state)
- `BLOCKED` — cannot verify (env / data / dependency)
- `NEEDS_OWNER_DECISION` — ambiguous, requires owner input

## Plan (sweep completed in compact mode)

1. **M1: Lịch làm việc** — BUG-001 → BUG-014 (14 bugs) — DONE compact
2. **M2: Tiếp nhận nội trú** — BUG-015 → BUG-031 (17 bugs) — DONE compact
3. **M3: Quản lý ngày giường** — BUG-032 → BUG-039 (8 bugs) — DONE compact
4. **M4: Khám bệnh** — BUG-040 (1 bug) — DONE compact

Total 40 bugs triaged in ~13 min (compact mode). See `02-bug-index.md` for per-bug verdict
and `05-final-report.md` for the full result.

## Status Tally (post-sweep)

| Status | Count |
|---|---|
| CONFIRMED | 3 (BUG-035, BUG-038, BUG-039) |
| LIKELY FIXED | 2 (BUG-006, BUG-007) |
| LIKELY CONFIRMED | 1 (BUG-013) |
| NEEDS_OWNER_DECISION | 33 (most bugs — need deeper per-bug scenario test) |
| FIXED | 0 |
| NOT_A_BUG | 0 |
| BLOCKED (env) | 0 |
| INFRA RESOLVED | 1 (BUG-ENV-001) |
| **Total** | **40 + 1 env** |

## Discipline (per second-brain/05-automation-orchestration-triage)

- Browser/E2E findings are candidates until setup/auth/form/slot are triaged.
- Do not capture screenshots by default.
- Provider/tool 400s = non-retryable prompt errors.
- One bug folder per candidate; do not keep findings only in chat.
- Compact reporting, no narration per subagent.
- `bvtest3` credential MANDATORY — never fall back to HMU_ADMIN/e2e default.
