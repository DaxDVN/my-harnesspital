# SYSTEM PROMPT — EVAL GOVERNANCE (HISTORICAL)

Lifecycle policy (DRAFT/LAB/PROVEN/DEFAULT) was removed 2026-06-29 per owner decision.
All workflows are always available when the owner invokes them; `auto_route_allowed`
controls auto-routing.

Evals (`docs/harness/evals/`) remain as optional historical artifacts. Use
`scripts/harness_eval.py` to validate/scan/summarize eval ledgers.

## Validation

```bash
python scripts/harness_eval.py --self-test
python scripts/harness_eval.py scan
python scripts/harness_workflow_governance.py scan
python scripts/harness_doctor.py
```
