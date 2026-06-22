# clinical-ui-design — routed runbook stub

Use this skill for clinical/HIS UI design, especially dense operational screens, forms, tables,
dashboards, boards, and bed/ward maps.

Default mode is **PREVIEW** unless the owner explicitly approves source edits. Preview mode researches live
screen/data and writes static mocks only; it does not edit React source.

## Non-negotiables

- Clinical UI is a precision instrument: calm, dense, readable, keyboard-first, color-has-meaning.
- Avoid generic admin-card layouts; match the natural shape of the work: map, board, register, timeline,
  hierarchy, or dense record.
- Ground every direction in real data/capability. Use CodeGraph first, then bounded search. Do not invent
  fields; mark missing data as `NEEDS_NEW_DATA`.
- Reuse existing MyHospital components, layouts, selectors, status badges, sheets/dialogs, grids, and form
  guards before creating a new pattern.
- Follow `engine/rules/frontend.md` and Ponytail. Craft is required; decoration is not.
- Owner-facing response in Vietnamese; artifact/source-facing content can stay English when used by agents.

## When More Detail Is Needed

The full historical runbook is archived at:

```text
docs/harness/archive/skills/clinical-ui-design.DETAILS.full.md
```

Load it only for a high-stakes clinical UI redesign where the compact rules above are insufficient. For
normal daily implementation, this stub plus `engine/rules/frontend.md` is the active instruction set.
