# BUG-001: Treatment sheet tabs not rendering on detail page

```text
status      : CANDIDATE
severity    : HIGH
bug_class   : missing-tab-registration
scanner_candidate: no
flow        : Navigate to /medical-visits/:id/inpatient-detail
actor       : bvtest3 (lynkhanh9822@gmail.com) — TenantId=6
data_preconditions: Visit ID 104 (InProgress, TenantId=6, HospitalId=7)
```

## Expected

After navigating to `/medical-visits/104/inpatient-detail`, the page should render with tabs including "Tờ điều trị" (treatment sheet).

## Actual

Page loads but `getByRole('tab')` returns empty array `[]`. No tabs visible. Console shows:
- `EntityHospitalShare` API error (400)
- 404 errors on some endpoints

## Reproduction Steps

1. Login as bvtest3/lynkhanh9822@gmail.com/12.[s7HXZQ;NfAoF
2. Navigate to `http://localhost:3003/medical-visits/104/inpatient-detail`
3. Wait 5 seconds
4. Query `page.getByRole('tab').allTextContents()` → returns `[]`

## Evidence

- Playwright test output: `Visible tabs: []`
- Console errors: `EntityHospitalShare: ApiError: Không thể kết nối tới máy chủ`
- 404/400 errors on API calls

## Triage

**Needs investigation.** Possible causes:
1. Admission data not loading → tabs not generated
2. EntityHospitalShare API failure blocking page render
3. Tab registration issue in admission-detail-page.tsx
4. Permission/tenant mismatch

## RCA (pending)

Need to check:
- Is `admission` data loading properly?
- Are tabs being generated in `admissionTabs` useMemo?
- Is the EntityHospitalShare error blocking render?
