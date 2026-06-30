# Test Map — ipd-improve-v3 treatment sheet + prescription

## Actor

- **Role:** Bác sĩ điều trị (Doctor)
- **Permission:** InpatientManagement.CanUpdate, PrescriptionManagement.CanUpdate
- **Login:** (to be determined from browser)

## Data Preconditions

- At least 1 inpatient visit with status "Đang điều trị"
- Visit has MedicalVisitId accessible
- Patient with basic info (name, DOB, gender)

---

## Test Flows

### TF-01: Treatment Note — Create (Lưu mới)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to patient detail → Tab "Tờ điều trị" | Treatment sheet tab visible |
| 2 | Click "Thêm tờ điều trị" | Empty form with defaults (today's date) |
| 3 | Fill NoteAt (datetime) | DateTimePicker with HH:mm |
| 4 | Fill RoundedAt (datetime) | DateTimePicker with HH:mm |
| 5 | Select DoctorUserId | Combobox with doctors |
| 6 | Fill diagnosis (add primary) | ICD combobox works |
| 7 | Fill ProgressText (FreeText mode) | Textarea accepts input |
| 8 | Fill NutritionMode (checkbox) | Checkbox group works |
| 9 | Fill CareLevel (radio) | Radio group works |
| 10 | Fill FallRiskLevel (radio) | Radio group works |
| 11 | Click "Lưu" | Note created, status = Saved |

### TF-02: Treatment Note — Sign (Ký số)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open existing Saved note | Form loads with data |
| 2 | Verify no dirty changes | isDirty = false |
| 3 | Click "Ký số" | Sign succeeds, status = Signed |
| 4 | Verify form becomes read-only | isReadOnly = true |

### TF-03: Treatment Note — Sign validation (missing fields)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open Saved note missing NutritionMode | Form loads |
| 2 | Click "Ký số" | Toast error: "Thiếu Chế độ dinh dưỡng" |
| 3 | Verify note NOT signed | Status still Saved |

### TF-04: Treatment Note — Cancel (Hủy)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open Saved note | Form loads |
| 2 | Click "Hủy" button | Confirmation dialog |
| 3 | Confirm cancel | Note cancelled, status = Cancelled |
| 4 | Verify form read-only | isReadOnly = true |

### TF-05: Treatment Note — DateTimePicker

| Step | Action | Expected |
|------|--------|----------|
| 1 | Click NoteAt field | DateTimePicker opens |
| 2 | Select date + time | Value format: dd/MM/yyyy HH:mm |
| 3 | Verify time portion preserved | Not truncated to date-only |

### TF-06: Prescription — Create from treatment note

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open Saved treatment note | Form loads |
| 2 | Click "Chỉ định thuốc" | Drug order dialog opens |
| 3 | Add 1 drug row | Product search works |
| 4 | Set dosing (Sáng/Trưa/Chiều/Tối) | Quantity fields accept input |
| 5 | Click "Lưu" | Prescription created (Draft) |
| 6 | Verify card appears in treatment note | "Y lệnh thuốc" card visible |

### TF-07: Prescription — Sign per-card

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open drug order dialog | Dialog loads |
| 2 | Click "Ký số" | Sign succeeds |
| 3 | Verify card shows signed status | SignedBy/SignedAt visible |

### TF-08: Stop Order — Ngừng y lệnh

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open signed prescription | Dialog loads |
| 2 | Select drug row | Checkbox selected |
| 3 | Click "Ngừng y lệnh" | Confirmation with reason field |
| 4 | Enter reason, confirm | Stop succeeds, status = Stopped |
| 5 | Verify row shows strikethrough | Visual indicator |

### TF-09: Stop Order — Block Draft

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open Draft prescription (not sent) | Dialog loads |
| 2 | Select drug row | Checkbox selected |
| 3 | Click "Ngừng y lệnh" | Should be disabled or throw error |

### TF-10: Diagnosis — Add/Remove

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open treatment note form | Form loads |
| 2 | Add primary diagnosis | ICD combobox + IsPrimary |
| 3 | Add secondary diagnosis | Additional row |
| 4 | Remove diagnosis | Row removed |
| 5 | Save and reload | Diagnoses persisted correctly |

---

## Priority

| Flow | Priority | Risk |
|------|----------|------|
| TF-01 (Create) | P0 | Core flow |
| TF-02 (Sign) | P0 | Core flow |
| TF-03 (Sign validation) | P0 | Q-03 fix |
| TF-04 (Cancel) | P1 | Q-18 fix |
| TF-05 (DateTime) | P1 | Q-12 fix |
| TF-06 (Prescription create) | P0 | Core flow |
| TF-07 (Prescription sign) | P0 | Core flow |
| TF-08 (Stop order) | P0 | Q-07/Q-08 fix |
| TF-09 (Stop Draft block) | P1 | Q-07 fix |
| TF-10 (Diagnosis) | P1 | New feature |
