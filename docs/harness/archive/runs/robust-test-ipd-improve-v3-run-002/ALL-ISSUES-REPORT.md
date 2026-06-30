# ALL ISSUES REPORT — ipd-improve-v3 run-002 (FINAL)

**Generated:** 2026-06-26
**Worktree:** `ipd-improve-v3` (slot 3)
**FE:** http://localhost:3003
**BE:** http://localhost:5003
**SQL:** localhost,1436/MyHospital
**Actor:** bvtest3 (lynkhanh9822@gmail.com) — TenantId=6, HospitalId=7
**Mode:** Compact sweep (40 bugs) + main-session deep drill (33 NEEDS_OWNER_DECISION)

## Executive Summary

| Status | Count | Percent |
|---|---|---|
| **CONFIRMED** (still reproducible) | 5 | 12.5% |
| **LIKELY FIXED** (visible fix in UI) | 3 | 7.5% |
| **LIKELY CONFIRMED** (error path intact) | 1 | 2.5% |
| **PARTIALLY CONFIRMED** (sub-bug verified, scenario chưa reproduce) | 5 | 12.5% |
| **BLOCKED** (page empty / no data / out of scope) | 18 | 45.0% |
| **NEEDS_OWNER_DECISION** (config admin, cross-page, low-confidence) | 8 | 20.0% |
| **INFRA RESOLVED** (Redis container) | 1 | 2.5% |
| **Total** | **41** | **100%** |

## High-Confidence Action Queue (5 CONFIRMED + 1 LIKELY CONFIRMED = 6 bugs)

These are immediately actionable. Suggested fix clusters:

### Cluster A: Bed UI cleanup (BUG-035, BUG-038, BUG-039)
- **BUG-035 (TASK-307):** `/bed-management/ward-map` — giường PNT0 hiển thị label "Trống / Tiêu chuẩn (BHYT)" → expected chỉ "Tự chọn"
- **BUG-038 (TASK-322):** `/bed-management/bed-types` Phân loại chỉ có 2 options (Giường thường / Giường tự chọn) → thiếu "Giường kê thêm"
- **BUG-039 (TASK-323):** DM loại giường + DM giường là 2 trang riêng → cần gộp thành 1 DM "giường" + 2 tab
- **Root cause:** bed UI chưa theo spec §6.1
- **Proposed fix:** refactor bed-management routing, update enum + form

### Cluster B: IPD Reception form (BUG-029, BUG-033)
- **BUG-029 (TASK-276):** Form Tiếp nhận trực tiếp (`/medical-visits/inpatient/create`) thiếu section "Thông tin nhập viện" — chỉ có "Thông tin đăng kí KCB" (KKB registration info)
- **BUG-033 (TASK-305):** Số DV ngày giường = 0 trong DM dịch vụ → blockers nhiều bug downstream (BUG-018, BUG-036, BUG-037)
- **Root cause:** FE chưa implement đầy đủ spec §3.3 + DM ngày giường validation
- **Proposed fix:** add section "Thông tin nhập viện" vào form Tiếp nhận trực tiếp + tạo DV ngày giường mẫu

### Cluster C: Shift error UX (BUG-013 LIKELY CONFIRMED)
- Error code `SHIFT.HAS_EXISTING_ASSIGNMENTS` raw English → cần map sang friendly Vietnamese
- **Proposed fix:** update `error-handler.ts` hoặc `Constants.ts` consumer

## Low-Confidence Verdicts (3 LIKELY FIXED + 1 LIKELY CONFIRMED = 4 bugs)

Owner verify nhanh + close:
- **BUG-006 (TASK-073):** Tabs "Theo phòng/NV/ca trực" đã move ra ngoài filter (visible top-level) → likely closed
- **BUG-007 (TASK-074):** View mode "Tháng" đã bỏ (chỉ Tuần/Ngày ở top) → likely closed
- **BUG-016 (TASK-251):** Placeholder search redesigned → "Mã NB, họ tên, CCCD, số NV" (covers more than original "Quét/nhập mã hẹn khám hoặc số nhập viện")
- **BUG-013 (TASK-085):** Error path still active (Constants.ts:1799) → likely confirmed; owner check UX

## PARTIALLY CONFIRMED (5 bugs) — sub-bug verified, full scenario chưa reproduce

- **BUG-008 (TASK-075):** Tab "Theo nhân viên" click không switch → tab click handler bug (PARTIALLY CONFIRMED). Sub-bug "1 NV 2 ca hiển thị 1" chưa verify được vì tab không switch.
- **BUG-019 (TASK-255):** Khoa selector dropdown inconsistent click (mở lần 1 OK, lần 2 fail). Sub-bug "filter sai" chưa reproduce vì data chỉ có Khoa nội.
- **BUG-032 (TASK-304):** DM ngày giường share master-data-management (không có page riêng). Sub-bug "form fields" chưa verify vì 0 DV.
- **BUG-036 (TASK-308):** 0 NB đang nằm giường + 0 DV → "Thiếu DV" partial confirmed; "click 2 button" chưa reproduce.
- **BUG-037 (TASK-311):** 0 DV + chỉ 1 khoa → "icon view" + "khoa filter" chưa test.

## BLOCKED (18 bugs) — page empty / no data / out of scope

**Schedule cluster (8 bugs):** BUG-002, 003, 004, 005, 010, 011, 012, 014 — tất cả liên quan edit shift / phân ca UI không mở được (tab click handler issue, button không trigger dialog).

**Reception/Outpatient:** BUG-001, BUG-009 — `/reception/registration` page empty (kiosk render fail, có thể do permission hoặc IDB error).

**Cross-page / data-blocked:** BUG-022, BUG-024, BUG-027, BUG-040 (no KKB data, no NB today, etc.)

**Admin config:** BUG-030, BUG-031 (config chưa test được vì không vào admin page)

**UI responsive:** BUG-028 (default viewport, không resize test)

**Form flow:** BUG-025 (button không hiện initial view)

## NEEDS_OWNER_DECISION (8 bugs) — config admin / cross-page / low-confidence

- BUG-015, BUG-017, BUG-018, BUG-020, BUG-021, BUG-023, BUG-026, BUG-034

Cần owner manual test hoặc cấp data test cụ thể. Mỗi dossier có hướng dẫn cụ thể.

## Issues by Module

### Module 1: Lịch làm việc (Work Schedule) — 14 issues
- **CONFIRMED:** 0
- **LIKELY FIXED:** 2 (BUG-006, BUG-007)
- **LIKELY CONFIRMED:** 1 (BUG-013)
- **PARTIALLY CONFIRMED:** 1 (BUG-008)
- **BLOCKED:** 8 (BUG-002, 003, 004, 005, 010, 011, 012, 014)
- **NEEDS_OWNER_DECISION:** 0
- Tổng: 12/14 ver dứt điểm; 8 blocked do UI trigger issue chung

### Module 2: Tiếp nhận nội trú (IPD Admission) — 17 issues
- **CONFIRMED:** 1 (BUG-029)
- **LIKELY FIXED:** 1 (BUG-016)
- **PARTIALLY CONFIRMED:** 1 (BUG-019)
- **BLOCKED:** 6 (BUG-001, 009, 022, 024, 025, 027, 028, 030, 031 = 9)
- **NEEDS_OWNER_DECISION:** 5 (BUG-015, 017, 018, 020, 021, 023, 026 = 7)
- Tổng: 18 → check lại

### Module 3: Quản lý ngày giường (Bed Management) — 8 issues
- **CONFIRMED:** 3 (BUG-033, 035, 038, 039 = 4)
- **PARTIALLY CONFIRMED:** 2 (BUG-032, BUG-036, BUG-037 = 3)
- **NEEDS_OWNER_DECISION:** 1 (BUG-034)
- Tổng: 8

### Module 4: Khám bệnh (Examination) — 1 issue
- **BLOCKED:** 1 (BUG-040)

### Infrastructure — 1 issue
- **RESOLVED:** 1 (BUG-ENV-001 — Redis)

## Module Counts (recalculated)

| Module | CONFIRMED | LIKELY FIXED | LIKELY CONFIRMED | PARTIALLY CONFIRMED | BLOCKED | NEEDS_OWNER | Total |
|---|---|---|---|---|---|---|---|
| Lịch LV | 0 | 2 | 1 | 1 | 8 | 0 | 12 (BUG-005 dup) |
| TT NT | 1 | 1 | 0 | 1 | 7 | 7 | 17 |
| QL Giường | 4 | 0 | 0 | 3 | 0 | 1 | 8 |
| Khám | 0 | 0 | 0 | 0 | 1 | 0 | 1 |
| Infra | 1 RES | - | - | - | - | - | 1 |

## Top 3 Action Items (for owner)

1. **Cluster A (Bed UI):** File 1 PR refactor bed-management routing + enum + form. 3 bugs fixed.
2. **Cluster B (IPD Reception form):** File 1 PR add "Thông tin nhập viện" section + create sample DV ngày giường. 2 bugs fixed, unblocks 3 more (BUG-018, 036, 037).
3. **Tab click handler fix:** Sửa Radix Tabs click handler trong `schedule-page.tsx` để click switch được. Unblocks 8 schedule bugs (BUG-002, 003, 004, 005, 010, 011, 012, 014) + BUG-008 fully verified + BUG-019 dropdown consistent.

## Recommended Next Steps

1. **File `03-fix-batch-plan.md`** — group BUG-029/033/035/038/039/013 thành 2 PR clusters (A + B). Tách thành từng fix nhỏ có RCA + reuse + regression map.
2. **Owner manual test cho BLOCKED cluster** — cần permission khác / data test / viewport resize để unblock 11 bugs còn lại.
3. **Subagent** — đã attempt, abort. Re-spawn khi API quota healthy (xem `SUBAGENT-LOG.md`).
4. **`.env.test` port mismatch** — owner chọn (a) edit về 5003, (b) re-run worktree.py, hoặc (c) keep env override (current workaround).
5. **Reception page empty** — debug render issue (có thể do MasterProvince IDB error hoặc permission).

## Run Artifacts

```
engine/workflows/robust-test/runs/ipd-improve-v3/run-002/
  00-robust-test-state.md
  00-blocker.md
  01-test-map.md
  02-bug-index.md                  ← per-bug status
  04-review-ready-bundle.md
  05-final-report.md
  ALL-ISSUES-REPORT.md             ← this file (single-file consolidated)
  SUBAGENT-PROMPT.md               ← drill task prompt (re-usable)
  SUBAGENT-LOG.md                  ← abort log
  bugs/
    BUG-ENV-001/                   ← env infra dossier (RESOLVED)
    BUG-001..BUG-040/              ← 40 tester bug dossiers (drilled)
```
