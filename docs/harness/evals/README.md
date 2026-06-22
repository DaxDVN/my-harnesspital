# Harness Eval Ledger

P4 goal: lifecycle and routing decisions must be backed by run evidence, not vibes.

Eval files live under this directory and follow `_TEMPLATE.yaml`. The template is intentionally small:
it records workflow, risk tier, artifacts, validation evidence, cost/time proxies, outcome quality, and
residual risks.

## Commands

```bash
python scripts/harness_eval.py validate docs/harness/evals/<run>.yaml
python scripts/harness_eval.py scan
python scripts/harness_eval.py summarize
python scripts/harness_eval.py --self-test
python scripts/harness_lifecycle_eval.py scan
python scripts/harness_lifecycle_eval.py new-template <workflow> <short-scope>
```

## Lifecycle Promotion Rules

Use eval evidence conservatively:

| target status | minimum evidence |
|---|---|
| `DRAFT` | docs/design exist; no reliable run evidence |
| `LAB` | runnable/scaffolded enough for explicit owner invocation |
| `PROVEN` | at least one real run eval with output artifacts, validations, and `PASS` or defensible `PARTIAL` |
| `DEFAULT` | repeated real runs across representative tasks, stable validation, low false-positive/reopened rate, owner accepts auto-route |
| `DEPRECATED` | replacement workflow documented and compatibility route/alias exists |

P4 doctor policy:

- `PROVEN` / `DEFAULT` without `eval_summary.artifact_path` is a warning.
- If `eval_summary.artifact_path` is set, it must exist and validate as an eval ledger.
- `DEFAULT` must have `auto_route_allowed=true`.
- Workflows below `PROVEN` cannot auto-route.

## What Not To Do

- Do not promote a workflow because its prompt looks good.
- Do not mark `DEFAULT` from a single smoke test.
- Do not compare cost without also recording validation and residual risk.
- Do not deprecate a workflow without a replacement and compatibility path.

## File Naming

Use date folders for new real evals:

```text
docs/harness/evals/<YYYY-MM-DD>/<workflow>-<short-scope>.yaml
```

Keep payloads/reports as separate artifacts and reference them by path in `input_artifacts` /
`output_artifacts`.
