# Source Audit - IPD Vital Signs

## DOCX Facts

Source: `D:\arabica\roast\specs\Tài liệu Nội trú.docx`, section 5.2 `Tab Sinh hiệu`.

The tab is part of `Chi tiết hồ sơ điều trị` for one inpatient. The user enters from the ward patient list, opens the treatment detail, then uses the `Sinh hiệu` tab.

DOCX structure is three blocks:

1. `Sơ đồ theo dõi sinh hiệu`
2. `Form Sinh hiệu (lần đo hiện tại)`
3. `Lịch sử đo`

Chart requirements:

- Line chart over time.
- Default visible metrics: blood pressure and temperature.
- X-axis is measurement time with `dd/MM` and `hh:mm`.
- Each point maps to one measurement.
- Chart sorts ascending by measurement time.
- Blood pressure uses systolic and diastolic values, with separate lines.
- Temperature has its own line and DOCX mentions default range 36-42.
- A `Đo sinh hiệu` button opens the create popup.
- Chart supports metric selector: blood pressure, temperature, pulse, heart rate, respiratory rate, SpO2.
- Tooltip and legend are specified by DOCX, but can be implemented after the data and base chart are correct.

Create popup requirements:

- Header shows inpatient patient context.
- `Thời gian đo` is required, defaults to current time, and is editable.
- `Trạng thái thở` is required: `Tự thở`, `Bóp bóng`, `Thở máy`.
- `Tay đo` is required in DOCX, with left/right options.
- Basic fields: pulse, blood pressure systolic/diastolic, temperature, respiratory rate, heart rate, SpO2.
- Anthropometry: height, weight, BMI auto-calculated, body surface area auto-calculated.
- Pain and allergies: handedness, pain point, VAS score, drug allergy, food allergy, other allergy.
- Saving reloads chart and history and updates the patient record.

Current/latest form requirements:

- Title format: `Sinh hiệu [dd/mm/yyyy hh:mm]`.
- Default selected record is the latest measurement.
- Clicking a chart time/point should load that measurement into the form.
- DOCX says the selected measurement can be edited.

History requirements:

- Shows all measurements for the patient in the treatment episode.
- Sorts descending by measurement time.
- Filters by measurer and measurement date.
- Columns include STT, measured arm, blood pressure, temperature, heart rate, respiratory rate, height, weight, BMI, SpO2, handedness, VAS.
- Group/header row includes measurer and measurement time.
- Hidden expandable detail row includes allergies, pain, notes.

## Current Codebase Facts

BE vital signs exists:

- Entity: `D:\arabica\roast\myhospital-be\MyHospital.ServiceInterface\Models\VitalSigns.cs`
  - Class starts at line 11.
  - Existing core fields include `PatientId`, `MedicalVisitId`, `Pulse`, `Bmi`, `MeasuredArm`, `VasScore`, `Notes`.
- Create request: `D:\arabica\roast\myhospital-be\MyHospital.Apis\MedicalVisitApi.cs`
  - `CreateVitalSignsRequest` starts at line 115.
  - BP validation starts around line 190.
  - POST handler starts at line 774.
- History/detail services:
  - `D:\arabica\roast\myhospital-be\MyHospital.ServiceInterface\VitalSignsManagementService.cs`
  - `CreateVitalSignsAsync` starts at line 33.
  - `GetVitalSignsHistoryAsync` starts at line 87.
  - Detail request: `D:\arabica\roast\myhospital-be\MyHospital.Apis\VitalSignsApi.cs` line 11.
- History endpoints exist both by patient and by medical visit:
  - `D:\arabica\roast\myhospital-be\MyHospital.Apis\PatientApi.cs` line 28.
  - `D:\arabica\roast\myhospital-be\MyHospital.Apis\MedicalVisitApi.cs` line 56.

FE vital signs exists, but it is examination-oriented:

- Page: `D:\arabica\roast\myhospital-fe\src\modules\examination\pages\vital-signs-page.tsx`
  - Uses `VitalSignsForm`, `VitalSignsHistory`, and a request list.
  - Fetches detail by `LastMeasuredId` around line 217.
  - Fetches patient-wide history around line 375.
  - Renders form around line 524 and history around line 539.
- Reusable form:
  - `D:\arabica\roast\myhospital-fe\src\modules\examination\pages\components\vital-signs\vital-signs-form.tsx`
  - `VitalSignsForm` starts at line 75.
  - Uses `HospitalFormConfig` around line 95.
  - Builds create payload around line 297.
- Reusable history:
  - `D:\arabica\roast\myhospital-fe\src\modules\examination\pages\components\vital-signs\vital-signs-history.tsx`
  - History item shape starts around line 87.
  - VAS column appears around line 357.
- Existing EMR chart node exists, but it is not the live inpatient chart:
  - `D:\arabica\roast\myhospital-fe\src\components\form-builder\extensions\vital-signs-chart-node.tsx` line 83.
  - `D:\arabica\roast\myhospital-fe\src\modules\emr\components\vital-signs-chart-panel.tsx` line 40 says source path is not wired as a live provider.

Inpatient detail shell exists:

- Route: `D:\arabica\roast\myhospital-fe\src\modules\inpatient-reception\inpatient-reception-routing.tsx` line 98.
- Current tabs in confirm/detail page are admission/admin/transfer, not vital signs:
  - `D:\arabica\roast\myhospital-fe\src\modules\inpatient-reception\pages\confirm-admission\confirm-admission-page.tsx` line 1378.
- The page explicitly says inpatient vital signs will be recorded separately later:
  - `D:\arabica\roast\myhospital-fe\src\modules\inpatient-reception\pages\confirm-admission\confirm-admission-page.tsx` lines 2369-2370.

Nurse handover has a vital-sign snapshot, but this is not the same module:

- FE maps handover vital signs in `D:\arabica\roast\myhospital-fe\src\modules\inpatient-reception\pages\nurse-handover\nurse-handover-page.tsx` lines 662-667 and payload around line 800.
- BE DTO snapshot is in `D:\arabica\roast\myhospital-be\MyHospital.ServiceInterface\DepartmentTransferService.cs` line 258.

## GPT/Web UI Catalogue Evaluation

Useful parts:

- Correctly captures the three-block structure.
- Correctly highlights `Thời gian đo` as business axis.
- Correctly identifies chart/form/history synchronization.
- Correctly captures the history columns and filters from DOCX.
- Correctly calls out open BA questions such as body surface area formula and handedness representation.

Parts to downgrade or reframe:

- Header, breadcrumb, and patient-switching panel are inpatient detail shell concerns, not vital-signs-only M0.
- The catalogue treats many DOCX UI details as M0. For implementation, split into data contract first, then chart/form/history, then integrations.
- It does not account for existing BE lacking editable measurement time and some fields.
- It does not distinguish existing examination vital signs from the new inpatient tab.

## Codebase Fit Summary

The module is feasible as an early/parallel workstream because core vital sign storage and form components already exist. The risky part is not the basic form; it is aligning the data contract with DOCX before building a live inpatient chart and editable selected measurement form.

