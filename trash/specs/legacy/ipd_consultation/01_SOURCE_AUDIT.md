# Source Audit - IPD Consultation

## DOCX Facts - Treatment Sheet / Progress

Source: `D:\arabica\roast\specs\Tài liệu Nội trú.docx`, section 5.3.

DOCX describes `Tờ điều trị` as the doctor-facing treatment note used during inpatient treatment.

Key facts:

- Doctors create treatment notes during rounds/daily care, or more often when the patient worsens.
- Left panel shows `Quá trình điều trị`, sorted descending.
- Right panel contains `Thông tin tờ điều trị` and `Danh sách chỉ định`.
- Treatment sheet fields include:
  - order date,
  - round date,
  - treating doctor,
  - on-duty doctor,
  - linked department/doctor,
  - main diagnosis,
  - secondary diagnoses.
- `Diễn biến bệnh` can be free text or SOAP.
- SOAP includes subjective/objective/assessment/plan; objective includes vital signs.
- The treatment sheet must be saved before opening order popups.
- Signed/locked treatment sheets should not remain freely editable.
- Medicine popup references `Biên bản hội chẩn thuốc`; diagnosis loads from the treatment sheet.

## DOCX Facts - Consultation

Source: `D:\arabica\roast\specs\Tài liệu Nội trú.docx`, section 5.5.

DOCX has three major consultation areas:

1. `Biên bản hội chẩn diễn biến bệnh`
2. `Biên bản hội chẩn thuốc`
3. `Giấy mời hội chẩn`

Clinical-progress consultation minutes:

- Consultation is for multi-doctor/multi-department discussion of complex patients or special drug usage.
- The minutes record process, conclusion, and next treatment direction.
- Code auto-generates as `HC[ddyymm]-[seq]`.
- Header fields include consultation time, chair, secretary, reason, place, consultation type, participants.
- Consultation types include department, inter-department, whole hospital, inter-hospital, and other.
- Patient block includes patient/admission/department/bed/room details.
- Diagnosis includes main and secondary diagnoses with ICD.
- Content fields:
  - summary of clinical progress/treatment/care,
  - issues requiring consultation,
  - conclusion,
  - next treatment direction.
- Actions include cancel, save draft, complete/sign, save and send for signature.
- Signed minutes become legally effective and locked.

Drug consultation minutes:

- Similar UI/fields to clinical-progress consultation.
- Adds proposed drug list selected from drug catalog.
- Diagnosis context is loaded from treatment sheet.
- Drug may be prescribed after the drug consultation minutes are approved/signed.

Invitation:

- Doctor creates invitation based on consultation type.
- Place, expected consultation time, chair, secretary, and consultation type are required.
- Recipient UI changes by consultation type.
- Patient summary and current diagnosis are loaded from latest treatment sheet if available.
- Invitee can confirm or decline attendance.
- Attachments can be uploaded and are locked after sending.

## Current Codebase Facts

Inpatient detail route exists:

- `D:\arabica\roast\myhospital-fe\src\modules\inpatient-reception\inpatient-reception-routing.tsx` line 98.

Current inpatient detail page does not yet expose consultation or treatment-sheet tabs:

- Current tabs are around `D:\arabica\roast\myhospital-fe\src\modules\inpatient-reception\pages\confirm-admission\confirm-admission-page.tsx` line 1378.

Transfer handover has a `ClinicalProgress` field:

- BE DTO: `D:\arabica\roast\myhospital-be\MyHospital.ServiceInterface\DepartmentTransferService.cs` line 211.
- FE doctor handover form reads and writes it:
  - `D:\arabica\roast\myhospital-fe\src\modules\inpatient-reception\pages\doctor-handover\doctor-handover-page.tsx` line 199.
  - Payload uses `ClinicalProgress` around line 299.

This is not enough for DOCX consultation:

- It is transfer-specific.
- It is stored in handover JSON.
- It does not model daily treatment notes, SOAP, orders, diagnosis snapshots, signing, or latest treatment sheet lookup.

No clear dedicated consultation module was found in FE/BE search:

- Search for consultation/hội chẩn mostly returns unrelated specialty/consulting labels or mock fields.
- Existing `Specialty` code is for specialty examination, not consultation minutes/invitations.

Existing code relevant to future integration:

- Inpatient service, department transfer, bed/day, and admission detail already provide patient/admission/department/bed context.
- Medication/product code has inpatient flags and allergy warnings, but drug consultation validation is not present as a dedicated domain.

## GPT/Web UI Catalogue Evaluation

Useful parts:

- Correctly captures clinical-progress consultation fields from DOCX.
- Correctly separates clinical-progress consultation, drug consultation, and invitation.
- Correctly highlights signed/locked state.
- Correctly notes that drug consultation is separate from clinical-progress consultation.
- Correctly highlights recipient behavior by consultation type.

Parts to downgrade or reframe:

- It labels drug-consultation prescription validation as L0. In implementation, this should be a later integration phase because it touches medication/order/signing workflows.
- It labels full invitation workflow as high priority. For codebase fit, it should come after basic minutes and treatment-progress foundation.
- It treats snapshot as directly required by DOCX. Snapshot is a strong technical design recommendation, but DOCX only directly requires read-only patient/context fields.
- It does not know that current code lacks treatment-sheet foundation, so its consultation-first ordering is unsafe.

## Codebase Fit Summary

The correct first deliverable for this stream is not full consultation. It is the treatment-progress foundation that creates a canonical latest treatment sheet. After that, consultation minutes can safely prefill diagnosis/progress/current condition without duplicating transfer-handover data.

