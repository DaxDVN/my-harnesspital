-- Seed VitalSigns for 3 InProgress inpatient visits (Tenant=6, Hospital=7)
-- Mirrors the column set of Levi Carter (MedicalVisitId=6332063, MeasuredByUserId=176)
-- Idempotent: skips rows where (MedicalVisitId, MeasuredAt) already exists

-- ============================================================
-- Patient 1: MedicalVisitId=6332060, PatientId=6331060
-- ============================================================
INSERT INTO VitalSigns (
    IsActive, PatientId, MedicalVisitId, MedicalVisitClinicalServiceId,
    Pulse, HeartRate, Spo2, BloodPressureSys, BloodPressureDia, RespiratoryRate,
    Temperature, Weight, Height, Bmi, MeasuredArm, MeasuredAt, MeasuredByUserId,
    MedicalVisitDepartmentStayId, BreathingStatus, Bsa, VasScore, PainPoint, Notes,
    CreatedAt, CreatedBy, UpdatedAt, UpdatedBy,
    LanguageCode, TenantId, HospitalId
)
SELECT 1, 6331060, 6332060, NULL,
    80, 82, 98.00, 120, 80, 18, 37.00, 65.00, 170.00, 22.49, 'right',
    '2026-06-18 07:00:00', 176,
    NULL, N'Tự thở', 1.73, 1, N'Không đau', NULL,
    GETDATE(), 176, GETDATE(), 176,
    NULL, 6, 7
WHERE NOT EXISTS (
    SELECT 1 FROM VitalSigns WHERE MedicalVisitId=6332060 AND MeasuredAt='2026-06-18 07:00:00'
)

INSERT INTO VitalSigns (
    IsActive, PatientId, MedicalVisitId, MedicalVisitClinicalServiceId,
    Pulse, HeartRate, Spo2, BloodPressureSys, BloodPressureDia, RespiratoryRate,
    Temperature, Weight, Height, Bmi, MeasuredArm, MeasuredAt, MeasuredByUserId,
    MedicalVisitDepartmentStayId, BreathingStatus, Bsa, VasScore, PainPoint, Notes,
    CreatedAt, CreatedBy, UpdatedAt, UpdatedBy,
    LanguageCode, TenantId, HospitalId
)
SELECT 1, 6331060, 6332060, NULL,
    86, 88, 97.00, 130, 85, 20, 37.50, 65.00, 170.00, 22.49, 'right',
    '2026-06-18 19:00:00', 176,
    NULL, N'Tự thở', 1.73, 2, N'Đau nhẹ', NULL,
    GETDATE(), 176, GETDATE(), 176,
    NULL, 6, 7
WHERE NOT EXISTS (
    SELECT 1 FROM VitalSigns WHERE MedicalVisitId=6332060 AND MeasuredAt='2026-06-18 19:00:00'
)

INSERT INTO VitalSigns (
    IsActive, PatientId, MedicalVisitId, MedicalVisitClinicalServiceId,
    Pulse, HeartRate, Spo2, BloodPressureSys, BloodPressureDia, RespiratoryRate,
    Temperature, Weight, Height, Bmi, MeasuredArm, MeasuredAt, MeasuredByUserId,
    MedicalVisitDepartmentStayId, BreathingStatus, Bsa, VasScore, PainPoint, Notes,
    CreatedAt, CreatedBy, UpdatedAt, UpdatedBy,
    LanguageCode, TenantId, HospitalId
)
SELECT 1, 6331060, 6332060, NULL,
    92, 94, 96.00, 140, 90, 22, 38.10, 65.00, 170.00, 22.49, 'right',
    '2026-06-19 07:00:00', 176,
    NULL, N'Tự thở', 1.73, 3, N'Đau vừa', NULL,
    GETDATE(), 176, GETDATE(), 176,
    NULL, 6, 7
WHERE NOT EXISTS (
    SELECT 1 FROM VitalSigns WHERE MedicalVisitId=6332060 AND MeasuredAt='2026-06-19 07:00:00'
)

INSERT INTO VitalSigns (
    IsActive, PatientId, MedicalVisitId, MedicalVisitClinicalServiceId,
    Pulse, HeartRate, Spo2, BloodPressureSys, BloodPressureDia, RespiratoryRate,
    Temperature, Weight, Height, Bmi, MeasuredArm, MeasuredAt, MeasuredByUserId,
    MedicalVisitDepartmentStayId, BreathingStatus, Bsa, VasScore, PainPoint, Notes,
    CreatedAt, CreatedBy, UpdatedAt, UpdatedBy,
    LanguageCode, TenantId, HospitalId
)
SELECT 1, 6331060, 6332060, NULL,
    78, 80, 98.00, 118, 76, 17, 36.80, 65.00, 170.00, 22.49, 'left',
    '2026-06-19 19:00:00', 176,
    NULL, N'Tự thở', 1.73, 1, N'Không đau', NULL,
    GETDATE(), 176, GETDATE(), 176,
    NULL, 6, 7
WHERE NOT EXISTS (
    SELECT 1 FROM VitalSigns WHERE MedicalVisitId=6332060 AND MeasuredAt='2026-06-19 19:00:00'
)

INSERT INTO VitalSigns (
    IsActive, PatientId, MedicalVisitId, MedicalVisitClinicalServiceId,
    Pulse, HeartRate, Spo2, BloodPressureSys, BloodPressureDia, RespiratoryRate,
    Temperature, Weight, Height, Bmi, MeasuredArm, MeasuredAt, MeasuredByUserId,
    MedicalVisitDepartmentStayId, BreathingStatus, Bsa, VasScore, PainPoint, Notes,
    CreatedAt, CreatedBy, UpdatedAt, UpdatedBy,
    LanguageCode, TenantId, HospitalId
)
SELECT 1, 6331060, 6332060, NULL,
    75, 76, 99.00, 115, 74, 16, 36.50, 65.00, 170.00, 22.49, 'left',
    '2026-06-20 07:00:00', 176,
    NULL, N'Tự thở', 1.73, 0, N'Không đau', NULL,
    GETDATE(), 176, GETDATE(), 176,
    NULL, 6, 7
WHERE NOT EXISTS (
    SELECT 1 FROM VitalSigns WHERE MedicalVisitId=6332060 AND MeasuredAt='2026-06-20 07:00:00'
)

-- ============================================================
-- Patient 2: MedicalVisitId=6332059, PatientId=6331059
-- ============================================================
INSERT INTO VitalSigns (
    IsActive, PatientId, MedicalVisitId, MedicalVisitClinicalServiceId,
    Pulse, HeartRate, Spo2, BloodPressureSys, BloodPressureDia, RespiratoryRate,
    Temperature, Weight, Height, Bmi, MeasuredArm, MeasuredAt, MeasuredByUserId,
    MedicalVisitDepartmentStayId, BreathingStatus, Bsa, VasScore, PainPoint, Notes,
    CreatedAt, CreatedBy, UpdatedAt, UpdatedBy,
    LanguageCode, TenantId, HospitalId
)
SELECT 1, 6331059, 6332059, NULL,
    95, 97, 94.00, 150, 95, 24, 38.80, 70.00, 165.00, 25.71, 'right',
    '2026-06-17 08:30:00', 176,
    NULL, N'Tự thở', 1.82, 4, N'Đau nhiều', NULL,
    GETDATE(), 176, GETDATE(), 176,
    NULL, 6, 7
WHERE NOT EXISTS (
    SELECT 1 FROM VitalSigns WHERE MedicalVisitId=6332059 AND MeasuredAt='2026-06-17 08:30:00'
)

INSERT INTO VitalSigns (
    IsActive, PatientId, MedicalVisitId, MedicalVisitClinicalServiceId,
    Pulse, HeartRate, Spo2, BloodPressureSys, BloodPressureDia, RespiratoryRate,
    Temperature, Weight, Height, Bmi, MeasuredArm, MeasuredAt, MeasuredByUserId,
    MedicalVisitDepartmentStayId, BreathingStatus, Bsa, VasScore, PainPoint, Notes,
    CreatedAt, CreatedBy, UpdatedAt, UpdatedBy,
    LanguageCode, TenantId, HospitalId
)
SELECT 1, 6331059, 6332059, NULL,
    88, 90, 96.00, 140, 88, 21, 38.20, 70.00, 165.00, 25.71, 'right',
    '2026-06-18 08:30:00', 176,
    NULL, N'Tự thở', 1.82, 3, N'Đau vừa', NULL,
    GETDATE(), 176, GETDATE(), 176,
    NULL, 6, 7
WHERE NOT EXISTS (
    SELECT 1 FROM VitalSigns WHERE MedicalVisitId=6332059 AND MeasuredAt='2026-06-18 08:30:00'
)

INSERT INTO VitalSigns (
    IsActive, PatientId, MedicalVisitId, MedicalVisitClinicalServiceId,
    Pulse, HeartRate, Spo2, BloodPressureSys, BloodPressureDia, RespiratoryRate,
    Temperature, Weight, Height, Bmi, MeasuredArm, MeasuredAt, MeasuredByUserId,
    MedicalVisitDepartmentStayId, BreathingStatus, Bsa, VasScore, PainPoint, Notes,
    CreatedAt, CreatedBy, UpdatedAt, UpdatedBy,
    LanguageCode, TenantId, HospitalId
)
SELECT 1, 6331059, 6332059, NULL,
    82, 84, 97.00, 132, 84, 19, 37.80, 70.00, 165.00, 25.71, 'left',
    '2026-06-19 08:30:00', 176,
    NULL, N'Tự thở', 1.82, 2, N'Đau nhẹ', NULL,
    GETDATE(), 176, GETDATE(), 176,
    NULL, 6, 7
WHERE NOT EXISTS (
    SELECT 1 FROM VitalSigns WHERE MedicalVisitId=6332059 AND MeasuredAt='2026-06-19 08:30:00'
)

INSERT INTO VitalSigns (
    IsActive, PatientId, MedicalVisitId, MedicalVisitClinicalServiceId,
    Pulse, HeartRate, Spo2, BloodPressureSys, BloodPressureDia, RespiratoryRate,
    Temperature, Weight, Height, Bmi, MeasuredArm, MeasuredAt, MeasuredByUserId,
    MedicalVisitDepartmentStayId, BreathingStatus, Bsa, VasScore, PainPoint, Notes,
    CreatedAt, CreatedBy, UpdatedAt, UpdatedBy,
    LanguageCode, TenantId, HospitalId
)
SELECT 1, 6331059, 6332059, NULL,
    76, 78, 98.00, 125, 80, 17, 37.20, 70.00, 165.00, 25.71, 'left',
    '2026-06-20 08:30:00', 176,
    NULL, N'Tự thở', 1.82, 1, N'Không đau', NULL,
    GETDATE(), 176, GETDATE(), 176,
    NULL, 6, 7
WHERE NOT EXISTS (
    SELECT 1 FROM VitalSigns WHERE MedicalVisitId=6332059 AND MeasuredAt='2026-06-20 08:30:00'
)

-- ============================================================
-- Patient 3: MedicalVisitId=6332058, PatientId=6331058
-- ============================================================
INSERT INTO VitalSigns (
    IsActive, PatientId, MedicalVisitId, MedicalVisitClinicalServiceId,
    Pulse, HeartRate, Spo2, BloodPressureSys, BloodPressureDia, RespiratoryRate,
    Temperature, Weight, Height, Bmi, MeasuredArm, MeasuredAt, MeasuredByUserId,
    MedicalVisitDepartmentStayId, BreathingStatus, Bsa, VasScore, PainPoint, Notes,
    CreatedAt, CreatedBy, UpdatedAt, UpdatedBy,
    LanguageCode, TenantId, HospitalId
)
SELECT 1, 6331058, 6332058, NULL,
    70, 72, 99.00, 110, 70, 15, 36.30, 58.00, 160.00, 22.66, 'right',
    '2026-06-17 06:00:00', 176,
    NULL, N'Tự thở', 1.65, 0, N'Không đau', NULL,
    GETDATE(), 176, GETDATE(), 176,
    NULL, 6, 7
WHERE NOT EXISTS (
    SELECT 1 FROM VitalSigns WHERE MedicalVisitId=6332058 AND MeasuredAt='2026-06-17 06:00:00'
)

INSERT INTO VitalSigns (
    IsActive, PatientId, MedicalVisitId, MedicalVisitClinicalServiceId,
    Pulse, HeartRate, Spo2, BloodPressureSys, BloodPressureDia, RespiratoryRate,
    Temperature, Weight, Height, Bmi, MeasuredArm, MeasuredAt, MeasuredByUserId,
    MedicalVisitDepartmentStayId, BreathingStatus, Bsa, VasScore, PainPoint, Notes,
    CreatedAt, CreatedBy, UpdatedAt, UpdatedBy,
    LanguageCode, TenantId, HospitalId
)
SELECT 1, 6331058, 6332058, NULL,
    74, 76, 98.00, 116, 74, 16, 36.60, 58.00, 160.00, 22.66, 'right',
    '2026-06-18 06:00:00', 176,
    NULL, N'Tự thở', 1.65, 1, N'Không đau', NULL,
    GETDATE(), 176, GETDATE(), 176,
    NULL, 6, 7
WHERE NOT EXISTS (
    SELECT 1 FROM VitalSigns WHERE MedicalVisitId=6332058 AND MeasuredAt='2026-06-18 06:00:00'
)

INSERT INTO VitalSigns (
    IsActive, PatientId, MedicalVisitId, MedicalVisitClinicalServiceId,
    Pulse, HeartRate, Spo2, BloodPressureSys, BloodPressureDia, RespiratoryRate,
    Temperature, Weight, Height, Bmi, MeasuredArm, MeasuredAt, MeasuredByUserId,
    MedicalVisitDepartmentStayId, BreathingStatus, Bsa, VasScore, PainPoint, Notes,
    CreatedAt, CreatedBy, UpdatedAt, UpdatedBy,
    LanguageCode, TenantId, HospitalId
)
SELECT 1, 6331058, 6332058, NULL,
    77, 79, 97.00, 122, 78, 17, 37.10, 58.00, 160.00, 22.66, 'left',
    '2026-06-19 06:00:00', 176,
    NULL, N'Tự thở', 1.65, 2, N'Đau nhẹ', NULL,
    GETDATE(), 176, GETDATE(), 176,
    NULL, 6, 7
WHERE NOT EXISTS (
    SELECT 1 FROM VitalSigns WHERE MedicalVisitId=6332058 AND MeasuredAt='2026-06-19 06:00:00'
)

INSERT INTO VitalSigns (
    IsActive, PatientId, MedicalVisitId, MedicalVisitClinicalServiceId,
    Pulse, HeartRate, Spo2, BloodPressureSys, BloodPressureDia, RespiratoryRate,
    Temperature, Weight, Height, Bmi, MeasuredArm, MeasuredAt, MeasuredByUserId,
    MedicalVisitDepartmentStayId, BreathingStatus, Bsa, VasScore, PainPoint, Notes,
    CreatedAt, CreatedBy, UpdatedAt, UpdatedBy,
    LanguageCode, TenantId, HospitalId
)
SELECT 1, 6331058, 6332058, NULL,
    72, 73, 98.00, 112, 72, 15, 36.40, 58.00, 160.00, 22.66, 'left',
    '2026-06-20 06:00:00', 176,
    NULL, N'Tự thở', 1.65, 0, N'Không đau', NULL,
    GETDATE(), 176, GETDATE(), 176,
    NULL, 6, 7
WHERE NOT EXISTS (
    SELECT 1 FROM VitalSigns WHERE MedicalVisitId=6332058 AND MeasuredAt='2026-06-20 06:00:00'
)

-- Verify
SELECT MedicalVisitId, PatientId, COUNT(*) as MeasurementCount
FROM VitalSigns
WHERE MedicalVisitId IN (6332058, 6332059, 6332060)
GROUP BY MedicalVisitId, PatientId
ORDER BY MedicalVisitId
