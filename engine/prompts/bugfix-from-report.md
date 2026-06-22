# bugfix-from-report — archived full prompt stub

Use this prompt only when the owner wants a fresh agent/session to fix from a large audit report.

Daily fix work should prefer:

- `engine/skills/mh-fix/DETAILS.md` for approved/simple findings;
- `engine/skills/bug-fix/DETAILS.md` for reproduce/RCA/fix/verify;
- `engine/rules/ponytail.md` for minimal correct diff;
- `engine/workflows/deep-review/findings-schema.md` for status updates.

The former full self-contained prompt was archived to:

```text
docs/harness/archive/prompts/bugfix-from-report.full.md
```

Load it only for a token-heavy, fresh-agent repair run from a full findings report.
