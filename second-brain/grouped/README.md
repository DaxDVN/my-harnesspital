# second-brain grouped view

Grouped view is the compressed management layer for `second-brain/`.

Use these files first when recalling or promoting lessons. The original `YYYY-MM-DD-*.md` notes live in
`../_archive/` as raw evidence for traceability and should only be opened when a grouped rule needs verification.

## Generalized Rule Gates

| file | role |
|---|---|
| `01-freshness-before-diagnosis.md` | Verify generated/runtime/env freshness before blaming source code |
| `02-canonical-reuse-gate.md` | Reuse existing project patterns before hand-rolling new code |
| `03-correct-boundary-data-integrity.md` | Put business/data rules at the right boundary and preserve real contracts |
| `04-evidence-verification-gate.md` | Require the right proof before claiming verified/safe/false-positive |
| `05-automation-orchestration-triage.md` | Treat automation as signal, batch work safely, keep owner gates |
| `06-design-spec-decision-gate.md` | Choose clinical UI genre by job and store module-local decisions in specs |

## Policy

- Grouped files are generalized provisional gates, not canonical rules yet.
- If a group becomes stable, graduate it into `engine/rules`, a scanner/checklist, or a skill before `main-brain`.
- Keep archived raw notes until the owner explicitly asks to delete them.
- Do not add zellij-specific operational detail here; owner controls that manually.
