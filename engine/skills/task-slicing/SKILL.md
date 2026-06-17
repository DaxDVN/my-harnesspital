---
name: task-slicing
description: Owner-invoked. Turns an approved technical design (specs/<module>/07-schema,08-api,03-ui) into specs/<module>/10-plan.md — vertical slices + per-task file-allowlist + per-task validation + dependency order — and updates 04-traceability.md. Gated. Trigger "/task-slicing", "slice tasks", "implementation plan".
---

# task-slicing (W8) — into specs/<module>/10-plan.md

Owner-invoked. **Input:** `specs/<module>/{07-schema,08-api,03-ui,02-requirements,09-test-cases,01-source-audit}` + risk from `/impact-analysis`. **Output:** `10-plan.md` (the EXISTING SDD plan file) + `04-traceability` update + envelope. Prevents uncontrolled "implement module" prompts. Full contract: `engine/workflows/task-slicing/README.md`.

## STEP 0 — input gate (deterministic; run BEFORE slicing)
```bash
python engine/workflows/_shared/gate-check.py <module> --require 07-schema,08-api,03-ui --no-blocking 05-open-questions
```
Exit `2` = **STOP**: `07-schema` (owner-authored) missing → `REQUIRES_OWNER_SCHEMA`; `08-api` missing/stub → `REQUIRES_TECH_DESIGN` (run `/technical-design`); `03-ui` missing → `REQUIRES_UI_SPEC` (run `/ui-spec`); a blocking `05` line → `REQUIRES_BA_DECISION`. Gate open → state should read `DESIGN`/`DESIGN_REVIEW`.

> **Note:** for a normal FE feature, `/mh-implement` (fe-flow) slices internally from `03-ui` (the UI.md reuse map) — use standalone `/task-slicing` mainly for LARGE / cross-cutting modules.

## Slice gate (REJECT layer-only)
Each slice MUST be a **vertical increment** — a thin user-visible path (BE + API + FE + test together), independently shippable/testable. **Reject a layer-only plan** ("all BE, then all FE") — it hides contract drift — UNLESS you record an explicit justification line in `10-plan.md`.
e.g. Slice1 BE minimal model/API + FE api-client smoke · Slice2 list/detail · Slice3 create/edit form · Slice4 validation+permission · Slice5 edge cases · Slice6 E2E.

## Each task — REQUIRED fields (a task missing any is INVALID — do not emit it)
`id` · `slice` · goal · inputs · **files-allowed-to-modify** (non-empty allowlist) · files-forbidden · steps · **validation commands** (non-empty, actually runnable) · expected artifact · dependencies · risk · rollback. No vague "implement API". The allowlist + validation are what let `/incremental-impl` run one task safely — without them the executor is unbounded.

## Steps (write INTO `specs/<module>/10-plan.md`; envelope under `engine/workflows/task-slicing/rounds/<id>/` — get `<id>` via `python engine/workflows/_shared/run-init.py task-slicing` → run-NNN + `00-run-meta` + `logs/`, per `_shared/run-memory.md`)
1. Strategy + vertical slices. 2. Per-task breakdown with the fields above. 3. File-allowlist per task (executor edits nothing outside it). 4. Validation per task (build/typecheck/unit/API/agent-browser). 5. Dependency order. 6. Rollback notes. 7. Update `04-traceability` (requirement → task → test).

## Boundaries
Plan only — never implement, never change the design silently, every task has an allowlist + validation.

## Close-out (envelope + state + learning)
1. Write `rounds/<id>/plan.envelope.json` (shared schema, `artifact_type: plan`, `next_recommended_workflow: incremental-impl`) → validate against `specs/<module>/10-plan.md`.
2. `python engine/workflows/_shared/module-state.py <module> --set SLICED --by task-slicing`.
3. **Learning loop:** if a slice keeps needing a field the template lacks, or the design keeps forcing the same rework → note it in `second-brain/` for `/promote`.

## Status
Scaffold + wiring + contract; slicing-quality UNPROVEN → owner gate. **Input-dependency: `specs/<module>/07,08` populated first (by `/technical-design`).**
