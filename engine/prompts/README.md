# engine/prompts — reusable system prompts

Standalone **system prompts** the owner can hand to a fresh/external agent. These are not skills and are not
auto-invoked. They are durable copy-paste templates for recurring real-world harness situations.

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

| Situation | Prompt |
|---|---|
| Deep module/worktree audit before merge | `deep-audit-orchestrator.md` |
| Fix from an audit/findings report | `bugfix-from-report.md` |
| Read-only harness architecture audit | `architecture-audit-readonly.md` |
| Evaluate quality-vs-cost adaptive harness argument | `adaptive-harness-evaluation.md` |
| Implement a named harness governance phase | `harness-governance-phase-runner.md` |
| Run all approved optimization phases in order | `harness-full-optimization-runner.md` |
| Check if optimized harness is ready to trial | `harness-readiness-check.md` |
| Classify a user prompt without executing workflow | `router-dry-run-classifier.md` |
| Owner-gated robust targeted/sweep testing | `robust-test.md` |
| Module-wide E2E bug harvest | `robust-test.md` |
| One failing E2E flow reproduction/retest | `robust-test.md` |
| One bug RCA/fix/verify | `bugfix-rca-single.md` |
| Small approved finding patch | `mh-fix-approved-finding.md` |
| Implement a scoped feature/module | `mh-implement-feature.md` |
| Preflight blast-radius/risk analysis | `impact-analysis-preflight.md` |
| Review a scoped diff without full deep audit | `scope-aware-review.md` |
| Generate/refine UI spec from docs/mockups | `ui-spec-from-docs-mockups.md` |
| Technical/API/schema design | `technical-api-design.md` |
| Slice a design into implementation tasks | `task-slicing.md` |
| Give a subagent one bounded implementation slice | `incremental-impl-worker.md` |
| Design/review high-quality clinical UI | `clinical-ui-design.md` |
| Capture durable learning safely | `learning-capture.md` |
| Repair harness doctor/drift issues | `doctor-drift-repair.md` |
| Browser smoke/E2E evidence run | `browser-e2e-smoke.md` |
| Locate source and impact with CodeGraph-first | `codegraph-source-discovery.md` |
| Review external executor wrapper boundary | `external-executor-wrapper.md` |
| Harden envelope/runtime compatibility | `envelope-runtime-hardening.md` |
| Govern eval-backed lifecycle promotion | `eval-lifecycle-governance.md` |
| Consolidate/deprecate workflows with evidence | `workflow-consolidation-deprecation.md` |
| Recover worktree/slot/dev environment | `worktree-environment-recovery.md` |

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
