#!/usr/bin/env python3
"""Generate comprehensive OPD (outpatient) seed data for slot 1 (ipd-improve-v2).
Target: TenantId=6, HospitalId=7, SQL localhost,1434/MyHospital
Produces idempotent SQL with IF NOT EXISTS guards.
"""

from __future__ import annotations

import random
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

OUTPUT = Path("/home/dax/Documents/arabica/roast/scripts/seed_opd_wt1.sql")

TENANT = 6
HOSPITAL = 7
USER_ADMIN = 176
USER_DOCTOR1 = 179
USER_DOCTOR2 = 180
USER_NURSE = 181

# Existing max IDs in the database
PATIENT_START = 100
VISIT_START = 200
CS_START = 200
VS_START = 100
RX_START = 100
LAB_START = 200
DIAG_IMG_START = 200
DIAG_DX_START = 200
BILLING_START = 200
BILLING_ITEM_START = 200
DEPT_STAY_START = 20
PTYPE_START = 100
SICK_LEAVE_START = 100

# Departments: 5=Khoa khám bệnh, 6=Khoa nội, 17=Khoa ngoại, 23=Khoa xét nghiệm
DEPT_KHAM_BENH = 5
DEP_NOI = 6
DEP_NGOAI = 17
DEP_XN = 23

VISIT_REASONS = [
    "Đau đầu, chóng mặt",
    "Ho khan kéo dài 2 tuần",
    "Đau bụng vùng thượng vị",
    "Sốt cao 39°C, mệt mỏi",
    "Đau lưng dưới",
    "Khó thở khi gắng sức",
    "Đau ngực trái",
    "Nổi mẩn đỏ toàn thân",
    "Đau khớp gối bên phải",
    "Rối loạn giấc ngủ",
    "Chóng mặt, buồn nôn",
    "Đau họng, nuốt đau",
    "Sụt cân không rõ nguyên nhân",
    "Tê bì tay chân",
    "Đau vai gáy",
    "Ngứa da đầu kéo dài",
    "Đau bụng dưới bên phải",
    "Mờ mắt bên trái",
    "Ù tai phải",
    "Đau răng hàm dưới",
    "Nóng rát thượng vị sau ăn",
    "Tiểu buốt, tiểu rắt",
    "Đau ngực khi hít sâu",
    "Sưng phù hai chân",
    "Mệt mỏi, chán ăn",
    "Sốt nhẹ về chiều",
    "Đau đầu vùng trán",
    "Ho có đờm vàng",
    "Đau bụng quanh rốn",
    "Nổi hạch vùng cổ",
]

ICD_CODES = [
    ("J06.9", "Nhiễm trùng đường hô hấp trên không xác định", 3470),
    ("K21.0", "Trào ngược dạ dày thực quản", 3775),
    ("M54.5", "Đau lưng dưới", 6299),
    ("I10", "Tăng huyết áp nguyên phát", None),
    ("E11.9", "Đái tháo đường type 2", 1707),
    ("J20.9", "Viêm phế quản cấp", 3514),
    ("K59.1", "Tiêu chảy chức năng", None),
    ("R51", "Đau đầu", None),
    ("M79.3", "Đau cơ không xác định", None),
    ("J45.9", "Hen phế quản", None),
    ("K29.7", "Viêm dạ dày không xác định", None),
    ("R10.4", "Đau bụng khác", 9837),
    ("B34.9", "Nhiễm virus không xác định", None),
    ("J02.9", "Viêm họng cấp", 3459),
    ("M25.50", "Đau khớp", None),
    ("R05", "Ho", None),
    ("L30.9", "Viêm da không xác định", 4206),
    ("N39.0", "Nhiễm trùng đường tiết niệu", 8192),
    ("K08.9", "Rối loạn răng và cấu trúc", None),
    ("H10.9", "Viêm kết mạc", 2749),
]

ICD_CODES_WITH_ID = [x for x in ICD_CODES if x[2] is not None]

DRUGS = [
    (23, "Alphachoay (Vitamin E)", "Viên", "Uống", 2, 500, "1 viên x 3 lần/ngày sau ăn", 1500),
    (24, "Mekocetin 0,5mg", "Viên", "Uống", 7, 1500, "1 viên x 3 lần/ngày sau ăn", 2500),
    (25, "Methylprednisolon 16mg", "Viên", "Uống", 14, 2800, "1 viên trước ăn sáng 30 phút", 3000),
    (26, "Medrol 16mg", "Viên", "Uống", 7, 700, "1 viên x 1 lần trước ngủ", 2000),
    (27, "Hydrocotisone 10mg", "Viên", "Uống", 30, 6000, "1 viên x 2 lần trong bữa ăn", 1800),
    (28, "Myonal 50mg", "Viên", "Uống", 30, 3000, "1 viên x 1 lần/ngày", 2200),
    (29, "Allopurinol 300mg", "Viên", "Uống", 5, 1000, "1 viên x 3 lần/ngày sau ăn", 2000),
    (37, "Augmentin 1g", "Viên", "Uống", 7, 1400, "1 viên x 3 lần/ngày", 5000),
]

LAB_SERVICES = [
    (1, "Xét nghiệm máu tổng quát"),
    (2, "Xét nghiệm đường huyết"),
    (3, "Xét nghiệm mỡ máu"),
    (4, "Xét nghiệm chức năng gan"),
    (5, "Xét nghiệm chức năng thận"),
    (6, "Xét nghiệm nước tiểu"),
    (7, "Xét nghiệm CRP"),
    (8, "Xét nghiệm HbA1c"),
]

DIAG_IMG_SERVICES = [
    (1, "X-quang ngực thẳng"),
    (2, "X-quang bụng"),
    (3, "Siêu âm bụng tổng quát"),
    (4, "Siêu âm tuyến giáp"),
    (5, "ECG điện tim"),
    (6, "CT Scanner sọ não"),
    (7, "X-quang cột sống"),
]

random.seed(42)

# Vietnamese names
MALE_FIRST = ["Nguyễn Văn", "Trần Văn", "Lê Văn", "Phạm Văn", "Hoàng Văn", "Vũ Văn", "Đặng Văn", "Bùi Văn", "Đỗ Văn", "Hồ Văn", "Ngô Văn", "Dương Văn", "Lý Văn", "Đinh Văn", "Tạ Văn"]
FEMALE_FIRST = ["Nguyễn Thị", "Trần Thị", "Lê Thị", "Phạm Thị", "Hoàng Thị", "Vũ Thị", "Đặng Thị", "Bùi Thị", "Đỗ Thị", "Hồ Thị", "Ngô Thị", "Dương Thị", "Lý Thị", "Đinh Thị", "Tạ Thị"]
LAST_NAMES = ["An", "Bình", "Cường", "Dũng", "Em", "Phương", "Giang", "Hà", "Hùng", "Khánh", "Linh", "Mai", "Ngọc", "Oanh", "Phong", "Quân", "Sơn", "Thảo", "Uyên", "Vy"]

PROVINCES = [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12]
WARDS = [280, 281, 282, 283, 590, 591, 592, 593]
COUNTRIES = [242]
ETHNICITIES = [1, 2, 3, 4, 5]

ADDRESSES = [
    "123 Nguyễn Huệ, Quận 1",
    "45 Lê Lợi, Quận 3",
    "78 Trần Hưng Đạo, Quận 5",
    "12 Pasteur, Quận 1",
    "56 Võ Văn Tần, Quận 3",
    "89 Cách Mạng Tháng 8, Quận 10",
    "34 Nguyễn Đình Chiểu, Quận 3",
    "67 Lý Thường Kiệt, Quận 10",
    "90 Hai Bà Trưng, Quận 1",
    "23 Phan Đình Phùng, Quận Phú Nhuận",
    "56 Nguyễn Văn Trỗi, Quận Phú Nhuận",
    "78 Hoàng Văn Thụ, Quận Tân Bình",
    "12 Cộng Hòa, Quận Tân Bình",
    "45 Trường Chinh, Quận Tân Bình",
    "90 Quang Trung, Quận Gò Vấp",
    "23 Phan Văn Trị, Quận Gò Vấp",
    "67 Nguyễn Oanh, Quận Gò Vấp",
    "34 Lê Đức Thọ, Quận Gò Vấp",
    "56 Thống Nhất, Quận Gò Vấp",
    "78 Nguyễn Kiệm, Quận Phú Nhuận",
]

VISIT_STATUSES = ["Completed", "Completed", "Completed", "Completed", "Completed",
                  "Pending", "Pending", "Pending",
                  "InProgress", "InProgress"]

CS_STATUSES_COMPLETED = ["Completed", "Completed", "Completed", "InProgress"]
CS_STATUSES_PENDING = ["Pending", "WaitingForExamination"]
CS_STATUSES_INPROGRESS = ["InProgress", "WaitingForExamination"]


def nid(prefix: str, counter: int) -> str:
    return f"{prefix}{counter}"


def code(prefix: str, counter: int) -> str:
    return f"{prefix}{counter:06d}"


def phone() -> str:
    prefixes = ["090", "091", "093", "094", "096", "097", "098", "032", "033", "034", "035", "036", "037", "038", "039"]
    return random.choice(prefixes) + "".join([str(random.randint(0, 9)) for _ in range(7)])


def birth_year() -> int:
    return random.choice(range(1955, 2015))


def gender() -> str:
    return random.choice(["Male", "Female"])


def sql_str(val) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return f"{val:.2f}"
    s = str(val).replace("'", "''")
    return f"N'{s}'"


def sql_dt(dt: datetime) -> str:
    return f"N'{dt.strftime('%Y-%m-%d %H:%M:%S')}'"


def sql_date(dt: datetime) -> str:
    return f"N'{dt.strftime('%Y-%m-%d')}'"


def not_exists(table: str, col: str, val) -> str:
    return f"IF NOT EXISTS (SELECT 1 FROM [{table}] WHERE [{col}] = {sql_str(val)})"


def main():
    lines = []
    now = datetime(2026, 6, 22, 8, 0, 0)
    base_date = datetime(2026, 6, 15, 0, 0, 0)

    def emit(sql: str):
        lines.append(sql)

    def emit_row(table: str, columns: list[str], values: list, id_col: str = "Id"):
        col_str = ", ".join(f"[{c}]" for c in columns)
        val_str = ", ".join(sql_str(v) for v in values)
        row_id = values[columns.index(id_col)]
        emit(f"IF NOT EXISTS (SELECT 1 FROM [{table}] WHERE [{id_col}] = {sql_str(row_id)})")
        emit(f"    INSERT INTO [{table}] ({col_str}) VALUES ({val_str});")

    def emit_row_dt(table: str, columns: list[str], values: list, id_col: str = "Id"):
        """Like emit_row but values can contain datetime objects."""
        col_str = ", ".join(f"[{c}]" for c in columns)
        val_parts = []
        for v in values:
            if isinstance(v, datetime):
                val_parts.append(sql_dt(v))
            else:
                val_parts.append(sql_str(v))
        val_str = ", ".join(val_parts)
        row_id = values[columns.index(id_col)]
        emit(f"IF NOT EXISTS (SELECT 1 FROM [{table}] WHERE [{id_col}] = {sql_str(row_id)})")
        emit(f"    INSERT INTO [{table}] ({col_str}) VALUES ({val_str});")

    def identity_on(table: str):
        emit(f"SET IDENTITY_INSERT [{table}] ON;")

    def identity_off(table: str):
        emit(f"SET IDENTITY_INSERT [{table}] OFF;")

    # Header
    emit("SET NOCOUNT ON;")
    emit("SET XACT_ABORT ON;")
    emit("SET QUOTED_IDENTIFIER ON;")
    emit("SET ANSI_NULLS ON;")
    emit("GO")
    emit("")
    emit("-- Comprehensive OPD seed data for slot 1 (ipd-improve-v2)")
    emit(f"-- TenantId={TENANT}, HospitalId={HOSPITAL}")
    emit(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    emit("")
    emit("BEGIN TRANSACTION;")
    emit("")

    # ================================================================
    # 1. PATIENT TYPES
    # ================================================================
    emit("-- ============================================================")
    emit("-- PatientType")
    emit("-- ============================================================")

    patient_types = [
        (PTYPE_START + 1, "KSK", "Khám sức khỏe", "Optional", "Disabled", False, False),
        (PTYPE_START + 2, "BHYT", "Bảo hiểm y tế", "Required", "Disabled", False, False),
        (PTYPE_START + 3, "DV", "Dịch vụ", "Disabled", "Disabled", True, False),
        (PTYPE_START + 4, "TE", "Trẻ em", "Disabled", "Disabled", False, False),
        (PTYPE_START + 5, "NN", "Ngoại quốc", "Disabled", "Optional", False, True),
    ]

    pt_cols = ["Id", "IsActive", "PatientTypeCode", "PatientTypeName", "HealthInsuranceOption",
               "CommercialInsuranceOption", "IsDefault", "IsForeign", "CreatedAt", "CreatedBy",
               "UpdatedAt", "UpdatedBy", "LanguageCode", "TenantId", "HospitalId"]
    identity_on("PatientType")
    for pt_id, pt_code, pt_name, hi_opt, ci_opt, is_def, is_foreign in patient_types:
        vals = [pt_id, True, pt_code, pt_name, hi_opt, ci_opt, is_def, is_foreign,
                now, USER_ADMIN, now, USER_ADMIN, f"seed-opd-pt-{pt_id}", TENANT, HOSPITAL]
        emit_row_dt("PatientType", pt_cols, vals)
    identity_off("PatientType")

    # ================================================================
    # 2. PATIENTS (30 new)
    # ================================================================
    emit("-- ============================================================")
    emit("-- Patients (30 new)")
    emit("-- ============================================================")

    patient_cols = ["Id", "Code", "PatientTypeId", "FullName", "Gender",
                    "BirthYear", "BirthDate", "Phone", "PhoneNormalized", "Email",
                    "IdentityNumber", "Address", "WardId", "ProvinceId", "EthnicityId",
                    "CountryId", "Workplace", "TotalVisits", "CreatedAt", "CreatedBy",
                    "UpdatedAt", "UpdatedBy", "LanguageCode", "TenantId", "HospitalId"]

    patients = []
    identity_on("Patient")
    for i in range(30):
        pid = PATIENT_START + i + 1
        g = gender()
        first_pool = MALE_FIRST if g == "Male" else FEMALE_FIRST
        fname = f"{random.choice(first_pool)} {random.choice(LAST_NAMES)}"
        by = birth_year()
        bd = datetime(by, random.randint(1, 12), random.randint(1, 28))
        ph = phone()
        addr = random.choice(ADDRESSES)
        ward = random.choice(WARDS)
        prov = random.choice(PROVINCES)
        eth = random.choice(ETHNICITIES)
        country = COUNTRIES[0]
        pt_type = random.choice([PTYPE_START + 2, PTYPE_START + 3, PTYPE_START + 3, PTYPE_START + 3])
        workplace = random.choice(["Công ty ABC", "Bệnh viện XYZ", "Trường đại học", "Nhà riêng", "Cơ quan nhà nước", ""])
        visit_count = random.randint(1, 5)

        vals = [pid, code("OPD-PT-", pid), pt_type, fname, g,
                by, bd, ph, ph, f"patient{pid}@mail.vn",
                f"CMND{random.randint(100000000, 999999999)}", addr, ward, prov, eth,
                country, workplace, visit_count, now, USER_ADMIN,
                now, USER_ADMIN, f"seed-opd-p-{pid}", TENANT, HOSPITAL]
        emit_row_dt("Patient", patient_cols, vals)
        patients.append(pid)
    identity_off("Patient")

    # ================================================================
    # 3. MEDICAL VISITS (~60 OPD visits)
    # ================================================================
    emit("-- ============================================================")
    emit("-- MedicalVisit (60 OPD visits)")
    emit("-- ============================================================")

    visit_cols = ["Id", "Code", "PatientId", "PatientTypeId", "VisitReasonId",
                  "ReceivedBy", "ReceptionTime", "EndTime", "Status", "TreatmentTypeId",
                  "IsPriority", "Notes", "DepartmentId", "InitialDepartmentId",
                  "AttendingUserId", "AssignedNurseUserId", "ClinicalServiceCount",
                  "DiagnosticImagingServiceCount", "LaboratoryTestServiceCount",
                  "PatientConditionCode", "IsLongTermOutpatient",
                  "CreatedAt", "CreatedBy", "UpdatedAt", "UpdatedBy",
                  "LanguageCode", "TenantId", "HospitalId"]

    visits = []
    visit_patient_map = {}

    identity_on("MedicalVisit")
    for i in range(60):
        vid = VISIT_START + i + 1
        patient_id = random.choice(patients)
        pt_type = random.choice([PTYPE_START + 2, PTYPE_START + 3, PTYPE_START + 3])
        status = random.choice(VISIT_STATUSES)

        day_offset = random.randint(0, 7)
        hour = random.randint(6, 16)
        minute = random.randint(0, 59)
        reception_time = base_date + timedelta(days=day_offset, hours=hour - 6, minutes=minute)

        end_time = None
        if status == "Completed":
            end_time = reception_time + timedelta(minutes=random.randint(15, 120))

        reason = random.choice(VISIT_REASONS)
        priority = random.random() < 0.1
        dept = DEPT_KHAM_BENH
        doctor = random.choice([USER_DOCTOR1, USER_DOCTOR2])
        nurse = USER_NURSE if random.random() < 0.5 else None
        cs_count = random.randint(1, 3)
        lab_count = random.randint(0, 2)
        diag_count = random.randint(0, 1)
        cond_code = random.choice(["Stable", "Stable", "Stable", "Moderate"])

        vals = [vid, code("MV-", vid), patient_id, pt_type, None,
                USER_ADMIN, reception_time, end_time, status, 1,
                priority, reason, dept, dept,
                doctor, nurse, cs_count, diag_count, lab_count,
                cond_code, False,
                now, USER_ADMIN, now, USER_ADMIN,
                f"seed-opd-mv-{vid}", TENANT, HOSPITAL]
        emit_row_dt("MedicalVisit", visit_cols, vals)
        visits.append((vid, patient_id, status, reception_time, end_time, doctor, pt_type, dept))
        visit_patient_map[vid] = patient_id
    identity_off("MedicalVisit")

    # ================================================================
    # 4. MEDICAL VISIT CLINICAL SERVICES
    # ================================================================
    emit("-- ============================================================")
    emit("-- MedicalVisitClinicalService")
    emit("-- ============================================================")

    cs_cols = ["Id", "Code", "MedicalVisitId", "PatientId", "MedicalServiceId",
               "Quantity", "QueueNumber", "QueueDate", "HasPrescription",
               "OrderedById", "AssignedDoctorId", "Status", "ReasonForVisit",
               "SubjectiveExamination", "GeneralExamination", "SystemicExamination",
               "TreatmentPlan", "DoctorNotes", "Note", "StartedAt", "CompletedAt",
               "CreatedAt", "CreatedBy", "UpdatedAt", "UpdatedBy",
               "LanguageCode", "TenantId", "HospitalId"]

    clinical_services = []
    cs_counter = 0

    identity_on("MedicalVisitClinicalService")
    for vid, patient_id, vstatus, rtime, etime, doctor, ptype, dept in visits:
        cs_counter += 1
        cs_id = CS_START + cs_counter

        if vstatus == "Completed":
            cs_status = random.choice(CS_STATUSES_COMPLETED)
            started = rtime + timedelta(minutes=random.randint(2, 15))
            completed = started + timedelta(minutes=random.randint(5, 30)) if cs_status == "Completed" else None
        elif vstatus == "InProgress":
            cs_status = random.choice(CS_STATUSES_INPROGRESS)
            started = rtime + timedelta(minutes=random.randint(2, 15))
            completed = None
        else:
            cs_status = random.choice(CS_STATUSES_PENDING)
            started = None
            completed = None

        icd_code, icd_name, _ = random.choice(ICD_CODES)
        reason = random.choice(VISIT_REASONS)
        subj = f"Bệnh nhân {random.choice(['tự đến khám', 'được người nhà đưa đến khám'])}. {random.choice(VISIT_REASONS)}."
        gen_exam = f"Mạch {random.randint(70, 100)} lần/phút, HA {random.randint(110, 150)}/{random.randint(60, 90)} mmHg, nhiệt độ {random.uniform(36.2, 38.5):.1f}°C, SpO2 {random.randint(95, 100)}%"
        sys_exam = random.choice([
            "Tim: nhịp đều, không tiếng thổi. Phổi: thông khí hai bên.",
            "Bụng: mềm, không đau ấn. Gan lách không to.",
            "Họng: đỏ, amiđan sưng nhẹ. Phổi: ran rải rác.",
            "Khám bình thường, không có dấu hiệu bất thường.",
            "Da: không phát ban. Hạch ngoại vi không sưng.",
        ])
        treatment = random.choice([
            "Điều trị nội trú tại khoa khám bệnh",
            "Kê đơn thuốc, hẹn tái khám sau 7 ngày",
            "Chuyển khám chuyên khoa",
            "Theo dõi tại nhà, tái khám nếu triệu chứng nặng hơn",
            "Nhập viện điều trị",
        ])
        notes = random.choice(["", "Bệnh nhân có tiền sử cao huyết áp", "Bệnh nhân dị ứng penicillin", ""])

        vals = [cs_id, code("CS-", cs_id), vid, patient_id, 247,
                1, cs_counter, rtime.date() if rtime else None, False,
                USER_ADMIN, doctor, cs_status, reason,
                subj, gen_exam, sys_exam,
                treatment, notes, notes, started, completed,
                now, USER_ADMIN, now, USER_ADMIN,
                f"seed-opd-cs-{cs_id}", TENANT, HOSPITAL]
        emit_row_dt("MedicalVisitClinicalService", cs_cols, vals)
        clinical_services.append((cs_id, vid, patient_id, doctor, cs_status, started, completed))
    identity_off("MedicalVisitClinicalService")

    # ================================================================
    # 5. DIAGNOSIS DETAILS
    # ================================================================
    emit("-- ============================================================")
    emit("-- MedicalVisitClinicalServiceDiagnosesDetails")
    emit("-- ============================================================")

    dx_cols = ["Id", "MedicalVisitServiceId", "MedicalVisitId", "DiseaseId",
               "DoctorInterpretation", "IsPrimary", "IsInitial", "CreatedAt", "CreatedBy",
               "UpdatedAt", "UpdatedBy", "LanguageCode", "TenantId", "HospitalId"]

    dx_counter = 0
    identity_on("MedicalVisitClinicalServiceDiagnosesDetails")
    for cs_id, vid, patient_id, doctor, cs_status, started, completed in clinical_services:
        num_dx = random.choice([1, 1, 1, 2])
        used_diseases = set()
        for d in range(num_dx):
            dx_counter += 1
            dx_id = DIAG_DX_START + dx_counter
            icd_code, icd_name, disease_id = random.choice(ICD_CODES_WITH_ID)
            while icd_code in used_diseases:
                icd_code, icd_name, disease_id = random.choice(ICD_CODES_WITH_ID)
            used_diseases.add(icd_code)

            interp = random.choice([
                f"Chẩn đoán {icd_name.lower()} dựa trên triệu chứng lâm sàng",
                f"Xác nhận {icd_name.lower()} qua khám và xét nghiệm",
                f"Nghi ngờ {icd_name.lower()}, cần theo dõi thêm",
                "",
            ])
            is_primary = (d == 0)

            vals = [dx_id, cs_id, vid, disease_id,
                    interp, is_primary, True, now, USER_ADMIN,
                    now, USER_ADMIN, f"seed-opd-dx-{dx_id}", TENANT, HOSPITAL]
            emit_row_dt("MedicalVisitClinicalServiceDiagnosesDetails", dx_cols, vals)
    identity_off("MedicalVisitClinicalServiceDiagnosesDetails")

    # ================================================================
    # 6. VITAL SIGNS
    # ================================================================
    emit("-- ============================================================")
    emit("-- VitalSigns")
    emit("-- ============================================================")

    vs_cols = ["Id", "IsActive", "PatientId", "MedicalVisitId", "MedicalVisitClinicalServiceId",
               "Pulse", "HeartRate", "Spo2", "BloodPressureSys", "BloodPressureDia",
               "RespiratoryRate", "Temperature", "Weight", "Height", "Bmi",
               "MeasuredArm", "MeasuredAt", "MeasuredByUserId", "BreathingStatus",
               "VasScore", "PainPoint",
               "CreatedAt", "CreatedBy", "UpdatedAt", "UpdatedBy",
               "LanguageCode", "TenantId", "HospitalId"]

    vs_counter = 0
    identity_on("VitalSigns")
    for cs_id, vid, patient_id, doctor, cs_status, started, completed in clinical_services:
        if started is None:
            continue
        num_vs = random.choice([1, 1, 1, 2])
        for v in range(num_vs):
            vs_counter += 1
            vs_id = VS_START + vs_counter
            measured_at = started + timedelta(minutes=random.randint(1, 10))
            weight = random.uniform(40, 90)
            height = random.uniform(145, 185)
            bmi = round(weight / ((height / 100) ** 2), 2)
            temp = round(random.uniform(36.0, 38.5), 1)
            pulse = random.randint(60, 100)
            hr = pulse + random.randint(-3, 5)
            spo2 = round(random.uniform(95, 100), 1)
            bp_sys = random.randint(100, 155)
            bp_dia = random.randint(60, 95)
            rr = random.randint(14, 24)
            arm = random.choice(["right", "left"])
            breathing = random.choice(["Tự thở", "Tự thở", "Tự thở", "Thở oxy"])
            vas = random.randint(0, 6)
            pain = random.choice(["Không đau", "Đau nhẹ", "Đau vừa", "Đau nhiều"])

            vals = [vs_id, True, patient_id, vid, cs_id,
                    pulse, hr, spo2, bp_sys, bp_dia,
                    rr, temp, round(weight, 2), round(height, 2), bmi,
                    arm, measured_at, random.choice([doctor, USER_NURSE]), breathing,
                    vas, pain,
                    now, USER_ADMIN, now, USER_ADMIN,
                    f"seed-opd-vs-{vs_id}", TENANT, HOSPITAL]
            emit_row_dt("VitalSigns", vs_cols, vals)
    identity_off("VitalSigns")

    # ================================================================
    # 7. PRESCRIPTIONS
    # ================================================================
    emit("-- ============================================================")
    emit("-- Prescription")
    emit("-- ============================================================")

    rx_cols = ["Id", "Code", "FacilityCode", "VisitSeed", "Suffix", "Type", "BytCodeType",
               "MedicalVisitId", "MedicalVisitClinicalServiceId",
               "PatientId", "PrescribedBy", "IsInsurance", "IssuedAt", "Note",
               "DepartmentId", "CreatedAt", "CreatedBy", "UpdatedAt", "UpdatedBy",
               "LanguageCode", "TenantId", "HospitalId"]

    rx_item_cols = ["Id", "MedicalVisitClinicalServiceId", "PrescriptionId",
                    "MedicalVisitId", "PatientId", "ProductId", "ProductName", "ProductUnit",
                    "DoseUnit", "DurationDays", "TotalQuantity", "HowToUse", "UnitPrice",
                    "IsInsurance", "IsExternal", "PrescribedBy", "Status",
                    "CreatedAt", "CreatedBy", "UpdatedAt", "UpdatedBy",
                    "LanguageCode", "TenantId", "HospitalId"]

    rx_counter = 0
    rx_item_counter = 0

    rx_rows = []
    ri_rows = []

    for cs_id, vid, patient_id, doctor, cs_status, started, completed in clinical_services:
        if cs_status not in ("Completed", "InProgress"):
            continue
        if random.random() < 0.3:
            continue

        rx_counter += 1
        rx_id = RX_START + rx_counter
        is_ins = random.random() < 0.4
        issued_at = completed or started or now
        note = random.choice(["", "Uống đủ liều", "Tái khám sau 7 ngày", "Kiêng rượu bia"])

        vals = [rx_id, code("RX-", rx_id)[:14], f"H{rx_id % 1000:03d}", f"V{rx_id % 1000:03d}", f"S{rx_id % 100:02d}", "O", "B",
                vid, cs_id,
                patient_id, doctor, is_ins, issued_at, note,
                DEPT_KHAM_BENH, now, USER_ADMIN, now, USER_ADMIN,
                f"seed-opd-rx-{rx_id}", TENANT, HOSPITAL]
        rx_rows.append(("Prescription", rx_cols, vals))

        num_drugs = random.randint(1, 4)
        used_drugs = set()
        for d in range(num_drugs):
            rx_item_counter += 1
            ri_id = RX_START + rx_item_counter
            drug_id, drug_name, drug_unit, route, dur, qty, how, price = random.choice(DRUGS)
            while drug_id in used_drugs:
                drug_id, drug_name, drug_unit, route, dur, qty, how, price = random.choice(DRUGS)
            used_drugs.add(drug_id)

            ri_vals = [ri_id, cs_id, rx_id, vid, patient_id,
                       drug_id, drug_name, drug_unit, drug_unit, dur, qty, how, price,
                       is_ins, False, doctor, "Prescribed",
                       now, USER_ADMIN, now, USER_ADMIN,
                       f"seed-opd-ri-{ri_id}", TENANT, HOSPITAL]
            ri_rows.append(("MedicalVisitClinicalServicePrescription", rx_item_cols, ri_vals))

    identity_on("Prescription")
    for tbl, cols, vals in rx_rows:
        emit_row_dt(tbl, cols, vals)
    identity_off("Prescription")

    identity_on("MedicalVisitClinicalServicePrescription")
    for tbl, cols, vals in ri_rows:
        emit_row_dt(tbl, cols, vals)
    identity_off("MedicalVisitClinicalServicePrescription")

    # ================================================================
    # 8. LAB TEST SERVICES
    # ================================================================
    emit("-- ============================================================")
    emit("-- MedicalVisitLabTestServices")
    emit("-- ============================================================")

    lab_cols = ["Id", "Code", "MedicalVisitId", "PatientId", "MedicalServiceId",
                "ServiceGroupId", "ServiceCategoryId", "Quantity", "IsUrgent",
                "OrderedById", "Status", "QueueNumber", "QueueDate", "IsSkipMissed",
                "Note", "StartedAt", "CompletedAt",
                "CreatedAt", "CreatedBy", "UpdatedAt", "UpdatedBy",
                "LanguageCode", "TenantId", "HospitalId"]

    lab_counter = 0
    identity_on("MedicalVisitLabTestServices")
    for cs_id, vid, patient_id, doctor, cs_status, started, completed in clinical_services:
        num_lab = random.choice([0, 0, 1, 1, 2])
        for l in range(num_lab):
            lab_counter += 1
            lab_id = LAB_START + lab_counter
            svc_id, svc_name = random.choice(LAB_SERVICES)
            if cs_status == "Completed":
                lab_status = random.choice(["Completed", "Completed", "InProgress"])
            elif cs_status == "InProgress":
                lab_status = random.choice(["InProgress", "Pending"])
            else:
                lab_status = "Pending"

            lab_started = started + timedelta(minutes=random.randint(10, 60)) if started else None
            lab_completed = lab_started + timedelta(minutes=random.randint(10, 45)) if lab_started and lab_status == "Completed" else None
            note = random.choice(["", "Mẫu máu tĩnh mạch", "Mẫu nước tiểu giữa dòng", "Nhịn ăn 8 tiếng"])

            vals = [lab_id, code("LAB-", lab_id), vid, patient_id, svc_id,
                    1, 1, 1, False,
                    doctor, lab_status, lab_counter, rtime.date() if rtime else None, False,
                    note, lab_started, lab_completed,
                    now, USER_ADMIN, now, USER_ADMIN,
                    f"seed-opd-lab-{lab_id}", TENANT, HOSPITAL]
            emit_row_dt("MedicalVisitLabTestServices", lab_cols, vals)
    identity_off("MedicalVisitLabTestServices")

    # ================================================================
    # 9. DIAGNOSTIC IMAGING SERVICES
    # ================================================================
    emit("-- ============================================================")
    emit("-- MedicalVisitDiagnosticImagingServices")
    emit("-- ============================================================")

    diag_cols = ["Id", "Code", "MedicalVisitId", "PatientId", "MedicalServiceId",
                 "ServiceGroupId", "ServiceCategoryId", "Quantity", "IsUrgent",
                 "OrderedById", "Status", "QueueNumber", "QueueDate", "IsSkipMissed",
                 "Note", "StartedAt", "CompletedAt",
                 "CreatedAt", "CreatedBy", "UpdatedAt", "UpdatedBy",
                 "LanguageCode", "TenantId", "HospitalId"]

    diag_counter = 0
    identity_on("MedicalVisitDiagnosticImagingServices")
    for cs_id, vid, patient_id, doctor, cs_status, started, completed in clinical_services:
        if random.random() < 0.6:
            continue
        diag_counter += 1
        diag_id = DIAG_IMG_START + diag_counter
        svc_id, svc_name = random.choice(DIAG_IMG_SERVICES)
        if cs_status == "Completed":
            diag_status = random.choice(["Completed", "Completed", "InProgress"])
        else:
            diag_status = "Pending"

        diag_started = started + timedelta(minutes=random.randint(15, 90)) if started else None
        diag_completed = diag_started + timedelta(minutes=random.randint(5, 30)) if diag_started and diag_status == "Completed" else None
        note = random.choice(["", "Chụp không cản quang", "Có tiêm thuốc cản quang", "Siêu âm đầu dò"])

        vals = [diag_id, code("DIAG-", diag_id), vid, patient_id, svc_id,
                2, 2, 1, False,
                doctor, diag_status, diag_counter, rtime.date() if rtime else None, False,
                note, diag_started, diag_completed,
                now, USER_ADMIN, now, USER_ADMIN,
                f"seed-opd-diag-{diag_id}", TENANT, HOSPITAL]
        emit_row_dt("MedicalVisitDiagnosticImagingServices", diag_cols, vals)
    identity_off("MedicalVisitDiagnosticImagingServices")

    # ================================================================
    # 10. BILLINGS & BILLING ITEMS
    # ================================================================
    emit("-- ============================================================")
    emit("-- Billings & BillingItems")
    emit("-- ============================================================")

    billing_cols = ["Id", "Code", "PatientId", "MedicalVisitId", "PaymentMode",
                    "Status", "CreatedAt", "CreatedBy", "UpdatedAt", "UpdatedBy",
                    "LanguageCode", "TenantId", "HospitalId"]

    bi_cols = ["Id", "BillingId", "ItemType", "ItemRefId", "InsuranceCostGroupId",
               "MedicalServiceId", "Quantity", "UnitPrice", "TotalPrice", "Status",
               "CreatedAt", "CreatedBy", "UpdatedAt", "UpdatedBy",
               "LanguageCode", "TenantId", "HospitalId"]

    billing_counter = 0
    bi_counter = 0

    billing_rows = []
    bi_rows = []

    for vid, patient_id, vstatus, rtime, etime, doctor, ptype, dept in visits:
        if vstatus != "Completed":
            continue
        billing_counter += 1
        bill_id = BILLING_START + billing_counter
        bill_status = random.choice(["Unsettled", "Unsettled", "Settled"])

        vals = [bill_id, code("BILL-", bill_id), patient_id, vid, "Cash",
                bill_status, now, USER_ADMIN, now, USER_ADMIN,
                f"seed-opd-bill-{bill_id}", TENANT, HOSPITAL]
        billing_rows.append(("Billings", billing_cols, vals))

        # billing items
        num_items = random.randint(1, 3)
        for item in range(num_items):
            bi_counter += 1
            bi_id = BILLING_ITEM_START + bi_counter
            svc_name = random.choice(["Khám bệnh", "Xét nghiệm máu", "X-quang", "Siêu âm"])
            svc_price = random.choice([100000, 150000, 200000, 80000, 250000])
            quantity = 1
            total = svc_price * quantity

            bi_vals = [bi_id, bill_id, "Service", bi_id, 1,
                       247, quantity, svc_price, total, "Active",
                       now, USER_ADMIN, now, USER_ADMIN,
                       f"seed-opd-bi-{bi_id}", TENANT, HOSPITAL]
            bi_rows.append(("BillingItems", bi_cols, bi_vals))

    identity_on("Billings")
    for tbl, cols, vals in billing_rows:
        emit_row_dt(tbl, cols, vals)
    identity_off("Billings")

    identity_on("BillingItems")
    for tbl, cols, vals in bi_rows:
        emit_row_dt(tbl, cols, vals)
    identity_off("BillingItems")

    # ================================================================
    # 11. MEDICAL VISIT DEPARTMENT STAY (for completed OPD)
    # ================================================================
    emit("-- ============================================================")
    emit("-- MedicalVisitDepartmentStay")
    emit("-- ============================================================")

    ds_cols = ["Id", "MedicalVisitId", "DepartmentId", "AttendingUserId",
               "StartAt", "EndAt", "CreatedAt", "CreatedBy", "UpdatedAt", "UpdatedBy",
               "LanguageCode", "TenantId", "HospitalId"]

    ds_counter = 0
    identity_on("MedicalVisitDepartmentStay")
    for vid, patient_id, vstatus, rtime, etime, doctor, ptype, dept in visits:
        if vstatus != "Completed":
            continue
        if random.random() < 0.5:
            continue
        ds_counter += 1
        ds_id = DEPT_STAY_START + ds_counter

        vals = [ds_id, vid, DEPT_KHAM_BENH, doctor,
                rtime, etime, now, USER_ADMIN, now, USER_ADMIN,
                f"seed-opd-ds-{ds_id}", TENANT, HOSPITAL]
        emit_row_dt("MedicalVisitDepartmentStay", ds_cols, vals)
    identity_off("MedicalVisitDepartmentStay")

    # ================================================================
    # Commit
    # ================================================================
    emit("COMMIT TRANSACTION;")
    emit("GO")
    emit("")
    emit("-- Summary")
    emit(f"-- Patients: {len(patients)}")
    emit(f"-- Visits: {len(visits)}")
    emit(f"-- Clinical Services: {len(clinical_services)}")
    emit(f"-- Diagnoses: {dx_counter}")
    emit(f"-- Vital Signs: {vs_counter}")
    emit(f"-- Prescriptions: {rx_counter}")
    emit(f"-- Lab Tests: {lab_counter}")
    emit(f"-- Diagnostic Imaging: {diag_counter}")
    emit(f"-- Billings: {billing_counter}")
    emit(f"-- Billing Items: {bi_counter}")
    emit(f"-- Department Stays: {ds_counter}")
    emit(f"-- Patient Types: {len(patient_types)}")

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Output: {OUTPUT}")
    print(f"Patients: {len(patients)}")
    print(f"Visits: {len(visits)}")
    print(f"Clinical Services: {len(clinical_services)}")
    print(f"Diagnoses: {dx_counter}")
    print(f"Vital Signs: {vs_counter}")
    print(f"Prescriptions: {rx_counter} ({rx_item_counter} items)")
    print(f"Lab Tests: {lab_counter}")
    print(f"Diagnostic Imaging: {diag_counter}")
    print(f"Billings: {billing_counter}")
    print(f"Billing Items: {bi_counter}")
    print(f"Department Stays: {ds_counter}")
    print(f"Patient Types: {len(patient_types)}")


if __name__ == "__main__":
    main()
