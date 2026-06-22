---
title: "Mass-parallel subagent spawn botches tool-call across runtimes → prompts cần fallback inline"
date: "2026-06-19"
status: provisional
source: user-correction
scope: workspace
confidence: high
owner_confirmed: false
proposed_target: engine/rules/backend
tags: [spawn, subagent, fan-out, runtime-agnostic, fallback, prompts]
applies_tasks: [review, fix, any]
applies_globs: [engine/prompts/**, engine/workflows/**]
applies_keywords: [spawn, subagent, parallel, fan-out, actor, tool-call, delegate, fallback]
expires: ""
---

# What

Prompt ép fan-out mạnh (spawn ≥10 reviewer song song) + chạy trên runtime KHÔNG phải Claude (opencode/codex/mimo/'actor' tool) → model gọi SAI schema tool spawn (truyền operation=string thay vì object) → cả đợt delegate chết. Reusable system prompt phải runtime-agnostic: dùng spawn native, đọc schema trước khi gọi, spawn BATCH NHỎ (3-5), và FALLBACK bậc thang (batch→tuần tự→INLINE single-agent D1-D10) — spawn lỗi degrade chứ KHÔNG abort. Đã thêm §4.5 vào deep-audit-orchestrator + §3.5 vào bugfix-from-report.

# Evidence

- deep-audit-orchestrator fan-out D1-D10: 'actor tool invalid arguments: operation expected object, received string' x10

# Why It Matters

Fan-out là phương tiện tăng recall, không phải mục tiêu. Một lỗi tool-call ở bước spawn không được giết cả audit/fix. Prompt tái dùng trên nhiều tool nên không được hard-code cơ chế spawn của 1 runtime.

# How To Apply

_See # What above._

# Boundaries

Áp cho mọi reusable system prompt có fan-out subagent. Không áp khi chạy trong đúng 1 runtime đã biết schema (vd Claude Code Agent tool) — nhưng fallback vẫn nên có.

# Promotion Recommendation

Promote to: engine/rules/backend
Reason: (fill in before promoting)
