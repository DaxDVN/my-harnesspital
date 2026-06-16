# Agent Brief - IPD Consultation

Use this as the starting prompt for a future Codex session.

```text
You are working in D:\arabica\roast. Follow root AGENTS.md and FE/BE harnesses.
This is for the inpatient consultation submodule, with a required treatment-progress foundation.
Read:

- specs/ipd_consultation/00_INDEX.md
- specs/ipd_consultation/01_SOURCE_AUDIT.md
- specs/ipd_consultation/02_REQUIREMENT_SEEDS.md
- specs/ipd_consultation/03_TREATMENT_PROGRESS_FOUNDATION.md
- specs/ipd_consultation/04_DESIGN_API_SEEDS.md
- specs/ipd_consultation/05_PHASE_PLAN.md
- specs/ipd_consultation/06_OPEN_QUESTIONS.md

Source priority:
1. specs/Tài liệu Nội trú.docx sections 5.3 and 5.5
2. current myhospital-fe/myhospital-be codebase
3. pasted GPT/web UI catalogue only as reference

Goal for the session: produce finalized requirements/design/API docs or implement the agreed phase, depending on user request.

Important constraints:
- Do not edit main FE/BE branches.
- If implementation is requested, create/use a worktree under worktrees/<slug>/fe and worktrees/<slug>/be.
- Do not implement consultation by reusing only transfer handover ClinicalProgress.
- Treatment-progress foundation should come before full consultation minutes/invitations/drug consultation.
- Implement BE contract first, regenerate FE DTO/client second, then FE usage.
- Do not hand-edit generated DTOs.
```

