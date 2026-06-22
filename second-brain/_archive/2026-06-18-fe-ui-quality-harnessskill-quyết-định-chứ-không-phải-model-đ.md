---
title: "FE UI quality: harness/skill quyết định chứ không phải model -> đừng đổi committer"
date: "2026-06-18"
status: provisional
source: conversation
scope: workspace
confidence: medium
owner_confirmed: false
proposed_target: main-brain
tags: [model-selection, harness, ui, strategy]
applies_tasks: [implement, design, review, any]
applies_globs: []
applies_keywords: [model, opus, gpt, gemini, harness, ui, committer]
expires: ""
---

# What

Cho HIS FE UI, chênh lệch giữa Opus/GPT-5.x/Gemini ở năng lực GỐC là nhỏ; cái quyết định chất lượng là layer TRÊN model (skill + harness + convention guard + a11y verify). Workspace đã đầu tư harness Claude nặng -> moat nằm ở đó, KHÔNG nên phân mảnh sang multi-model pipeline (Opus+GPT+Gemini) như lời khuyên generic.

# Evidence

- Web research 2026-06-18 (Anthropic blog, arena.ai, WCAG) + ChatGPT cross-eval: model advantage nhỏ, layer trên model thắng

# Why It Matters

Tránh vứt bỏ harness đã chín + friction lớn khi đổi committer; eval model chỉ đáng khi model thật sự là bottleneck (hiện bottleneck là coverage của review + cost/time của pipeline).

# How To Apply

_See # What above._

# Boundaries

Có thể xét lại nếu internal eval chứng minh model là bottleneck thật, hoặc khi 1 model bỏ xa hẳn.

# Promotion Recommendation

Promote to: main-brain
Reason: (fill in before promoting)
