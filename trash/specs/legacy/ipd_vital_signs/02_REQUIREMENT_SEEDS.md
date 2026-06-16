# Requirement Seeds - IPD Vital Signs

These are requirement candidates. Convert them into final numbered requirements only after BA/tech decisions in `05_OPEN_QUESTIONS.md`.

## VS-R-001 - Inpatient Entry And Context

The vital signs feature must be accessible as a tab or section inside the inpatient treatment detail for an active inpatient visit.

Acceptance seeds:

- User can open the tab from the current inpatient detail route.
- Header/context identifies the inpatient, department, room, bed, admission number, and patient code.
- Data is scoped to the inpatient treatment episode, not all patient visits by default.

## VS-R-002 - Three Block Layout

The tab must contain:

1. Vital-signs chart.
2. Current/latest selected measurement form.
3. Measurement history.

Acceptance seeds:

- Chart is above the form and history.
- Latest record is selected on first load.
- Selecting a chart point or history row changes the selected measurement.

## VS-R-003 - Business Measurement Time

Each measurement must have a business measurement timestamp.

Acceptance seeds:

- Create form defaults `MeasuredAt` to current local time.
- User can edit `MeasuredAt` before save.
- Chart and history sort/filter by `MeasuredAt`.
- `CreatedAt` remains audit metadata and must not be the only business timestamp if strict DOCX compliance is required.

## VS-R-004 - Create Measurement

User can create a new inpatient vital-signs measurement.

Required in DOCX:

- Measurement time.
- Breathing status.
- Measured arm.

Optional but part of the form:

- Pulse.
- Blood pressure systolic/diastolic.
- Temperature.
- Respiratory rate.
- Heart rate.
- SpO2.
- Height.
- Weight.
- Pain point.
- VAS score.
- Drug allergy.
- Food allergy.
- Other allergy.
- Notes, if final design keeps the history detail row note.

Validation seeds:

- Blood pressure systolic must be greater than or equal to diastolic. The current BE validates `<=` as invalid, so confirm equality rule.
- SpO2 range is 0-100.
- VAS range must be confirmed: DOCX says 1-10, current FE schema allows 1-10 in setting text but verify actual schema before finalizing.
- At least one clinical value should probably be required beyond required metadata, but DOCX does not explicitly say so.

## VS-R-005 - BMI And Body Surface Area

BMI must be auto-calculated from weight and height and not manually typed.

Body surface area is mentioned by DOCX as auto-calculated, but formula is not specified. Treat as deferred until BA confirms formula.

## VS-R-006 - Current/Selected Measurement Form

The form title must use the selected measurement time: `Sinh hiệu [dd/mm/yyyy hh:mm]`.

Acceptance seeds:

- On initial load, selected measurement is the latest by `MeasuredAt`.
- Selecting chart point/history row loads that measurement.
- Editing selected measurement must update chart and history after save.

## VS-R-007 - Vital Signs Chart

Chart must show vital signs over time.

MVP:

- Default metrics: blood pressure and temperature.
- Blood pressure displayed as systolic and diastolic lines.
- Temperature displayed as a separate line.
- X-axis uses `MeasuredAt`, ascending.
- Button `Đo sinh hiệu` opens create dialog.

Full:

- Metric multi-select includes blood pressure, temperature, pulse, heart rate, respiratory rate, SpO2.
- Tooltip and legend follow DOCX.
- Additional metric axes/scales need a design decision.

## VS-R-008 - History

History must show all measurements for the inpatient treatment episode, sorted descending by measurement time.

Acceptance seeds:

- Filter by measurer.
- Filter by measurement date.
- Display columns from DOCX: STT, measured arm, BP, temperature, heart rate, respiratory rate, height, weight, BMI, SpO2, handedness, VAS.
- Expandable detail shows allergies, pain, and notes when available.

## VS-R-009 - Handover Integration

Nurse handover should load latest vital signs and latest allergies from the canonical vital-signs/allergy source.

Decision needed:

- Whether handover stores a snapshot at save/sign time or always reads live latest.
- Current handover already stores a snapshot payload. Preserve that snapshot model unless BA says otherwise.

## VS-R-010 - Medication Allergy Integration

Medication order screens should display drug allergies sourced from the patient allergy data updated through vital signs.

This is not part of the first vital-signs tab MVP unless the chosen phase includes medication integration.

