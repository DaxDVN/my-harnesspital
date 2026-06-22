# AGENTS.md - MyHospital Harness Bootloader

Thin bootloader only. Keep global invariants here; load details through the router.

<!-- CODEGRAPH_START -->
## CodeGraph

Use CodeGraph before grep/find/direct reads for source code when the repo has `.codegraph/`.
Workspace root is not a source index; FE/BE indexes live in `myhospital-fe/`, `myhospital-be/`, and
`worktrees/<slug>/{fe,be}`. Source policy: `engine/rules/source-discovery.md`.
<!-- CODEGRAPH_END -->

## 1. Session Start

At first prompt: run `python scripts/worktree.py list`.

- If exactly one active worktree is named, use it and state it.
- If source-edit scope is ambiguous, ask: `Bạn muốn làm việc trong worktree nào?`
- Requirement/design-only/spec/harness sessions do not require a worktree.
- Slot/port and browser-login details are lazy refs in `engine/rules/session-boot-details.md`.

## 2. Router First

For non-trivial harness/workflow routing:

```bash
python scripts/harness_router.py "<user prompt>"
python scripts/harness_preflight.py "<user prompt>"
```

Router and preflight are advisory/read-only. They must not execute workflows or enforce fast-path. Load only
files returned by the decision unless local evidence requires more.

For natural-language actionable work, present the preflight route card and wait for owner confirmation before
executing workflows, launching agents/subagents, running browser/E2E sweeps, or making non-trivial source edits.
Skip only for read-only explanation, simple terminal facts, local non-mutating inspection, or an owner-named exact
command. Details: `engine/rules/preflight-confirmation.md`.

## 3. Owner-Gated Execution

- Do not self-launch multi-agent loops, external executors, browser sweeps, `mh-review`, `robust-test`, or workflow state machines from intent words.
- Workflows below `PROVEN` or with `auto_route_allowed=false` need explicit owner instruction before execution.
- `incremental-impl`, `technical-design`, `task-slicing`, and `ui-spec` are manual-only owner-gated workflows.
- Direct single-agent fix/implement work is allowed when the owner asks for it, bounded by worktree, discovery, and validation rules.

## 4. Hard Safety Rules

Default: do not edit `myhospital-fe/` or `myhospital-be/` directly. Source changes go under `worktrees/<slug>/fe|be`.

Hard blocks unless explicitly authorized:

- no `git commit`, `git push`, `git reset --hard`, `git clean`, or destructive checkout;
- no recursive delete;
- no dependency install/add;
- no DB/data mutation except approved worktree-slot migration/data workflows;
- no manual edits to generated FE DTO/client/`Constants.ts` or BE EF migrations;
- no direct writes to `main-brain/`;
- no workflow runtime gate removal unless that is the explicit task.

PowerShell is deprecated.

## 5. Ponytail Always On

Before fix/implement/scaffold/design/review work, prefer the smallest correct change: reuse existing project behavior/component/helper/pattern first; stdlib/platform/current dependency second; local change third; new abstraction last.

Never simplify away validation, security, accessibility, clinical/business correctness, generated-code discipline, or required artifacts. Details: `engine/rules/ponytail.md`.

## 6. Source, Rules, Memory

- Source discovery: CodeGraph first → bounded exact search → narrowed reads.
- FE work: load `myhospital-fe/CLAUDE.md`, then run `python scripts/rule_card.py fe "<task>"` and open the returned quick/topic cards. Open full `engine/rules/frontend.md` only when the cards do not cover the task or risk is high.
- BE work: run `python scripts/rule_card.py be "<task>"` and open the returned quick/topic cards. Open full `engine/rules/backend.md` only when the cards do not cover the task or risk is high; `myhospital-be/CONVENTIONS.md` is advisory only.
- FE+BE work: BE contract first, regenerate FE DTO/client second, validate both sides.
- `main-brain/knowledge.md` is mandatory standing memory. If the tool did not preload it, read it once before substantive work.
- Before fix/review/implement/design/scaffold: `python scripts/learning_recall.py --context "<task>"`; open matched notes only.
- Before fix/implement/review/test: apply `engine/rules/quality-gates.md` when the routed task triggers reuse evidence, fix-plan, regression-map, adjudication, robust-test triage, or validation gates.
- Before executing a natural-language workflow route: apply `engine/rules/preflight-confirmation.md`.
- Never write `main-brain/` directly; capture reusable provisional lessons in `second-brain/`.

## 7. Validation And Artifacts

Report actual validation commands run. If validation cannot run, state why and residual risk.

Use `engine/rules/artifact-policy.md` before reports/evals/screenshots/audit/runtime artifacts. Use `engine/rules/session-boot-details.md` for lazy reference inventory.

## 8. Stop Protocol

```text
BLOCKED_RULE: <short rule name>
Evidence: <file/symbol or planned change that violates it>
Why it matters: <project-specific risk>
Recommended path: <safe option>
```
