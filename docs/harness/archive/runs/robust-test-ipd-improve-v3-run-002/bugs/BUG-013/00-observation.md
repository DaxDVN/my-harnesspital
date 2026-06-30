# BUG-013 — TASK-85: Xóa ca đã dùng → SHIFT.HAS_EXISTING_ASSIGNMENTS (no graceful)

## Metadata

- status: **LIKELY CONFIRMED** (error code vẫn tồn tại trong FE Constants, no friendly UX change)
- severity: HIGH
- bug_class: shift-delete-blocked-raw-error
- scanner_candidate: yes
- scanner_candidate_tier: review-checklist
- flow: Danh sách ca làm việc → click Xóa trên ca có assignment
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T05:18Z

## 00 Observation

FE `Constants.ts:1799` vẫn define `'SHIFT.HAS_EXISTING_ASSIGNMENTS'` — error code vẫn tồn tại. BE `ShiftService.cs` vẫn tồn tại. → error path vẫn active.

Không có OData cho Shift (test API `/odata/Shift?$top=3` → 404/empty). Cần UI test để xem error message có friendly không, hay vẫn raw "Cannot delete shift because it has existing shift assignments" như tester report.

## 02 Triage

Verdict: LIKELY CONFIRMED — error path vẫn intact; UX friendly/unfriendly chưa verify trong scope này. Nếu owner muốn xác nhận, cần click Xóa trên 1 ca đang dùng.

## Note

Possible improvement: error code hiện tại có thể map sang message tiếng Việt thân thiện ("Không thể xóa ca đang được phân công cho nhân viên. Vui lòng hủy phân công trước.") thay vì để raw English.
