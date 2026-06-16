# Design And API Seeds - IPD Consultation

This is a design/API seed, not a final contract.

## Domain Objects To Consider

### TreatmentProgressNote

Purpose: canonical treatment-sheet/progress source.

Candidate fields:

- `Id`
- `MedicalVisitId`
- `NoteCode` if needed
- `RoundAt`
- `OrderAt`
- `DoctorUserId`
- `OnDutyDoctorUserId`
- `DepartmentId`
- `ProgressMode`
- `ClinicalProgressText`
- `SoapSubjective`
- `SoapObjective`
- `SoapAssessment`
- `SoapPlan`
- `MainDiagnosisCode`
- `MainDiagnosisName`
- `MainDiagnosisText`
- `SecondaryDiagnosesJson` or normalized child table
- `Status`
- audit fields

### ConsultationMinute

Purpose: clinical-progress or drug consultation minutes.

Candidate fields:

- `Id`
- `MedicalVisitId`
- `Code`
- `Type`: `ClinicalProgress` or `Drug`
- `ConsultationAt`
- `ChairUserId`
- `SecretaryUserId`
- `Reason`
- `Place`
- `ConsultationScope`: department/inter-department/whole-hospital/inter-hospital/other
- `ParticipantsText` or structured participants
- patient/admission snapshot JSON or normalized snapshot fields
- diagnosis snapshot
- `ClinicalSummary`
- `ConsultationIssues`
- `Conclusion`
- `NextTreatmentDirection`
- `ProposedDrugsJson` for drug consultation
- `SourceTreatmentProgressNoteId`
- `Status`: draft/pendingSignature/signed/cancelled

### ConsultationInvitation

Purpose: invite departments/doctors/external facility to a consultation.

Candidate fields:

- `Id`
- `MedicalVisitId`
- `Code` if needed
- `ExpectedConsultationAt`
- `Place`
- `ChairUserId`
- `SecretaryUserId`
- `ConsultationScope`
- `PatientSummary`
- `CurrentDiagnosisSnapshot`
- `CurrentCondition`
- `ConsultationRequest`
- `SourceTreatmentProgressNoteId`
- `Status`: draft/sent/cancelled

### ConsultationInvitationRecipient

Purpose: structured recipient and attendance response.

Candidate fields:

- `InvitationId`
- `RecipientType`: user/department/externalFacility
- `RecipientId`
- `ParticipantUserId` if department assigns participant
- `AttendanceStatus`: pending/confirmed/declined
- `RespondedBy`
- `RespondedAt`
- `ResponseNote`

## Candidate API Shape

### Treatment Progress

`GET /medical-visits/{medicalVisitId}/treatment-progress-notes`

List notes for the visit.

`GET /medical-visits/{medicalVisitId}/treatment-progress-notes/latest`

Latest eligible note for prefill.

`POST /medical-visits/{medicalVisitId}/treatment-progress-notes`

Create note.

`PUT /treatment-progress-notes/{id}`

Update draft note.

`POST /treatment-progress-notes/{id}/sign`

Lock/sign, if signature infrastructure is in scope.

### Consultation Minutes

`GET /medical-visits/{medicalVisitId}/consultation-minutes`

List minutes for a visit.

`POST /medical-visits/{medicalVisitId}/consultation-minutes`

Create clinical-progress or drug consultation minute.

`GET /consultation-minutes/{id}`

Detail.

`PUT /consultation-minutes/{id}`

Update draft.

`POST /consultation-minutes/{id}/send-signature`

Move to pending signature.

`POST /consultation-minutes/{id}/sign`

Sign/lock.

### Consultation Invitations

`GET /medical-visits/{medicalVisitId}/consultation-invitations`

List invitations.

`POST /medical-visits/{medicalVisitId}/consultation-invitations`

Create draft.

`PUT /consultation-invitations/{id}`

Update draft.

`POST /consultation-invitations/{id}/send`

Send and lock existing recipient set.

`POST /consultation-invitations/{id}/recipients/{recipientId}/confirm`

Confirm attendance.

`POST /consultation-invitations/{id}/recipients/{recipientId}/decline`

Decline attendance.

## BE Design Guidance

Follow project harness:

- New endpoints should use `BaseService`.
- Use tenant/hospital scoped queries.
- Use `[RequireAuth]`.
- Prefer OData/list patterns already used in the project.
- Avoid N+1 when loading participants, users, departments, diagnoses, and patient snapshots.
- Add code generation via existing `proc_CodeGeneratorAsync` pattern if consistent with other modules.
- Avoid new transaction/lock patterns unless necessary and justified.

## FE Design Seeds

Recommended screens/components:

- Add `Tờ điều trị` tab before full `Hội chẩn`, or create a treatment-progress component used by consultation prefill.
- Add `Hội chẩn` tab in inpatient detail after treatment-progress foundation.
- Consultation tab starts with a list/table:
  - code,
  - type,
  - consultation time,
  - chair,
  - status,
  - actions.
- Detail/edit form switches read-only/editable by status.
- Drug consultation form reuses common minute fields plus proposed-drug list.
- Invitation form should be a separate flow/modal/page to avoid overloading the minutes form.

## Snapshot Guidance

Snapshot patient/admission/diagnosis data when a record is saved or sent/signed.

Reason:

- inpatient bed/room/department can change,
- diagnosis can change,
- historical consultation documents should remain stable.

This is a design recommendation derived from DOCX read-only document semantics and inpatient workflow, not a direct quote.

