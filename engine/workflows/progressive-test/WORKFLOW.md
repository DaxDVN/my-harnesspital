# Multi-Agent E2E Debug/Repair Workflow

## Architecture

```text
Claude Code Orchestrator
  -> .agentflow/bin wrapper scripts
  -> OpenCode executor using the configured cli_model
  -> agent-browser-compatible browser automation for E2E test/retest
  -> artifact files under .agentflow/rounds/<round-id>/
  -> Claude RCA subagent
  -> optional Codex plan review
  -> approved plan
  -> OpenCode IMPLEMENT_ONLY
  -> OpenCode RETEST_ONLY
```

Artifacts and `state.json` are the durable message bus. Chat context is not source of truth.

## Phase A: TEST_ONLY

Claude calls `.agentflow/bin/test-with-opencode <round>`. OpenCode runs Vercel Labs `agent-browser` CLI browser automation and writes `01-bug-packet.json`. In this standalone setup, browser automation is provided by the project-local `.agentflow/bin/agent-browser` shim plus `.opencode/skills/agent-browser/SKILL.md`. OpenCode cannot read source, edit code, triage, RCA, or infer root cause.

## Phase B: RCA

Claude/RCA subagent reads bug packet and targeted code, then writes `02-rca-plan.json` with `DIRECT_PATCH`, `CODEX_REQUIRED`, `MORE_EVIDENCE`, or `HUMAN_DECISION`.

## Phase C: Codex Review Loop

If required, Codex reviews `02-rca-plan.json` and writes `03-codex-review.json` with `APPROVE`, `APPROVE_WITH_CHANGES`, or `REJECT`. Rejections return to RCA until loop limits are hit.

## Phase D: Approved Plan

Claude writes `04-approved-plan.md` after direct approval or Codex approval. This is the immutable executor contract.

## Phase E: IMPLEMENT_ONLY

Claude calls `.agentflow/bin/implement-with-opencode <round>`. OpenCode edits only allowlisted files and writes `05-implementation-report.json`. If the plan does not match code reality, it writes `PLAN_MISMATCH`.

## Phase F: RETEST_ONLY

Claude calls `.agentflow/bin/retest-with-opencode <round>`. OpenCode reruns agent-browser-compatible browser automation and writes `06-retest-report.json`.

## State Machine

States: `IDLE`, `TESTING`, `BUG_PACKET_READY`, `RCA_RUNNING`, `RCA_PLAN_READY`, `CODEX_REVIEW_REQUIRED`, `CODEX_REVIEWING`, `CODEX_REJECTED`, `CODEX_APPROVED`, `DIRECT_PATCH_APPROVED`, `IMPLEMENTING`, `IMPLEMENTED`, `RETESTING`, `RETEST_PASSED`, `RETEST_FAILED`, `PLAN_MISMATCH`, `NEEDS_MORE_EVIDENCE`, `HUMAN_DECISION_REQUIRED`, `DONE`, `FAILED`.

Core transitions are enforced by `update-state`.

## Artifact Contract

`validate-artifact` checks JSON parsing, required fields, enums, null executor RCA fields, hard toolchain fields (`runtime=opencode`, `call_method=bash-wrapper`), and that implementation/retest artifacts report the configured executor model for the run.

## Plan Mismatch

OpenCode must stop with `PLAN_MISMATCH` when the plan requires unknown files, outside-allowlist edits, or unapproved API/schema/business changes.

## Retest Fail Handling

`SAME_BUG` returns to RCA with bug packet + approved plan + implementation report + retest report. `NEW_BUG` starts a new round. `UNKNOWN` requires Claude decision.

## Quota Exhausted

MiMo quota exhaustion stops the workflow. No automatic fallback model.

## Security Boundary

No automatic commit/push, dependency update, destructive command, secret/env edit, source edit outside plan, or raw OpenCode call outside wrappers.


## Browser Capability Guard

Real `TEST_ONLY` and `RETEST_ONLY` require the `agent-browser` CLI by default. If no project-local or PATH `agent-browser` is detected, wrappers stop with `AGENT_BROWSER_NOT_AVAILABLE` instead of allowing a false PASS. Set `AGENTFLOW_REQUIRE_AGENT_BROWSER=0` only for low-level OpenCode smoke/debug runs, not for E2E validation.

The current standalone setup vendors `agent-browser@0.27.3`, installs Chrome through `agent-browser install`, and registers an OpenCode skill at `.opencode/skills/agent-browser/SKILL.md`.

Additional probes:

```bash
.agentflow/bin/probe-web-with-opencode https://example.com
.agentflow/bin/probe-browser-with-opencode https://example.com
.agentflow/bin/probe-agent-browser-with-opencode https://example.com
```

The first uses OpenCode webfetch/websearch and is not browser automation. The second asks OpenCode to drive Firefox headless via bash as a low-level browser smoke. The third uses Vercel Labs `agent-browser` CLI and is the real browser automation probe.
