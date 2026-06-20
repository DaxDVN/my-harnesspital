---
title: "clinical-ui-design v4: constraint != quality; thêm kỹ thuật legible-density + ép đa dạng theo JOB + fresh-eyes critique"
date: "2026-06-19"
status: provisional
source: user-correction
scope: workflow:clinical-ui-design
confidence: high
owner_confirmed: false
proposed_target: skill
tags: [ui, design, clinical-ui-design, density, craft, divergence]
applies_tasks: [design, implement, scaffold]
applies_globs: [docs/ui-mocks/**, myhospital-fe/**]
applies_keywords: [ui, design, clinical-ui-design, mock, screen, redesign, density, cluttered]
expires: ""
---

# What

META-LESSON: mỗi vòng chất thêm rule 'đừng...' làm agent rụt rè/nhạt/hội tụ — CONSTRAINT != QUALITY. v4 đổi hướng: (1) 'don't be timid' — rule là FLOOR không phải ceiling. (2) Section 'Legible density' kỹ thuật DƯƠNG: encode majority-state ngầm (đừng stamp 'Đang dùng' mọi giường — chỉ exception+action mới loud), figure/ground, group bằng whitespace+hairline KHÔNG border, 1 organizing principle, giảm per-item chrome, color làm việc thay text. (3) Diverge theo USER'S JOB không theo shape (brainstorm 5-6 framing → chọn 3 khác nhất: spatial/availability/action-queue/find-patient) — 3 take cùng 1 grid = fail. (4) Crafted table ĐƯỢC phép lại (lỗi cũ là RANK nó best, không phải tồn tại). (5) Fresh-eyes 'timid-wireframe critique' 5 câu trên render TRƯỚC khi handoff.

# Evidence

- v3 run docs/ui-mocks/ward-map: process(capability audit) tốt nhưng visual downgrade — 3 variant hội tụ về cùng grid, lặp 'Đang dùng' mọi giường, border khắp nơi, wireframe-y

# Why It Matters

Tránh output an-toàn-nhưng-nhạt; density bệnh viện OK nhưng phải TỔ CHỨC tường minh; ép sáng tạo + craft thật thay vì chỉ tuân rule.

# How To Apply

_See # What above._

# Boundaries

Vẫn giữ clinical safety + capability grounding v3. Không quay lại marketing decoration.

# Promotion Recommendation

Promote to: skill
Reason: (fill in before promoting)
