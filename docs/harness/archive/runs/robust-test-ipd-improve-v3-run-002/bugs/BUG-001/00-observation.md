# BUG-001 — TASK-65: "Bác sĩ không có ca trực hôm nay" sai ở Tiếp đón

## Metadata

- status: **BLOCKED** (page empty / kiosk UI)
- severity: MED
- bug_class: reception-schedule-mismatch
- scanner_candidate: no
- flow: Tiếp đón ngoại trú → chọn bác sĩ
- actor: bvtest3
- route/url: /reception/registration, /reception/registration/create
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:00Z

## 00 Observation (drill)

Expected: Khi chọn BS. Administrator (đang có ca sáng hôm nay theo schedule) ở màn Tiếp đón ngoại trú, hệ thống KHÔNG hiển thị "Bác sĩ không có ca trực hôm nay".

Actual: Navigate `/reception`, `/reception/outpatient`, `/reception/registration`, `/reception/registration/create` — tất cả đều có `rootHTML = 0` (React không mount). API calls vẫn 200 (GetKioskTicketsRequest, GetQueueStatsRequest, etc.) nhưng DOM trống. Console có lỗi IDB liên quan tới MasterProvince. Reception page render thuộc Kiosk UI, có thể cần role/permission đặc biệt mà bvtest3 không có, hoặc có bug render.

Cannot verify the actual bug because Tiếp đón page không load được.

## 02 Triage

Verdict: **BLOCKED** — reception kiosk page không render trên bvtest3, dù API 200. Bug không verify được trong session này.

## 03 RCA

Possibilities:
- Reception route yêu cầu role `Reception` permission mà bvtest3 thiếu
- Bug render liên quan tới MasterProvince IDB error
- Bug thuộc FE reception module

## 04 Fix Plan

N/A — defer. Owner nên test thủ công với user có role reception, hoặc sửa page render trước.
