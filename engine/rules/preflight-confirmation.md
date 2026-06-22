# Natural-Language Preflight Confirmation

Use this rule when the owner gives a natural-language task that could select a workflow, agent, skill, rule
bundle, browser/E2E run, external executor, or source edit.

## Goal

Predict the smallest safe route, show the owner what will be applied, then wait for confirmation before
execution. This gives natural-language convenience without autonomous workflow operation.

## Command

```bash
python scripts/harness_preflight.py "<user prompt>"
python scripts/harness_preflight.py --json "<user prompt>"
```

The helper is read-only. It wraps `scripts/harness_router.py` and reports:

- predicted workflow;
- risk tier and confidence;
- inferred FE/BE package scope and package rule files;
- matched worktree when the route actually needs one;
- entry skill and additional skills;
- candidate agents and external agents;
- rules and gates to apply;
- files to load;
- allowed write boundary and validators;
- whether owner confirmation is required.

## When Confirmation Is Required

Stop and ask for owner confirmation before:

- executing any workflow;
- launching agents/subagents or external executors;
- running browser/E2E sweeps;
- making non-trivial source edits;
- applying a manual-only or owner-gated workflow;
- continuing when route confidence is low or ambiguous.

Confirmation phrase can be natural language, for example:

```text
đồng ý route này
chạy theo route đó
triển khai theo preflight
```

If the owner changes workflow/scope/worktree in the confirmation, rerun preflight with the corrected prompt.

For Codex-specific cooperative use:

```bash
python scripts/codex_preflight.py "<user prompt>"
```

Codex does not have the same prompt-time hook coverage as Claude Code in this repo. The wrapper is therefore a
standard entrypoint, not a sandbox.

## Safe Skips

No preflight is needed for:

- read-only explanations or casual questions;
- simple terminal facts such as date/time;
- local inspection that cannot mutate source or runtime state;
- owner explicitly naming a specific command and asking to run that exact command.

Even when preflight is skipped, hard safety rules and validation reporting still apply.

## Report Shape

Keep the confirmation card compact and owner-facing Vietnamese:

```text
Workflow:
Risk:
Skill/agents:
Rules/gates:
Files to load:
Writes:
Need confirmation because:
```
