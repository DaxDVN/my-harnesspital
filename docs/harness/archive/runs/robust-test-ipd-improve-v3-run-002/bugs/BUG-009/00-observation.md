# BUG-009 — TASK-77: BS không gán phòng B vẫn tiếp nhận được

## Metadata

- status: **BLOCKED** (reception page empty — see BUG-001)
- severity: HIGH
- bug_class: reception-schedule-bypass
- scanner_candidate: yes
- scanner_candidate_tier: mh_scan
- flow: Tiếp nhận → bật "Áp dụng lịch làm việc" → thử tiếp nhận BS không có ca
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:03Z

## 00 Observation (drill)

Same as BUG-001 — reception page không render trên bvtest3, không thể test scenario bypass.

## 02 Triage

Verdict: **BLOCKED** — same reception blocker as BUG-001.

## 04 Fix Plan

N/A — defer. Cần sửa reception render trước, hoặc test với user có role reception.
