# Phase Plan - IPD Vital Signs

## Recommended Worktree

Suggested slug: `ipd-vital-signs-tab`.

This worktree can run in parallel with the consultation/treatment-progress worktree if BE DTO regeneration and shared generated client changes are coordinated.

## Phase VS0 - Requirement And Contract Decisions

Goal: finish `requirements.md`, `design.md`, and `api.md` for this submodule before coding.

Decisions:

- Is `MeasuredAt` required as a new persisted field?
- Is `BreathingStatus` required for every measurement?
- What formula is used for body surface area?
- Can old measurements be edited after discharge/transfer/sign?
- Does history show allergies per measurement snapshot or current patient allergies?

Exit criteria:

- Final field table.
- Final create/update/detail/list API shape.
- Migration impact identified.

## Phase VS1 - BE Contract And Data Model

Goal: make backend capable of storing and returning DOCX-compliant inpatient measurements.

Candidate work:

- Add missing persisted fields.
- Add/update request DTOs.
- Add update endpoint if not already available.
- Ensure history filters by measurement date, not audit create date.
- Return data sorted consistently.
- Regenerate FE DTO/client after BE contract changes.

Risk:

- If `MeasuredAt` is skipped, chart/history may pass visually but fail DOCX semantics.

## Phase VS2 - FE Inpatient Tab

Goal: add `Sinh hiệu` tab to inpatient detail.

Candidate work:

- Add tab shell.
- Fetch by `MedicalVisitId`.
- Add chart defaulting to BP + temperature.
- Add create dialog.
- Add selected/latest form.
- Add history with filters and row selection.

Risk:

- Current `confirm-admission-page.tsx` is already large. Consider extracting tab components instead of growing it much further.

## Phase VS3 - Integration

Goal: wire vital signs into dependent clinical flows.

Candidate work:

- Nurse handover prefill from latest measurement and allergy state.
- Medication allergy display from patient allergy data.
- Treatment sheet/SOAP objective integration after the treatment-progress module exists.

## Suggested Validation

BE:

- Focused unit/service tests around create/update/list by `MedicalVisitId`.
- Validate tenant/hospital scope.
- Validate date filter uses `MeasuredAt`.

FE:

- Component tests if local test patterns exist.
- Manual browser smoke with a patient detail route:
  - create measurement,
  - chart point appears,
  - latest form updates,
  - history desc order,
  - row/chart point selection loads form.

