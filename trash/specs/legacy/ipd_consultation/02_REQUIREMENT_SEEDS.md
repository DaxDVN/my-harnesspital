# Requirement Seeds - IPD Consultation

These are consultation requirement candidates. Convert into final numbered requirements after resolving `06_OPEN_QUESTIONS.md`.

## HC-R-001 - Consultation Entry

The inpatient treatment detail must expose a `Hội chẩn` area for the current inpatient visit.

Acceptance seeds:

- User can view consultation records linked to the inpatient visit.
- Records are scoped to the treatment episode.
- Records display status and type.

## HC-R-002 - Clinical-Progress Consultation Minutes

User can create clinical-progress consultation minutes for the inpatient.

Fields from DOCX:

- Auto-generated code: `HC[ddyymm]-[seq]`.
- Consultation datetime.
- Chair.
- Secretary.
- Reason.
- Place.
- Consultation type.
- Participants.
- Patient/admission/context block.
- Main diagnosis and secondary diagnoses.
- Summary of clinical progress/treatment/care.
- Issues requiring consultation.
- Conclusion.
- Next treatment direction.

## HC-R-003 - Patient And Admission Context

The minutes must show read-only inpatient context.

Data seeds:

- patient name,
- year of birth/age,
- gender,
- object/insurance class if available,
- address,
- admission number,
- patient code,
- department,
- room,
- bed,
- admission date,
- current department treatment duration if available.

Design recommendation:

- Store a snapshot on the consultation record at draft/sign time to avoid later bed/department changes rewriting historical documents.

## HC-R-004 - Diagnosis In Consultation

The minutes must capture main and secondary diagnoses.

Acceptance seeds:

- Main diagnosis is required.
- Main diagnosis supports ICD-10 code/name and free-text explanation.
- Secondary diagnoses support multiple rows, each with ICD-10 and explanation.
- The default value should come from the latest treatment sheet when available.

## HC-R-005 - Consultation Content

The four content text areas from DOCX are required:

1. Summary of clinical progress/treatment/care.
2. Issues requiring consultation.
3. Conclusion.
4. Next treatment direction.

The first field should prefill from latest treatment progress if available, then allow editing.

## HC-R-006 - Consultation Workflow

States to design:

- Draft / `Đang soạn thảo`
- Pending signature / `Chờ ký`
- Signed / `Đã ký số`

Acceptance seeds:

- Save draft validates minimum required fields chosen by final design.
- Save and send for signature validates all required fields.
- Signed record is locked.
- Canceling dirty form asks for confirmation.

## HC-R-007 - Drug Consultation Minutes

Drug consultation minutes are a separate record type, not a flag on clinical-progress minutes.

Fields:

- Common consultation minute fields.
- Proposed drug list selected from drug catalog.
- Diagnosis context loaded from treatment sheet.

Dependency:

- Do not implement full drug-consultation validation before treatment sheet and medication-order integration points are defined.

## HC-R-008 - Consultation Invitation

User can create and send consultation invitations.

Fields:

- place,
- expected consultation time,
- chair,
- secretary,
- consultation type,
- recipients based on consultation type,
- patient summary,
- current diagnosis,
- current condition,
- consultation request,
- attachments.

Workflow:

- Draft.
- Sent.
- Confirm attendance.
- Decline attendance.

Dependency:

- Prefill patient summary and current diagnosis from latest treatment sheet.

## HC-R-009 - Boundary With Specialty Examination

Consultation must not be merged with specialty examination.

Reason:

- DOCX section 5.5 `Hội chẩn` and 5.6 `Khám chuyên khoa` are separate workflows.
- Existing code named `Specialty` is not a substitute for consultation minutes.

## HC-R-010 - Medication Integration

Medication order must eventually validate special consultation-drug rules.

Seeds from DOCX:

- If selected drug requires consultation and no valid drug-consultation minutes exist, show warning.
- Warning does not block draft/save.
- Sending/signing medication order should validate all consultation-required drugs have valid drug-consultation minutes.

This should be a later integration phase, not phase 1.

