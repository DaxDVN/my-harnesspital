---
title: "PatientHeaderDto carries precomputed *Display fields — reuse them for patient headers"
date: "2026-06-19"
status: provisional
source: harness-fix
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: frontend-rules
tags: [frontend, dto, patient-header, reuse, component-reuse]
applies_tasks: [implement, fix, review]
applies_globs: [worktrees/*/fe/src/**/*.tsx, myhospital-fe/src/**/*.tsx]
applies_keywords: [header, patient, PatientHeaderDto, display, BedRoomDeptDisplay, AdmissionNumber, object, đối tượng, giường, phòng, khoa]
expires: ""
---

# What

When a spec asks for a "Header thông tin người bệnh" (patient identity header), the data is usually already
on the response DTO as **precomputed display fields** — do NOT recompute or join master-data on the FE.
`PatientHeaderDto` (the `Patient` field on `InpatientAdmissionDetailResponse`) carries: `FullName`,
`PatientCode` (Mã NB), `Gender`, `BirthYear` + `Age`, `PatientTypeName` (Đối tượng),
`BedRoomDeptDisplay` (Giường-Phòng-Khoa as ONE ready string), `AdmissionNumber` (Số nhập viện).
"Trạng thái điều trị" is `InpatientAdmissionDetailResponse.DisplayStatus` (top-level, not on Patient).

# Evidence

- Gap G1, `vital-signs-create-dialog.tsx`: the "Đo sinh hiệu" popup hand-rolled a 4-field header
  (FullName/PatientCode/Gender/BedName) and missed trạng thái điều trị, năm sinh–tuổi, đối tượng, phòng,
  khoa, số nhập viện — all of which were already on the already-fetched `PatientHeaderDto` + `DisplayStatus`.
  Fix just read the existing fields; no BE change, no `dtos:update`.
- `docs/audit/2026-06-19/vital-signs-tab-spec-gap.round-1.md` §6.

# Why It Matters

Prevents incomplete headers AND prevents FE recomputing bed/room/dept or age from master-data when the BE
already shipped a `*Display` string. Check the DTO for `*Display` / precomputed fields BEFORE adding
master-data joins or a new header component.

# How To Apply

Before building/critiquing a patient (or any entity) header: grep the response DTO for `Display`, `Name`,
`Number`, `Age` fields. Reuse those. Only recompute when the DTO genuinely lacks the field. Relates to
[[ui-deep-audit-must-verify-live-widgets-and-layout-patterns]] (semantic reuse matrix before coding UI).

# Promotion Recommendation

Promote to: engine/rules/frontend.md (reuse section) — "check DTO for precomputed *Display fields before
recomputing or adding master-data joins in a header/list cell."
