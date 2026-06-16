# IPD Consultation Spec Seed Pack

This folder is a working material pack for the inpatient consultation submodule.
It is not the final requirement/design/API spec yet.

## Scope

Small module: `Hội chẩn nội trú`.

Important dependency: `Tờ điều trị / Diễn biến người bệnh`.

Although the user may call this the consultation module, current DOCX and codebase analysis show that consultation cannot be designed safely without first defining the treatment-progress source that supplies:

- latest clinical progress,
- current diagnosis,
- current condition summary,
- treatment/care summary,
- drug consultation diagnosis context.

## Source Priority

1. `D:\arabica\roast\specs\Tài liệu Nội trú.docx`
   - section 5.3 `Tờ điều trị`
   - section 5.5 `Hội chẩn`
2. Current codebase under `D:\arabica\roast\myhospital-fe` and `D:\arabica\roast\myhospital-be`.
3. The pasted GPT/web UI catalogue is reference only. Use it only after validating against DOCX and codebase.

## Reading Order

1. `01_SOURCE_AUDIT.md` - DOCX/code/GPT evaluation.
2. `02_REQUIREMENT_SEEDS.md` - consultation requirement candidates.
3. `03_TREATMENT_PROGRESS_FOUNDATION.md` - required dependency before full consultation.
4. `04_DESIGN_API_SEEDS.md` - data/API/design materials.
5. `05_PHASE_PLAN.md` - recommended phase order and worktree slicing.
6. `06_OPEN_QUESTIONS.md` - BA/product/tech questions.
7. `99_AGENT_BRIEF.md` - handoff prompt for a future Codex session.

## Hard Rule For Future Work

Do not implement consultation by reusing only the transfer handover field `ClinicalProgress`.
That field belongs to department-transfer handover and is not the canonical treatment-progress record required by DOCX consultation flows.

