#!/usr/bin/env python3
"""Vital Signs (sinh hiệu nội trú) seed for slot 4 (ipd-improve-v4).

Seeds VitalSigns + VitalSignsHistory for all 20 inpatient visits (320101–320120)
and updates MedicalVisit.LastMeasuredId to the latest reading per visit.

Design:
- 4 measurements per visit spread across the admission duration (t+2h, t+8h, t+16h, t+24h)
- Medically-plausible values (temp 36.5–38.5°C, pulse 60–110, SpO2 88–99%, BP 90–145/60–95)
- 1 correction per visit (reading #2 gets a history snapshot to simulate CorrectVitalSigns)
- BreathingStatus + MeasuredArm always set (required for inpatient visits with AdmissionTime)
- FK VitalSignsId in VitalSignsHistory references VitalSigns.Id
- LastMeasuredId = the latest VitalSigns.Id per visit (by MeasuredAt DESC, Id DESC)
- Idempotent: IF NOT EXISTS guards on both tables

ID allocation (range 390000–399999, already used: 390001–390020 by inpatient seed):
- VitalSigns:        390100 – 390179  (20 visits × 4 readings = 80 rows)
- VitalSignsHistory: 390200 – 390219  (1 snapshot per visit = 20 rows)
"""
from __future__ import annotations
import subprocess
from pathlib import Path
import math

CONTAINER = "mssql-hospital-wt4"
DB = "MyHospital"
SA = "Hospital123!"
TENANT, HOSPITAL, USER = 1, 1, 1
OUT = Path(__file__).with_name("seed_slot4_vitalsigns.sql")

# ---------- visit metadata -------------------------------------------------------
# visit id -> (patient_id, dept_stay_id, admission_datetime_str)
# Visit 320110 has two dept stays; use 390019 (second/latest per seed script order)
# Visit 320112 is Discharged with no dept stay; MedicalVisitDepartmentStayId = NULL
VISITS = {
    320101: (310101, 390001,  "2026-06-01T09:00:00"),
    320102: (310102, 390002,  "2026-06-01T09:30:00"),
    320103: (310103, 390003,  "2026-06-02T10:00:00"),
    320104: (310104, 390004,  "2026-06-02T10:30:00"),
    320105: (310105, 390005,  "2026-06-03T11:00:00"),
    320106: (310106, 390006,  "2026-06-03T11:30:00"),
    320107: (310107, 390007,  "2026-06-04T12:00:00"),
    320108: (310108, 390008,  "2026-06-04T12:30:00"),
    320109: (310109, 390009,  "2026-06-05T13:00:00"),
    320110: (310110, 390019,  "2026-06-05T13:30:00"),
    320111: (310111, 390020,  "2026-06-01T14:00:00"),
    320112: (310112, None,    "2026-06-02T14:30:00"),   # Discharged, no dept stay
    320113: (310113, 390011,  "2026-06-06T15:00:00"),
    320114: (310114, 390012,  "2026-06-06T15:30:00"),
    320115: (310115, 390013,  "2026-06-06T16:00:00"),
    320116: (310116, 390014,  "2026-06-06T16:30:00"),
    320117: (310117, 390015,  "2026-06-03T17:00:00"),
    320118: (310118, 390016,  "2026-06-03T17:30:00"),
    320119: (310119, 390017,  "2026-06-04T18:00:00"),
    320120: (310120,390018,  "2026-06-04T18:30:00"),
}

# Offset hours for 4 readings per visit
READING_OFFSETS_H = [2, 8, 16, 24]

# Medically-plausible value sets cycling across visits (index = visit ordinal 0..19)
# Each tuple: (temp, pulse, heart_rate, spo2, bp_sys, bp_dia, rr, weight, height, vas, breathing, arm)
# breathing: "Tự thở" | "Bóp bóng" | "Thở máy"   arm: "Left" | "Right"
def _vs(i: int, reading_idx: int):
    """Generate vital sign values for visit ordinal i, reading index r (0–3)."""
    # Deterministic pseudo-variation so values look real across readings
    seed = (i * 4 + reading_idx)
    temp_base = [36.5, 36.8, 37.1, 37.4, 37.6, 37.9, 38.2, 38.5,
                 36.6, 36.9, 37.2, 37.5, 37.0, 37.3, 36.7, 37.8,
                 38.0, 37.7, 36.4, 37.1][i]
    # Reading drift: fever typically rises then resolves
    temp_drift = [0.0, 0.3, 0.2, -0.2][reading_idx]
    temp = round(min(39.0, max(36.0, temp_base + temp_drift)), 1)

    pulse_base = [72, 80, 88, 76, 95, 68, 84, 100, 110, 78,
                  66, 90, 74, 82, 96, 70, 88, 76, 84, 92][i]
    pulse_drift = [0, 5, 3, -4][reading_idx]
    pulse = max(55, min(115, pulse_base + pulse_drift))

    spo2_base = [98, 97, 96, 99, 95, 98, 97, 94, 92, 99,
                 98, 96, 97, 98, 95, 99, 96, 97, 98, 93][i]
    spo2_drift = [0, -1, 0, 1][reading_idx]
    spo2 = max(88, min(100, spo2_base + spo2_drift))

    bp_sys_base = [120, 130, 125, 118, 140, 115, 128, 145, 135, 122,
                   119, 132, 124, 127, 138, 116, 129, 121, 133, 141][i]
    bp_sys_drift = [0, 3, -2, -3][reading_idx]
    bp_sys = max(90, min(150, bp_sys_base + bp_sys_drift))

    bp_dia_base = [80, 85, 82, 76, 90, 72, 84, 95, 88, 78,
                   75, 86, 80, 83, 89, 74, 85, 79, 87, 92][i]
    bp_dia_drift = [0, 2, -1, -2][reading_idx]
    bp_dia = max(60, min(100, bp_dia_base + bp_dia_drift))
    # Ensure systolic >= diastolic
    if bp_sys <= bp_dia:
        bp_sys = bp_dia + 20

    rr_base = [16, 18, 20, 16, 22, 15, 18, 24, 26, 17,
               15, 20, 16, 18, 21, 15, 19, 16, 18, 23][i]
    rr_drift = [0, 2, 1, -1][reading_idx]
    rr = max(12, min(30, rr_base + rr_drift))

    weight = [65.0, 70.0, 55.0, 80.0, 72.0, 58.0, 68.0, 90.0, 85.0, 62.0,
              75.0, 60.0, 78.0, 52.0, 83.0, 67.0, 71.0, 56.0, 88.0, 73.0][i]
    height = [165, 170, 158, 175, 168, 160, 172, 180, 176, 162,
              173, 155, 178, 152, 177, 163, 169, 157, 182, 171][i]
    bmi = round(weight / ((height / 100) ** 2), 2)
    # Du Bois BSA
    bsa = round(0.007184 * (height ** 0.725) * (weight ** 0.425), 4)

    vas = [2, 3, 2, 4, 5, 2, 3, 6, 7, 2,
           2, 4, 3, 2, 5, 2, 3, 2, 4, 6][i]
    vas_drift = [0, 1, 0, -1][reading_idx]
    vas = max(1, min(10, vas + vas_drift))

    # For some high-acuity patients use BagMask/Ventilator
    if spo2 <= 92 or rr >= 24:
        breathing_options = ["Bóp bóng", "Thở máy", "Bóp bóng"]
        breathing = breathing_options[reading_idx % 3]
    else:
        breathing = "Tự thở"

    arm = "Left" if i % 2 == 0 else "Right"
    return (temp, pulse, pulse,  # heart_rate = pulse for simplicity
            spo2, bp_sys, bp_dia, rr, weight, height, bmi, bsa, vas, breathing, arm)


def add_hours(base_dt: str, hours: int) -> str:
    """Naive datetime string offset by integer hours."""
    from datetime import datetime, timedelta
    dt = datetime.fromisoformat(base_dt)
    return (dt + timedelta(hours=hours)).isoformat(timespec="seconds")


def main():
    L: list[str] = []
    L.append("SET QUOTED_IDENTIFIER ON;")
    L.append("SET ANSI_NULLS ON;")
    L.append("SET NOCOUNT ON;")
    L.append("")

    # ── VitalSigns ───────────────────────────────────────────────────────────────
    L.append("SET IDENTITY_INSERT [VitalSigns] ON;")
    visit_list = list(VISITS.items())
    # vs_id base: 390100; 4 readings per visit, 20 visits → 390100–390179
    for vi, (visit_id, (patient_id, dept_stay_id, base_dt)) in enumerate(visit_list):
        for ri, offset_h in enumerate(READING_OFFSETS_H):
            vs_id = 390100 + vi * 4 + ri
            measured_at = add_hours(base_dt, offset_h)
            (temp, pulse, hr, spo2, bpsys, bpdia, rr,
             weight, height, bmi, bsa, vas, breathing, arm) = _vs(vi, ri)
            dept_val = str(dept_stay_id) if dept_stay_id is not None else "NULL"
            created_at = measured_at  # created same as measured for seed simplicity
            L.append(
                f"IF NOT EXISTS (SELECT 1 FROM [VitalSigns] WHERE Id={vs_id})\n"
                f"  INSERT INTO [VitalSigns] "
                f"([Id],[IsActive],[PatientId],[MedicalVisitId],[MedicalVisitDepartmentStayId],"
                f"[Pulse],[HeartRate],[Spo2],[BloodPressureSys],[BloodPressureDia],[RespiratoryRate],"
                f"[Temperature],[Weight],[Height],[Bmi],[Bsa],[MeasuredAt],[MeasuredByUserId],"
                f"[BreathingStatus],[MeasuredArm],[VasScore],[Notes],"
                f"[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) "
                f"VALUES ({vs_id},1,{patient_id},{visit_id},{dept_val},"
                f"{pulse},{hr},{spo2},{bpsys},{bpdia},{rr},"
                f"{temp},{weight},{height},{bmi},{bsa},"
                f"'{measured_at}',{USER},"
                f"N'{breathing}',N'{arm}',{vas},N'Seed slot4',"
                f"'{created_at}',{USER},{TENANT},{HOSPITAL});"
            )
    L.append("SET IDENTITY_INSERT [VitalSigns] OFF;")
    L.append("")

    # ── VitalSignsHistory ─────────────────────────────────────────────────────────
    # One history snapshot per visit (simulates a correction of reading #2, ri=1)
    L.append("SET IDENTITY_INSERT [VitalSignsHistory] ON;")
    for vi, (visit_id, (patient_id, dept_stay_id, base_dt)) in enumerate(visit_list):
        hist_id = 390200 + vi
        # The VitalSigns record being corrected is reading #2 (ri=1)
        vs_id_corrected = 390100 + vi * 4 + 1
        measured_at = add_hours(base_dt, READING_OFFSETS_H[1])
        snapshot_at = add_hours(base_dt, READING_OFFSETS_H[1] + 1)  # 1h after measurement
        (temp, pulse, hr, spo2, bpsys, bpdia, rr,
         weight, height, bmi, bsa, vas, breathing, arm) = _vs(vi, 1)
        dept_val = str(dept_stay_id) if dept_stay_id is not None else "NULL"
        L.append(
            f"IF NOT EXISTS (SELECT 1 FROM [VitalSignsHistory] WHERE Id={hist_id})\n"
            f"  INSERT INTO [VitalSignsHistory] "
            f"([Id],[VitalSignsId],[PatientId],[MedicalVisitId],[MedicalVisitDepartmentStayId],"
            f"[MeasuredAt],[MeasuredByUserId],[BreathingStatus],[Pulse],[HeartRate],[Spo2],"
            f"[BloodPressureSys],[BloodPressureDia],[RespiratoryRate],[Temperature],"
            f"[Weight],[Height],[Bmi],[Bsa],[MeasuredArm],[VasScore],[Notes],"
            f"[SnapshotAt],[SnapshotBy],[Reason],"
            f"[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) "
            f"VALUES ({hist_id},{vs_id_corrected},{patient_id},{visit_id},{dept_val},"
            f"'{measured_at}',{USER},N'{breathing}',{pulse},{hr},{spo2},"
            f"{bpsys},{bpdia},{rr},{temp},"
            f"{weight},{height},{bmi},{bsa},N'{arm}',{vas},N'Seed slot4 (pre-correction snapshot)',"
            f"'{snapshot_at}',{USER},N'Correction during seed',"
            f"'{snapshot_at}',{USER},{TENANT},{HOSPITAL});"
        )
    L.append("SET IDENTITY_INSERT [VitalSignsHistory] OFF;")
    L.append("")

    # ── Update MedicalVisit.LastMeasuredId ─────────────────────────────────────────
    # LastMeasuredId = the VitalSigns row with MAX MeasuredAt, then MAX Id per visit.
    # Reading #4 (ri=3) has the latest MeasuredAt for each visit by construction.
    L.append("-- Update MedicalVisit.LastMeasuredId to the latest VitalSigns per visit")
    for vi, (visit_id, _) in enumerate(visit_list):
        last_vs_id = 390100 + vi * 4 + 3  # reading index 3 = latest
        L.append(
            f"UPDATE [MedicalVisit] SET [LastMeasuredId]={last_vs_id} "
            f"WHERE Id={visit_id} AND ([LastMeasuredId] IS NULL OR [LastMeasuredId] <> {last_vs_id});"
        )
    L.append("")

    # ── Verification counts ────────────────────────────────────────────────────────
    L.append(
        "SELECT "
        "(SELECT COUNT(*) FROM [VitalSigns] WHERE Id BETWEEN 390100 AND 390179) AS VitalSigns_seeded, "
        "(SELECT COUNT(*) FROM [VitalSignsHistory] WHERE Id BETWEEN 390200 AND 390219) AS VitalSignsHistory_seeded, "
        "(SELECT COUNT(*) FROM [MedicalVisit] WHERE Id BETWEEN 320101 AND 320120 AND LastMeasuredId IS NOT NULL) AS Visits_with_LastMeasuredId;"
    )

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"Wrote {OUT} ({len(visit_list)*4} VitalSigns, {len(visit_list)} VitalSignsHistory)")

    # ── Apply ──────────────────────────────────────────────────────────────────────
    cmd = ["docker", "exec", "-i", CONTAINER, "/opt/mssql-tools18/bin/sqlcmd",
           "-S", "localhost", "-U", "sa", "-P", SA, "-C", "-d", DB, "-b"]
    with OUT.open("rb") as f:
        r = subprocess.run(cmd, stdin=f, capture_output=True, text=True)
    print("STDOUT:", r.stdout.strip())
    if r.returncode != 0:
        print("STDERR:", r.stderr.strip())
        raise SystemExit(r.returncode)
    print("Seed applied successfully.")


if __name__ == "__main__":
    main()
