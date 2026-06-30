# BUG-019 — TASK-255: Chọn khoa chưa work (filter sai)

## Metadata

- status: **PARTIALLY CONFIRMED** (dropdown mở được nhưng filter behavior chưa verify)
- severity: HIGH
- bug_class: department-filter-not-applied
- flow: Click "Khoa" button trên header → chọn khoa → verify list filter
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:06Z

## 00 Observation (drill)

Trên `/medical-visits/inpatient`:
- Button "Khoa" với text "Chọn khoa" (ref=e14) trên header
- Click e14 lần 1: dropdown mở với 4 options ["Khoa khám bệnh", "Khoa nội", "Khoa ngoại", "Khoa Xét Nghiệm"] (từ /inpatient/create page test trước đó)
- Click e14 lần 2 trên /inpatient page: dropdown KHÔNG mở rõ ràng (snapshot không thấy options, hasListbox: false)
- Trên /inpatient create, e14 click 2 lần liên tiếp → lần 2 không mở lại (mất focus?)

Hiện tại tất cả NB trên list đều "Khoa nội" — không có NB từ khoa khác để verify "chọn khoa khám bệnh vẫn thấy khoa nội". Cần owner manual test với data NB từ khoa khác.

## 02 Triage

Verdict: **PARTIALLY CONFIRMED** — Khoa selector có issue (click handler), nhưng bug gốc "filter sai" chưa reproduce được vì data chỉ có khoa nội.

## 04 Fix Plan

Sửa Khoa selector dropdown — cần dùng component phù hợp để click mở consistent (có thể cần dùng Radix Popover + DropdownMenu chuẩn).
