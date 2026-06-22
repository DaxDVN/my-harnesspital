# Frontend Quick Rule Card

Use this before opening the full `engine/rules/frontend.md`.

## Always

- Source discovery: CodeGraph in the FE repo first, then bounded exact search.
- Reuse existing module/shared component, hook, adapter, schema, and UI pattern before creating new code.
- Generated DTO/client/`Constants.ts` are read-only; regenerate from BE when contracts change.
- FE data access goes through generated adapters/hooks, not raw `fetch`, `axios`, or manual ServiceStack clients.
- User-facing visible UI needs i18n, accessibility basics, dirty-state protection where applicable, and targeted browser/manual smoke when changed.
- Report actual validation. For visible/form/table changes, prefer `tsc -p tsconfig.app.json` plus targeted smoke.

## Load Topic Cards

- Forms/sheets/fields: `engine/rules/frontend/forms.md`
- Query/mutation/master data/cache: `engine/rules/frontend/data.md`
- DTO/API/generated/permission contracts: `engine/rules/frontend/contracts.md`
- UI reuse/table/layout/i18n: `engine/rules/frontend/ui-reuse.md`

Open the full `engine/rules/frontend.md` only when these cards conflict with local evidence, the task is high-risk,
or the selected topic cards do not cover the change.
