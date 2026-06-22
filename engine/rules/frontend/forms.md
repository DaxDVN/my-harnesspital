# Frontend Forms, Sheets, And Fields

- Reuse canonical form/sheet/field components and dirty guards before hand-rolling controls.
- Keep schemas in the module `forms/` area when the pattern exists; prefer RHF + zod patterns already used nearby.
- Do not create a new field/control when an existing semantic component covers the behavior.
- If coding reveals the selected component cannot fit, record reuse evidence and why extension/new code is safer.
- Check value sync, focus retention, one-shot open/init behavior, validation target, and save/reload persistence for form fixes.
- For visible form changes, include a compact reuse matrix: field/surface, existing pattern checked, decision, reason.
