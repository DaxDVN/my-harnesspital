---
title: "clinical-ui-design v5: genre FIRST (sơ đồ=MAP); variant=design-approach cùng 1 màn KHÔNG phải feature bổ sung; schematic>=geographic; overview!=list"
date: "2026-06-19"
status: provisional
source: user-correction
scope: workflow:clinical-ui-design
confidence: high
owner_confirmed: false
proposed_target: skill
tags: [ui, design, clinical-ui-design, genre, map, variant, schematic]
applies_tasks: [design, implement, scaffold]
applies_globs: [docs/ui-mocks/**, myhospital-fe/**]
applies_keywords: [ui, design, clinical-ui-design, mock, screen, redesign, map, sơ-đồ, variant]
expires: ""
---

# What

4 fix gốc: (1) PHASE 1a GENRE FIRST — hiểu artifact LÀ GÌ trước user/data: sơ đồ→MAP spatial, bảng→board, danh sách→list; biến map thành dashboard = lỗi gốc 'không giống cái nó là'. (2) VARIANT = design-approach loại trừ cho CÙNG 1 màn hoàn chỉnh (owner chọn 1 là xong) — KHÔNG phải feature khác nhau; test: nếu 2 variant ship chung được = chúng là 1 variant; mảnh bổ sung (overview+inspector+queue) gộp vào 1 variant. (3) SCHEMATIC >= GEOGRAPHIC — không cần tọa độ vẫn làm map thật (phòng xếp như mặt bằng, giường trong phòng), như bản đồ metro; 'no coordinate' KHÔNG phải cớ rớt về card grid. (4) OVERVIEW != LIST — map đọc bằng spatial pattern, không liệt kê full text mọi item; aggregate + detail-on-focus.

# Evidence

- v4 run ward-map: A/B/C = board+assign+queue = 3 feature bổ sung (không phải 3 design alternative); không cái nào là SƠ ĐỒ dù màn tên 'Sơ đồ khoa phòng'; A liệt kê mọi giường = quá tải

# Why It Matters

Tránh design sai thể loại (map ra dashboard), tránh phân rã 1 product thành nhiều 'variant' giả, tránh quá tải text trên overview.

# How To Apply

_See # What above._

# Boundaries

Giữ legible-density v4 + capability-grounding v3 + don't-be-timid. Schematic map vẫn tag to-scale version NEEDS-NEW-DATA.

# Promotion Recommendation

Promote to: skill
Reason: (fill in before promoting)
