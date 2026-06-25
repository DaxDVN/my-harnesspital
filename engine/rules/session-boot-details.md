# Session Boot Details

Lazy reference for details intentionally kept out of `AGENTS.md`.

## Worktree Slot Map

| Slot | FE | BE | SQL |
|---|---|---|---|
| 1 | `:3001` | `:5001` | `localhost,1434` |
| 2 | `:3002` | `:5002` | `localhost,1435` |
| 3 | `:3003` | `:5003` | `localhost,1436` |
| 4 | `:3004` | `:5004` | `localhost,1437` |

## Lazy-Load Index

| Need | File(s) |
|---|---|
| Harness inventory | `engine/README.md`, `engine/REGISTRY.md` |
| Router contract | `engine/router/README.md` |
| Backend rules | `engine/rules/backend.md` |
| Frontend rules | `engine/rules/frontend.md` |
| Source discovery | `engine/rules/source-discovery.md` |
| Minimal-diff discipline | `engine/rules/ponytail.md` |
| Cross-tool enforcement | `engine/rules/cross-tool-enforcement.md` |
| Worktree reference | `engine/rules/worktree-workflow.md` |
| Memory/learning | `engine/rules/memory-policy.md` |
| Artifacts/date folders/audit paths | `engine/rules/artifact-policy.md` |
| Requirement/design/spec protocol | `engine/rules/spec-driven-development.md` |
| Graphify docs/spec graph | `engine/rules/graphify.md` |
| Multi-agent/subagent execution | `engine/rules/multi-agent-execution.md` |
| Review harness | `engine/workflows/deep-review/{protocol,checklist,findings-schema}.md` |
| Workflow behavior | `engine/workflows/<name>/manifest.json` + routed docs |

## Worktree Commands

Worktree lifecycle is owner-driven. Do not auto-run create/join/setup/cleanup/sync on intent words. When asked, print the exact `scripts/worktree.py` command and run it only when the owner explicitly says to run that command.

## Local Agent Browser Smoke Login

MANDATORY browser/E2E test credential — **every** browser-driven test (agent-browser or Playwright), every session, MUST log in with this account:

```text
customer code: bvtest3
username: lynkhanh9822@gmail.com
password: 12.[s7HXZQ;NfAoF
tenant: bvtest3 -> TenantId = 6, HospitalId = 7
```

BLOCK: do NOT use `e2e/helpers/login.ts` `HMU_ADMIN` (`admin` / `123456`) or any other account for browser tests. That account is a different tenant and lacks bed-management / inpatient / schedule permissions, so it produces false "Không có quyền truy cập" (no-permission) results. Inject the `bvtest3` credential above into every browser-test subagent prompt; never let a tester fall back to the e2e default.
