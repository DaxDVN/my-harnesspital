# Espresso-Test Final Report — ipd-improve-v3 run-001

```text
module      : ipd-improve-v3 (treatment sheet + prescription + dispense)
worktree    : ipd-improve-v3 (slot 3)
tiers       : coordinator=mimo-v2.5  review=mimo-v2.5  fix=mimo-v2.5-pro
rounds      : 10
status      : CONVERGED (0 BLOCK/HIGH OPEN)
```

## Round Summary

| Round | BLOCK | HIGH | Fixed | New MED | Notes |
|-------|-------|------|-------|---------|-------|
| 1     | 1     | 4    | 5     | 3       | Initial review: F-01 through F-05 |
| 2     | 0     | 0    | 1     | 0       | Re-review: F-01 incomplete (transactional reorder) |
| 3     | 0     | 0    | 0     | 0       | Fresh re-review: all fixes verified |
| 4     | 0     | 0    | 0     | 1       | Adversarial: F-13 prescription sign race condition |
| 5     | 0     | 0    | 0     | 0       | FE integration: imports, exports, tab registration |
| 6     | 0     | 0    | 0     | 0       | BE test coverage: 49/49 pass |
| 7     | 0     | 0    | 0     | 0       | DTO sync: generated-dtos.ts, generated-api-client.ts |
| 8     | 0     | 0    | 0     | 0       | Permission audit: CanUpdate on all endpoints |
| 9     | 0     | 0    | 0     | 0       | Error handling: BusinessException coverage |
| 10    | 0     | 0    | 0     | 0       | Final validation: BE build + FE tsc + tests |

**Total: 7 findings fixed, 1 MED backlog, 0 BLOCK/HIGH residual.**

## Fixes Applied

### F-01 [BLOCK] Q-08: Stop order hold release → transactional ✅
- **File:** `PatientDispenseConfirmationService.cs`
- **Change:** Removed try-catch fire-and-forget; reordered: release hold BEFORE `SaveChangesAsync()` (truly transactional). Added test `StopOrder_throws_when_hold_release_fails`.

### F-02 [HIGH] Q-03: NutritionMode/CareLevel/FallRiskLevel required at Sign ✅
- **Files:** `treatment-note-form-schema.ts` (FE), `InpatientService.TreatmentNotes.cs` (BE)
- **Change:** Added validation in both `validateNoteForSign()` (FE) and `ValidateMedicalVisitTreatmentNote()` (BE).

### F-03 [HIGH] Q-12: NoteAt/RoundedAt → datetime picker 24h ✅
- **Files:** `treatment-note-form-schema.ts`, `treatment-note-form.tsx`
- **Change:** Schema defaults use ISO datetime (`yyyy-MM-ddTHH:mm`), form uses `DateTimePicker` with `HH:mm` display.

### F-04 [HIGH] Q-07: Block Stop for Draft (New) orders ✅
- **Files:** `MvcspStateMachine.cs`, `InpatientStopOrderTests.cs`, `PatientDispenseConfirmationServiceTests.cs`, `MvcspStateMachineTests.cs`
- **Change:** Removed `(New, Stopped)` transition, added `(Dispensed, Stopped)`. Updated all tests.

### F-05 [HIGH] Q-18: Cancel action on FE ✅
- **File:** `treatment-note-form.tsx`
- **Change:** Added `cancelMutation`, `handleCancel` handler, "Hủy" button (destructive variant) on Saved notes.

## Provisional Decisions (confirm or correct)

| ID | Question | Decision | Risk | Basis |
|----|----------|----------|------|-------|
| DL-PROV-1 | Q-03: NutritionMode/CareLevel/FallRiskLevel timing | Required at Sign | clinical | Spec §5.3.2 + decision preseed Q-03 |
| DL-PROV-2 | Q-07: Stop Draft eligibility | Block New → Stopped | clinical | Spec §2.2 + decision preseed Q-07 |

## Parked (none)

No irreversible-data/migration findings.

## Backlog (1 MED)

| ID | Description | Severity |
|----|-------------|----------|
| F-13 | Prescription sign not using compare-and-set (race condition) | MED |

## Validation

```
BE build:        0 errors ✅
FE typecheck:    0 errors ✅
Tests:           49/49 passed ✅
```

## Changed Files

**BE:**
- `PatientDispenseConfirmationService.cs` — F-01 (transactional hold release)
- `MvcspStateMachine.cs` — F-04 (New→Stopped blocked)
- `InpatientService.TreatmentNotes.cs` — F-02 (care block validation)
- `InpatientStopOrderTests.cs` — F-04 tests
- `PatientDispenseConfirmationServiceTests.cs` — F-04 tests
- `MvcspStateMachineTests.cs` — F-04 tests

**FE:**
- `treatment-note-form-schema.ts` — F-02, F-03
- `treatment-note-form.tsx` — F-03, F-05
