# Treatment Progress Foundation

## Why This Exists

DOCX consultation depends on `Tờ điều trị / Diễn biến người bệnh`.

Without this foundation, consultation would need to duplicate:

- diagnosis,
- current condition,
- clinical progress,
- treatment/care summary,
- next treatment direction,
- SOAP/free-text progress.

That would create drift and make drug consultation unsafe.

## DOCX Inputs

Source: `D:\arabica\roast\specs\Tài liệu Nội trú.docx`, section 5.3.

Treatment sheet structure:

- Left panel: treatment process list sorted descending.
- Right panel: treatment sheet form and order list.
- Free-text or SOAP mode for disease progress.
- Diagnosis and doctor fields.
- Orders for medication, CLS, VTYT, blood, clinical, and nursing.
- Treatment sheet must be saved before opening order popups.
- Signing/locking exists in the workflow.

## Minimal Foundation For Consultation

The consultation stream needs at least:

- A treatment note entity linked to `MedicalVisitId`.
- Note datetime / round datetime.
- Author doctor.
- Main diagnosis snapshot.
- Secondary diagnosis snapshots.
- Progress mode: free text or SOAP.
- Free-text progress summary.
- SOAP fields if enabled:
  - Subjective
  - Objective
  - Assessment
  - Plan
- Current condition summary, if the invitation needs it separately.
- Status: draft/signed or draft/locked depending final design.
- Latest treatment sheet query for a visit.

## Not Required In First Foundation Phase

These can be deferred if the immediate goal is to unblock consultation design:

- Full medication order card implementation.
- CLS/VTYT/blood order implementation.
- Nursing order scheduler.
- Full digital signature integration.
- Prescription validation for consultation drugs.

## Codebase Warning

Existing transfer handover field `ClinicalProgress` is not a treatment sheet.

References:

- `D:\arabica\roast\myhospital-be\MyHospital.ServiceInterface\DepartmentTransferService.cs` line 211.
- `D:\arabica\roast\myhospital-fe\src\modules\inpatient-reception\pages\doctor-handover\doctor-handover-page.tsx` line 199.

Using this as the canonical consultation source is a BLOCK-level design error because it is tied to transfer, not ongoing inpatient treatment.

## Candidate Foundation Requirements

### TP-R-001 - Treatment Note List

List treatment notes for the current inpatient visit, sorted descending.

### TP-R-002 - Treatment Note Create/Update

Create/update a treatment note with date, doctor, diagnosis, and progress.

### TP-R-003 - Progress Mode

Support free-text and SOAP progress modes.

### TP-R-004 - Latest Treatment Note

Expose a read model/API that returns the latest eligible treatment note for:

- consultation invitation prefill,
- consultation minutes diagnosis/progress prefill,
- drug consultation diagnosis prefill.

### TP-R-005 - Locking

Once a note reaches a locked/signed state, editing is blocked unless final BA workflow says otherwise.

