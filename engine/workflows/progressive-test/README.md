# progressive-test

Standalone MVP harness for a self-running E2E debug/repair workflow:

```text
Claude Code Orchestrator -> Bash wrapper -> OpenCode MiMo v2.5 -> agent-browser / implement / retest -> artifacts -> Claude RCA -> optional Codex review -> approved plan -> OpenCode patch -> OpenCode retest
```

This project is isolated from the main harness and can be copied in later.

## Why No Harness MCP For MVP

The orchestration MVP does not need a custom MCP/server. File artifacts plus Bash wrappers are simpler to debug and already enforce the key boundary: Claude calls `.agentflow/bin/*`, not raw OpenCode.

OpenCode itself is configured with a project-local `agent-browser` skill and shim so the executor can perform real browser automation without Playwright MCP.

## Why Claude Calls Wrappers

Allowed Claude entrypoints:

```text
.agentflow/bin/test-with-opencode
.agentflow/bin/implement-with-opencode
.agentflow/bin/retest-with-opencode
.agentflow/bin/validate-artifact
.agentflow/bin/update-state
.agentflow/bin/init-round
.agentflow/bin/summarize-round
.agentflow/bin/doctor
```

Claude must not call raw `opencode run ...`. Wrappers bind model, prompt, logs, artifact validation, and state transitions.

## Why OpenCode Uses MiMo v2.5

OpenCode is the token-burning executor/tester/implementer. Default config:

```yaml
executor:
  runtime: opencode
  model: mimo-v2.5
  cli_model: xiaomi-token-plan-sgp/mimo-v2.5
  provider: xiaomi-token-plan-sgp
  call_method: bash-wrapper
```

No automatic fallback model is enabled. Quota exhaustion stops the workflow.

For this setup, `mimo-v2.5` is represented at the OpenCode CLI layer by the Xiaomi Token Plan Singapore provider model `xiaomi-token-plan-sgp/mimo-v2.5`.

## Install Browser Support

This tool vendors Vercel Labs `agent-browser@0.27.3` under `.agentflow/vendor/agent-browser-package` and exposes it via:

```bash
cd /home/dax/Documents/arabica/tools/progressive-test
.agentflow/bin/agent-browser --version
.agentflow/bin/agent-browser install
```

The browser install creates Chrome here:

```text
/home/dax/.agent-browser/browsers/chrome-149.0.7827.115
```

OpenCode sees `.opencode/skills/agent-browser/SKILL.md`; wrappers prepend `.agentflow/bin` to `PATH`, so OpenCode can run `agent-browser ...` directly.

## Run Doctor

```bash
cd /home/dax/Documents/arabica/tools/progressive-test
.agentflow/bin/doctor
```

Missing `opencode` or `agent-browser` now FAILS — there is no mock; both are required for a real run.

## Validate structure

```bash
.agentflow/bin/doctor
```

The mock executor + smoke test were removed (2026-06-17 — real OpenCode/mimo only). `doctor` validates the subsystem structure; the first real end-to-end run is the owner's gate.

## Run Real Wrapper

```bash
cd /home/dax/Documents/arabica/tools/progressive-test
.agentflow/bin/init-round round-001 "admission-flow"
.agentflow/bin/test-with-opencode round-001
```

Wrappers keep logical `executor.model: mimo-v2.5` for contract validation, then read `executor.cli_model` for the actual OpenCode CLI call:

```bash
opencode run --model xiaomi-token-plan-sgp/mimo-v2.5 "<prompt>"
```

## Agent Boundaries

- Claude Code Orchestrator: state, wrappers, RCA/Codex calls, approved plan. No source edits.
- OpenCode TEST_ONLY: agent-browser + bug packet only. No source reads, triage, RCA, or edits.
- Claude RCA Subagent: targeted code + RCA plan. No edits/browser.
- Codex Review Agent: plan review only. No implementation/browser.
- OpenCode IMPLEMENT_ONLY: approved plan only, allowlist edits only.
- OpenCode RETEST_ONLY: agent-browser retest only. No edits/RCA.

## Failure Handling

- `OPENCODE_NOT_FOUND`: install/configure OpenCode (no mock fallback — real executor required).
- `EXECUTOR_FAILED_NO_ARTIFACT`: executor did not produce required artifact.
- `EXECUTOR_INVALID_ARTIFACT`: artifact failed validation.
- `EXECUTOR_QUOTA_EXHAUSTED`: stop; no model fallback.
- `PLAN_MISMATCH`: return to RCA; executor must not improvise.

## Copy Into Main Harness Later

Copy `.agentflow/` and any wanted docs/tests. Keep the wrapper boundary intact.


## Capability Probe

Check whether the real OpenCode environment can run the intended browser E2E loop:

```bash
.agentflow/bin/capabilities
```

Run a real browser automation probe through OpenCode + agent-browser:

```bash
.agentflow/bin/probe-agent-browser-with-opencode https://example.com
```

Try real OpenCode web inspection using `webfetch`/`websearch` capabilities:

```bash
.agentflow/bin/probe-web-with-opencode https://example.com
```

`probe-web-with-opencode` is not browser automation. `probe-agent-browser-with-opencode` is the real browser automation probe and should show OpenCode invoking `agent-browser skills get core`, `agent-browser open`, `agent-browser snapshot -i`, and `agent-browser screenshot`.
