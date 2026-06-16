# Approved Plan - round-fixture

## Approval Source
DIRECT_PATCH_BY_CLAUDE

## Executor Runtime
OpenCode

## Executor Model
mimo-v2.5

## Executor Call Method
Bash wrapper script:
.agentflow/bin/implement-with-opencode

## Scope
Fixture scope.

## Root Cause Summary
Fixture root cause.

## Files Allowed To Modify
- `src/Fixture.tsx`

## Files Forbidden To Modify
- `package.json`

## Forbidden Changes
- Do not change API contract.
- Do not change schema.
- Do not add dependency.
- Do not refactor unrelated code.

## Implementation Steps
1. Update fixture handler.

## Validation Commands
- fixture validate

## E2E Retest Scenario
- fixture-flow

## Stop Conditions
- If required file does not exist, stop with PLAN_MISMATCH.
- If implementation requires modifying files outside allowlist, stop with PLAN_MISMATCH.
- If validation failure is unrelated to the plan, stop and report.
