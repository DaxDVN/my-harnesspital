# Design And API Seeds - IPD Vital Signs

## Existing Contract Inventory

Existing BE model: `VitalSigns`.

Existing create request has these useful fields:

- `PatientId`
- `MedicalVisitId`
- `MedicalVisitServiceId`
- `Pulse`
- `HeartRate`
- `Spo2`
- `BloodPressureSys`
- `BloodPressureDia`
- `RespiratoryRate`
- `Temperature`
- `Weight`
- `Height`
- `MeasuredArm`
- `Handedness`
- `VasScore`
- `PainPoint`
- allergy payloads
- `Notes`

Existing APIs:

- `GET /medical-visits/{MedicalVisitId}/vital-signs`
- `POST /medical-visits/{MedicalVisitId}/vital-signs`
- `GET /patients/{PatientId}/vital-signs`
- `GET /vital-signs/{VitalSignsId}`

Existing service:

- `VitalSignsManagementService.GetVitalSignsHistoryAsync(...)` supports patient/visit filtering, date filtering, created-by filtering, and pagination.

## Contract Gaps Against DOCX

Likely missing fields:

- `MeasuredAt` or equivalent business measurement timestamp.
- `BreathingStatus`.
- `BodySurfaceArea`.
- Possibly a normalized update path for editing a selected historical measurement.

Ambiguous fields:

- `Handedness` currently appears tied to patient data. DOCX shows handedness in the measurement form/history. Decide whether to snapshot it per vital-sign record or only update patient profile.
- Allergy data currently lives outside `VitalSigns` as `PatientAllergies`; this may be correct, but history row semantics need final design.

## Candidate API Shape

Do not treat this as final. It is a seed for `api.md`.

### List By Inpatient Visit

`GET /medical-visits/{medicalVisitId}/vital-signs`

Use current endpoint if possible, but align filters to business measurement time:

- `MeasuredAt >= start && MeasuredAt < end`
- `CreatedBy == measurerId`
- paging

Response should include records and allergy context if the FE needs to render history detail rows without N+1 calls.

### Create

`POST /medical-visits/{medicalVisitId}/vital-signs`

Add missing fields if strict DOCX:

- `MeasuredAt`
- `BreathingStatus`
- `BodySurfaceArea` if stored rather than derived

### Update

Candidate:

`PUT /vital-signs/{vitalSignsId}`

Purpose:

- Edit the selected measurement.
- Validate visit scope and active inpatient state.
- Update patient allergies/handedness only if the payload includes those changes.

### Detail

`GET /vital-signs/{vitalSignsId}` already exists and returns `VitalSignsDetailDto`.

Ensure detail includes the allergy context required by the edit form.

## FE Design Seeds

Recommended new components under inpatient module:

- `pages/confirm-admission/tabs/vital-signs-tab.tsx` or equivalent if the detail page is refactored.
- `components/vital-signs/ipd-vital-signs-chart.tsx`
- Reuse `VitalSignsForm` only if it can accept inpatient mode, selected record, update mode, and `MeasuredAt/BreathingStatus` fields cleanly.
- Reuse `VitalSignsHistory` only if it can sort/filter by measurement time and support row selection.

State model:

- `selectedVitalSignsId`
- `selectedMeasuredAt`
- `chartMetricSelection`
- `dateFilter`
- `measurerFilter`
- `isCreateDialogOpen`

Data flow:

1. Fetch inpatient admission detail for patient/context.
2. Fetch vital signs list by `MedicalVisitId`.
3. Sort ascending for chart.
4. Sort descending for history.
5. Select latest for form.
6. On create/update success, invalidate history/detail and recompute latest/selected.

## Reuse Guidance

Reuse:

- Existing generated API adapter pattern.
- Existing vital signs form field rendering and validation where compatible.
- Existing allergy input components.
- Existing date/number formatting helpers if present.

Avoid:

- Copying `VitalSignsRequestList`; that is for measurement worklist, not inpatient detail.
- Using EMR chart node as the live chart without adapting data and interaction needs.
- Manually editing generated DTOs.

## BE Design Guidance

Follow BE harness:

- Use `BaseService`.
- Use tenant/hospital scoping helpers.
- Add `[RequireAuth]` and function permissions consistently.
- Avoid N+1 allergy lookups in history.
- Do not introduce transaction/lock patterns unless the existing service pattern requires it.

