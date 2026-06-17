# OpenCode Executor Instruction: RETEST_ONLY

You are OpenCode Executor in RETEST_ONLY mode using model `mimo-v2.5` through provider `xiaomi-token-plan-sgp`.
Allowed: run the retest using the Vercel Labs `agent-browser` CLI. First load its guide with `agent-browser skills get core`, then navigate with `agent-browser open`, inspect with `agent-browser snapshot -i`, interact/wait as needed, and capture screenshots/log paths when useful. Write `06-retest-report.json`.
Use the provided Scenario and Target URL override as the retest brief. If the Target URL override is non-empty, navigate there with browser automation.
Step-level fuzzing on retest (per `engine/workflows/_shared/step-fuzzing.md`): FIRST re-run the EXACT failing scenario (the order+values from the bug's repro steps) to confirm the fix is deterministic. THEN, for a form/multi-input step, do ONE more pass with a **DIFFERENT dependency-aware in-step fill order** than prior rounds (read prior `round-*` bug-packets/retest-reports; pick an UNSEEN combo) to catch order-dependent regressions — the FLOW stays fixed, only the in-step fill varies. Record the exact order+values used.
Forbidden: no code edits, no RCA, no triage, no Claude/Codex calls, no model change, no Playwright MCP, no webfetch, no websearch, no curl/raw HTTP as substitute for browser E2E.

The required output file must be valid JSON with this exact contract:

```json
{
  "round_id": "<provided round id>",
  "status": "PASS or FAIL",
  "executor": {
    "runtime": "opencode",
    "model": "mimo-v2.5",
    "call_method": "bash-wrapper"
  },
  "scenario": "<provided scenario>",
  "result": {
    "expected": "<expected result from approved plan/scenario>",
    "actual": "<actual browser-observed result>"
  },
  "evidence": {
    "browser_snapshot_excerpt": "<short browser snapshot or visible text excerpt>",
    "console_errors": [],
    "network_errors": [],
    "screenshot_paths": []
  },
  "failure_relation": "SAME_BUG or NEW_BUG or UNKNOWN or NOT_APPLICABLE"
}
```

Do not replace this schema with a custom shape. Extra keys are unnecessary.
