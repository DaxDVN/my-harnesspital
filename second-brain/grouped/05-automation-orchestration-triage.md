---
title: "Rule Gate: Automation and orchestration triage"
date: "2026-06-22"
status: provisional
source: grouped-generalization
scope: workspace
confidence: high
owner_confirmed: true
proposed_target: engine/workflows/robust-test + workflow docs + prompt docs
tags: [grouped, automation, orchestration, browser, e2e, subagent, workflow]
applies_tasks: [fix, implement, review, test, any]
applies_globs: [engine/workflows/**, engine/prompts/**, docs/audit/**, docs/testing/**]
applies_keywords: [automation, workflow, subagent, browser, e2e, robust-test, screenshot, false-positive, batch, artifact, prompt, language, model]
expires: ""
---

# Automation And Orchestration Triage Gate

Automation output is useful signal, not authority. Batch work to reduce waste, but keep owner gates and high-risk
review.

## Use When

- Running browser/E2E/robust-test or reviewing findings from automation.
- Spawning subagents or external executors.
- Fixing/reviewing many bugs at once.
- Producing reports/prompts/artifacts for other agents or the owner.

## Rule

- Browser/E2E findings are candidates until setup, auth state, form state, slot/worktree binding, and tool limits
  are triaged.
- Do not capture screenshots by default; use them only for specific visual proof or owner-requested evidence.
- Provider/tool-shape 400s are usually non-retryable prompt/tool errors, not transient failures.
- For bug batches: RCA/dedupe first, group owner decisions, fix by dependency phase, validate per phase.
- Do not narrate every subagent completion; compact reports keep main context from ballooning.
- Subagent fan-out must have fallback; do not depend on perfect multi-agent launch behavior.
- Long reports/artifacts follow artifact policy and owner/agent language split.
- Model swaps do not replace harness discipline. Change model only when evidence shows model capability is the
  bottleneck.
- Auto-deciding business questions is not default; only owner-authorized flows may do it and must leave a
  reversible decision log.

## Why It Generalizes

This gate prevents agents from mistaking automation volume for correctness and from spending tokens/time on
redundant orchestration.

## Archive Sources

- [`agent-browser-sheet-portal`](../_archive/2026-06-17-agent-browser-sheet-portal-snapshots.md)
- [`mimo-provider-400`](../_archive/2026-06-17-mimo-executor-retries-provider-400.md)
- [`fix-list-batch-by-phase`](../_archive/2026-06-17-fix-một-list-bug-gộp-theo-phase-be-hết-buildregentest-1-lượt.md)
- [`multi-round-batch-reporting`](../_archive/2026-06-17-multi-round-fixreview-harness-batch-reporting-per-phase-vali.md)
- [`fe-quality-harness-not-model`](../_archive/2026-06-18-fe-ui-quality-harnessskill-quyết-định-chứ-không-phải-model-đ.md)
- [`artifact-date-folder`](../_archive/2026-06-19-agent-generated-artifacts-need-date-folder-convention-curren.md)
- [`fix-flow-auto-decide`](../_archive/2026-06-19-fix-flow-auto-decides-blocking-business-questions-and-writes.md)
- [`language-policy-owner-agent`](../_archive/2026-06-19-language-policy-agent-facingenglish-owner-facingvietnamese-m.md)
- [`mass-parallel-subagent-fallback`](../_archive/2026-06-19-mass-parallel-subagent-spawn-botches-tool-call-across-runtim.md)
- [`reusable-prompts-engine`](../_archive/2026-06-19-reusable-auditfix-system-prompts-live-in-engineprompts.md)
- [`e2e-no-default-screenshots`](../_archive/2026-06-20-e2e-browser-tester-subagents-should-not-capture-screenshots.md)
- [`e2e-false-positive-triage`](../_archive/2026-06-20-e2e-browser-testers-produce-false-positive-bugs-from-formaut.md)
- [`staging-test-slot-binding`](../_archive/2026-06-20-staging-test-bug-investigation-uses-slot3-code.md)
