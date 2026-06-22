---
title: "clinical-ui-design v3: ground vào data hệ thống thật + gu là của owner + đừng lead bằng table"
date: "2026-06-19"
status: provisional
source: user-correction
scope: workflow:clinical-ui-design
confidence: high
owner_confirmed: false
proposed_target: skill
tags: [ui, design, clinical-ui-design, capability-grounding, taste]
applies_tasks: [design, implement, scaffold]
applies_globs: [docs/ui-mocks/**, myhospital-fe/**, myhospital-be/**]
applies_keywords: [ui, design, clinical-ui-design, mock, screen, redesign, data, feasible]
expires: ""
---

# What

v3 thêm: (1) PHASE 2 capability/data grounding — audit data+component THẬT (CodeGraph+rg, cite file:line) TRƯỚC khi đề xuất; mỗi metaphor tag FEASIBLE-NOW / NEEDS-NEW-DATA / infeasible; không vẽ direction cần data không tồn tại (vd bed coordinates); chủ động liệt kê 'Gợi ý nâng cấp hệ thống' khi 1 field nhỏ mở khóa UI tốt hơn. (2) Gu/đẹp là của OWNER — agent CẤM tự rank 'đẹp nhất', chỉ nêu trade-off neutral. (3) Với data spatial/status, LEAD bằng metaphor visual/at-a-glance, table/register chỉ là 1 option phụ, không headline ('chỉ là 1 cái list' = chê).

# Evidence

- owner: B(table) bị chê tệ nhất dù agent khen đẹp nhất; A(floor-plan) cần data vị trí mà hệ thống không có

# Why It Matters

Tránh đề xuất viễn vông (data không có) + tránh áp gu agent lên owner + tránh default về register nhàm.

# How To Apply

_See # What above._

# Boundaries

Audit read-only, CodeGraph+bounded rg per source-discovery.md, không edit code ở preview.

# Promotion Recommendation

Promote to: skill
Reason: (fill in before promoting)
