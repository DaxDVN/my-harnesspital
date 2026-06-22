# dev-from-handoff — owner handoff to bounded development

Entry skill: `/dev-from-handoff`. Manual-only, owner-gated, lifecycle `DRAFT`.

## Purpose
Use this workflow when the owner supplies business/design handoff documents and wants development to start from
that handoff. The workflow is not a BA discovery process. It converts supplied material into a technical plan,
gets owner approval, then executes bounded slices with validation and a receipt.

## Non-goals
- Do not invent business, clinical, billing, permission, or design rules.
- Do not run BMAD-style requirement discovery or broad BA elicitation.
- Do not silently reinterpret mockups as business-rule authority.
- Do not start source edits before the owner approves the technical plan and a worktree/allowlist is known.

## Flow
1. Handoff intake: identify supplied documents, target module/worktree, scope, constraints, and explicit owner decisions.
2. Gap triage: classify gaps as blocker, assumption candidate, or technical constraint. Blockers go back to the owner.
3. Technical plan: produce a slice plan with file allowlists, reuse evidence, risk map, and validation per slice.
4. Owner approval gate: wait for explicit approval of the technical plan before source edits.
5. Dev slices: execute one approved slice at a time through `/mh-implement`; use CodeGraph first for source discovery.
6. Test and receipt: run targeted validation, capture actual commands/results, and write an envelope/receipt.

## Reused rules and workflows
- `spec-driven-development`: owner/BA truth outranks code; unresolved business gaps become open questions.
- `source-discovery`: CodeGraph first for source flows and blast radius, bounded exact search after.
- `ponytail` and `quality-gates`: smallest correct diff, reuse evidence, regression map, definition-of-done validation.
- `artifact-policy`: implementation plans and receipts go under the documented artifact paths.
- `/impact-analysis` for risky/shared changes; `robust-test targeted` for FE-visible receipt when the owner approves it.

Default execution is single-agent/manual. Do not launch workers or external executors from this workflow unless the
owner explicitly asks for a bounded worker for a specific approved slice.

## Stop conditions
- Missing or contradictory owner handoff for a business/design rule.
- Required worktree slug or source-edit package scope is absent.
- Technical plan is not explicitly owner-approved.
- Slice needs files outside the approved allowlist.
- Validation reveals a missing or contradicted business/design decision.

On stop, record the blocker and route back to the owner with options and technical impact only. Do not choose the
business/design rule on the owner's behalf.
