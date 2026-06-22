---
title: "clinical-ui-design v2: calm != bland; generic là failure mode; variant theo METAPHOR không theo effort"
date: "2026-06-18"
status: provisional
source: user-correction
scope: workflow:clinical-ui-design
confidence: high
owner_confirmed: false
proposed_target: skill
tags: [ui, design, clinical-ui-design, craft, metaphor]
applies_tasks: [design, implement, scaffold]
applies_globs: [docs/ui-mocks/**, myhospital-fe/**]
applies_keywords: [ui, design, clinical-ui-design, mock, screen, redesign]
expires: ""
---

# What

clinical-ui-design v1 over-correct: dạy 'calm + zero boldness' -> agent ra UI austere nhưng GENERIC (giống mọi Tailwind admin: border gray default, card phẳng, 1 type size, không craft). Fix v2: (1) enemy = generic, không phải beautiful -> 'zero decoration, maximal craft' + craft floor; (2) Phase 1 UNDERSTAND bắt buộc: research user+decisions thật + tìm METAPHOR tự nhiên của data (bed-map = floor-plan spatial, không phải card grid) + reference best-in-class (Linear/EMR-OR-board/NOC); (3) variant khác nhau theo METAPHOR/mental-model, KHÔNG theo effort (minimal vs full đều rớt về cùng 1 card grid); (4) thêm domain-fit gate + generic-smell-test gate ngoài 6-axis.

# Evidence

- docs/ui-mocks/bed-management-ward-map: 3 mock đúng rule nhưng trông generic/công nghiệp; owner reject

# Why It Matters

Tránh output đúng-rule-nhưng-vô-hồn; ép agent nghiên cứu user + chọn đúng shape data trước khi vẽ pixel.

# How To Apply

_See # What above._

# Boundaries

Vẫn giữ clinical safety (semantic color, contrast AA, no decorative motion). Không áp cho marketing page.

# Promotion Recommendation

Promote to: skill
Reason: (fill in before promoting)
