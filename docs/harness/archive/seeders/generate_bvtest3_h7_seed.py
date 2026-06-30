#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WORKTREE = ROOT / "worktrees" / "fix-bug-noi-tru" / "be"
SEED_LOCAL = WORKTREE / "MyHospital.ServiceInterface" / "SeedData" / "local"
OUTPUT_SQL = ROOT / "docs" / "session-notes" / "seed-bvtest3-h7-2026-06-19.sql"

TARGET_TENANT_ID = "6"
TARGET_HOSPITAL_ID = "7"

GENERIC_USER_ID = "176"
DOCTOR_USER_ID = "179"
SECOND_DOCTOR_USER_ID = "180"
NURSE_USER_ID = "181"

DEPARTMENT_MAP = {
    "3": "23",   # Lab
    "4": "6",    # Internal medicine
    "5": "17",   # Surgery
    "13": "6",   # Critical care folded into internal medicine for seed scope
}

ROOM_TYPE_MAP = {
    "3": "34",   # Examination room
    "5": "36",   # Bed room
    "6": "37",   # Self-select bed room
}

PATIENT_TYPE_ID_MAP = {
    "1": "6330501",
    "2": "6330502",
    "3": "6330503",
    "4": "6330504",
    "5": "6330505",
}

IMRT_ID_MAP = {
    "1": "6337201",
    "2": "6337202",
    "3": "6337203",
    "4": "6337204",
    "5": "6337205",
}

SERVICE_ID_MAP = {
    "1": "6337001",
    "1000": "6337002",
    "1002": "6337003",
    "1004": "6337004",
    "1005": "6337005",
}

BED_DAY_CONFIG_ID_MAP = {
    "1": "6337101",
    "3": "6337102",
    "4": "6337103",
}

SHIFT_ID_MAP = {
    "1": "6337301",
    "2": "6337302",
    "3": "6337303",
}


PATIENT_TYPE_ROWS = [
    {
        "Id": "6330501",
        "PatientTypeCode": "SV",
        "PatientTypeName": "Service Visit",
        "HealthInsuranceOption": "Disabled",
        "CommercialInsuranceOption": "Disabled",
        "IsForeign": "false",
        "IsDefault": "true",
        "CreatedAt": "2026-06-19T06:00:00",
        "CreatedBy": GENERIC_USER_ID,
        "UpdatedAt": "2026-06-19T06:00:00",
        "UpdatedBy": GENERIC_USER_ID,
        "IsActive": "true",
        "LanguageCode": "seed-h7-patient-type-service",
        "TenantId": TARGET_TENANT_ID,
        "HospitalId": TARGET_HOSPITAL_ID,
    },
    {
        "Id": "6330502",
        "PatientTypeCode": "HC",
        "PatientTypeName": "Health Check",
        "HealthInsuranceOption": "Disabled",
        "CommercialInsuranceOption": "Disabled",
        "IsForeign": "false",
        "IsDefault": "false",
        "CreatedAt": "2026-06-19T06:00:00",
        "CreatedBy": GENERIC_USER_ID,
        "UpdatedAt": "2026-06-19T06:00:00",
        "UpdatedBy": GENERIC_USER_ID,
        "IsActive": "true",
        "LanguageCode": "seed-h7-patient-type-health-check",
        "TenantId": TARGET_TENANT_ID,
        "HospitalId": TARGET_HOSPITAL_ID,
    },
    {
        "Id": "6330503",
        "PatientTypeCode": "INTL",
        "PatientTypeName": "International Patient",
        "HealthInsuranceOption": "Disabled",
        "CommercialInsuranceOption": "Optional",
        "IsForeign": "true",
        "IsDefault": "false",
        "CreatedAt": "2026-06-19T06:00:00",
        "CreatedBy": GENERIC_USER_ID,
        "UpdatedAt": "2026-06-19T06:00:00",
        "UpdatedBy": GENERIC_USER_ID,
        "IsActive": "true",
        "LanguageCode": "seed-h7-patient-type-international",
        "TenantId": TARGET_TENANT_ID,
        "HospitalId": TARGET_HOSPITAL_ID,
    },
    {
        "Id": "6330504",
        "PatientTypeCode": "NHI",
        "PatientTypeName": "National Insurance",
        "HealthInsuranceOption": "Required",
        "CommercialInsuranceOption": "Disabled",
        "IsForeign": "false",
        "IsDefault": "false",
        "CreatedAt": "2026-06-19T06:00:00",
        "CreatedBy": GENERIC_USER_ID,
        "UpdatedAt": "2026-06-19T06:00:00",
        "UpdatedBy": GENERIC_USER_ID,
        "IsActive": "true",
        "LanguageCode": "seed-h7-patient-type-nhi",
        "TenantId": TARGET_TENANT_ID,
        "HospitalId": TARGET_HOSPITAL_ID,
    },
    {
        "Id": "6330505",
        "PatientTypeCode": "COM",
        "PatientTypeName": "Commercial Insurance",
        "HealthInsuranceOption": "Disabled",
        "CommercialInsuranceOption": "Required",
        "IsForeign": "false",
        "IsDefault": "false",
        "CreatedAt": "2026-06-19T06:00:00",
        "CreatedBy": GENERIC_USER_ID,
        "UpdatedAt": "2026-06-19T06:00:00",
        "UpdatedBy": GENERIC_USER_ID,
        "IsActive": "true",
        "LanguageCode": "seed-h7-patient-type-commercial",
        "TenantId": TARGET_TENANT_ID,
        "HospitalId": TARGET_HOSPITAL_ID,
    },
]


IMRT_ROWS = [
    {"Id": "6337201", "Code": "InternalMedicine", "Name": "Internal Medicine Record", "DisplayOrder": "1", "IsActive": "true", "CreatedAt": "2026-06-19T06:05:00", "CreatedBy": GENERIC_USER_ID, "UpdatedAt": "2026-06-19T06:05:00", "UpdatedBy": GENERIC_USER_ID, "TenantId": TARGET_TENANT_ID, "HospitalId": TARGET_HOSPITAL_ID},
    {"Id": "6337202", "Code": "Surgery", "Name": "Surgery Record", "DisplayOrder": "2", "IsActive": "true", "CreatedAt": "2026-06-19T06:05:00", "CreatedBy": GENERIC_USER_ID, "UpdatedAt": "2026-06-19T06:05:00", "UpdatedBy": GENERIC_USER_ID, "TenantId": TARGET_TENANT_ID, "HospitalId": TARGET_HOSPITAL_ID},
    {"Id": "6337203", "Code": "ObstetricsGynecology", "Name": "Obstetrics And Gynecology Record", "DisplayOrder": "3", "IsActive": "true", "CreatedAt": "2026-06-19T06:05:00", "CreatedBy": GENERIC_USER_ID, "UpdatedAt": "2026-06-19T06:05:00", "UpdatedBy": GENERIC_USER_ID, "TenantId": TARGET_TENANT_ID, "HospitalId": TARGET_HOSPITAL_ID},
    {"Id": "6337204", "Code": "Pediatrics", "Name": "Pediatrics Record", "DisplayOrder": "4", "IsActive": "true", "CreatedAt": "2026-06-19T06:05:00", "CreatedBy": GENERIC_USER_ID, "UpdatedAt": "2026-06-19T06:05:00", "UpdatedBy": GENERIC_USER_ID, "TenantId": TARGET_TENANT_ID, "HospitalId": TARGET_HOSPITAL_ID},
    {"Id": "6337205", "Code": "IntensiveCare", "Name": "Intensive Care Record", "DisplayOrder": "5", "IsActive": "true", "CreatedAt": "2026-06-19T06:05:00", "CreatedBy": GENERIC_USER_ID, "UpdatedAt": "2026-06-19T06:05:00", "UpdatedBy": GENERIC_USER_ID, "TenantId": TARGET_TENANT_ID, "HospitalId": TARGET_HOSPITAL_ID},
]


SERVICE_OVERRIDES = {
    "1": ("H7.KB.NOI.001", "General Internal Examination", "Adult internal medicine examination for outpatient and admission intake."),
    "1000": ("H7.AdmissionAssessment", "Admission Assessment", "Admission evaluation used to convert an outpatient visit into inpatient admission."),
    "1002": ("H7.NGBNT.001", "Standard Inpatient Bed Day", "Standard inpatient bed-day service for internal and surgical wards."),
    "1004": ("H7.NGBNT.002", "Self-Select Bed Day", "Self-select inpatient bed-day service for private room scenarios."),
    "1005": ("H7.NGBNT.003", "Critical Care Bed Day", "Critical care bed-day service for monitored admissions."),
}


MALE_NAMES = [
    "Liam", "Noah", "Oliver", "Elijah", "James", "William", "Benjamin", "Lucas", "Henry", "Alexander",
    "Mason", "Michael", "Ethan", "Daniel", "Jacob", "Logan", "Jackson", "Levi", "Sebastian", "Mateo",
]

FEMALE_NAMES = [
    "Olivia", "Emma", "Charlotte", "Amelia", "Sophia", "Isabella", "Ava", "Mia", "Evelyn", "Harper",
    "Luna", "Camila", "Gianna", "Elizabeth", "Eleanor", "Ella", "Abigail", "Emily", "Avery", "Scarlett",
]

LAST_NAMES = [
    "Carter", "Bennett", "Reed", "Foster", "Brooks", "Hayes", "Morgan", "Turner", "Parker", "Cooper",
    "Howard", "Mitchell", "Murphy", "Sullivan", "Perry", "Coleman", "Stewart", "Powell", "Long", "Ross",
]


TABLE_MAP = [
    ("PatientType", "PatientType"),
    ("InpatientMedicalRecordType", "InpatientMedicalRecordType"),
    ("MedicalService", "MedicalService"),
    ("BedDayServiceConfig", "BedDayServiceConfig"),
    ("BedDayServiceConfigTier", "BedDayServiceConfigTier"),
    ("PaymentMerchantConfig", "PaymentMerchantConfigs"),
    ("Room", "Room"),
    ("DepartmentRoom", "DepartmentRoom"),
    ("Bed", "Bed"),
    ("Shift", "Shift"),
    ("Patient", "Patient"),
    ("MedicalVisit", "MedicalVisit"),
    ("MedicalVisitClinicalService", "MedicalVisitClinicalService"),
    ("InpatientAdmissionOrders", "InpatientAdmissionOrders"),
    ("MedicalVisitApproachLog", "MedicalVisitApproachLog"),
    ("VitalSigns", "VitalSigns"),
    ("MedicalVisitDepartmentStay", "MedicalVisitDepartmentStay"),
    ("BedReservation", "BedReservation"),
    ("BedReservationItem", "BedReservationItem"),
    ("MedicalVisitBedStay", "MedicalVisitBedStay"),
    ("Billing", "Billings"),
    ("BillingItem", "BillingItems"),
    ("Invoice", "Invoices"),
    ("InvoiceItem", "InvoiceItems"),
    ("PaymentTransaction", "PaymentTransactions"),
    ("InvoicePaymentAllocation", "InvoicePaymentAllocations"),
    ("PaymentLog", "PaymentLogs"),
    ("ScheduleRule", "ScheduleRule"),
    ("ShiftAssignment", "ShiftAssignment"),
    ("ScheduleSnapshot", "ScheduleSnapshot"),
]

TABLE_DEFAULTS = {
    "MedicalVisitBedStay": {
        "LinkedSurgeryServiceIds": "[]",
    },
}


USED_ROOM_SOURCE_IDS = [
    69, 70, 71, 72, 73,
    2001, 2002, 2003, 2004, 2005,
    2006, 2007, 2008, 2009, 2010,
    2011, 2012, 2013, 2014, 2015,
    2016, 2017, 2018, 2019, 2020,
]


def read_csv_rows(name: str) -> list[dict[str, str]]:
    with (SEED_LOCAL / name).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def fetch_table_columns(table_names: list[str]) -> dict[str, list[str]]:
    quoted = ",".join(f"'{name}'" for name in table_names)
    query = (
        "SET NOCOUNT ON; "
        "SELECT TABLE_NAME + '|' + COLUMN_NAME "
        f"FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME IN ({quoted}) "
        "ORDER BY TABLE_NAME, ORDINAL_POSITION;"
    )
    cmd = [
        "docker", "exec", "mssql-hospital-wt3",
        "/opt/mssql-tools18/bin/sqlcmd",
        "-S", "localhost",
        "-U", "sa",
        "-P", "Hospital123!",
        "-C",
        "-d", "MyHospital",
        "-W",
        "-w", "220",
        "-Q", query,
    ]
    output = subprocess.check_output(cmd, text=True)
    result: dict[str, list[str]] = defaultdict(list)
    for line in output.splitlines():
        if "|" not in line:
            continue
        table_name, column_name = line.strip().split("|", 1)
        if table_name and column_name:
            result[table_name].append(column_name)
    return result


def sql_value(value: str | None) -> str:
    if value is None:
        return "NULL"
    text = str(value)
    if text == "":
        return "NULL"
    lower = text.lower()
    if lower == "true":
        return "1"
    if lower == "false":
        return "0"
    escaped = text.replace("'", "''")
    return f"N'{escaped}'"


def prefix_code(value: str | None, prefix: str = "H7-") -> str:
    if not value:
        return ""
    return f"{prefix}{value}"


def map_generic_user(value: str | None) -> str:
    if not value:
        return ""
    return {
        "1": GENERIC_USER_ID,
        "4": DOCTOR_USER_ID,
        "5": SECOND_DOCTOR_USER_ID,
        "6": NURSE_USER_ID,
    }.get(value, GENERIC_USER_ID)


def map_staff_user(value: str | None) -> str:
    if not value:
        return ""
    return {
        "4": DOCTOR_USER_ID,
        "5": SECOND_DOCTOR_USER_ID,
        "6": NURSE_USER_ID,
        "1": DOCTOR_USER_ID,
    }.get(value, DOCTOR_USER_ID)


def mapped(mapping: dict[str, str], value: str | None) -> str:
    return mapping.get(value or "", "")


def realistic_patient_name(index: int, gender: str) -> str:
    first_pool = FEMALE_NAMES if gender.lower() == "female" else MALE_NAMES
    first = first_pool[index % len(first_pool)]
    last = LAST_NAMES[(index // len(first_pool)) % len(LAST_NAMES)]
    return f"{first} {last}"


def room_name_and_type(source_id: int) -> tuple[str, str]:
    if source_id == 69:
        return "Internal Ward Room 01", "36"
    if source_id == 70:
        return "Internal Ward Room 02", "36"
    if source_id == 71:
        return "Surgical Ward Room 01", "36"
    if source_id == 72:
        return "Surgical Ward Room 02", "36"
    if source_id == 73:
        return "Critical Care Room 01", "36"
    if 2001 <= source_id <= 2005:
        return f"Self-Select Suite {source_id - 2000:02d}", "37"
    if 2006 <= source_id <= 2010:
        return f"Internal Overflow Room {source_id - 2000:02d}", "36"
    if 2011 <= source_id <= 2020:
        return f"Surgical Overflow Room {source_id - 2000:02d}", "36"
    return f"Seed Room {source_id}", "36"


def bed_name(source_code: str, source_room_id: int) -> str:
    if source_room_id in {69, 70}:
        prefix = "Internal Bed"
    elif source_room_id in {71, 72}:
        prefix = "Surgical Bed"
    elif source_room_id == 73:
        prefix = "Critical Care Bed"
    elif 2001 <= source_room_id <= 2005:
        prefix = "Self-Select Bed"
    else:
        prefix = "Overflow Bed"
    return f"{prefix} {source_code.split('-')[-1]}"


def bed_status(source_bed_id: str, active_bed_ids: set[str], self_select_ids: set[str]) -> tuple[str, str]:
    if source_bed_id in active_bed_ids:
        return "Occupied", "Active inpatient bed stay is linked to this bed."
    if source_bed_id in self_select_ids:
        return "Reserved", "Self-select bed reserved for premium bed-day scenarios."
    numeric = int(source_bed_id)
    cycle = [
        ("Available", "Ready for immediate assignment."),
        ("Cleaning", "Post-discharge cleaning workflow."),
        ("Maintenance", "Short maintenance window for equipment checks."),
        ("Reserved", "Held for scheduled inpatient admission."),
    ]
    return cycle[numeric % len(cycle)]


@dataclass
class SeedBundle:
    table_name: str
    rows: list[dict[str, str]]


def main() -> None:
    source = {name: read_csv_rows(f"{name}.csv") for name, _ in TABLE_MAP if (SEED_LOCAL / f"{name}.csv").exists()}
    table_columns = fetch_table_columns([table for _, table in TABLE_MAP])

    patient_rows = source["Patient"]
    room_rows = source["Room"]
    dept_room_rows = source["DepartmentRoom"]
    bed_rows = source["Bed"]

    visit_rows = list(source["MedicalVisit"])
    existing_visit_ids = {row["Id"] for row in visit_rows}
    clinical_by_visit = defaultdict(list)
    for row in source["MedicalVisitClinicalService"]:
        clinical_by_visit[row["MedicalVisitId"]].append(row)

    missing_visit_ids = sorted(set(clinical_by_visit) - existing_visit_ids, key=int)
    for missing_visit_id in missing_visit_ids:
        first_clinical = clinical_by_visit[missing_visit_id][0]
        suffix = int(missing_visit_id) % 100
        is_transfer_assessment = missing_visit_id.startswith("3202")
        visit_rows.append(
            {
                "Id": missing_visit_id,
                "Code": f"QA-CSV-MV-{'SENT' if is_transfer_assessment else 'OPD'}-{suffix:02d}",
                "PatientId": first_clinical["PatientId"],
                "PatientTypeId": "1",
                "TreatmentTypeId": "1",
                "Status": "InProgress" if is_transfer_assessment else "Completed",
                "ReceptionTime": first_clinical["StartedAt"],
                "DepartmentId": "4",
                "InitialDepartmentId": "4",
                "IsPriority": "false",
                "ClinicalServiceCount": "1",
                "DiagnosticImagingServiceCount": "0",
                "LaboratoryTestServiceCount": "0",
                "AdmissionNumber": "",
                "AdmissionTime": "",
                "AttendingUserId": "1",
                "AssignedNurseUserId": "",
                "MedicalRecordTypeId": "",
                "ArrivalForm": "",
                "ExpectedAdmissionDate": "",
                "AdmissionCondition": "",
                "AdmissionReason": "",
                "AdmissionNotes": "",
                "PatientConditionCode": "Stable",
                "ReceivedBy": "1",
                "Notes": first_clinical["Note"] or first_clinical["ReasonForVisit"],
                "TenantId": "1",
                "HospitalId": "1",
                "CreatedBy": "1",
                "LanguageCode": f"Seed-Synthetic-Visit-{missing_visit_id}",
                "IsLongTermOutpatient": "false",
            }
        )
    source["MedicalVisit"] = sorted(visit_rows, key=lambda row: int(row["Id"]))

    room_map = {str(src_id): str(6338001 + idx) for idx, src_id in enumerate(USED_ROOM_SOURCE_IDS)}
    bed_map = {row["Id"]: str(6339001 + idx) for idx, row in enumerate(bed_rows)}
    patient_map = {row["Id"]: str(6331001 + idx) for idx, row in enumerate(patient_rows)}
    visit_map = {row["Id"]: str(6332001 + idx) for idx, row in enumerate(source["MedicalVisit"])}
    clinical_map = {row["Id"]: str(6332101 + idx) for idx, row in enumerate(source["MedicalVisitClinicalService"])}
    admission_order_map = {row["Id"]: str(6332201 + idx) for idx, row in enumerate(source["InpatientAdmissionOrders"])}
    approach_log_map = {row["Id"]: str(6332301 + idx) for idx, row in enumerate(source["MedicalVisitApproachLog"])}
    vital_sign_map = {row["Id"]: str(6332401 + idx) for idx, row in enumerate(source["VitalSigns"])}
    dept_stay_map = {row["Id"]: str(6333001 + idx) for idx, row in enumerate(source["MedicalVisitDepartmentStay"])}
    reservation_map = {row["Id"]: str(6335001 + idx) for idx, row in enumerate(source["BedReservation"])}
    reservation_item_map = {row["Id"]: str(6336001 + idx) for idx, row in enumerate(source["BedReservationItem"])}
    bed_stay_map = {row["Id"]: str(6334001 + idx) for idx, row in enumerate(source["MedicalVisitBedStay"])}
    billing_map = {row["Id"]: str(6337001 + idx) for idx, row in enumerate(source["Billing"])}
    billing_item_map = {row["Id"]: str(6338001 + idx) for idx, row in enumerate(source["BillingItem"])}
    invoice_map = {row["Id"]: str(6339001 + idx) for idx, row in enumerate(source["Invoice"])}
    invoice_item_map = {row["Id"]: str(6340001 + idx) for idx, row in enumerate(source["InvoiceItem"])}
    merchant_map = {row["Id"]: str(6344001 + idx) for idx, row in enumerate(source["PaymentMerchantConfig"])}
    payment_tx_map = {row["Id"]: str(6341001 + idx) for idx, row in enumerate(source["PaymentTransaction"])}
    allocation_map = {row["Id"]: str(6342001 + idx) for idx, row in enumerate(source["InvoicePaymentAllocation"])}
    payment_log_map = {row["Id"]: str(6343001 + idx) for idx, row in enumerate(source["PaymentLog"])}
    schedule_rule_map = {row["Id"]: str(6345001 + idx) for idx, row in enumerate(source["ScheduleRule"])}
    shift_assignment_map = {row["Id"]: str(6346001 + idx) for idx, row in enumerate(source["ShiftAssignment"])}
    schedule_snapshot_map = {row["Id"]: str(6347001 + idx) for idx, row in enumerate(source["ScheduleSnapshot"])}
    bed_day_tier_map = {row["Id"]: str(6348001 + idx) for idx, row in enumerate(source["BedDayServiceConfigTier"])}

    visit_code_map: dict[str, str] = {}
    patient_code_map: dict[str, str] = {}
    patient_name_map: dict[str, str] = {}

    patient_type_per_patient: dict[str, str] = {}
    for row in source["MedicalVisit"]:
        source_patient_id = row["PatientId"]
        if row.get("HealthInsuranceCardNumber"):
            patient_type_per_patient[source_patient_id] = PATIENT_TYPE_ID_MAP["4"]
        elif row.get("CommercialInsuranceContractNumber"):
            patient_type_per_patient[source_patient_id] = PATIENT_TYPE_ID_MAP["5"]
        else:
            patient_type_per_patient.setdefault(source_patient_id, PATIENT_TYPE_ID_MAP["1"])

    active_bed_ids = {
        row["BedId"]
        for row in source["MedicalVisitBedStay"]
        if row.get("Status") == "Active" and not row.get("EndedAt")
    }
    self_select_bed_ids = {row["BedId"] for row in source["MedicalVisitBedStay"] if row.get("MedicalServiceId") == "1004"}

    bundles: list[SeedBundle] = []

    bundles.append(SeedBundle("PatientType", PATIENT_TYPE_ROWS))
    bundles.append(SeedBundle("InpatientMedicalRecordType", IMRT_ROWS))

    medical_services: list[dict[str, str]] = []
    for row in source["MedicalService"]:
        source_id = row["Id"]
        if source_id not in SERVICE_ID_MAP:
            continue
        service_code, service_name, note = SERVICE_OVERRIDES[source_id]
        new_row = dict(row)
        new_row.update(
            {
                "Id": SERVICE_ID_MAP[source_id],
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "ServiceCode": service_code,
                "ServiceName": service_name,
                "Note": note,
                "LanguageCode": f"seed-h7-service-{source_id}",
            }
        )
        medical_services.append(new_row)
    bundles.append(SeedBundle("MedicalService", medical_services))

    bed_day_configs: list[dict[str, str]] = []
    for row in source["BedDayServiceConfig"]:
        if row["Id"] not in BED_DAY_CONFIG_ID_MAP:
            continue
        new_row = dict(row)
        new_row["Id"] = BED_DAY_CONFIG_ID_MAP[row["Id"]]
        new_row["TenantId"] = TARGET_TENANT_ID
        new_row["HospitalId"] = TARGET_HOSPITAL_ID
        new_row["MedicalServiceId"] = SERVICE_ID_MAP[row["MedicalServiceId"]]
        bed_day_configs.append(new_row)
    bundles.append(SeedBundle("BedDayServiceConfig", bed_day_configs))

    bed_day_tiers: list[dict[str, str]] = []
    for row in source["BedDayServiceConfigTier"]:
        new_row = dict(row)
        new_row["Id"] = bed_day_tier_map[row["Id"]]
        new_row["TenantId"] = TARGET_TENANT_ID
        new_row["HospitalId"] = TARGET_HOSPITAL_ID
        new_row["BedDayServiceConfigId"] = BED_DAY_CONFIG_ID_MAP[row["BedDayServiceConfigId"]]
        new_row["CreatedBy"] = GENERIC_USER_ID
        bed_day_tiers.append(new_row)
    bundles.append(SeedBundle("BedDayServiceConfigTier", bed_day_tiers))

    merchant_rows: list[dict[str, str]] = []
    for idx, row in enumerate(source["PaymentMerchantConfig"], start=1):
        new_row = dict(row)
        new_row["Id"] = merchant_map[row["Id"]]
        new_row["TenantId"] = TARGET_TENANT_ID
        new_row["HospitalId"] = TARGET_HOSPITAL_ID
        new_row["MerchantName"] = f"BVTest3 {row['Gateway']} Merchant {idx:02d}"
        new_row["TerminalId"] = prefix_code(row["TerminalId"], "H7M-")
        new_row["CreatedBy"] = GENERIC_USER_ID
        merchant_rows.append(new_row)
    bundles.append(SeedBundle("PaymentMerchantConfig", merchant_rows))

    used_room_row_map = {row["Id"]: row for row in room_rows if int(row["Id"]) in USED_ROOM_SOURCE_IDS}
    transformed_rooms: list[dict[str, str]] = []
    for source_id in USED_ROOM_SOURCE_IDS:
        source_row = used_room_row_map[str(source_id)]
        name, room_type_id = room_name_and_type(source_id)
        transformed_rooms.append(
            {
                "Id": room_map[str(source_id)],
                "IsActive": "true",
                "Code": prefix_code(source_row["Code"], "H7-"),
                "Name": name,
                "Description": f"English seed room for hospital 7 derived from source room {source_id}.",
                "LocationUndefined": f"Floor {source_row.get('Floor') or '1'}",
                "RoomTypeId": room_type_id,
                "CreatedAt": source_row.get("CreatedAt") or "2026-06-19T06:10:00",
                "CreatedBy": GENERIC_USER_ID,
                "UpdatedAt": source_row.get("CreatedAt") or "2026-06-19T06:10:00",
                "UpdatedBy": GENERIC_USER_ID,
                "LanguageCode": f"seed-h7-room-{source_id}",
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
            }
        )
    bundles.append(SeedBundle("Room", transformed_rooms))

    transformed_department_rooms: list[dict[str, str]] = []
    dept_room_id = 6338501
    for row in dept_room_rows:
        if row["RoomId"] not in room_map:
            continue
        transformed_department_rooms.append(
            {
                "Id": str(dept_room_id),
                "DepartmentId": DEPARTMENT_MAP[row["DepartmentId"]],
                "RoomId": room_map[row["RoomId"]],
                "IsAdministrative": row.get("IsAdministrative") or "false",
                "CreatedAt": row.get("CreatedAt") or "2026-06-19T06:12:00",
                "CreatedBy": GENERIC_USER_ID,
                "UpdatedAt": row.get("UpdatedAt") or row.get("CreatedAt") or "2026-06-19T06:12:00",
                "UpdatedBy": GENERIC_USER_ID,
                "IsActive": row.get("IsActive") or "true",
                "LanguageCode": f"seed-h7-dept-room-{dept_room_id}",
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
            }
        )
        dept_room_id += 1
    bundles.append(SeedBundle("DepartmentRoom", transformed_department_rooms))

    transformed_beds: list[dict[str, str]] = []
    for idx, row in enumerate(bed_rows, start=1):
        source_room_id = int(row["RoomId"])
        availability_status, status_reason = bed_status(row["Id"], active_bed_ids, self_select_bed_ids)
        bed_type_id = "4" if int(row["Id"]) >= 3001 else "7"
        transformed_beds.append(
            {
                "Id": bed_map[row["Id"]],
                "Code": prefix_code(row["Code"], "H7-"),
                "Name": bed_name(row["Code"], source_room_id),
                "RoomId": room_map[row["RoomId"]],
                "DepartmentId": DEPARTMENT_MAP[row["DepartmentId"]],
                "MaxCapacity": row["MaxCapacity"],
                "IsActive": row.get("IsActive") or "true",
                "Note": "Expanded hospital 7 seed bed for bed-management regression coverage.",
                "CreatedAt": f"2026-06-19T06:{10 + (idx % 40):02d}:00",
                "CreatedBy": GENERIC_USER_ID,
                "UpdatedAt": f"2026-06-19T06:{10 + (idx % 40):02d}:00",
                "UpdatedBy": GENERIC_USER_ID,
                "LanguageCode": f"seed-h7-bed-{idx:03d}",
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "BedTypeId": bed_type_id,
                "BhytBedCode": prefix_code(row["Code"], "BH-"),
                "AvailabilityStatus": availability_status,
                "StatusReason": status_reason,
                "StatusUpdatedBy": GENERIC_USER_ID,
                "StatusUpdatedAt": f"2026-06-19T06:{10 + (idx % 40):02d}:00",
            }
        )
    bundles.append(SeedBundle("Bed", transformed_beds))

    transformed_shifts: list[dict[str, str]] = []
    for row in source["Shift"]:
        if row["Id"] not in SHIFT_ID_MAP:
            continue
        shift_id = row["Id"]
        name = {
            "1": "Morning Round",
            "2": "Afternoon Coverage",
            "3": "Night Duty",
        }[shift_id]
        transformed_shifts.append(
            {
                "Id": SHIFT_ID_MAP[shift_id],
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "DepartmentId": DEPARTMENT_MAP.get(row.get("DepartmentId") or "", ""),
                "Code": prefix_code(row["Code"], "H7-"),
                "Name": name,
                "StartTime": row["StartTime"],
                "EndTime": row["EndTime"],
                "Color": row["Color"],
                "SortOrder": row["SortOrder"],
                "IsActive": row["IsActive"],
                "ShiftType": row["ShiftType"],
                "IsCrossMidnight": row["IsCrossMidnight"],
                "WorkCoefficient": row["WorkCoefficient"],
                "IsOtEnabled": row["IsOtEnabled"],
                "LateToleranceMin": row["LateToleranceMin"],
                "EarlyLeaveToleranceMin": row["EarlyLeaveToleranceMin"],
                "Description": f"Hospital 7 seed shift derived from source shift {shift_id}.",
                "AttendanceMethodsJson": "[\"MACHINE\"]",
                "CreatedAt": row["CreatedAt"],
                "CreatedBy": GENERIC_USER_ID,
                "UpdatedAt": row["CreatedAt"],
                "UpdatedBy": GENERIC_USER_ID,
                "LanguageCode": f"seed-h7-shift-{shift_id}",
            }
        )
    bundles.append(SeedBundle("Shift", transformed_shifts))

    transformed_patients: list[dict[str, str]] = []
    for idx, row in enumerate(patient_rows):
        mapped_name = realistic_patient_name(idx, row.get("Gender", ""))
        mapped_code = prefix_code(row["Code"], "H7-")
        mapped_email = f"h7.{row['Email']}" if row.get("Email") else ""
        mapped_identity = prefix_code(row.get("IdentityNumber"), "H7ID-")
        patient_code_map[row["Id"]] = mapped_code
        patient_name_map[row["Id"]] = mapped_name
        transformed_patients.append(
            {
                "Id": patient_map[row["Id"]],
                "Code": mapped_code,
                "PatientTypeId": patient_type_per_patient.get(row["Id"], PATIENT_TYPE_ID_MAP["1"]),
                "FullName": mapped_name,
                "Gender": row["Gender"],
                "BirthYear": row["BirthYear"],
                "BirthDate": row["BirthDate"],
                "Phone": row["Phone"],
                "Email": mapped_email,
                "IdentityNumber": mapped_identity,
                "Address": row["Address"],
                "WardId": row["WardId"],
                "ProvinceId": row["ProvinceId"],
                "EthnicityId": row["EthnicityId"],
                "CountryId": row["CountryId"],
                "Workplace": row["Workplace"],
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "CreatedBy": GENERIC_USER_ID,
                "LanguageCode": row["LanguageCode"],
                "CreatedAt": "2026-06-19T06:20:00",
                "UpdatedAt": "2026-06-19T06:20:00",
            }
        )
    bundles.append(SeedBundle("Patient", transformed_patients))

    transformed_visits: list[dict[str, str]] = []
    for row in source["MedicalVisit"]:
        mapped_code = prefix_code(row["Code"], "H7-")
        visit_code_map[row["Id"]] = mapped_code
        transformed_visits.append(
            {
                **row,
                "Id": visit_map[row["Id"]],
                "Code": mapped_code,
                "PatientId": patient_map[row["PatientId"]],
                "PatientTypeId": patient_type_per_patient.get(row["PatientId"], PATIENT_TYPE_ID_MAP["1"]),
                "DepartmentId": DEPARTMENT_MAP.get(row.get("DepartmentId") or "", ""),
                "InitialDepartmentId": DEPARTMENT_MAP.get(row.get("InitialDepartmentId") or "", ""),
                "AttendingUserId": DOCTOR_USER_ID if row.get("AttendingUserId") else "",
                "AssignedNurseUserId": NURSE_USER_ID if row.get("AssignedNurseUserId") else "",
                "MedicalRecordTypeId": IMRT_ID_MAP.get(row.get("MedicalRecordTypeId") or "", ""),
                "ReceivedBy": GENERIC_USER_ID if row.get("ReceivedBy") else "",
                "AdmissionNumber": prefix_code(row.get("AdmissionNumber"), "H7ADM-"),
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "CreatedBy": GENERIC_USER_ID,
            }
        )
    bundles.append(SeedBundle("MedicalVisit", transformed_visits))

    transformed_clinical_services: list[dict[str, str]] = []
    for row in source["MedicalVisitClinicalService"]:
        transformed_clinical_services.append(
            {
                **row,
                "Id": clinical_map[row["Id"]],
                "Code": prefix_code(row["Code"], "H7-"),
                "MedicalVisitId": visit_map[row["MedicalVisitId"]],
                "PatientId": patient_map[row["PatientId"]],
                "MedicalServiceId": SERVICE_ID_MAP[row["MedicalServiceId"]],
                "OrderedById": DOCTOR_USER_ID if row.get("OrderedById") else "",
                "AssignedDoctorId": DOCTOR_USER_ID if row.get("AssignedDoctorId") else "",
                "ConcludedBy": DOCTOR_USER_ID if row.get("ConcludedBy") else "",
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "CreatedBy": GENERIC_USER_ID,
            }
        )
    bundles.append(SeedBundle("MedicalVisitClinicalService", transformed_clinical_services))

    transformed_admission_orders: list[dict[str, str]] = []
    for row in source["InpatientAdmissionOrders"]:
        transformed_admission_orders.append(
            {
                **row,
                "Id": admission_order_map[row["Id"]],
                "Code": prefix_code(row["Code"], "H7-"),
                "SourceOpdVisitId": visit_map[row["SourceOpdVisitId"]],
                "SourceMedicalVisitClinicalServiceId": clinical_map[row["SourceMedicalVisitClinicalServiceId"]],
                "PatientId": patient_map[row["PatientId"]],
                "TargetDepartmentId": DEPARTMENT_MAP[row["TargetDepartmentId"]],
                "OrderedByUserId": DOCTOR_USER_ID,
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "CreatedBy": GENERIC_USER_ID,
            }
        )
    bundles.append(SeedBundle("InpatientAdmissionOrders", transformed_admission_orders))

    transformed_approach_logs: list[dict[str, str]] = []
    for row in source["MedicalVisitApproachLog"]:
        transformed_approach_logs.append(
            {
                **row,
                "Id": approach_log_map[row["Id"]],
                "MedicalVisitId": visit_map[row["MedicalVisitId"]],
                "PatientId": patient_map[row["PatientId"]],
                "MedicalVisitClinicalServiceId": clinical_map[row["MedicalVisitClinicalServiceId"]],
                "ReferId": admission_order_map[row["ReferId"]],
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "CreatedBy": GENERIC_USER_ID,
                "CreatedAt": "2026-06-19T06:25:00",
                "UpdatedAt": "2026-06-19T06:25:00",
            }
        )
    bundles.append(SeedBundle("MedicalVisitApproachLog", transformed_approach_logs))

    transformed_vital_signs: list[dict[str, str]] = []
    for row in source["VitalSigns"]:
        transformed_vital_signs.append(
            {
                **row,
                "Id": vital_sign_map[row["Id"]],
                "PatientId": patient_map[row["PatientId"]],
                "MedicalVisitId": visit_map[row["MedicalVisitId"]],
                "MedicalVisitClinicalServiceId": clinical_map[row["MedicalVisitClinicalServiceId"]] if row.get("MedicalVisitClinicalServiceId") else "",
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "CreatedBy": GENERIC_USER_ID,
                "CreatedAt": "2026-06-19T06:26:00",
                "UpdatedAt": "2026-06-19T06:26:00",
            }
        )
    bundles.append(SeedBundle("VitalSigns", transformed_vital_signs))

    transformed_dept_stays: list[dict[str, str]] = []
    for row in source["MedicalVisitDepartmentStay"]:
        transformed_dept_stays.append(
            {
                **row,
                "Id": dept_stay_map[row["Id"]],
                "MedicalVisitId": visit_map[row["MedicalVisitId"]],
                "DepartmentId": DEPARTMENT_MAP[row["DepartmentId"]],
                "TriggeredByDTRId": "",
                "AttendingUserId": DOCTOR_USER_ID if row.get("AttendingUserId") else "",
                "MedicalRecordTypeId": IMRT_ID_MAP.get(row.get("MedicalRecordTypeId") or "", ""),
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "CreatedBy": GENERIC_USER_ID,
            }
        )
    bundles.append(SeedBundle("MedicalVisitDepartmentStay", transformed_dept_stays))

    transformed_reservations: list[dict[str, str]] = []
    for row in source["BedReservation"]:
        transformed_reservations.append(
            {
                **row,
                "Id": reservation_map[row["Id"]],
                "MedicalVisitId": mapped(visit_map, row.get("MedicalVisitId")),
                "PatientId": patient_map[row["PatientId"]],
                "ReservedById": GENERIC_USER_ID if row.get("ReservedById") else "",
                "ConfirmedById": GENERIC_USER_ID if row.get("ConfirmedById") else "",
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
            }
        )
    bundles.append(SeedBundle("BedReservation", transformed_reservations))

    transformed_reservation_items: list[dict[str, str]] = []
    for row in source["BedReservationItem"]:
        transformed_reservation_items.append(
            {
                **row,
                "Id": reservation_item_map[row["Id"]],
                "BedReservationId": reservation_map[row["BedReservationId"]],
                "BedId": bed_map[row["BedId"]],
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
            }
        )
    bundles.append(SeedBundle("BedReservationItem", transformed_reservation_items))

    transformed_bed_stays: list[dict[str, str]] = []
    for row in source["MedicalVisitBedStay"]:
        transformed_bed_stays.append(
            {
                **row,
                "Id": bed_stay_map[row["Id"]],
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "MedicalVisitId": visit_map[row["MedicalVisitId"]],
                "BedId": bed_map[row["BedId"]],
                "MedicalServiceId": SERVICE_ID_MAP[row["MedicalServiceId"]],
                "MedicalVisitDepartmentStayId": mapped(dept_stay_map, row.get("MedicalVisitDepartmentStayId")),
                "RoomId": room_map[row["RoomId"]],
                "PhysicalDepartmentId": DEPARTMENT_MAP[row["PhysicalDepartmentId"]],
                "StartedBy": DOCTOR_USER_ID if row.get("StartedBy") else "",
                "EndedBy": DOCTOR_USER_ID if row.get("EndedBy") else "",
                "ReservationId": mapped(reservation_map, row.get("ReservationId")),
                "PreviousBedId": mapped(bed_map, row.get("PreviousBedId")),
                "LanguageCode": prefix_code(row.get("LanguageCode"), "seed-h7-"),
            }
        )
    bundles.append(SeedBundle("MedicalVisitBedStay", transformed_bed_stays))

    transformed_billings: list[dict[str, str]] = []
    for row in source["Billing"]:
        transformed_billings.append(
            {
                **row,
                "Id": billing_map[row["Id"]],
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "Code": prefix_code(row["Code"], "H7-"),
                "PatientId": patient_map[row["PatientId"]],
                "MedicalVisitId": visit_map[row["MedicalVisitId"]],
                "SettledBy": GENERIC_USER_ID if row.get("SettledBy") else "",
                "CreatedBy": GENERIC_USER_ID,
            }
        )
    bundles.append(SeedBundle("Billing", transformed_billings))

    transformed_billing_items: list[dict[str, str]] = []
    for row in source["BillingItem"]:
        transformed_billing_items.append(
            {
                **row,
                "Id": billing_item_map[row["Id"]],
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "BillingId": billing_map[row["BillingId"]],
                "ItemRefId": bed_stay_map.get(row["ItemRefId"], row["ItemRefId"]),
                "MedicalServiceId": SERVICE_ID_MAP[row["MedicalServiceId"]],
                "CreatedBy": GENERIC_USER_ID,
            }
        )
    bundles.append(SeedBundle("BillingItem", transformed_billing_items))

    transformed_invoices: list[dict[str, str]] = []
    for row in source["Invoice"]:
        source_visit_id = row["MedicalVisitId"]
        source_patient_id = row["PatientId"]
        transformed_invoices.append(
            {
                **row,
                "Id": invoice_map[row["Id"]],
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "InvoiceNo": prefix_code(row["InvoiceNo"], "H7-"),
                "PatientId": patient_map[source_patient_id],
                "PatientCode": patient_code_map[source_patient_id],
                "PatientName": patient_name_map[source_patient_id],
                "BillingId": billing_map[row["BillingId"]],
                "MedicalVisitId": visit_map[source_visit_id],
                "IssuedBy": GENERIC_USER_ID if row.get("IssuedBy") else "",
                "MedicalVisitCode": visit_code_map[source_visit_id],
                "CreatedBy": GENERIC_USER_ID,
            }
        )
    bundles.append(SeedBundle("Invoice", transformed_invoices))

    transformed_invoice_items: list[dict[str, str]] = []
    for row in source["InvoiceItem"]:
        transformed_invoice_items.append(
            {
                **row,
                "Id": invoice_item_map[row["Id"]],
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "InvoiceId": invoice_map[row["InvoiceId"]],
                "BillingItemId": billing_item_map[row["BillingItemId"]],
                "CreatedBy": GENERIC_USER_ID,
            }
        )
    bundles.append(SeedBundle("InvoiceItem", transformed_invoice_items))

    payment_reference_map: dict[str, str] = {}
    transformed_payment_transactions: list[dict[str, str]] = []
    for row in source["PaymentTransaction"]:
        new_txn_ref = prefix_code(row["TxnRef"], "H7-")
        new_transaction_no = prefix_code(row["TransactionNo"], "H7-")
        payment_reference_map[row["TransactionNo"]] = new_transaction_no
        transformed_payment_transactions.append(
            {
                **row,
                "Id": payment_tx_map[row["Id"]],
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "TransactionCode": prefix_code(row["TransactionCode"], "H7-"),
                "IdempotencyKey": prefix_code(row["IdempotencyKey"], "h7-"),
                "InvoiceId": invoice_map[row["InvoiceId"]],
                "MerchantConfigId": merchant_map[row["MerchantConfigId"]],
                "TxnRef": new_txn_ref,
                "TransactionNo": new_transaction_no,
                "CreatedBy": GENERIC_USER_ID,
            }
        )
    bundles.append(SeedBundle("PaymentTransaction", transformed_payment_transactions))

    transformed_allocations: list[dict[str, str]] = []
    for row in source["InvoicePaymentAllocation"]:
        transformed_allocations.append(
            {
                **row,
                "Id": allocation_map[row["Id"]],
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "InvoiceId": invoice_map[row["InvoiceId"]],
                "PaymentTransactionId": mapped(payment_tx_map, row.get("PaymentTransactionId")),
                "RefundTransactionId": mapped(payment_tx_map, row.get("RefundTransactionId")),
                "TransactionReference": payment_reference_map.get(row.get("TransactionReference") or "", prefix_code(row.get("TransactionReference"), "H7-")),
                "CashierId": GENERIC_USER_ID if row.get("CashierId") else "",
                "CreatedBy": GENERIC_USER_ID,
            }
        )
    bundles.append(SeedBundle("InvoicePaymentAllocation", transformed_allocations))

    transformed_payment_logs: list[dict[str, str]] = []
    for row in source["PaymentLog"]:
        transformed_payment_logs.append(
            {
                **row,
                "Id": payment_log_map[row["Id"]],
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "PaymentTransactionId": mapped(payment_tx_map, row.get("PaymentTransactionId")),
                "RefundTransactionId": mapped(payment_tx_map, row.get("RefundTransactionId")),
                "CreatedBy": GENERIC_USER_ID,
            }
        )
    bundles.append(SeedBundle("PaymentLog", transformed_payment_logs))

    transformed_schedule_rules: list[dict[str, str]] = []
    for row in source["ScheduleRule"]:
        transformed_schedule_rules.append(
            {
                **row,
                "Id": schedule_rule_map[row["Id"]],
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "Code": prefix_code(row["Code"], "H7-"),
                "ShiftId": SHIFT_ID_MAP[row["ShiftId"]],
                "DepartmentId": DEPARTMENT_MAP[row["DepartmentId"]],
                "RoomId": room_map[row["RoomId"]],
                "StaffId": map_staff_user(row.get("StaffId")),
                "CreatedBy": GENERIC_USER_ID,
            }
        )
    bundles.append(SeedBundle("ScheduleRule", transformed_schedule_rules))

    transformed_shift_assignments: list[dict[str, str]] = []
    for row in source["ShiftAssignment"]:
        transformed_shift_assignments.append(
            {
                **row,
                "Id": shift_assignment_map[row["Id"]],
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "DepartmentId": DEPARTMENT_MAP[row["DepartmentId"]],
                "RoomId": room_map[row["RoomId"]],
                "ShiftId": SHIFT_ID_MAP[row["ShiftId"]],
                "ShiftCode": prefix_code(row["ShiftCode"], "H7-"),
                "StaffId": map_staff_user(row.get("StaffId")),
                "SubmittedBy": GENERIC_USER_ID if row.get("SubmittedBy") else "",
                "ApprovedBy": GENERIC_USER_ID if row.get("ApprovedBy") else "",
                "RejectedBy": GENERIC_USER_ID if row.get("RejectedBy") else "",
                "CancelledBy": GENERIC_USER_ID if row.get("CancelledBy") else "",
                "ScheduleRuleId": schedule_rule_map[row["ScheduleRuleId"]] if row.get("ScheduleRuleId") else "",
                "CreatedBy": GENERIC_USER_ID,
            }
        )
    bundles.append(SeedBundle("ShiftAssignment", transformed_shift_assignments))

    transformed_schedule_snapshots: list[dict[str, str]] = []
    for row in source["ScheduleSnapshot"]:
        transformed_schedule_snapshots.append(
            {
                **row,
                "Id": schedule_snapshot_map[row["Id"]],
                "TenantId": TARGET_TENANT_ID,
                "HospitalId": TARGET_HOSPITAL_ID,
                "DepartmentId": DEPARTMENT_MAP[row["DepartmentId"]],
                "GeneratedBy": GENERIC_USER_ID if row.get("GeneratedBy") else "",
                "CreatedBy": GENERIC_USER_ID,
            }
        )
    bundles.append(SeedBundle("ScheduleSnapshot", transformed_schedule_snapshots))

    lines: list[str] = [
        "-- Append-only H7 seed for bvtest3 account visibility.",
        "-- Target tenant/hospital: 6 / 7",
        "USE MyHospital;",
        "GO",
        "SET NOCOUNT ON;",
        "SET XACT_ABORT ON;",
        "SET QUOTED_IDENTIFIER ON;",
        "SET ANSI_NULLS ON;",
        "SET ANSI_PADDING ON;",
        "SET ANSI_WARNINGS ON;",
        "SET ARITHABORT ON;",
        "SET CONCAT_NULL_YIELDS_NULL ON;",
        "SET NUMERIC_ROUNDABORT OFF;",
        "GO",
        "BEGIN TRANSACTION;",
        "",
    ]

    for logical_name, actual_table_name in TABLE_MAP:
        bundle = next((b for b in bundles if b.table_name == logical_name), None)
        if bundle is None or not bundle.rows:
            continue

        actual_columns = table_columns[actual_table_name]
        row_columns = []
        seen = set()
        for key in bundle.rows[0].keys():
            if key in actual_columns and key not in seen:
                row_columns.append(key)
                seen.add(key)
        if "CreatedAt" in actual_columns and "CreatedAt" not in seen:
            row_columns.append("CreatedAt")
            seen.add("CreatedAt")
        if "UpdatedAt" in actual_columns and "UpdatedAt" not in seen:
            row_columns.append("UpdatedAt")
            seen.add("UpdatedAt")
        for default_column in TABLE_DEFAULTS.get(logical_name, {}):
            if default_column in actual_columns and default_column not in seen:
                row_columns.append(default_column)
                seen.add(default_column)

        lines.append(f"SET IDENTITY_INSERT [{actual_table_name}] ON;")
        for row in bundle.rows:
            values = []
            for column in row_columns:
                if column == "CreatedAt" and column not in row:
                    values.append(sql_value("2026-06-19T06:00:00"))
                elif column == "UpdatedAt" and column not in row:
                    values.append(sql_value(row.get("CreatedAt") or "2026-06-19T06:00:00"))
                elif column in TABLE_DEFAULTS.get(logical_name, {}) and column not in row:
                    values.append(sql_value(TABLE_DEFAULTS[logical_name][column]))
                else:
                    values.append(sql_value(row.get(column)))
            column_sql = ", ".join(f"[{col}]" for col in row_columns)
            value_sql = ", ".join(values)
            row_id = row["Id"]
            lines.append(f"IF NOT EXISTS (SELECT 1 FROM [{actual_table_name}] WHERE [Id] = {sql_value(row_id)})")
            lines.append(f"    INSERT INTO [{actual_table_name}] ({column_sql}) VALUES ({value_sql});")
        lines.append(f"SET IDENTITY_INSERT [{actual_table_name}] OFF;")
        lines.append("GO")
        lines.append("")

    occupied_target_ids = [bed_map[source_id] for source_id in active_bed_ids]
    if occupied_target_ids:
        occupied_sql = ", ".join(sql_value(value) for value in occupied_target_ids)
        lines.extend(
            [
                "UPDATE [Bed]",
                "SET [AvailabilityStatus] = N'Occupied',",
                "    [StatusReason] = N'Linked to an active seed bed stay.',",
                f"    [StatusUpdatedBy] = {sql_value(GENERIC_USER_ID)},",
                "    [StatusUpdatedAt] = N'2026-06-19T06:59:00'",
                f"WHERE [Id] IN ({occupied_sql});",
                "GO",
                "",
            ]
        )

    lines.extend(
        [
            "COMMIT TRANSACTION;",
            "GO",
        ]
    )

    OUTPUT_SQL.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "output": str(OUTPUT_SQL),
        "rooms": len(transformed_rooms),
        "beds": len(transformed_beds),
        "patients": len(transformed_patients),
        "visits": len(transformed_visits),
        "clinical_services": len(transformed_clinical_services),
        "admission_orders": len(transformed_admission_orders),
        "dept_stays": len(transformed_dept_stays),
        "bed_stays": len(transformed_bed_stays),
        "reservations": len(transformed_reservations),
        "billing": len(transformed_billings),
        "schedule_rules": len(transformed_schedule_rules),
        "shift_assignments": len(transformed_shift_assignments),
        "schedule_snapshots": len(transformed_schedule_snapshots),
        "merchant_configs": len(merchant_rows),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
