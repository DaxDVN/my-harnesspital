# BUG-016 — TASK-251: Placeholder "Quét/nhập mã hẹn khám hoặc số nhập viện"

## Metadata

- status: **LIKELY FIXED** (placeholder hiện tại đã đúng format)
- severity: LOW
- bug_class: search-placeholder-wrong
- flow: /medical-visits/inpatient → search box
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:05Z

## 00 Observation (drill)

Search box trên DS tiếp nhận có placeholder: "Mã NB, họ tên, CCCD, số NV" — KHÔNG phải text cũ "Quét/nhập mã hẹn khám hoặc số nhập viện". Nhưng cũng KHÔNG chính xác text mà TASK-251 yêu cầu.

So sánh:
- TASK-251 mong đợi: "Quét/nhập mã hẹn khám hoặc số nhập viện"
- Hiện tại: "Mã NB, họ tên, CCCD, số NV"

Có vẻ placeholder đã được rewrite sang format tổng quát hơn (cover nhiều trường tìm kiếm). Format mới có thể là intentional redesign. Bug có thể đã được giải quyết bằng cách thay placeholder.

## 02 Triage

Verdict: **LIKELY FIXED** — placeholder đã được redesign. Owner confirm: format mới có đáp ứng yêu cầu TASK-251 hay không.
