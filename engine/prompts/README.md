# engine/prompts — reusable system prompts

Standalone **system prompts** the owner can hand to a fresh/external agent. These are not skills and are not
auto-invoked. They are durable copy-paste templates for recurring real-world harness situations.

## Layout

```text
engine/prompts/
  *.md            top-level = WIRED prompts a workflow/skill/router can dispatch (each is referenced by a
                  manifest `recommended_prompt_file`, a skill, a rule, or a script). Keep this dir clean.
  governance/     harness-maintenance LIBRARY — prompts the owner hands an agent for harness / governance /
                  optimization / recovery work. Catalogued here, never auto-dispatched by a workflow.
  manual/         read-only MANUAL prompts the owner runs by hand (architecture audit / browser smoke /
                  source discovery / scoped review). Read-only, never auto-dispatched.
```

Only top-level prompts are reachable by the router and workflow manifests. Moving a wired prompt into a subdir
would break its `recommended_prompt_file` path (harness doctor `registry` / workflow-governance flags it as a
dangling reference) — so dispatched prompts MUST stay at the top level. `governance/` and `manual/` prompts are
owner-handed runbooks only.

## How to use

Give an agent one file path plus the concrete task input:

```text
Đọc engine/prompts/<prompt-file>.md làm system prompt.
<Task-specific input...>
Bắt đầu.
```

Unless a prompt says otherwise:

- Agent-facing prompt/report language may be English for cross-agent handoff.
- Chat response to owner should be Vietnamese.
- Harness hard blocks still apply.
- The prompt does not override `AGENTS.md`, `CLAUDE.md`, or local workflow rules.

## Router Integration

Workflow manifests expose these files through `recommended_prompt_file`. The router returns that value as
`prompt_file_recommended`, but does **not** put it in `files_to_load` by default.

Use this distinction:

- Daily work: let router load lightweight skill/workflow docs.
- Fresh/external agent: hand it the recommended prompt file as the session runbook.
- Wrapper automation: inject the prompt file only when the workflow explicitly selects an external executor.

## Fast Picker

### Wired / dispatched (top level)

These have a workflow/skill/script behind them; the router exposes them via `recommended_prompt_file`.

| Situation | Prompt |
|---|---|
| Deep module/worktree audit before merge | `deep-audit-orchestrator.md` |
| Fix from an audit/findings report | `bugfix-from-report.md` |
| Owner-gated robust targeted/sweep testing | `robust-test.md` |
| Module-wide E2E bug harvest | `robust-test.md` |
| One failing E2E flow reproduction/retest | `robust-test.md` |
| One bug RCA/fix/verify | `bugfix-rca-single.md` |
| Small approved finding patch | `mh-fix-approved-finding.md` |
| Implement a scoped feature/module | `mh-implement-feature.md` |
| Preflight blast-radius/risk analysis | `impact-analysis-preflight.md` |
| Generate/refine UI spec from docs/mockups | `ui-spec-from-docs-mockups.md` |
| Technical/API/schema design | `technical-api-design.md` |
| Slice a design into implementation tasks | `task-slicing.md` |
| Give a subagent one bounded implementation slice | `incremental-impl-worker.md` |
| Design/review high-quality clinical UI | `clinical-ui-design.md` |
| Review/espresso loop coordination | `espresso-test.md` |
| Always-on PM orchestrator runbook | `pm-orchestrator.md` |
| Bounded subagent prompt scaffold | `subagent-prompt-template.md` |

### Governance library (`governance/`)

Harness-maintenance prompts — owner-handed only, never auto-dispatched. The 7 one-off rollout
prompts from the completed P0–P8 optimization (adaptive-eval, full-optimization-runner,
governance-phase-runner, readiness-check, workflow-consolidation, GUIDELINE stub,
eval-lifecycle tombstone) were archived to `docs/harness/archive/prompts/`.

| Situation | Prompt |
|---|---|
| Classify a user prompt without executing workflow | `governance/router-dry-run-classifier.md` |
| Capture durable learning safely | `governance/learning-capture.md` |
| Repair harness doctor/drift issues | `governance/doctor-drift-repair.md` |
| Review external executor wrapper boundary | `governance/external-executor-wrapper.md` |
| Harden envelope/runtime compatibility | `governance/envelope-runtime-hardening.md` |
| Recover worktree/slot/dev environment | `governance/worktree-environment-recovery.md` |

### Manual read-only (`manual/`)

Read-only prompts the owner runs by hand; no source edits.

| Situation | Prompt |
|---|---|
| Read-only harness architecture audit | `manual/architecture-audit-readonly.md` |
| Browser smoke/E2E evidence run | `manual/browser-e2e-smoke.md` |
| Locate source and impact with CodeGraph-first | `manual/codegraph-source-discovery.md` |
| Review a scoped diff without full deep audit | `manual/scope-aware-review.md` |

## Audit/Fix Loop

```
deep-audit-orchestrator.md + <slug>  ──▶  docs/audit/<YYYY-MM-DD>/full-audit-<scope>.md   ──▶  bugfix-from-report.md + report-path(.md)
        (find + detail)                          + .vi.md (bản dịch cho owner)                     (Opus xhigh: triage → fix)
```

## Ngôn ngữ (cả 2 prompt)

- Prompt agent nhận + suy nghĩ + report cho-agent-đọc = **English**. Response chat cho owner = **tiếng Việt**.
- Mỗi report ra **2 file**: `<name>.md` (EN, canonical — agent/handoff đọc) + `<name>.vi.md` (VN — owner đọc).
  Gen EN trước, rồi 1 subagent rẻ (haiku/sonnet) clone bản VN. Mọi handoff/automation trỏ bản `.md` EN.

## Run an audit — 1 prompt + a slug

Hand the audit agent `engine/prompts/deep-audit-orchestrator.md` and name the target:
```
Đọc engine/prompts/deep-audit-orchestrator.md làm system prompt. Audit module: vital-signs. Chạy ngay.
```
Built-in registry targets (slug or Vietnamese name both resolve):
- `noi-tru-3modules` — bed / shift / reception (worktree `fix-bug-noi-tru`; carries the 42-item BA-FINAL list).
- `ipd-consultation` — Hội chẩn (merge-gate).
- `vital-signs` — Sinh hiệu nội trú (merge-gate, regression-heavy).

**New module not in the registry?** The agent asks you to fill the **MODULE BLOCK contract (§10)** once (or
auto-discovers baseline/scope via `worktree.py list` + `git diff --stat`), runs, then you append its preset to
§11 so next time it's just a slug.

Output → `docs/audit/<today>/full-audit-<scope>.md` (folder auto-created).

## Run the fix — Opus xhigh + report path

```
Đọc engine/prompts/bugfix-from-report.md làm system prompt.
Report: docs/audit/2026-06-19/full-audit-vital-signs.md   Worktree: worktrees/vital-signs   Bắt đầu.
```
Opus → trích OPEN findings theo severity+cluster → re-verify gốc LIVE → (mh-rca nếu phức tạp) → fix-plan
(+impact-analysis/Codex nếu rủi ro) → `/mh-fix` trong worktree → verify → cập nhật `status` trong report.

## Why this shape

The shared 90% (non-negotiables, harness workflows, dynamic floor, D1–D7, bug-classes, finding schema,
guardrails, DoD) + all per-module presets live **inside `deep-audit-orchestrator.md`** — one file, no external
instance files. Edit it once → every future audit inherits the upgrade. Output always lands in a
per-day folder (`docs/audit/<YYYY-MM-DD>/`), matching the workspace artifact convention.

## Prompt Design Convention

New prompts in this directory should include:

- Role.
- Inputs.
- Non-negotiables.
- Required reads or discovery.
- Process.
- Validation/reporting.
- Output format.
- Clear stop conditions when relevant.

Avoid adding prompts that are just prose duplicates of an existing workflow. Prefer a reusable prompt only when
the owner commonly hands a whole runbook to a fresh agent.
