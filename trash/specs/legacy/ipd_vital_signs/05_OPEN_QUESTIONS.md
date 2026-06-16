# Open Questions - IPD Vital Signs

## BA/Product

1. Is `Tay đo` required always, or only when blood pressure is entered?
2. Must a measurement include at least one clinical value beyond required metadata?
3. Is `Thuận tay` a radio/single choice despite DOCX wording as checkbox?
4. What formula should be used for body surface area?
5. If VAS is absent or no pain, should the value be null or 0?
6. Are `Mạch` and `Nhịp tim` always separate fields?
7. Which notes field should appear in the history expandable row?
8. Does `Dị ứng từ lần cập nhật sinh hiệu cuối cùng` mean latest vital-sign record or latest allergy change event?
9. What axes/scales should be used when charting pulse, heart rate, respiratory rate, and SpO2 together with BP/temperature?
10. Are abnormal-value warnings in scope, or is the chart only for visual review?
11. Should SOAP objective auto-fill latest vital signs, or should doctor copy/type values manually?
12. Do clinical orders such as `theo dõi sinh hiệu 4h/lần` create reminders/tasks, or are they plain text orders?
13. Should nurse handover store a snapshot after save/sign, or always display live latest values?
14. Should KKB/Emergency vital signs become the first inpatient vital-sign record, or only a read-only admission reference?
15. After discharge or department transfer, can staff edit old measurements?

## Technical

1. Should `MeasuredAt` be added to `VitalSigns`, or can an existing date field be safely reused?
2. Should `BodySurfaceArea` be stored or derived in DTO only?
3. Should `BreathingStatus` be enum/string master data?
4. Should update endpoint update allergies atomically with vital signs?
5. How should existing `Patient.Handedness` interact with per-record handedness display?
6. Which permission function should protect inpatient vital signs: existing `VitalSignsManagement` or a new inpatient-specific function?
7. Is `MedicalVisitId` sufficient to scope an inpatient episode across department transfers?

