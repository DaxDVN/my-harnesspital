---
title: "Audit claim: không claim 'tất cả X' nếu chưa verify tay"
date: "2026-06-22"
status: raw
scope: workspace
confidence: high
owner_confirmed: true
proposed_target: engine/rules/quality-gates + 04-evidence-verification-gate
tags: [audit, claim, verification, false-positive, script-trust]
applies_tasks: [fix, implement, review, rename, audit]
applies_globs: [worktrees/**]
applies_keywords: [audit, all, every, matches, correct, consistent, done, complete]
---

# Không claim "tất cả X đã Y" nếu chỉ dựa vào automated script

## Rule

Trước khi nói "tất cả file name khớp class name" / "tất cả prescription đã revert" / bất kỳ
claim **completeness** nào: phải có manual crosscheck, không chỉ script output.

Script output = necessary but not sufficient evidence.

## Why

Session 2026-06-22: chạy automated script để tìm file/class mismatch. Script miss
`InpatientRelativeType.cs` (class `PatientRelativeType`). Tôi trust script, tuyên bố
"tất cả file đã khớp tên class" — sai. Owner phải tự phát hiện.

## How to apply

Sau khi script chạy:
- Spot-check 3-5 file random từ danh sách "OK" để confirm script không bỏ sót
- Với completeness claim đặc biệt quan trọng: đọc thêm `git diff HEAD --stat` toàn bộ
  và verify từng file thay đổi thuộc đúng domain

Nếu không thể verify tay: nói "script không tìm thấy mismatch khác, nhưng chưa verify tay từng file"
thay vì claim clean.
