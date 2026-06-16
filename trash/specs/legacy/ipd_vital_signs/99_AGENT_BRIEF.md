# Agent Brief - IPD Vital Signs

Use this as the starting prompt for a future Codex session.

```text
You are working in D:\arabica\roast. Follow root AGENTS.md and FE/BE harnesses.
This is for the inpatient vital signs submodule. Read:

- specs/ipd_vital_signs/00_INDEX.md
- specs/ipd_vital_signs/01_SOURCE_AUDIT.md
- specs/ipd_vital_signs/02_REQUIREMENT_SEEDS.md
- specs/ipd_vital_signs/03_DESIGN_API_SEEDS.md
- specs/ipd_vital_signs/04_PHASE_PLAN.md
- specs/ipd_vital_signs/05_OPEN_QUESTIONS.md

Source priority:
1. specs/Tài liệu Nội trú.docx section 5.2
2. current myhospital-fe/myhospital-be codebase
3. pasted GPT/web UI catalogue only as reference

Goal for the session: produce finalized requirements/design/API docs or implement the agreed phase, depending on user request.

Important constraints:
- Do not edit main FE/BE branches.
- If implementation is requested, create/use a worktree under worktrees/<slug>/fe and worktrees/<slug>/be.
- Implement BE contract first, regenerate FE DTO/client second, then FE usage.
- Do not hand-edit generated DTOs.
- Do not assume CreatedAt is measurement time unless BA explicitly accepts it.
```

