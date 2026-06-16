# Open Questions - IPD Consultation

## BA/Product

1. Is `Tờ điều trị / Diễn biến người bệnh` required before any consultation work starts?
2. For latest treatment-sheet prefill, use latest saved draft, latest signed, or latest not-cancelled?
3. If no treatment sheet exists, what should consultation prefill from?
4. Is `Biên bản hội chẩn thuốc được duyệt` equivalent to signed, or is there a separate approval actor/status?
5. Does clinical-progress consultation require both chair and secretary to sign?
6. Is `Thành phần tham gia` in minutes free text, structured participants, or both?
7. Consultation type `Khác`: what recipient/UI rules apply?
8. Whole-hospital consultation: all departments, all clinical departments, selected departments, and/or board of directors?
9. Inter-hospital consultation: who can confirm attendance and what is the external facility catalog source?
10. Is there a separate dashboard/list for pending signatures and pending attendance confirmations?
11. Should consultation minutes/invitations support print/PDF in the first phase?
12. Can signed consultation minutes be cancelled, amended, or superseded?
13. Are attachments required for invitation only, or also for minutes?
14. Is drug consultation mandatory before prescribing, before sending to pharmacy, or before signing medication order?
15. If a warning says drug consultation is missing, can doctor still save draft medication order?
16. What exactly distinguishes consultation from specialty examination in UI navigation?

## Technical

1. Should treatment progress, consultation minutes, and invitation live under a new BE service namespace or inpatient service partials?
2. Should diagnosis snapshots be normalized child rows or JSON snapshots?
3. Should patient/admission context snapshot be stored as JSON or explicit columns?
4. What existing signing infrastructure can be reused?
5. What existing attachment model can be reused for invitation files?
6. Which permission function names should be added or reused?
7. Is `MedicalVisitId` enough for all consultation records across department transfers, or should department stay/ward stay also be referenced?
8. Should consultation code use `proc_CodeGeneratorAsync` with prefix `HC{ddMMyy}-`?
9. How will generated DTO/client regeneration be coordinated with the parallel vital-signs worktree?
10. What tests already exist for inpatient service patterns that should be copied?

