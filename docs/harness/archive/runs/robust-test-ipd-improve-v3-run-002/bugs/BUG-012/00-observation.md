# BUG-012 — TASK-84: Thêm ca 2 khoa → tạo 2 bản ghi

## Metadata

- status: **BLOCKED** (DS ca làm việc page not found in nav)
- severity: HIGH
- bug_class: shift-create-multiple-departments-creates-duplicates
- scanner_candidate: yes
- scanner_candidate_tier: mh_scan
- flow: DS ca làm việc → Thêm ca → chọn 2 khoa
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:03Z

## 00 Observation (drill)

Không tìm thấy route "DS ca làm việc" riêng. Schedule page có sẵn shifts (14 Ca sáng). Nút "+ Thêm ca" trên cell → có thể trigger create shift dialog. Cần tìm route riêng để test "Thêm ca 2 khoa".

Source: không có page `shift-list` riêng trong schedule/. → có thể DS ca làm việc = chính grid ở `/hospital-management/schedules`.

## 02 Triage

Verdict: **BLOCKED** — Phân ca dialog không mở (same blocker as BUG-011).

## 04 Fix Plan

N/A — defer.
