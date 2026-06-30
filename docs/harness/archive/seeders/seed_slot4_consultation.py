#!/usr/bin/env python3
"""Consultation module gap-fill seed for slot 4 (ipd-improve-v4).

Gap being closed:
  - ConsultationRecordDrug = 0 because the project CSV seeder lists
    "ConsultationRecordDrug" at line 267 BEFORE "Product" (line 289), so the
    CSV was processed before its FK target existed → silent skip + zero rows.
  - Product (and its dependency chain Company/Unit/DosageForm) = 0 on this slot.

This script seeds ONLY the minimum rows needed:
  1. Company (1 row) – no FK deps
  2. Unit    (1 row) – no FK deps
  3. DosageForm (1 row) – no FK deps
  4. Product  (5 drug rows referencing the above) – no enforced FKs in schema
  5. ConsultationRecordDrug – one entry per Drug-type ConsultationRecord
     (records 440006–440015, RecordType=Drug, IDs in range 440xxx)

ID range reserved for this agent: 380000–389999.
Target: mssql-hospital-wt4 (localhost,1437).
"""
from __future__ import annotations
import subprocess
from pathlib import Path

CONTAINER = "mssql-hospital-wt4"
DB = "MyHospital"
SA = "Hospital123!"
TENANT, HOSPITAL, USER = 1, 1, 1
OUT = Path(__file__).with_name("seed_slot4_consultation.sql")

# -----------------------------------------------------------------------
# Drug-type ConsultationRecord IDs (verified above: RecordType='Drug')
# -----------------------------------------------------------------------
DRUG_RECORD_IDS = [440006, 440007, 440008, 440009, 440010,
                   440011, 440012, 440013, 440014, 440015]

# -----------------------------------------------------------------------
# 5 minimal drug products (varied types for FE filter coverage)
# -----------------------------------------------------------------------
PRODUCTS = [
    # (Id, Code, Name, DrugCategory, Note)
    (380001, "DRUG-001", "Paracetamol 500mg",         "Analgesic",     "Hạ sốt giảm đau"),
    (380002, "DRUG-002", "Amoxicillin 500mg",         "Antibiotic",    "Kháng sinh nhóm beta-lactam"),
    (380003, "DRUG-003", "Omeprazole 20mg",           "GastroProtective", "Ức chế bơm proton"),
    (380004, "DRUG-004", "Metformin 500mg",           "Antidiabetic",  "Điều trị đái tháo đường type 2"),
    (380005, "DRUG-005", "Amlodipine 5mg",            "Antihypertensive","Chẹn kênh canxi"),
]

# Assign products round-robin to drug records
def product_for(record_id: int) -> int:
    idx = DRUG_RECORD_IDS.index(record_id)
    return PRODUCTS[idx % len(PRODUCTS)][0]

def product_code_for(record_id: int) -> str:
    idx = DRUG_RECORD_IDS.index(record_id)
    return PRODUCTS[idx % len(PRODUCTS)][1]

def product_name_for(record_id: int) -> str:
    idx = DRUG_RECORD_IDS.index(record_id)
    return PRODUCTS[idx % len(PRODUCTS)][2]


def main():
    L: list[str] = []
    L.append("SET QUOTED_IDENTIFIER ON;")
    L.append("SET ANSI_NULLS ON;")
    L.append("SET NOCOUNT ON;")
    L.append("")

    # ------------------------------------------------------------------
    # 1. Company (no FK deps, no identity on PK? let's check – use IDENTITY INSERT)
    # ------------------------------------------------------------------
    L.append("-- Company (manufacturer placeholder)")
    L.append("SET IDENTITY_INSERT [Company] ON;")
    L.append(
        "IF NOT EXISTS (SELECT 1 FROM [Company] WHERE Id=380001)\n"
        "  INSERT INTO [Company] ([Id],[Name],[IsActive],[TenantId],[HospitalId])\n"
        "  VALUES (380001,N'Dược phẩm Việt Nam (Seed)',1,1,1);"
    )
    L.append("SET IDENTITY_INSERT [Company] OFF;")
    L.append("")

    # ------------------------------------------------------------------
    # 2. Unit  (NOT-NULL: Id, Code, Name, IsActive, DisplayOrder, TenantId, HospitalId)
    # ------------------------------------------------------------------
    L.append("-- Unit (viên/tablet placeholder)")
    L.append("SET IDENTITY_INSERT [Unit] ON;")
    L.append(
        "IF NOT EXISTS (SELECT 1 FROM [Unit] WHERE Id=380001)\n"
        "  INSERT INTO [Unit] ([Id],[Code],[Name],[IsActive],[DisplayOrder],[TenantId],[HospitalId])\n"
        "  VALUES (380001,N'VIEN',N'Viên',1,1,1,1);"
    )
    L.append("SET IDENTITY_INSERT [Unit] OFF;")
    L.append("")

    # ------------------------------------------------------------------
    # 3. DosageForm  (NOT-NULL: Id, Code, Name, IsActive, TenantId, HospitalId)
    # ------------------------------------------------------------------
    L.append("-- DosageForm (tablet placeholder)")
    L.append("SET IDENTITY_INSERT [DosageForm] ON;")
    L.append(
        "IF NOT EXISTS (SELECT 1 FROM [DosageForm] WHERE Id=380001)\n"
        "  INSERT INTO [DosageForm] ([Id],[Code],[Name],[IsActive],[TenantId],[HospitalId])\n"
        "  VALUES (380001,N'TABLET',N'Viên nén',1,1,1);"
    )
    L.append("SET IDENTITY_INSERT [DosageForm] OFF;")
    L.append("")

    # ------------------------------------------------------------------
    # 4. Product (5 drug rows, all pointing at the Company/Unit/DosageForm above)
    # ------------------------------------------------------------------
    L.append("-- Product (5 minimal drug rows)")
    L.append("SET IDENTITY_INSERT [Product] ON;")
    for pid, code, name, drug_cat, desc in PRODUCTS:
        L.append(
            f"IF NOT EXISTS (SELECT 1 FROM [Product] WHERE Id={pid})\n"
            f"  INSERT INTO [Product]\n"
            f"    ([Id],[IsActive],[IsManagedByLot],[Code],[Name],[DrugCategory],\n"
            f"     [Description],[ManufacturerId],[UnitId],[DosageFormId],\n"
            f"     [RequiredDoctorPrescription],[AllowPurchaseFromSupplier],\n"
            f"     [DisableInpatient],[DisableOutpatient],\n"
            f"     [CreatedAt],[CreatedBy],[TenantId],[HospitalId])\n"
            f"  VALUES ({pid},1,0,N'{code}',N'{name}',N'{drug_cat}',\n"
            f"     N'{desc}',380001,380001,380001,\n"
            f"     1,1,\n"
            f"     0,0,\n"
            f"     '2026-06-01T08:00:00',{USER},{TENANT},{HOSPITAL});"
        )
    L.append("SET IDENTITY_INSERT [Product] OFF;")
    L.append("")

    # ------------------------------------------------------------------
    # 5. ConsultationRecordDrug (one per Drug-type ConsultationRecord)
    #    ID range: 380010–380019 (10 records)
    # ------------------------------------------------------------------
    L.append("-- ConsultationRecordDrug (one entry per Drug-type ConsultationRecord)")
    L.append("SET IDENTITY_INSERT [ConsultationRecordDrug] ON;")
    for i, rec_id in enumerate(DRUG_RECORD_IDS):
        drug_id = 380010 + i
        prod_id = product_for(rec_id)
        prod_code = product_code_for(rec_id)
        prod_name = product_name_for(rec_id)
        L.append(
            f"IF NOT EXISTS (SELECT 1 FROM [ConsultationRecordDrug] WHERE Id={drug_id})\n"
            f"  INSERT INTO [ConsultationRecordDrug]\n"
            f"    ([Id],[RecordId],[ProductId],[ProductNameSnapshot],[ProductCodeSnapshot],\n"
            f"     [Note],[CreatedAt],[CreatedBy],[TenantId],[HospitalId])\n"
            f"  VALUES ({drug_id},{rec_id},{prod_id},N'{prod_name}',N'{prod_code}',\n"
            f"     N'Thuốc hội chẩn (seed slot 4)','2026-06-19T09:00:00',{USER},{TENANT},{HOSPITAL});"
        )
    L.append("SET IDENTITY_INSERT [ConsultationRecordDrug] OFF;")
    L.append("")

    # ------------------------------------------------------------------
    # Verification query
    # ------------------------------------------------------------------
    L.append("-- Post-seed counts")
    L.append(
        "SELECT\n"
        "  (SELECT COUNT(*) FROM Company)               AS Company,\n"
        "  (SELECT COUNT(*) FROM Unit)                  AS Unit,\n"
        "  (SELECT COUNT(*) FROM DosageForm)            AS DosageForm,\n"
        "  (SELECT COUNT(*) FROM Product)               AS Product,\n"
        "  (SELECT COUNT(*) FROM ConsultationRecordDrug) AS ConsultationRecordDrug;"
    )

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT}")

    # Apply
    cmd = [
        "docker", "exec", "-i", CONTAINER,
        "/opt/mssql-tools18/bin/sqlcmd",
        "-S", "localhost", "-U", "sa", "-P", SA,
        "-C", "-d", DB, "-b", "-W", "-w", "300",
    ]
    with OUT.open("rb") as f:
        r = subprocess.run(cmd, stdin=f, capture_output=True, text=True)
    print("STDOUT:", r.stdout.strip())
    if r.stderr.strip():
        print("STDERR:", r.stderr.strip())
    if r.returncode != 0:
        raise SystemExit(r.returncode)


if __name__ == "__main__":
    main()
