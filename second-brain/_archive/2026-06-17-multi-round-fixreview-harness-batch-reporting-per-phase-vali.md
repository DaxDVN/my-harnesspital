---
title: "Multi-round fix/review harness: batch reporting + per-phase validation + trust-but-spot-check existing audits to cut cost without losing recall"
date: "2026-06-17"
status: provisional
source: conversation
scope: workspace
confidence: medium
owner_confirmed: false
proposed_target: main-brain
tags: [harness, orchestration, cost-efficiency, mh-fix, mh-review]
applies_tasks: [fix, review, implement]
applies_globs: []
applies_keywords: [harness, orchestration, cost, batch, multi-round, mh-fix, mh-review, subagent]
expires: ""
---

# What

When orchestrating a multi-round subagent fix/review batch, the dominant cost is the Opus main thread re-reading the growing conversation every turn — NOT the (mostly Sonnet) subagents. Four levers cut ~35-50% cost/time with no recall loss: (1) report ONCE per round, not after each subagent completion (each narration turn re-reads full context); (2) run ONE build+test+restart per PHASE (all-BE-code, then all-FE), not per round; (3) when an adversarially-verified audit already exists, independently re-verify only the HIGH + contested by-design/stale/false-positive claims and spot-check the rest, instead of re-deriving all findings from scratch with one investigator per dimension; (4) scope the test round to fix-locking tests and defer pure coverage-gap tests.

# Evidence

- _No specific evidence cited._

# Why It Matters

First real run of the new multi-agent harness on the bed-management fix batch cost ~$58 / 1.5h. Post-mortem: ~30+ Opus turns each re-reading 100k+ tokens of context (worsened by narrating every single subagent completion) + a full independent re-derivation of all 60 findings (6 investigators) + per-round (not per-phase) build/test/restart cycles. These three are redundancy, not depth — cutting them preserves the verified-fix quality (hand-reviewed billing diffs + the BA decision log are the parts to NEVER cut).

# How To Apply

_See # What above._

# Boundaries

Applies to multi-round orchestration where an orchestrator spawns disjoint subagents per round. Do NOT batch away: hand-review of billing/calc diffs, the decision log, or adversarial verification of HIGH/financial findings. The effort-level lever (max vs medium) is owner-managed, out of scope here.

# Promotion Recommendation

Promote to: main-brain
Reason: (fill in before promoting)
