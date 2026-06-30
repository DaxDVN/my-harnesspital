# Test Map — ipd-improve-v3 run-002 (40 tester bugs re-verify)

The bug inventory in `00-robust-test-state.md` IS the test map. One bug folder = one test case.
Each test case = one PASS / FAIL / INCONCLUSIVE observation recorded in the per-bug dossier.

## Actor (per session-boot-details.md)

- **customer code:** bvtest3
- **username:** lynkhanh9822@gmail.com
- **password:** 12.[s7HXZQ;NfAoF
- **tenant:** TenantId=6, HospitalId=7
- **role expectations (per task title):** Tiếp đón (reception), BS điều trị (doctor), ĐD (nurse), QTV (admin for cấu hình)

## Module Routes (FE)

| Module | Path prefix | Source |
|---|---|---|
| Lịch làm việc | `/hospital-management/schedule*` | `fe/src/modules/hospital-management/pages/schedule*` |
| Tiếp đón / Tiếp nhận nội trú | `/medical-visits/*` (inpatient-reception) | `fe/src/modules/inpatient-reception/*` |
| Quản lý giường | `/bed-management/*` | `fe/src/modules/bed-management/*` |
| Khám bệnh | `/examination/*` | `fe/src/modules/examination/*` |

## Test Discipline (per triage gate + robust-test README)

For every bug, before marking CONFIRMED:

1. Login with `bvtest3` (NOT HMU_ADMIN — that lacks IPD/bed/schedule perms).
2. Verify slot 3 (FE :3003, BE :5003, SQL :1436) — not 1/2/4.
3. Required fields filled before submit/save.
4. Current user has the gated permission for the action.
5. Test data/state matches the bug's preconditions.
6. Reproduce outside the first observation when feasible.
7. Use `agent-browser snapshot -i` (no screenshot by default).

False-positive guards:

- A button "missing" because of wrong actor/permission = `NOT_A_BUG`.
- An error toast = check if it's expected validation, not a product bug.
- A 400 from API = check if it's a request-shape error, not a product bug.

## Execution Order

| # | Module | Bugs | Order |
|---|---|---|---|
| M1 | Lịch làm việc | 14 | BUG-001 → BUG-014 |
| M2 | Tiếp nhận nội trú | 17 | BUG-015 → BUG-031 |
| M3 | QL ngày giường | 8 | BUG-032 → BUG-039 |
| M4 | Khám bệnh | 1 | BUG-040 |

Each bug: 1 open, snapshot, attempt repro, triage, write dossier. Compact.
