# Robust-Test Review-Ready Bundle — ipd-improve-v3 run-002

## Purpose

For a higher-reasoning review agent (or owner) to triage the 40-bug sweep outcome and decide
the next fix cycle. Compact mode — 33/40 bugs are NEEDS_OWNER_DECISION (deeper drill needed).
The 3 CONFIRMED + 2 LIKELY FIXED + 1 LIKELY CONFIRMED are immediately actionable.

## Bug Index (high-confidence verdicts only)

| Bug | Status | Severity | Title | Fix priority |
|---|---|---|---|---|
| BUG-ENV-001 | RESOLVED | BLOCK | Slot 3 BE master-instance timeout on Authenticate (Redis container) | done |
| BUG-006 | LIKELY FIXED | MED | Tabs "Theo phòng/NV/ca" đã move ra ngoài filter | verify + close |
| BUG-007 | LIKELY FIXED | MED | Bỏ view "THEO THÁNG" | verify + close |
| BUG-013 | LIKELY CONFIRMED | HIGH | SHIFT.HAS_EXISTING_ASSIGNMENTS error path vẫn active | confirm + UX-fy error |
| BUG-035 | CONFIRMED | MED | QL giường vẫn hiển thị "Tiêu chuẩn (BHYT)" + "Tự chọn" | **fix** |
| BUG-038 | CONFIRMED | MED | DM loại giường thiếu option "Giường kê thêm" | **fix** |
| BUG-039 | CONFIRMED | MED | DM giường: 2 trang riêng, chưa gộp thành 1 DM + 2 tab | **fix** |

## Bug Index (lower-confidence — NEEDS_OWNER_DECISION, 33 bugs)

| Bug | TASK | Title | Suggested next step |
|---|---|---|---|
| BUG-001 | TASK-65 | BS không ca trực hiển thị sai ở Tiếp đón | verify trên màn Tiếp đón ngoại trú (out of scope current sweep) |
| BUG-002 | TASK-67 | Hủy lịch Pending không hoạt động | setup Pending schedule assignment → click Hủy |
| BUG-003 | TASK-70 | Thiếu warning "áp dụng lịch kế tiếp" | open Chỉnh sửa ca → đổi giờ → check warning |
| BUG-004 | TASK-71 | Bỏ Phòng/Khoa/Loại lịch/Phê duyệt ở TT ca | open Chi tiết lịch → check fields |
| BUG-005 | TASK-72 | (dup 71) bỏ Phòng/Khoa | same as 004 |
| BUG-008 | TASK-75 | 1 NV 2 ca → view theo NV chỉ hiển thị 1 | fix tab click handler (role=tab click failed) → retest |
| BUG-009 | TASK-77 | BS không gán phòng B vẫn tiếp nhận được | enable "Áp dụng lịch làm việc" → test scenario |
| BUG-010 | TASK-78 | Sửa ca + thêm NV → lưu không cập nhật | drill vào Chỉnh sửa ca |
| BUG-011 | TASK-81 | Phân ca trùng 1 ngày → lỗi UI | click Phân ca → thử gán trùng |
| BUG-012 | TASK-84 | Thêm ca 2 khoa → tạo 2 bản ghi | DS ca làm việc → Thêm ca → chọn 2 khoa |
| BUG-014 | TASK-86 | Sửa tên ca → popup Tiếp tục không work | DS ca làm việc → Chỉnh sửa → đổi tên → popup |
| BUG-015 | TASK-249 | Cấu hình "Bắt buộc tạm ứng trước NV" | Cấu hình thanh toán (admin) |
| BUG-016 | TASK-251 | Placeholder tìm kiếm ngoại trú dài ngày | Tiếp nhận trực tiếp page |
| BUG-017 | TASK-253 | Kết luận BS TT: ICD hiển thị cả mã và tên | form Tiếp nhận trực tiếp |
| BUG-018 | TASK-254 | Ngoại trú dài ngày chưa gắn giấy hẹn/SNV | test scenario cross-page |
| BUG-019 | TASK-255 | Chọn khoa chưa work (filter sai) | fix Khoa selector click → test |
| BUG-020 | TASK-263 | NB chờ NV vẫn lưu mới được | test: pick NB "Chờ NV" → tạo mới |
| BUG-021 | TASK-264 | Trường đối tượng BHYT (Re-open) | verify field exists in form |
| BUG-022 | TASK-266 | Khoa nhận vs khoa chuyển sai | test KKB → Ngoại admission |
| BUG-023 | TASK-267 | BN dịch vụ chỉ định NV → không fill đối tượng | test scenario |
| BUG-024 | TASK-268 | CĐ kèm theo mapping sai | test scenario 2 ICD KKB |
| BUG-025 | TASK-269 | Text "Thêm chẩn đoán phụ" → "kèm theo" | open form NV → check button text |
| BUG-026 | TASK-270 | Upload file → báo OK nhưng không hiển thị | test upload + reload |
| BUG-027 | TASK-271 | Mất thông tin BHYT khi tiếp đón nội trú | cross-page scenario |
| BUG-028 | TASK-275 | UI màn bé dính chữ, mất nút | resize viewport → retest |
| BUG-029 | TASK-276 | Nhập viện TT không có section TTNV | click "Tiếp nhận trực tiếp" → form create |
| BUG-030 | TASK-324 | Sửa cấu hình chặn→warning vẫn chặn NV | test config toggle + retest NV |
| BUG-031 | TASK-325 | Cấu hình vận hành = chỉ cảnh báo, no confirm button | same as 030 + check confirm button |
| BUG-032 | TASK-304 | DM DV ngày giường: bỏ Chuyên khoa + BHYT figma | navigate to DM DV page → Thêm |
| BUG-033 | TASK-305 | Chưa tạo được DV ngày giường (blocker) | test Thêm DV → reproduce |
| BUG-034 | TASK-306 | Sắp xếp lại menu theo figma | compare menu vs figma |
| BUG-036 | TASK-308 | QL giường: data + UI kết thúc nằm giường + thiếu DV | need 1 NB đang nằm giường (current count 0) |
| BUG-037 | TASK-311 | QL DV ngày giường: icon view + khoa sai | navigate to DM DV page |
| BUG-040 | TASK-328 | Form "Sản phụ khoa" hiển thị ngay khi chọn NB | test NB cấu hình sản phụ khoa |

## Fix Clusters (for the 3 CONFIRMED)

| Cluster | Bugs | Root cause | Proposed fix |
|---|---|---|---|
| Bed UI cleanup | BUG-035, BUG-039 | bed UI chưa unified theo spec | refactor ward-map: chỉ hiển thị "Tự chọn" cho giường không-BHYT; gộp DM loại giường + DM giường thành 1 page với 2 tab |
| Bed type option | BUG-038 | spec §6.1 chưa có option "Giường kê thêm" | update spec + cấu hình DM loại giường: thêm option "Giường kê thêm" |

## High-Risk Review Targets

- BUG-013 (LIKELY CONFIRMED HIGH) — error path `SHIFT.HAS_EXISTING_ASSIGNMENTS` vẫn active, có thể là UX issue (raw English error) thay vì logic bug. Worth checking if mapping hiện tại có render ra toast tiếng Việt thân thiện chưa.
- 33 NEEDS_OWNER_DECISION bugs chưa verified — risk rằng nhiều bug đã âm thầm tồn tại nhưng compact sweep missed.

## Reuse Evidence (per quality-gates.md)

This sweep không propose code fix nào (chỉ verify), nên reuse evidence section N/A.

## Regression Map (N/A cho compact sweep)

N/A — no code changes proposed. For each confirmed bug, the regression map will be in the per-bug dossier when fix is proposed.

## Scanner / Rule Promotion Candidates

- **BUG-008 / BUG-019** — tab/dropdown click via `agent-browser click` không switch. → Có thể do FE dùng keyboard nav hoặc event handler đặc biệt. Promote thành `review-checklist` rule: "Schedule tabs Theo phòng/NV/ca phải switch được bằng click chuột bình thường" + "Khoa selector phải mở dropdown bằng click chuột bình thường".
- **BUG-035, BUG-038, BUG-039** — UI theo spec. Promote thành `review-checklist` rule so future spec changes are caught: "Ward map giường chỉ hiển thị label 'Tự chọn' (không 'Tiêu chuẩn BHYT')" + "DM loại giường có 3 option: Giường thường / Tự chọn / Kê thêm" + "DM giường là 1 page với 2 tab".
- **BUG-ENV-001** — promote thành `mh_scan` rule: "Slot health check — POST /json/reply/Authenticate với bvtest3 phải trả UserId non-null trong vòng 10s". Add to `scripts/slot_health.py` (suggest new file).

## Retest Coverage

- targeted retests: 0 (compact mode không retest cụ thể bug nào)
- sweep/regression retests: 0
- skipped and why: most bugs deferred due to 90-min sweep budget

## Review Questions for Higher-Reasoning Reviewer

1. Với 3 CONFIRMED bugs (035, 038, 039), fix approach nào là minimum correct?
   - BUG-035: chỉ ẩn label "Tiêu chuẩn (BHYT)" cho ward-map → 1 dòng CSS/conditional
   - BUG-038: thêm option "Giường kê thêm" vào enum Phân loại → 1 dòng + migration
   - BUG-039: refactor 2 page thành 1 page với 2 tab → larger refactor; có thể tách thành 1 PR riêng
2. 33 NEEDS_OWNER_DECISION bugs — owner muốn:
   - (a) drill sâu với owner-instruction per bug → ~3-4 giờ
   - (b) assign cho FE-dev từng bug tự verify
   - (c) accept current state và close run
3. `.env.test` port mismatch — owner muốn:
   - (a) edit file về 5003
   - (b) re-run worktree.py
   - (c) keep env override (current)

## Pointers

- Run state: `00-robust-test-state.md`
- Env blocker + resolution: `00-blocker.md`
- Bug index: `02-bug-index.md`
- Final report: `05-final-report.md`
- BUG-ENV-001 dossier: `bugs/BUG-ENV-001/` (with 11 evidence files)
- BUG-001..040 dossiers: `bugs/BUG-NNN/00-observation.md` (40 files, 1-2 KB each)
