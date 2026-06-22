# Artifact and Path Policy

This file is lazy-loaded when creating reports, plans, evals, audit findings, screenshots, API diffs, or workflow artifacts.

## Workspace Root

The workspace root is reserved for harness entry files and top-level repo/tooling folders. Do not save ad-hoc artifacts directly to root.

## Artifact Locations

| Artifact type | Save to |
|---|---|
| Task plans, implementation plans | `docs/tasks/<YYYY-MM-DD>/` |
| Session analysis, audit reports, research notes | `docs/session-notes/<YYYY-MM-DD>/` |
| Test cases, setup docs | `docs/testing/<YYYY-MM-DD>/` |
| Browser screenshots, UI captures | `docs/testing/screenshots/<YYYY-MM-DD>/` |
| DTO dumps, API diffs, BE diffs | `docs/session-notes/<YYYY-MM-DD>/` |
| Durable harness plans/notes/evals | `docs/harness/plans/`, `docs/harness/notes/`, `docs/harness/evals/` |
| One-off scripts | `scripts/` |
| Feature specs, BA docs | `specs/<module>/` |

## Date-Folder Rule

For new generated artifacts under `docs/audit/`, `docs/tasks/`, `docs/session-notes/`, and `docs/testing/`, group by day:

```text
<dir>/<YYYY-MM-DD>/<file>
```

Specs and one-off scripts are not date-foldered by this rule.

## Audit Round-Version Rule

Every new document under `docs/audit/` must be round-versioned:

```text
<base>.round-<N>.md
```

Use the helper; do not eyeball the round number:

```bash
python scripts/audit_path.py "<base>"
python scripts/audit_path.py "<base>" --vi
python scripts/audit_path.py "<base>" --current
```

The Vietnamese clone shares the same round number and uses `.vi.md`.

## Tracked vs Ignored

- `docs/harness/**` and `docs/graphify-agent-guide.md` are durable harness history.
- `docs/session-notes`, `docs/tasks`, and `docs/testing` are working-space artifacts unless project git rules say otherwise.

## Validation Contract

Report actual validation commands run. If a command cannot run, state why and name the residual risk.
