# Frontend UI Reuse, Layout, And I18n

- Reuse existing shared/module UI shells, table/grid patterns, labels, status badges, headers, and action layouts before adding new components.
- New tabular admin/list UI should not bypass the established grid/list shell unless current evidence proves it cannot fit.
- Hard-coded user-facing text is a warning in areas that already use i18n.
- Prefer project layout containment patterns for pages/sheets/modals instead of local one-off CSS.
- Patient/header/display fields should use precomputed DTO display fields when available instead of recomputing in FE.
- For UI review, verify the live widget/layout pattern, not only static screenshot similarity.
