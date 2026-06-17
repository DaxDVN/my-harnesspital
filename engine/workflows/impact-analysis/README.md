# impact-analysis (W10) — preflight blast-radius

Entry skill: `/impact-analysis` (`engine/skills/impact-analysis/`). Read-only, cross-cutting.

## Reuses (does NOT rebuild)
- **CodeGraph** `codegraph impact <symbol>` / `codegraph affected <path>` = the dependency/blast-radius engine.
- This workflow only ADDS: the BE/FE/API/business/test framing + the preflight verdict envelope.

## Artifacts (per run, `rounds/<id>/`)
- `01-risk-assessment.md` (+ `.envelope.json`) — affected-surface map + risk_level + verdict.

## Verdict / gate
`SAFE_TO_IMPLEMENT` → proceed · `REQUIRES_CODEX_REVIEW` → route to Codex before change · `REQUIRES_BA_DECISION`
→ `specs/<m>/05-open-questions.md` · `BLOCKED_INSUFFICIENT_CONTEXT` → stop, gather context.

## Cross-cutting callers
`bug-fix` (before a risky fix) · `technical-design` (before design approval) · `task-slicing` (before a slice) · `deep-review` (when a finding suggests hidden impact).

## Status
Scaffold + contract; CodeGraph step REAL; risk-framing quality UNPROVEN → first real run = owner gate.
