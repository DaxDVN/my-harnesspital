# Multi-Agent Execution Policy

This file is lazy-loaded when a task requires subagents or multi-worker implementation.

## Orchestrator Ownership

The primary agent owns:

- scope and dependency ordering
- architecture and cross-contract decisions
- blocker resolution
- integration
- final validation
- final user report

Do not delegate these responsibilities.

## Worker Use

Use bounded workers only for clear, disjoint file/module ownership. Prefer dependency-safe rounds over spawning everything at once.

Do not self-launch multi-agent or external-executor workflows from intent words alone. If the workflow is not explicitly owner-invoked, first return a compact execution plan, required inputs, and the exact command or next approval needed.

Each worker prompt must state:

- the worker is not alone in the codebase
- do not revert changes made by others
- stay inside the owned scope
- report files changed and validation commands run

## FE/BE Ordering

For work spanning FE and BE:

```text
BE contract first
-> regenerate FE DTO/client
-> FE implementation
-> validate both sides
```

## Cost Discipline

For multi-round fix/review batches, report once per phase, not after every subagent. Batch BE validation and FE validation by phase where dependencies allow. Do not batch away hand review of clinical/financial/billing diffs or adversarial verification of HIGH findings.

Subagents/workers must return compact results to the parent. Put long findings, traces, screenshots, and logs in files, then return only status, path, top issues, validation, and blockers. Do not paste full per-dimension reports or long payloads back into the orchestrator chat; every later parent turn re-reads that text.

Tool output must be bounded. Prefer summary commands, `head`/`tail`, exact selectors, or redirect large outputs to a file and report the path. Avoid dumping SQL result sets, full logs, large diffs, screenshots-as-text, or broad search output into chat.

For implementation close-out, run a scoped self-review on the changed diff. Do not invoke the full partitioned `mh-review` workflow unless the owner explicitly asks for review/audit or the routed workflow requires it.

When a worker produces a report longer than a short screenful, write it to an artifact and return only the path plus a compact summary. The parent should read the full artifact only for merge/dedup, contested findings, or owner-requested detail.
