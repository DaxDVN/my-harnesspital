# technical-design (W7) — BE+FE+API design INTO specs/<module>/

Entry skill: `/technical-design`. Produces design by WRITING the EXISTING SDD files — no parallel artifacts.

## Reuses (does NOT rebuild)
- The **SDD layout** `specs/<module>/{07-schema,08-api,03-ui,06-decision-log,04-traceability}.md` (these ARE the design artifacts).
- **CodeGraph** + `01-source-audit` for technical truth; **`mh-rule-auditor`** for the convention/design gate; **codex** for high-risk review; **`/impact-analysis`** for blast-radius.

## Inputs → Outputs
IN: `specs/<module>/{02-requirements,03-ui,05-open-questions,06-decision-log,01-source-audit}`.
OUT: `specs/<module>/{07-schema,08-api,03-ui(contract),06-decision-log,04-traceability}.md` + a design envelope.

## Gate
BLOCKING `05` question on schema/API/core-flow → STOP (`REQUIRES_BA_DECISION`). Design-review gate before task-slicing on schema/API/complex-state/cross-module/ambiguity.

## Why BE+FE+API together (not split)
One coherent contract prevents FE/BE drift (the vertical-slice principle). Sub-sections (schema/api/ui) live in their SDD files but are designed in one pass.

## Status
Scaffold + contract; design-quality UNPROVEN → owner gate. **Needs `specs/<module>/02,03` populated first.**
