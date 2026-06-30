SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
SET NOCOUNT ON;

-- 1. Spread Bed.AvailabilityStatus for visual diversity
UPDATE [Bed] SET AvailabilityStatus=N'Maintenance', StatusReason=N'Bảo trì định kỳ', StatusUpdatedBy=1, StatusUpdatedAt='2026-06-20T08:00:00', UpdatedAt='2026-06-20T08:00:00', UpdatedBy=1 WHERE Id=1 AND AvailabilityStatus=N'Available';
UPDATE [Bed] SET AvailabilityStatus=N'Maintenance', StatusReason=N'Bảo trì định kỳ', StatusUpdatedBy=1, StatusUpdatedAt='2026-06-20T08:00:00', UpdatedAt='2026-06-20T08:00:00', UpdatedBy=1 WHERE Id=8 AND AvailabilityStatus=N'Available';
UPDATE [Bed] SET AvailabilityStatus=N'Maintenance', StatusReason=N'Bảo trì định kỳ', StatusUpdatedBy=1, StatusUpdatedAt='2026-06-20T08:00:00', UpdatedAt='2026-06-20T08:00:00', UpdatedBy=1 WHERE Id=2001 AND AvailabilityStatus=N'Available';
UPDATE [Bed] SET AvailabilityStatus=N'Maintenance', StatusReason=N'Bảo trì định kỳ', StatusUpdatedBy=1, StatusUpdatedAt='2026-06-20T08:00:00', UpdatedAt='2026-06-20T08:00:00', UpdatedBy=1 WHERE Id=2041 AND AvailabilityStatus=N'Available';
UPDATE [Bed] SET AvailabilityStatus=N'Cleaning', StatusReason=N'Đang vệ sinh sau bệnh nhân xuất viện', StatusUpdatedBy=1, StatusUpdatedAt='2026-06-23T07:00:00', UpdatedAt='2026-06-23T07:00:00', UpdatedBy=1 WHERE Id=2 AND AvailabilityStatus=N'Available';
UPDATE [Bed] SET AvailabilityStatus=N'Cleaning', StatusReason=N'Đang vệ sinh sau bệnh nhân xuất viện', StatusUpdatedBy=1, StatusUpdatedAt='2026-06-23T07:00:00', UpdatedAt='2026-06-23T07:00:00', UpdatedBy=1 WHERE Id=14 AND AvailabilityStatus=N'Available';
UPDATE [Bed] SET AvailabilityStatus=N'Cleaning', StatusReason=N'Đang vệ sinh sau bệnh nhân xuất viện', StatusUpdatedBy=1, StatusUpdatedAt='2026-06-23T07:00:00', UpdatedAt='2026-06-23T07:00:00', UpdatedBy=1 WHERE Id=2011 AND AvailabilityStatus=N'Available';
UPDATE [Bed] SET AvailabilityStatus=N'Cleaning', StatusReason=N'Đang vệ sinh sau bệnh nhân xuất viện', StatusUpdatedBy=1, StatusUpdatedAt='2026-06-23T07:00:00', UpdatedAt='2026-06-23T07:00:00', UpdatedBy=1 WHERE Id=2051 AND AvailabilityStatus=N'Available';
UPDATE [Bed] SET AvailabilityStatus=N'Isolated', StatusReason=N'Cách ly bệnh nhân nghi ngờ', StatusUpdatedBy=1, StatusUpdatedAt='2026-06-22T09:00:00', UpdatedAt='2026-06-22T09:00:00', UpdatedBy=1 WHERE Id=3 AND AvailabilityStatus=N'Available';
UPDATE [Bed] SET AvailabilityStatus=N'Isolated', StatusReason=N'Cách ly bệnh nhân nghi ngờ', StatusUpdatedBy=1, StatusUpdatedAt='2026-06-22T09:00:00', UpdatedAt='2026-06-22T09:00:00', UpdatedBy=1 WHERE Id=21 AND AvailabilityStatus=N'Available';
UPDATE [Bed] SET AvailabilityStatus=N'Blocked', StatusReason=N'Dành riêng cho ca phẫu thuật', StatusUpdatedBy=1, StatusUpdatedAt='2026-06-23T06:00:00', UpdatedAt='2026-06-23T06:00:00', UpdatedBy=1 WHERE Id=20 AND AvailabilityStatus=N'Available';
UPDATE [Bed] SET AvailabilityStatus=N'Blocked', StatusReason=N'Dành riêng cho ca phẫu thuật', StatusUpdatedBy=1, StatusUpdatedAt='2026-06-23T06:00:00', UpdatedAt='2026-06-23T06:00:00', UpdatedBy=1 WHERE Id=22 AND AvailabilityStatus=N'Available';

-- 2. Link Bed.StatusRelatedVisitId to active MedicalVisit
UPDATE [Bed] SET StatusRelatedVisitId=320101, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=2021 AND StatusRelatedVisitId IS NULL;
UPDATE [Bed] SET StatusRelatedVisitId=320102, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=2022 AND StatusRelatedVisitId IS NULL;
UPDATE [Bed] SET StatusRelatedVisitId=320103, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=2023 AND StatusRelatedVisitId IS NULL;
UPDATE [Bed] SET StatusRelatedVisitId=320104, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=2024 AND StatusRelatedVisitId IS NULL;
UPDATE [Bed] SET StatusRelatedVisitId=320105, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=3001 AND StatusRelatedVisitId IS NULL;
UPDATE [Bed] SET StatusRelatedVisitId=320106, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=5 AND StatusRelatedVisitId IS NULL;
UPDATE [Bed] SET StatusRelatedVisitId=320107, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=6 AND StatusRelatedVisitId IS NULL;
UPDATE [Bed] SET StatusRelatedVisitId=320108, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=7 AND StatusRelatedVisitId IS NULL;
UPDATE [Bed] SET StatusRelatedVisitId=320113, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=19 AND StatusRelatedVisitId IS NULL;
UPDATE [Bed] SET StatusRelatedVisitId=320114, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=13 AND StatusRelatedVisitId IS NULL;
UPDATE [Bed] SET StatusRelatedVisitId=320115, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=3002 AND StatusRelatedVisitId IS NULL;
UPDATE [Bed] SET StatusRelatedVisitId=320116, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=11 AND StatusRelatedVisitId IS NULL;
UPDATE [Bed] SET StatusRelatedVisitId=320110, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=26 AND StatusRelatedVisitId IS NULL;

-- 3. BedType diversity (SelfSelect beds for BedClassification filter)
UPDATE [Bed] SET BedTypeId=2, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=2031;
UPDATE [Bed] SET BedTypeId=3, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=2032;
UPDATE [Bed] SET BedTypeId=2, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=2033;
UPDATE [Bed] SET BedTypeId=2, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=2041;
UPDATE [Bed] SET BedTypeId=3, UpdatedAt='2026-06-23T08:00:00', UpdatedBy=1 WHERE Id=2042;

-- 4. BedDayServiceConfigTier rows
SET IDENTITY_INSERT [BedDayServiceConfigTier] ON;
IF NOT EXISTS (SELECT 1 FROM [BedDayServiceConfigTier] WHERE Id=370021)
  INSERT INTO [BedDayServiceConfigTier] ([Id],[BedDayServiceConfigId],[Portion],[FromHours],[ToHours],[ConvertedDays],[DisplayOrder],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370021,1,N'Bhyt',0,6,0.0,1,'2026-06-23T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedDayServiceConfigTier] WHERE Id=370022)
  INSERT INTO [BedDayServiceConfigTier] ([Id],[BedDayServiceConfigId],[Portion],[FromHours],[ToHours],[ConvertedDays],[DisplayOrder],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370022,1,N'Bhyt',6,24,1.0,2,'2026-06-23T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedDayServiceConfigTier] WHERE Id=370023)
  INSERT INTO [BedDayServiceConfigTier] ([Id],[BedDayServiceConfigId],[Portion],[FromHours],[ToHours],[ConvertedDays],[DisplayOrder],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370023,1,N'Bhyt',24,NULL,1.0,3,'2026-06-23T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedDayServiceConfigTier] WHERE Id=370024)
  INSERT INTO [BedDayServiceConfigTier] ([Id],[BedDayServiceConfigId],[Portion],[FromHours],[ToHours],[ConvertedDays],[DisplayOrder],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370024,2,N'Bhyt',0,6,0.0,1,'2026-06-23T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedDayServiceConfigTier] WHERE Id=370025)
  INSERT INTO [BedDayServiceConfigTier] ([Id],[BedDayServiceConfigId],[Portion],[FromHours],[ToHours],[ConvertedDays],[DisplayOrder],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370025,2,N'Bhyt',6,24,1.0,2,'2026-06-23T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedDayServiceConfigTier] WHERE Id=370026)
  INSERT INTO [BedDayServiceConfigTier] ([Id],[BedDayServiceConfigId],[Portion],[FromHours],[ToHours],[ConvertedDays],[DisplayOrder],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370026,2,N'Bhyt',24,NULL,1.0,3,'2026-06-23T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedDayServiceConfigTier] WHERE Id=370027)
  INSERT INTO [BedDayServiceConfigTier] ([Id],[BedDayServiceConfigId],[Portion],[FromHours],[ToHours],[ConvertedDays],[DisplayOrder],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370027,3,N'Service',0,12,0.0,1,'2026-06-23T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedDayServiceConfigTier] WHERE Id=370028)
  INSERT INTO [BedDayServiceConfigTier] ([Id],[BedDayServiceConfigId],[Portion],[FromHours],[ToHours],[ConvertedDays],[DisplayOrder],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370028,3,N'Service',12,24,1.0,2,'2026-06-23T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedDayServiceConfigTier] WHERE Id=370029)
  INSERT INTO [BedDayServiceConfigTier] ([Id],[BedDayServiceConfigId],[Portion],[FromHours],[ToHours],[ConvertedDays],[DisplayOrder],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370029,3,N'Service',24,NULL,1.0,3,'2026-06-23T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedDayServiceConfigTier] WHERE Id=370030)
  INSERT INTO [BedDayServiceConfigTier] ([Id],[BedDayServiceConfigId],[Portion],[FromHours],[ToHours],[ConvertedDays],[DisplayOrder],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370030,4,N'Bhyt',0,24,1.0,1,'2026-06-23T08:00:00',1,1,1);
SET IDENTITY_INSERT [BedDayServiceConfigTier] OFF;

-- 5. New BedReservations
SET IDENTITY_INSERT [BedReservation] ON;
IF NOT EXISTS (SELECT 1 FROM [BedReservation] WHERE Id=370001)
  INSERT INTO [BedReservation] ([Id],[MedicalVisitId],[PatientId],[ExpectedAdmissionDate],[ExpectedDischargeDate],[Status],[ReservedById],[ReservedAt],[LinkedSurgeryServiceIds],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370001,320101,310101,'2026-07-01T08:00:00','2026-07-05T10:00:00',N'Pending',1,'2026-06-20T08:00:00',N'[]','2026-06-20T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedReservation] WHERE Id=370002)
  INSERT INTO [BedReservation] ([Id],[MedicalVisitId],[PatientId],[ExpectedAdmissionDate],[ExpectedDischargeDate],[Status],[ReservedById],[ReservedAt],[LinkedSurgeryServiceIds],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370002,320102,310102,'2026-07-02T08:00:00','2026-07-07T10:00:00',N'Confirmed',1,'2026-06-20T08:00:00',N'[]','2026-06-20T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedReservation] WHERE Id=370003)
  INSERT INTO [BedReservation] ([Id],[MedicalVisitId],[PatientId],[ExpectedAdmissionDate],[ExpectedDischargeDate],[Status],[ReservedById],[ReservedAt],[LinkedSurgeryServiceIds],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370003,320103,310103,'2026-07-03T08:00:00','2026-07-08T10:00:00',N'Confirmed',1,'2026-06-20T08:00:00',N'[]','2026-06-20T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedReservation] WHERE Id=370004)
  INSERT INTO [BedReservation] ([Id],[MedicalVisitId],[PatientId],[ExpectedAdmissionDate],[ExpectedDischargeDate],[Status],[ReservedById],[ReservedAt],[LinkedSurgeryServiceIds],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370004,320104,310104,'2026-06-10T08:00:00','2026-06-14T10:00:00',N'Expired',1,'2026-06-20T08:00:00',N'[]','2026-06-20T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedReservation] WHERE Id=370005)
  INSERT INTO [BedReservation] ([Id],[MedicalVisitId],[PatientId],[ExpectedAdmissionDate],[ExpectedDischargeDate],[Status],[ReservedById],[ReservedAt],[LinkedSurgeryServiceIds],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370005,320105,310105,'2026-07-05T08:00:00','2026-07-09T10:00:00',N'Pending',1,'2026-06-20T08:00:00',N'[]','2026-06-20T08:00:00',1,1,1);
SET IDENTITY_INSERT [BedReservation] OFF;

-- 6. BedReservationItems
SET IDENTITY_INSERT [BedReservationItem] ON;
IF NOT EXISTS (SELECT 1 FROM [BedReservationItem] WHERE Id=370011)
  INSERT INTO [BedReservationItem] ([Id],[BedReservationId],[BedId],[IsForCompanion],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370011,370001,2003,0,'2026-06-20T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedReservationItem] WHERE Id=370012)
  INSERT INTO [BedReservationItem] ([Id],[BedReservationId],[BedId],[IsForCompanion],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370012,370002,2013,0,'2026-06-20T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedReservationItem] WHERE Id=370013)
  INSERT INTO [BedReservationItem] ([Id],[BedReservationId],[BedId],[IsForCompanion],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370013,370003,2043,0,'2026-06-20T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedReservationItem] WHERE Id=370014)
  INSERT INTO [BedReservationItem] ([Id],[BedReservationId],[BedId],[IsForCompanion],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370014,370004,2004,0,'2026-06-20T08:00:00',1,1,1);
IF NOT EXISTS (SELECT 1 FROM [BedReservationItem] WHERE Id=370015)
  INSERT INTO [BedReservationItem] ([Id],[BedReservationId],[BedId],[IsForCompanion],[CreatedAt],[CreatedBy],[TenantId],[HospitalId]) VALUES (370015,370005,2044,0,'2026-06-20T08:00:00',1,1,1);
SET IDENTITY_INSERT [BedReservationItem] OFF;
