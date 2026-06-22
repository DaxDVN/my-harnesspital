# Harness v2 Final Readiness - 2026-06-20

Status after P0-P8 hardening: ready for owner real-run experiments.

## Completed

| phase | result |
|---|---|
| P0 | lifecycle/public/internal/advisory metadata + doctor governance |
| P1 | dry-run router |
| P2 | thin root + lazy-loaded workflow docs |
| P3 | envelope compatibility adapter + runtime boundary contract |
| P4 | eval/cost ledger validator + lifecycle evidence gate |
| P5 | workflow consolidation/deprecation governance |
| P6 | one-shot readiness command |
| P7 | runtime contract scanner |
| P8 | evidence-gated consolidation policy; no unsafe deprecation |

## Current Readiness Command

```bash
python scripts/harness_ready.py
```

This runs:

- `python scripts/harness_doctor.py --strict`
- `python scripts/harness_router.py --self-test`
- `python scripts/harness_eval.py scan`
- `python scripts/harness_workflow_governance.py scan`
- `python scripts/harness_runtime_contract.py scan`
- `python scripts/learning_check.py`

## Graphify Decision

`graphify-out/` was quarantined to:

```text
/tmp/graphify-out-quarantine-20260620-1319
```

Reason: `graphify update .` and `graphify update . --force` rebuilt a graph that still included
FE/BE source symbols such as `myhospital-fe/src/...` and `myhospital-be/...`, which violates the current
policy that graphify is optional docs/specs design-intent tooling only. With `graphify-out/` absent,
doctor reports INFO instead of WARN and agents will not trust an unsafe graph.

Re-enable graphify only after a docs/specs-only build can be produced and `python scripts/harness_doctor.py`
returns no graphify trust/secrets warnings.

## Current Routing Posture

- No workflow is auto-routable.
- No workflow is `PROVEN` or `DEFAULT`.
- `LAB` workflows remain explicit owner-invocation only.
- Consolidation/deprecation is blocked until eval artifacts prove replacement safety.

## First Real Experiments

Recommended order:

1. Run one `deep-review` real audit and write an eval ledger.
2. Run one `ui-spec` or `bug-fix` real workflow and write an eval ledger.
3. Run one `super-test` module harvest after the browser/test environment is stable.
4. Promote lifecycle only after eval evidence exists.
