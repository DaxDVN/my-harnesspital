# Harness v2 P5 Consolidation Plan - 2026-06-20

P5 goal: reduce workflow surface area only when evidence proves a replacement preserves quality.

## Decision

No workflow is deprecated in P5.

Reason: P4 eval ledger exists, but there are not enough real eval artifacts yet to prove that any workflow
can be safely removed, aliased, or made default. P5 therefore adds governance and scanner support rather
than destructive consolidation.

## Current Taxonomy

| workflow | class | status | P5 decision |
|---|---|---|---|
| `bug-fix` | workflow | DRAFT | keep; full investigate/RCA/fix/verify path |
| `deep-review` | workflow | LAB | keep; high-risk/merge review |
| `impact-analysis` | advisory | DRAFT | keep; preflight blast-radius |
| `incremental-impl` | internal | DRAFT | keep; internal per-slice executor |
| `progressive-test` | internal | LAB | keep; compatibility-protected fix-first E2E loop |
| `super-test` | workflow | LAB | keep; public harvest-first module test |
| `task-slicing` | workflow | DRAFT | keep; large-module planning |
| `technical-design` | workflow | DRAFT | keep; API-contract design |
| `ui-spec` | workflow | DRAFT | keep; UI reuse/spec generation |

## Consolidation Candidates Requiring Evidence

### CAND-001 - `mh-fix` skill and `bug-fix` workflow

- Hypothesis: direct patch and full RCA path may be confusing as public entries.
- Keep for now: they serve different risk tiers.
- Required evidence: evals showing which route handles T0/T1/T2 bug classes with fewer rounds and equal validation quality.

### CAND-002 - `progressive-test` and `super-test`

- Hypothesis: both use browser/executor artifacts and can look overlapping.
- Keep for now: `progressive-test` is fix-first/internal; `super-test` is harvest-first/public.
- Required evidence: real super-test harvest + repair evals and progressive-test fix-loop evals across the same module class.

### CAND-003 - `task-slicing`, `incremental-impl`, and `mh-implement`

- Hypothesis: too many implementation-related entry points can cause routing ambiguity.
- Keep for now: `task-slicing` plans, `incremental-impl` executes one approved slice, `mh-implement` remains the public feature skill.
- Required evidence: router misroute logs or evals showing repeated unnecessary task-slicing for small features.

### CAND-004 - `technical-design` and `ui-spec`

- Hypothesis: both are design/spec workflows.
- Keep for now: API contract and UI reuse-map are different quality gates.
- Required evidence: evals showing one workflow can consume the other's output without losing API/UI quality.

## P5 Acceptance Policy

A later consolidation patch may deprecate a workflow only if:

- replacement workflow is named;
- compatibility alias/path exists;
- eval artifact proves quality/cost tradeoff;
- doctor governance scan is clean;
- router handles the old name safely.

Until then, workflow count is optimized by routing and lifecycle gates, not deletion.
