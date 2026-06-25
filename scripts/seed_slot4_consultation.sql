SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
SET NOCOUNT ON;

-- Company (manufacturer placeholder)
SET IDENTITY_INSERT [Company] ON;
IF NOT EXISTS (SELECT 1 FROM [Company] WHERE Id=380001)
  INSERT INTO [Company] ([Id],[Name],[IsActive],[TenantId],[HospitalId])
  VALUES (380001,N'Dược phẩm Việt Nam (Seed)',1,1,1);
SET IDENTITY_INSERT [Company] OFF;

-- Unit (viên/tablet placeholder)
SET IDENTITY_INSERT [Unit] ON;
IF NOT EXISTS (SELECT 1 FROM [Unit] WHERE Id=380001)
  INSERT INTO [Unit] ([Id],[Code],[Name],[IsActive],[DisplayOrder],[TenantId],[HospitalId])
  VALUES (380001,N'VIEN',N'Viên',1,1,1,1);
SET IDENTITY_INSERT [Unit] OFF;

-- DosageForm (tablet placeholder)
SET IDENTITY_INSERT [DosageForm] ON;
IF NOT EXISTS (SELECT 1 FROM [DosageForm] WHERE Id=380001)
  INSERT INTO [DosageForm] ([Id],[Code],[Name],[IsActive],[TenantId],[HospitalId])
  VALUES (380001,N'TABLET',N'Viên nén',1,1,1);
SET IDENTITY_INSERT [DosageForm] OFF;

-- Product (5 minimal drug rows)
SET IDENTITY_INSERT [Product] ON;
IF NOT EXISTS (SELECT 1 FROM [Product] WHERE Id=380001)
  INSERT INTO [Product]
    ([Id],[IsActive],[IsManagedByLot],[Code],[Name],[DrugCategory],
     [Description],[ManufacturerId],[UnitId],[DosageFormId],
     [RequiredDoctorPrescription],[AllowPurchaseFromSupplier],
     [DisableInpatient],[DisableOutpatient],
     [CreatedAt],[CreatedBy],[TenantId],[HospitalId])
  VALUES (380001,1,0,N'DRUG-001',N'Paracetamol 500mg',N'Analgesic',
     N'Hạ sốt giảm đau',380001,380001,380001,
     1,1,
     0,0,
     '2026-06-01T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [Product] WHERE Id=380002)
  INSERT INTO [Product]
    ([Id],[IsActive],[IsManagedByLot],[Code],[Name],[DrugCategory],
     [Description],[ManufacturerId],[UnitId],[DosageFormId],
     [RequiredDoctorPrescription],[AllowPurchaseFromSupplier],
     [DisableInpatient],[DisableOutpatient],
     [CreatedAt],[CreatedBy],[TenantId],[HospitalId])
  VALUES (380002,1,0,N'DRUG-002',N'Amoxicillin 500mg',N'Antibiotic',
     N'Kháng sinh nhóm beta-lactam',380001,380001,380001,
     1,1,
     0,0,
     '2026-06-01T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [Product] WHERE Id=380003)
  INSERT INTO [Product]
    ([Id],[IsActive],[IsManagedByLot],[Code],[Name],[DrugCategory],
     [Description],[ManufacturerId],[UnitId],[DosageFormId],
     [RequiredDoctorPrescription],[AllowPurchaseFromSupplier],
     [DisableInpatient],[DisableOutpatient],
     [CreatedAt],[CreatedBy],[TenantId],[HospitalId])
  VALUES (380003,1,0,N'DRUG-003',N'Omeprazole 20mg',N'GastroProtective',
     N'Ức chế bơm proton',380001,380001,380001,
     1,1,
     0,0,
     '2026-06-01T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [Product] WHERE Id=380004)
  INSERT INTO [Product]
    ([Id],[IsActive],[IsManagedByLot],[Code],[Name],[DrugCategory],
     [Description],[ManufacturerId],[UnitId],[DosageFormId],
     [RequiredDoctorPrescription],[AllowPurchaseFromSupplier],
     [DisableInpatient],[DisableOutpatient],
     [CreatedAt],[CreatedBy],[TenantId],[HospitalId])
  VALUES (380004,1,0,N'DRUG-004',N'Metformin 500mg',N'Antidiabetic',
     N'Điều trị đái tháo đường type 2',380001,380001,380001,
     1,1,
     0,0,
     '2026-06-01T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [Product] WHERE Id=380005)
  INSERT INTO [Product]
    ([Id],[IsActive],[IsManagedByLot],[Code],[Name],[DrugCategory],
     [Description],[ManufacturerId],[UnitId],[DosageFormId],
     [RequiredDoctorPrescription],[AllowPurchaseFromSupplier],
     [DisableInpatient],[DisableOutpatient],
     [CreatedAt],[CreatedBy],[TenantId],[HospitalId])
  VALUES (380005,1,0,N'DRUG-005',N'Amlodipine 5mg',N'Antihypertensive',
     N'Chẹn kênh canxi',380001,380001,380001,
     1,1,
     0,0,
     '2026-06-01T08:00:00',1,1,1);
SET IDENTITY_INSERT [Product] OFF;

-- ConsultationRecordDrug (one entry per Drug-type ConsultationRecord)
SET IDENTITY_INSERT [ConsultationRecordDrug] ON;
IF NOT EXISTS (SELECT 1 FROM [ConsultationRecordDrug] WHERE Id=380010)
  INSERT INTO [ConsultationRecordDrug]
    ([Id],[RecordId],[ProductId],[ProductNameSnapshot],[ProductCodeSnapshot],
     [Note],[CreatedAt],[CreatedBy],[TenantId],[HospitalId])
  VALUES (380010,440006,380001,N'Paracetamol 500mg',N'DRUG-001',
     N'Thuốc hội chẩn (seed slot 4)','2026-06-19T09:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [ConsultationRecordDrug] WHERE Id=380011)
  INSERT INTO [ConsultationRecordDrug]
    ([Id],[RecordId],[ProductId],[ProductNameSnapshot],[ProductCodeSnapshot],
     [Note],[CreatedAt],[CreatedBy],[TenantId],[HospitalId])
  VALUES (380011,440007,380002,N'Amoxicillin 500mg',N'DRUG-002',
     N'Thuốc hội chẩn (seed slot 4)','2026-06-19T09:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [ConsultationRecordDrug] WHERE Id=380012)
  INSERT INTO [ConsultationRecordDrug]
    ([Id],[RecordId],[ProductId],[ProductNameSnapshot],[ProductCodeSnapshot],
     [Note],[CreatedAt],[CreatedBy],[TenantId],[HospitalId])
  VALUES (380012,440008,380003,N'Omeprazole 20mg',N'DRUG-003',
     N'Thuốc hội chẩn (seed slot 4)','2026-06-19T09:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [ConsultationRecordDrug] WHERE Id=380013)
  INSERT INTO [ConsultationRecordDrug]
    ([Id],[RecordId],[ProductId],[ProductNameSnapshot],[ProductCodeSnapshot],
     [Note],[CreatedAt],[CreatedBy],[TenantId],[HospitalId])
  VALUES (380013,440009,380004,N'Metformin 500mg',N'DRUG-004',
     N'Thuốc hội chẩn (seed slot 4)','2026-06-19T09:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [ConsultationRecordDrug] WHERE Id=380014)
  INSERT INTO [ConsultationRecordDrug]
    ([Id],[RecordId],[ProductId],[ProductNameSnapshot],[ProductCodeSnapshot],
     [Note],[CreatedAt],[CreatedBy],[TenantId],[HospitalId])
  VALUES (380014,440010,380005,N'Amlodipine 5mg',N'DRUG-005',
     N'Thuốc hội chẩn (seed slot 4)','2026-06-19T09:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [ConsultationRecordDrug] WHERE Id=380015)
  INSERT INTO [ConsultationRecordDrug]
    ([Id],[RecordId],[ProductId],[ProductNameSnapshot],[ProductCodeSnapshot],
     [Note],[CreatedAt],[CreatedBy],[TenantId],[HospitalId])
  VALUES (380015,440011,380001,N'Paracetamol 500mg',N'DRUG-001',
     N'Thuốc hội chẩn (seed slot 4)','2026-06-19T09:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [ConsultationRecordDrug] WHERE Id=380016)
  INSERT INTO [ConsultationRecordDrug]
    ([Id],[RecordId],[ProductId],[ProductNameSnapshot],[ProductCodeSnapshot],
     [Note],[CreatedAt],[CreatedBy],[TenantId],[HospitalId])
  VALUES (380016,440012,380002,N'Amoxicillin 500mg',N'DRUG-002',
     N'Thuốc hội chẩn (seed slot 4)','2026-06-19T09:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [ConsultationRecordDrug] WHERE Id=380017)
  INSERT INTO [ConsultationRecordDrug]
    ([Id],[RecordId],[ProductId],[ProductNameSnapshot],[ProductCodeSnapshot],
     [Note],[CreatedAt],[CreatedBy],[TenantId],[HospitalId])
  VALUES (380017,440013,380003,N'Omeprazole 20mg',N'DRUG-003',
     N'Thuốc hội chẩn (seed slot 4)','2026-06-19T09:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [ConsultationRecordDrug] WHERE Id=380018)
  INSERT INTO [ConsultationRecordDrug]
    ([Id],[RecordId],[ProductId],[ProductNameSnapshot],[ProductCodeSnapshot],
     [Note],[CreatedAt],[CreatedBy],[TenantId],[HospitalId])
  VALUES (380018,440014,380004,N'Metformin 500mg',N'DRUG-004',
     N'Thuốc hội chẩn (seed slot 4)','2026-06-19T09:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [ConsultationRecordDrug] WHERE Id=380019)
  INSERT INTO [ConsultationRecordDrug]
    ([Id],[RecordId],[ProductId],[ProductNameSnapshot],[ProductCodeSnapshot],
     [Note],[CreatedAt],[CreatedBy],[TenantId],[HospitalId])
  VALUES (380019,440015,380005,N'Amlodipine 5mg',N'DRUG-005',
     N'Thuốc hội chẩn (seed slot 4)','2026-06-19T09:00:00',1,1,1);
SET IDENTITY_INSERT [ConsultationRecordDrug] OFF;

-- Post-seed counts
SELECT
  (SELECT COUNT(*) FROM Company)               AS Company,
  (SELECT COUNT(*) FROM Unit)                  AS Unit,
  (SELECT COUNT(*) FROM DosageForm)            AS DosageForm,
  (SELECT COUNT(*) FROM Product)               AS Product,
  (SELECT COUNT(*) FROM ConsultationRecordDrug) AS ConsultationRecordDrug;