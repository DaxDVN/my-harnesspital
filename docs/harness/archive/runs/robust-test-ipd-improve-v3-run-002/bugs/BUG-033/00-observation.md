# BUG-033 — TASK-305: Chưa tạo được DV ngày giường (blocker)

## Metadata

- status: **CONFIRMED** (Số dịch vụ = 0 trong cả 2 loại Ngày giường)
- severity: BLOCK
- bug_class: bed-day-service-cannot-create
- flow: /master-data-management/services → Loại dịch vụ → Thêm DV
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:09Z

## 00 Observation (drill)

DM DV ngày giường:
- Nhóm: "Ngày giường" (NG) — có
- Loại: "Ngày giường ngoại khoa" + "Ngày giường nội khoa" — có
- **Số dịch vụ: 0** trong cả 2 loại

→ DV ngày giường chưa được tạo → test phụ thuộc (như BUG-036 — QL giường, BUG-018 — gắn SNV) bị block.

## 02 Triage

Verdict: **CONFIRMED**.

## 04 Fix Plan

Cần owner tạo ít nhất 1 DV ngày giường mẫu để unblock các test downstream. Sau đó test thủ công form Thêm DV (có thể có validation required fields mà bug TASK-305 nói về).
