---
title: "Bed reservation (Đặt lịch) form follows mockup (lean), not doc-text §5.2"
date: "2026-06-19"
status: provisional
source: conversation
scope: module:bed-management
confidence: high
owner_confirmed: false
proposed_target: spec-decision
tags: []
applies_tasks: []
applies_globs: []
applies_keywords: []
expires: ""
---

# What

Doc Tài liệu Nội trú §5.2 line 1294 says the 'Đặt lịch' (advance reservation) popup form has the SAME fields as 'Đã có người bệnh' + Thời gian vào dự kiến (i.e. would include Dịch vụ ngày giường + Thông tin phẫu thuật). Mockup image 6_3_..._8 (Đặt lịch) does NOT show those two fields — it shows only Người bệnh, Thời gian vào dự kiến, Thời gian ra dự kiến, Nằm giường (days), Thêm giường tự chọn. OWNER DECISION (2026-06-19): follow the MOCKUP — reservation form stays lean; bed-day service + surgery are chosen later when the patient actually arrives (switching to 'Đã có người bệnh'), not at booking time. Code (bed-reservation-form.tsx) already matches this.

# Evidence

- _No specific evidence cited._

# Why It Matters

At advance-booking time the service/surgery are usually not yet known, so the lean form is the correct UX. BE reservation DTO fields (BedDayMedicalServiceId/LinkedSurgeryServiceIds/ExpectedStartTime added earlier) remain but are sent undefined by the lean form — harmless (nullable), kept in case the doc-text behavior is ever wanted. Mockup-vs-doc conflicts: surface, don't silently pick — resolved here in owner's favor toward the mockup.

# How To Apply

_See # What above._

# Boundaries

_No specific boundaries noted._

# Promotion Recommendation

Promote to: spec-decision
Reason: (fill in before promoting)
