---
name: dev-from-handoff
description: Owner-invoked. Implements from owner-supplied business/design handoff docs: intake -> technical plan -> owner approval -> bounded dev slices -> validation/receipt. Manual-only DRAFT workflow.
---

# dev-from-handoff — full runbook

> `SKILL.md` is the token-light discovery stub. This file is the authoritative runbook.

## Role
Drive development from an owner-supplied business/design handoff. The workflow starts after the owner provides
the handoff. It does not perform BA discovery, invent requirements, invent clinical/business/billing rules, or
use BMAD-style requirement discovery.

## Required inputs
- Owner-supplied handoff document(s): business requirements, design notes, UI mockups, API notes, approved specs,
  or an explicit owner message.
- Target scope: module/package and intended FE/BE surface.
- Target worktree slug before source edits.
- Explicit owner approval of the technical implementation plan.

## Step 0 — boot and intake gates
1. Run normal session boot rules: worktree list, router/preflight if applicable, `learning_recall`, and standing memory.
2. Load `engine/rules/artifact-policy.md`, `engine/rules/spec-driven-development.md`,
   `engine/rules/source-discovery.md`, `engine/rules/ponytail.md`, and `engine/rules/quality-gates.md`.
3. Inventory the handoff sources and cite them. If the source is a `specs/<module>/` package, read
   `00-module-state.md` and `00-session-handoff.md` first.
4. If the handoff is missing, contradictory, or asks the agent to discover business rules, STOP with:

```text
BLOCKED_RULE: owner handoff required
Evidence: <missing/contradictory source>
Why it matters: development would require invented business/design rules
Recommended path: owner supplies/clarifies the handoff, then rerun dev-from-handoff
```

## Step 1 — handoff intake
Create a concise intake record under `docs/tasks/<YYYY-MM-DD>/` or
`engine/workflows/dev-from-handoff/rounds/<run-id>/`:
- source documents and exact scope;
- confirmed owner decisions;
- open blockers, with technical impact only;
- target worktree/package;
- candidate source areas to inspect.

Do not turn blockers into assumptions unless the owner explicitly authorizes that.

## Step 2 — source and reuse discovery
Use CodeGraph first for source discovery in the selected worktree/package. Use bounded exact search only after
CodeGraph narrows the area. Record reuse evidence before creating new helpers, components, services, contracts,
or patterns.

For API/DTO/schema/security/permission/business/clinical/billing/state-machine surfaces, produce a regression
map before planning slices.

## Step 3 — technical implementation plan
Draft a plan with:
- scope and non-scope;
- slice list in dependency order;
- per-slice file allowlist;
- per-slice validation commands;
- reuse evidence;
- regression map when triggered;
- explicit owner decisions consumed;
- unresolved blockers and paused slices.

The plan is technical only. It may recommend options, tradeoffs, and risk, but it must not choose new
business/design rules.

## Step 4 — owner approval gate
Stop before source edits and ask the owner to approve the technical plan. Source edits require:
- approved plan;
- selected worktree slug;
- approved slice;
- file allowlist;
- validation target.

## Step 5 — dev slices
Execute one approved slice at a time through `/mh-implement` or the existing implementation path. Keep edits
inside the selected worktree and allowlist. If the slice needs a new business/design decision, STOP and return
to the owner with an implementation discovery report from `spec-driven-development.md`.

For high-risk/shared changes, run `/impact-analysis` before editing. For FE-visible changes, include targeted
smoke/browser validation or owner-approved `robust-test targeted`.

## Step 6 — test and receipt
Run the validation commands from the approved plan. Record actual command results, not expected results.
Write a receipt/envelope that includes:
- handoff sources consumed;
- slices completed/skipped/blocked;
- changed files;
- validation commands/results;
- residual risk;
- next recommended workflow if blocked.

Validate workflow envelopes with `engine/workflows/_shared/validate-envelope.py` when an envelope is written.

## Boundaries
- Manual-only and owner-gated; never auto-route.
- Single-agent/manual by default; do not launch workers or external executors unless the owner explicitly approves a bounded slice.
- No BA discovery, BMAD-style discovery, or invented rules.
- No source edits before owner approval.
- No direct edits to `myhospital-fe/`, `myhospital-be/`, `worktrees/` outside the selected slug, or `main-brain/`.
- Generated FE DTO/client, `Constants.ts`, and BE migrations follow existing generated-code discipline.

## Status
Lifecycle `DRAFT`. First real run must remain owner-supervised and should produce eval evidence before any
promotion discussion.
