# SUBAGENT TASK PROMPT — deep drill 33 NEEDS_OWNER_DECISION bugs

**Spawned by:** main pm-orchestrator session
**Working dir:** `engine/workflows/robust-test/runs/ipd-improve-v3/run-002/`
**Worktree:** `ipd-improve-v3` (slot 3)
**Mode:** Browser-based testing, bounded, no source edit

---

## Context (read this first)

You are a subagent spawned by the main session to do **deep drill** on 33 bugs that the
main session marked as `NEEDS_OWNER_DECISION` because the 90-min compact sweep was not
enough to drill into each scenario.

Prior state: see `00-robust-test-state.md`, `02-bug-index.md`, `04-review-ready-bundle.md`,
`05-final-report.md`, and the individual `bugs/BUG-NNN/00-observation.md` dossiers. The
main session already verified:
- 3 CONFIRMED: BUG-035, BUG-038, BUG-039
- 2 LIKELY FIXED: BUG-006, BUG-007
- 1 LIKELY CONFIRMED: BUG-013
- 33 NEEDS_OWNER_DECISION: your work
- 1 INFRA RESOLVED: BUG-ENV-001 (Redis restart)

Environment: `ipd-improve-v3` worktree is up. BE is on port 5003 (pid 80391, running
~30 min). Redis container `redis-hospital` is up with `unless-stopped` policy.

**FE vite dev is NOT running** — main session killed it at cleanup. **You need to start it**
with the right env override (see Setup below).

---

## Setup (do this before testing)

```bash
# 1. Start FE with the right VITE_BACKEND_URL override
cd /home/dax/Documents/arabica/roast/worktrees/ipd-improve-v3/fe
VITE_BACKEND_URL=http://localhost:5003 nohup npm run dev:test > /tmp/fe-drill.log 2>&1 &
sleep 5
curl -s -o /dev/null -w "FE:%{http_code}\n" http://localhost:3003/

# 2. Open agent-browser to login page
agent-browser open http://localhost:3003/auth/signin

# 3. Login with bvtest3 (MANDATORY — never fall back to HMU_ADMIN)
#    Fill Mã khách hàng = bvtest3, Tên đăng nhập = lynkhanh9822@gmail.com, Mật khẩu = 12.[s7HXZQ;NfAoF
#    Use `agent-browser click @ref` + `agent-browser keyboard type "text"` (NOT `type @ref` — that fails for React Hook Form inputs)
```

Session TTL is 5 min. If you get redirected to `/auth/signin?next=...` mid-test, re-login.

---

## The 33 bugs to drill (by ID, in order)

### Module 1: Lịch làm việc (14 bugs, 11 NEEDS here)

- **BUG-001 / TASK-65** — "BS không ca trực hiển thị sai ở Tiếp đón". Out of M1 scope (Tiếp đón = outpatient reception). Try `/reception/...` routes. If not reachable from current worktree, mark `BLOCKED-OUT-OF-SCOPE` with reason.
- **BUG-002 / TASK-67** — "Hủy lịch Pending không hoạt động". Click button Hủy on a schedule assignment. If no Pending assignment visible, create one via Phân ca làm việc.
- **BUG-003 / TASK-70** — "Thiếu warning 'áp dụng lịch kế tiếp'". Open Chỉnh sửa ca (click a Ca sáng on grid) → change thời gian → check for warning text.
- **BUG-004 / TASK-71** — "Bỏ Phòng/Khoa/Loại lịch/Phê duyệt ở thông tin ca". Open Chi tiết lịch (panel detail) → check if those fields are present or absent.
- **BUG-005 / TASK-72** — (dup of 71). Same verification as BUG-004. If both still present, mark FIXED-or-NOT-A-BUG with reason.
- **BUG-008 / TASK-75** — "1 NV 2 ca → view theo NV chỉ hiển thị 1". Try clicking "Theo nhân viên" tab. If click doesn't switch, that's a separate bug from TASK-75 (tab handler issue). Then if you CAN switch, check if BS. Administrator (who has multiple Ca sáng in Phòng khám nội 101) shows all his shifts in NV view.
- **BUG-009 / TASK-77** — "BS không gán phòng B vẫn tiếp nhận được". Out of M1 scope (Tiếp nhận). If not reachable, mark `BLOCKED-OUT-OF-SCOPE`.
- **BUG-010 / TASK-78** — "Sửa ca + thêm NV → lưu không cập nhật". Open Chỉnh sửa ca, add a NV, save, verify data updated. If hard, mark `BLOCKED-NEED-MORE-DATA`.
- **BUG-011 / TASK-81** — "Phân ca trùng 1 ngày → lỗi UI". Click Phân ca làm việc button (top-right) → try to assign same doctor to 2 overlapping shifts. Check if system chặn or just báo lỗi.
- **BUG-012 / TASK-84** — "Thêm ca 2 khoa → tạo 2 bản ghi". Navigate to `/bed-management/shifts` or similar. If no obvious route, search routes for "ca làm việc" page. Try Thêm ca, chọn 2 khoa, save, verify single vs duplicate.
- **BUG-014 / TASK-86** — "Sửa tên ca → popup Tiếp tục không work". Same page as 012. Edit tên, click Cập nhật, see popup, click Tiếp tục.

### Module 2: Tiếp nhận nội trú (17 bugs, all 17 NEEDS)

Working page: `/medical-visits/inpatient` (DS tiếp nhận nội trú).

- **BUG-015 / TASK-249** — Cấu hình "Bắt buộc tạm ứng trước NV". Cấu hình admin, possibly `/setting-management/...` or similar. Check if flag exists.
- **BUG-016 / TASK-251** — Placeholder "Quét/nhập mã hẹn khám hoặc số nhập viện". Navigate to "Tiếp nhận trực tiếp" (button on DS page or `/medical-visits/inpatient/create`) — check search box placeholder.
- **BUG-017 / TASK-253** — ICD hiển thị cả mã và tên. In form Tiếp nhận trực tiếp, look at "Kết luận BS tuyến trước" section. Select an ICD, verify dropdown shows "(mã) tên".
- **BUG-018 / TASK-254** — Ngoại trú dài ngày chưa gắn với giấy hẹn/SNV. In form Tiếp nhận, search for an existing SNV and see if it links correctly.
- **BUG-019 / TASK-255** — Chọn khoa chưa work. Click button "Khoa" on top header (or "Chọn khoa"). Try mouse-event click via `agent-browser eval` (regular click may fail if FE uses keyboard nav). Pick "Khoa khám bệnh" → verify list filters to only KB patients (not all).
- **BUG-020 / TASK-263** — NB chờ NV vẫn lưu mới được. Click a row with status "Chờ nhập viện" (rows 2,3,4,5 in current data) → try to create new admission → verify hệ thống chặn.
- **BUG-021 / TASK-264** — Trường đối tượng BHYT. In form, check if "Đối tượng BHYT" field exists in the thông tin BHYT section.
- **BUG-022 / TASK-266** — Khoa nhận vs khoa chuyển. Hard to test without admission order data. If can't, mark `BLOCKED-NEED-MORE-DATA`.
- **BUG-023 / TASK-267** — BN dịch vụ chỉ định NV → không fill đối tượng. Click a row with "Đối tượng = Dịch vụ" (rows 4, 5, 6) → see if đối tượng autofills when creating admission.
- **BUG-024 / TASK-268** — CĐ kèm theo mapping. Need KKB visit with 2 ICDs. Hard without data. Mark `BLOCKED-NEED-MORE-DATA`.
- **BUG-025 / TASK-269** — Text "Thêm chẩn đoán phụ" → "kèm theo". In form nhập viện, find button for adding diagnosis. Check its text.
- **BUG-026 / TASK-270** — Upload file không hiển thị. In form TT hành chính, click Thêm file, select any file, save, verify it shows in list.
- **BUG-027 / TASK-271** — Mất thông tin BHYT. Hard without OPD→IPD cross scenario. Mark `BLOCKED-NEED-MORE-DATA`.
- **BUG-028 / TASK-275** — UI màn bé dính chữ. Use `agent-browser eval` to set window.innerWidth = 600 or similar, then snapshot. If UI breaks, CONFIRM.
- **BUG-029 / TASK-276** — Nhập viện TT không có section TTNV. Click "Tiếp nhận trực tiếp" button on DS page → check if form has "Thông tin nhập viện" section.
- **BUG-030 / TASK-324** — Sửa cấu hình chặn→warning vẫn chặn NV. Hard without config access. Mark `BLOCKED-NEED-MORE-DATA`.
- **BUG-031 / TASK-325** — Cấu hình vận hành = chỉ cảnh báo, no confirm button. Same as 030.

### Module 3: QL ngày giường (8 bugs, 5 NEEDS here)

- **BUG-032 / TASK-304** — DM DV ngày giường: bỏ Chuyên khoa + BHYT theo figma. Navigate to DM DV ngày giường. Try routes: `/bed-management/bed-day-services`, `/bed-management/services`, or check Quản trị menu.
- **BUG-033 / TASK-305** — Chưa tạo được DV ngày giường. Same page. Click Thêm DV → try to save with required fields → see if it works.
- **BUG-034 / TASK-306** — Sắp xếp lại menu theo figma. Visual comparison only. Note in dossier.
- **BUG-036 / TASK-308** — QL giường: data + UI kết thúc nằm giường + thiếu DV. Currently 0 NB đang nằm giường. Mark `BLOCKED-NO-DATA` or try to add 1 NB to test.
- **BUG-037 / TASK-311** — QL DV ngày giường: icon view + khoa sai. Same as 032.

### Module 4: Khám bệnh (1 bug, 1 NEEDS)

- **BUG-040 / TASK-328** — Form "Sản phụ khoa" hiển thị ngay khi chọn NB. Navigate `/examination/*`. Pick a NB that has "Sản phụ khoa" form config → verify form renders correctly on first view.

---

## Output Protocol (strict)

For EACH of the 33 bug dossiers, you must:

1. **Read** `bugs/BUG-NNN/00-observation.md` (the compact version from main session).
2. **Drill** the bug using agent-browser per the hint above. Time-box each bug to ~3-5 min.
3. **Update** the dossier with new sections:
   - Change `status` to: `CONFIRMED` / `FIXED` / `NOT_A_BUG` / `BLOCKED-OUT-OF-SCOPE` / `BLOCKED-NEED-MORE-DATA` / `BLOCKED-NO-DATA` / `STILL_NEEDS_OWNER` (with reason).
   - Update `severity` if changed.
   - Fill in `03 RCA` section with file:line evidence if CONFIRMED.
   - Fill in `04 Fix Plan` section with reuse evidence, regression map, proposed fix, risk, validation.
   - Add a new `08 Drill evidence` section at the bottom with: page visited, button clicks tried, network requests observed, agent-browser snapshot excerpt, exact failure or success.
4. **Write back** to the same file path.

For bugs you cannot drill, **state the reason** clearly (out of scope, no data, click handler broken, etc).

---

## Hard Constraints

- **DO NOT edit** any source file in `worktrees/ipd-improve-v3/{fe,be,docs}`. Only edit files in `engine/workflows/robust-test/runs/ipd-improve-v3/run-002/bugs/BUG-NNN/`.
- **DO NOT run** DB migrations, DTO regen, or `worktree.py` commands. The env is already up.
- **DO NOT capture screenshots** by default. Use `agent-browser snapshot -i` for text snapshots only.
- **DO NOT use HMU_ADMIN** or other credentials. **MUST use** `bvtest3` per `engine/rules/session-boot-details.md`.
- **DO NOT change** the Redis container or restart BE.
- **MUST stop** and report if you hit a BLOCK that the main session could not (e.g., a CORS issue, a server 500, a page that won't load). Don't fabricate verdicts.

---

## Final Output

After drilling all 33 bugs, write `SUBAGENT-LOG.md` to the same folder (`engine/workflows/robust-test/runs/ipd-improve-v3/run-002/SUBAGENT-LOG.md`) with:

```text
# Subagent Drill Log

Started: <timestamp>
Finished: <timestamp>
Total time: <minutes>

## Summary

| Status | Count | Bug IDs |
|---|---|---|
| CONFIRMED | N | BUG-XXX, BUG-YYY |
| FIXED | N | BUG-XXX, BUG-YYY |
| NOT_A_BUG | N | BUG-XXX |
| BLOCKED-* | N | BUG-XXX, BUG-YYY |
| STILL_NEEDS_OWNER | N | BUG-XXX |

## Per-Bug Verdict (1 line each)

- BUG-001: <verdict> — <1 sentence reason>
- BUG-002: <verdict> — <1 sentence reason>
- ... (33 lines)

## Notable Findings (CONFIRMED bugs with RCA + fix plan)

<For each CONFIRMED bug, 3-5 lines with root cause + fix proposal>

## Blocked / Skipped (with reason)

<Bugs that couldn't be drilled, with concrete reason>
```

---

## Time Budget

Total: 2-3 hours. If you hit ~3 hour mark, stop and write SUBAGENT-LOG.md with whatever you
have. Don't burn tokens on bugs that clearly can't be drilled without more data.

## Save your model effort

Use `sonnet` for navigation/snapshot reading. Use `opus` only when reasoning about RCA or
writing the SUBAGENT-LOG. (If you can't switch models mid-session, just stay on whatever
default; don't over-optimize.)

## Begin

Start by reading the run-002 state files, then setup (start FE + login), then drill bug by
bug in the order listed above. Write SUBAGENT-LOG.md when done.
