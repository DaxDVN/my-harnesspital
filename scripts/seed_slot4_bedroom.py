#!/usr/bin/env python3
"""Bed/Room coherence seed for slot 4 (ipd-improve-v4).

Goals:
  1. Spread Bed.AvailabilityStatus across Available / Maintenance / Cleaning /
     Isolated / Blocked so ward-map shows a non-monotone board.
  2. Set StatusRelatedVisitId on beds with active MedicalVisitBedStay so the
     ward-map popup has a visitId to navigate to.
  3. Add BedDayServiceConfigTier rows (currently 0) so the bed-day billing panel
     has data.
  4. Add 5 future BedReservations with realistic status spread (Pending / Confirmed
     / Expired) — linked to beds in dept 4/5 that have no active stay.
  5. Update BedType flags to use diverse types per room so BedClassification
     filter shows meaningful results (some SelfSelect, some GBCA).

ID range: 370000–379999 (this agent only).
Idempotent: every INSERT is guarded with IF NOT EXISTS.
"""
from __future__ import annotations
import subprocess
from pathlib import Path

CONTAINER = "mssql-hospital-wt4"
DB = "MyHospital"
SA = "Hospital123!"
TENANT, HOSPITAL, USER = 1, 1, 1
OUT = Path(__file__).with_name("seed_slot4_bedroom.sql")

# ── Beds with active stays (from audit) – update StatusRelatedVisitId ──
# BedId -> VisitId for active stays
ACTIVE_STAY_BEDS = {
    2021: 320101,
    2022: 320102,
    2023: 320103,
    2024: 320104,
    3001: 320105,
    5:    320106,
    6:    320107,
    7:    320108,
    19:   320113,
    13:   320114,
    3002: 320115,  # also 320117 Released – keep 320115 (Active)
    11:   320116,
    26:   320110,
}

# ── Beds with NO active stays to set non-Available statuses ──
# Chosen spread: a few beds in each dept 4+5 room
MAINTENANCE_BEDS = [1, 8]          # dept 4 room 69, dept 5 room 72
CLEANING_BEDS    = [2, 14]          # dept 4 room 69, dept 5 room 71
ISOLATED_BEDS    = [3, 21]          # dept 4 room 69, dept 5 room 72
BLOCKED_BEDS     = [20, 22]         # dept 4 room 69, dept 5 room 72

# Additional beds in QA rooms to show diversity
MAINTENANCE_BEDS += [2001, 2041]    # QA rooms 01 / 11
CLEANING_BEDS    += [2011, 2051]    # QA rooms 01 / 11

# ── BedType diversity: update some beds to use type 2 (GTCL/SelfSelect) and
#    type 3 (GVIP/SelfSelect) in QA rooms so BedClassification filter works ──
# We UPDATE existing beds (not insert), so no identity issues.
# Target: QA-IPD-BED-031 (id 2031) -> type 2; QA-IPD-BED-032 (id 2032) -> type 3
BEDTYPE_UPDATES = {
    2031: 2,   # GTCL – SelfSelect
    2032: 3,   # GVIP – SelfSelect
    2033: 2,   # another SelfSelect in room 03
    2041: 2,   # dept 5 QA room 11
    2042: 3,   # dept 5 QA room 12
}

# ── New BedReservations (IDs 370001–370005) ──
# Beds chosen: free beds in dept 4/5 with no active stay
NEW_RESERVATIONS = [
    # (reservationId, patientId, visitId, bedId, status, admDate, disDate)
    (370001, 310101, 320101, 2003, "Pending",   "2026-07-01", "2026-07-05"),
    (370002, 310102, 320102, 2013, "Confirmed", "2026-07-02", "2026-07-07"),
    (370003, 310103, 320103, 2043, "Confirmed", "2026-07-03", "2026-07-08"),
    (370004, 310104, 320104, 2004, "Expired",   "2026-06-10", "2026-06-14"),
    (370005, 310105, 320105, 2044, "Pending",   "2026-07-05", "2026-07-09"),
]

# BedReservationItem IDs: 370011–370015
RESERVATION_ITEMS = [
    (370011, 370001, 2003),
    (370012, 370002, 2013),
    (370013, 370003, 2043),
    (370014, 370004, 2004),
    (370015, 370005, 2044),
]

# ── BedDayServiceConfigTier (currently 0 rows) ──
# BedDayServiceConfig IDs already present: 1, 2, 3, 4
# Tier IDs: 370021–370030
TIERS = [
    # (id, configId, portion, fromH, toH, convertedDays, displayOrder)
    # Portion must be 'Bhyt' or 'Service' per BedDayServiceConfigService.TierPortion
    (370021, 1, "Bhyt",    0,    6,    0.0,  1),
    (370022, 1, "Bhyt",    6,   24,    1.0,  2),
    (370023, 1, "Bhyt",   24, None,    1.0,  3),
    (370024, 2, "Bhyt",    0,    6,    0.0,  1),
    (370025, 2, "Bhyt",    6,   24,    1.0,  2),
    (370026, 2, "Bhyt",   24, None,    1.0,  3),
    (370027, 3, "Service",  0,   12,    0.0,  1),
    (370028, 3, "Service", 12,   24,    1.0,  2),
    (370029, 3, "Service", 24, None,    1.0,  3),
    (370030, 4, "Bhyt",    0,   24,    1.0,  1),
]


def sql_null(v):
    return "NULL" if v is None else str(v)


def main():
    L: list[str] = []
    L.append("SET QUOTED_IDENTIFIER ON;")
    L.append("SET ANSI_NULLS ON;")
    L.append("SET NOCOUNT ON;")
    L.append("")

    # ── 1. Update AvailabilityStatus for non-Available beds ──
    L.append("-- 1. Spread Bed.AvailabilityStatus for visual diversity")
    for bid in MAINTENANCE_BEDS:
        L.append(
            f"UPDATE [Bed] SET AvailabilityStatus=N'Maintenance', "
            f"StatusReason=N'Bảo trì định kỳ', StatusUpdatedBy={USER}, "
            f"StatusUpdatedAt='2026-06-20T08:00:00', UpdatedAt='2026-06-20T08:00:00', UpdatedBy={USER} "
            f"WHERE Id={bid} AND AvailabilityStatus=N'Available';"
        )
    for bid in CLEANING_BEDS:
        L.append(
            f"UPDATE [Bed] SET AvailabilityStatus=N'Cleaning', "
            f"StatusReason=N'Đang vệ sinh sau bệnh nhân xuất viện', StatusUpdatedBy={USER}, "
            f"StatusUpdatedAt='2026-06-23T07:00:00', UpdatedAt='2026-06-23T07:00:00', UpdatedBy={USER} "
            f"WHERE Id={bid} AND AvailabilityStatus=N'Available';"
        )
    for bid in ISOLATED_BEDS:
        L.append(
            f"UPDATE [Bed] SET AvailabilityStatus=N'Isolated', "
            f"StatusReason=N'Cách ly bệnh nhân nghi ngờ', StatusUpdatedBy={USER}, "
            f"StatusUpdatedAt='2026-06-22T09:00:00', UpdatedAt='2026-06-22T09:00:00', UpdatedBy={USER} "
            f"WHERE Id={bid} AND AvailabilityStatus=N'Available';"
        )
    for bid in BLOCKED_BEDS:
        L.append(
            f"UPDATE [Bed] SET AvailabilityStatus=N'Blocked', "
            f"StatusReason=N'Dành riêng cho ca phẫu thuật', StatusUpdatedBy={USER}, "
            f"StatusUpdatedAt='2026-06-23T06:00:00', UpdatedAt='2026-06-23T06:00:00', UpdatedBy={USER} "
            f"WHERE Id={bid} AND AvailabilityStatus=N'Available';"
        )
    L.append("")

    # ── 2. Set StatusRelatedVisitId on beds with active stays ──
    L.append("-- 2. Link Bed.StatusRelatedVisitId to active MedicalVisit")
    for bid, vid in ACTIVE_STAY_BEDS.items():
        L.append(
            f"UPDATE [Bed] SET StatusRelatedVisitId={vid}, "
            f"UpdatedAt='2026-06-23T08:00:00', UpdatedBy={USER} "
            f"WHERE Id={bid} AND StatusRelatedVisitId IS NULL;"
        )
    L.append("")

    # ── 3. Update BedType on selected beds for classification diversity ──
    L.append("-- 3. BedType diversity (SelfSelect beds for BedClassification filter)")
    for bid, btid in BEDTYPE_UPDATES.items():
        L.append(
            f"UPDATE [Bed] SET BedTypeId={btid}, "
            f"UpdatedAt='2026-06-23T08:00:00', UpdatedBy={USER} "
            f"WHERE Id={bid};"
        )
    L.append("")

    # ── 4. BedDayServiceConfigTier (currently empty) ──
    L.append("-- 4. BedDayServiceConfigTier rows")
    L.append("SET IDENTITY_INSERT [BedDayServiceConfigTier] ON;")
    for (tid, cid, portion, fromH, toH, days, order) in TIERS:
        to_val = "NULL" if toH is None else str(toH)
        L.append(
            f"IF NOT EXISTS (SELECT 1 FROM [BedDayServiceConfigTier] WHERE Id={tid})\n"
            f"  INSERT INTO [BedDayServiceConfigTier] "
            f"([Id],[BedDayServiceConfigId],[Portion],[FromHours],[ToHours],[ConvertedDays],[DisplayOrder],"
            f"[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) "
            f"VALUES ({tid},{cid},N'{portion}',{fromH},{to_val},{days},{order},"
            f"'2026-06-23T08:00:00',{USER},{TENANT},{HOSPITAL});"
        )
    L.append("SET IDENTITY_INSERT [BedDayServiceConfigTier] OFF;")
    L.append("")

    # ── 5. New BedReservations ──
    L.append("-- 5. New BedReservations")
    L.append("SET IDENTITY_INSERT [BedReservation] ON;")
    for (rid, pid, vid, bid, status, admDate, disDate) in NEW_RESERVATIONS:
        L.append(
            f"IF NOT EXISTS (SELECT 1 FROM [BedReservation] WHERE Id={rid})\n"
            f"  INSERT INTO [BedReservation] "
            f"([Id],[MedicalVisitId],[PatientId],[ExpectedAdmissionDate],[ExpectedDischargeDate],"
            f"[Status],[ReservedById],[ReservedAt],[LinkedSurgeryServiceIds],"
            f"[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) "
            f"VALUES ({rid},{vid},{pid},'{admDate}T08:00:00','{disDate}T10:00:00',"
            f"N'{status}',{USER},'2026-06-20T08:00:00',N'[]',"
            f"'2026-06-20T08:00:00',{USER},{TENANT},{HOSPITAL});"
        )
    L.append("SET IDENTITY_INSERT [BedReservation] OFF;")
    L.append("")

    # ── 6. BedReservationItems ──
    L.append("-- 6. BedReservationItems")
    L.append("SET IDENTITY_INSERT [BedReservationItem] ON;")
    for (iid, rid, bid) in RESERVATION_ITEMS:
        L.append(
            f"IF NOT EXISTS (SELECT 1 FROM [BedReservationItem] WHERE Id={iid})\n"
            f"  INSERT INTO [BedReservationItem] "
            f"([Id],[BedReservationId],[BedId],[IsForCompanion],"
            f"[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) "
            f"VALUES ({iid},{rid},{bid},0,"
            f"'2026-06-20T08:00:00',{USER},{TENANT},{HOSPITAL});"
        )
    L.append("SET IDENTITY_INSERT [BedReservationItem] OFF;")
    L.append("")

    sql = "\n".join(L)
    OUT.write_text(sql, encoding="utf-8")
    print(f"[seed_slot4_bedroom] SQL written to {OUT}")

    result = subprocess.run(
        [
            "docker", "exec", "-i", CONTAINER,
            "/opt/mssql-tools18/bin/sqlcmd",
            "-S", "localhost", "-U", "sa", "-P", SA,
            "-C", "-d", DB, "-W", "-w", "300", "-b",
        ],
        input=sql,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("[ERROR] sqlcmd failed:")
        print(result.stderr)
        print(result.stdout)
        raise SystemExit(1)
    print("[seed_slot4_bedroom] Applied successfully.")
    if result.stdout.strip():
        print(result.stdout)


if __name__ == "__main__":
    main()
