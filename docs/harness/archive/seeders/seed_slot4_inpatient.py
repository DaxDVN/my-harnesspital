#!/usr/bin/env python3
"""Coherent inpatient admission seed for slot 4 (ipd-improve-v4).

The project's local-scenario CSVs for MedicalVisitClinicalService / AdmissionOrder
are stale (they reference trimmed OPD visits 320002-320020), so `seed local` skips
them and AdmissionOrder ends up empty. This script authors a per-patient-coherent
admission chain on top of the rows `seed local` DID create:

  inpatient visit 3201xx  ->  MedicalVisitClinicalService 3301xx  ->  AdmissionOrder 3601xx

Every FK points at that patient's own seeded visit / patient / department, so each
admission navigates cleanly to its bed stay. Idempotent (IF NOT EXISTS), so re-runs
are safe. Target: mssql-hospital-wt4 (localhost,1437).
"""
from __future__ import annotations
import subprocess
from pathlib import Path

CONTAINER = "mssql-hospital-wt4"
DB = "MyHospital"
SA = "Hospital123!"
TENANT, HOSPITAL, USER = 1, 1, 1
SVC_ID = 1            # a valid MedicalService
OUT = Path(__file__).with_name("seed_slot4_inpatient.sql")

# visit id -> department id (from seeded MedicalVisit 320101..320120)
VISIT_DEPT = {
    320101: 4, 320102: 4, 320103: 4, 320104: 4, 320105: 4,
    320106: 5, 320107: 5, 320108: 5, 320109: 4, 320110: 4,
    320111: 4, 320112: 4, 320113: 4, 320114: 5, 320115: 4,
    320116: 4, 320117: 4, 320118: 5, 320119: 4, 320120: 5,
}
# visit 3201NN -> patient 3101NN, MVCS 3301NN, admission 3601NN
PATIENT = lambda v: 310000 + (v - 320000)
MVCS = lambda v: 330000 + (v - 320000)
ADM = lambda v: 360000 + (v - 320000)

# 320109 has no bed stay in seed -> leave it "Received" (pre-bed); rest are Admitted.
def status(v):
    return "Received" if v == 320109 else "Admitted"


def main():
    L = []
    L.append("SET QUOTED_IDENTIFIER ON;")
    L.append("SET ANSI_NULLS ON;")
    L.append("SET NOCOUNT ON;")
    # ---- MedicalVisitClinicalService (admission-trigger clinical service) ----
    L.append("SET IDENTITY_INSERT [MedicalVisitClinicalService] ON;")
    for v in VISIT_DEPT:
        mid, pid = MVCS(v), PATIENT(v)
        L.append(
            f"IF NOT EXISTS (SELECT 1 FROM [MedicalVisitClinicalService] WHERE Id={mid})\n"
            f"  INSERT INTO [MedicalVisitClinicalService] "
            f"([Id],[Code],[MedicalVisitId],[PatientId],[MedicalServiceId],[Quantity],[Status],"
            f"[QueueNumber],[QueueDate],[HasPrescription],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) "
            f"VALUES ({mid},N'MVCS-WT4-{v}',{v},{pid},{SVC_ID},1,N'Completed',"
            f"{v-320100},'2026-06-01',0,'2026-06-01T08:00:00',{USER},{TENANT},{HOSPITAL});"
        )
    L.append("SET IDENTITY_INSERT [MedicalVisitClinicalService] OFF;")
    L.append("")
    # ---- AdmissionOrder (one per inpatient visit) ----
    L.append("SET IDENTITY_INSERT [AdmissionOrder] ON;")
    for v, dept in VISIT_DEPT.items():
        aid, pid, mvcs, st = ADM(v), PATIENT(v), MVCS(v), status(v)
        admitted = "'2026-06-01T09:30:00'" if st == "Admitted" else "NULL"
        admitted_by = f"{USER}" if st == "Admitted" else "NULL"
        L.append(
            f"IF NOT EXISTS (SELECT 1 FROM [AdmissionOrder] WHERE Id={aid})\n"
            f"  INSERT INTO [AdmissionOrder] "
            f"([Id],[Code],[SourceOpdVisitId],[SourceMedicalVisitClinicalServiceId],[PatientId],"
            f"[TargetDepartmentId],[OrderType],[Status],[ExpectedAdmissionDate],[PatientConditionCode],"
            f"[AdmissionReason],[OrderedByUserId],[OrderedAt],[InpatientVisitId],[ReceivedAt],[ReceivedBy],"
            f"[AdmittedAt],[AdmittedBy],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) "
            f"VALUES ({aid},N'PNV-WT4-{v}',{v},{mvcs},{pid},{dept},N'Immediate',N'{st}',"
            f"'2026-06-01T08:00:00',N'Moderate',N'Nhập viện nội trú (seed slot 4)',{USER},'2026-06-01T08:00:00',"
            f"{v},'2026-06-01T08:30:00',{USER},{admitted},{admitted_by},'2026-06-01T08:00:00',{USER},{TENANT},{HOSPITAL});"
        )
    L.append("SET IDENTITY_INSERT [AdmissionOrder] OFF;")
    L.append("")
    L.append("SELECT (SELECT COUNT(*) FROM AdmissionOrder) AS AdmissionOrder, "
             "(SELECT COUNT(*) FROM MedicalVisitClinicalService) AS MVCS;")
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT} ({len(VISIT_DEPT)} admissions)")

    # apply
    cmd = ["docker", "exec", "-i", CONTAINER, "/opt/mssql-tools18/bin/sqlcmd",
           "-S", "localhost", "-U", "sa", "-P", SA, "-C", "-d", DB, "-b"]
    with OUT.open("rb") as f:
        r = subprocess.run(cmd, stdin=f, capture_output=True, text=True)
    print("STDOUT:", r.stdout.strip())
    if r.returncode != 0:
        print("STDERR:", r.stderr.strip())
        raise SystemExit(r.returncode)


if __name__ == "__main__":
    main()
