---
title: "Language policy: agent-facing=English, owner-facing=Vietnamese, MD deliverables=2 bản (EN canonical + VN clone)"
date: "2026-06-19"
status: provisional
source: user-correction
scope: workspace
confidence: high
owner_confirmed: false
proposed_target: main-brain
tags: [language, vietnamese, english, bilingual, report-output, workflow]
applies_tasks: [any]
applies_globs: [engine/prompts/**, docs/audit/**, docs/tasks/**, docs/session-notes/**]
applies_keywords: [language, tiếng-việt, english, report, response, output, translate, dịch]
expires: ""
---

# What

Chính sách ngôn ngữ cho mọi agent/workflow: (1) INPUT/PROMPT agent NHẬN + suy nghĩ nội bộ + report EN-cho-agent-khác-đọc = TIẾNG ANH (agent làm việc tốt hơn, prompt chuẩn hơn). (2) RESPONSE chat trả owner = TIẾNG VIỆT (owner đọc). (3) FILE .md deliverable (audit/findings/fix/plan report) = 2 BẢN: '<name>.md' = English CANONICAL (nguồn sự thật, agent khác đọc) + '<name>.vi.md' = tiếng Việt (owner đọc), cùng folder ngày. Gen bản EN TRƯỚC (đầy đủ, chuẩn), rồi spawn 1 subagent RẺ (haiku hoặc sonnet) dịch nguyên văn EN->VI thành bản .vi.md. EN là source-of-truth; VN là bản dịch trung thành, không tự thêm/bớt nội dung.

# Evidence

- Owner không giỏi tiếng Anh; agent response + report đang toàn English

# Why It Matters

Owner kém tiếng Anh -> report toàn EN khó dùng. Nhưng agent + cross-agent handoff cần EN để chuẩn + tái dùng. Tách 2 trục: ngôn-ngữ-làm-việc-của-agent (EN) vs ngôn-ngữ-cho-owner (VI). 2 bản file = vừa cho agent khác đọc (.md EN) vừa cho owner đọc (.vi.md). Dịch bằng subagent rẻ để không tốn token model chính.

# How To Apply

_See # What above._

# Boundaries

Code/identifier/commit/PR/log error giữ nguyên (không dịch). Bản .vi.md chỉ là CLONE dịch, mọi quyết định/handoff/automation trỏ bản EN .md. Nếu chỉ có 1 file (vd note ngắn) thì EN + tóm tắt VI trong response là đủ — 2-file áp cho deliverable report dài.

# Promotion Recommendation

Promote to: main-brain
Reason: (fill in before promoting)
