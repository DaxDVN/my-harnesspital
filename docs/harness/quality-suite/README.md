# Harness Quality Suite

Small acceptance suite for daily harness quality. These are representative task classes, not source-code
tests. The suite checks whether routing and required quality gates stay aligned after harness changes.

Run:

```bash
python scripts/harness_quality_eval.py run
```

Each case declares:

- prompt sample;
- expected workflow;
- expected risk tier;
- quality gates that must be considered by the agent/harness.
