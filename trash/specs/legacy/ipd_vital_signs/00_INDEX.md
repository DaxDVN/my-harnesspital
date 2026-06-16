# IPD Vital Signs Spec Seed Pack

This folder is a working material pack for the inpatient vital signs submodule.
It is not the final requirement/design/API spec yet.

## Scope

Small module: `Sinh hiệu nội trú`.

Parent domain: inpatient treatment record (`Nội trú`). The feature lives inside the
inpatient patient treatment detail screen, not as a standalone outpatient/examination
workflow.

## Source Priority

1. `D:\arabica\roast\specs\Tài liệu Nội trú.docx` section 5.2 `Tab Sinh hiệu` is the business source of truth.
2. Current codebase under `D:\arabica\roast\myhospital-fe` and `D:\arabica\roast\myhospital-be` is the implementation source of truth.
3. The pasted GPT/web UI catalogue is reference only. Use it only after validating against DOCX and codebase.

## Reading Order

1. `01_SOURCE_AUDIT.md` - what is known from DOCX, codebase, and GPT reference.
2. `02_REQUIREMENT_SEEDS.md` - requirement candidates to turn into `requirements.md`.
3. `03_DESIGN_API_SEEDS.md` - design/API materials and codebase-fit notes.
4. `04_PHASE_PLAN.md` - recommended implementation and documentation phases.
5. `05_OPEN_QUESTIONS.md` - BA/product/tech questions before final design.
6. `99_AGENT_BRIEF.md` - handoff prompt for a future Codex session.

## Do Not Assume

- Do not assume `CreatedAt` is equal to business measurement time. DOCX requires editable `Thời gian đo`.
- Do not copy the existing outpatient `VitalSignsPage` as-is into inpatient.
- Do not treat nurse handover vital signs snapshot as the canonical inpatient vital signs module.
- Do not modify generated DTOs by hand. If API contracts change, regenerate the FE client.

