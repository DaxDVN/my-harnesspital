# bug-fix (W3) — investigate → RCA → fix → verify

Entry skill: `/bug-fix` (`engine/skills/bug-fix/`). General debugging discipline for bugs from ANY source
(not only E2E). robust-test may recommend routing a confirmed E2E bug here after owner approval.

## Reuses (does NOT rebuild)
- **`mh-rca`** agent — the RCA step (read-only root-cause). It follows the **bug-trace playbook** (`docs/harness/plans/bug-trace-workflow-research-2026-06-16.md`): 3 governing facts (200≠success · master-data-in-IndexedDB · two caches) + the L1→L6 layered investigation + FE/BE/contract bisection. That playbook IS the body of step 2 (REPRODUCE: triage + bisection) and step 3 (RCA: L1–L6 + evidence + verdict).
- **`/mh-fix`** skill — the fix step (worktree, allowlist, self-review-diff).
- optionally **`/impact-analysis`** before a HIGH-risk fix; **codex** plugin for the fix-plan gate.

## Artifacts (per run, `rounds/<id>/`, payload + envelope each)
`01-bug-intake` · `02-reproduction` · `03-rca` · `04-fix-plan` · `05-codex-review` (if needed) ·
`06-approved-fix-plan` · `07-fix-implementation` · `08-fix-verification` · `09-regression-test-notes`.

## State machine
INTAKE → REPRODUCING → REPRODUCED → RCA_RUNNING → FIX_PLAN_READY →
CODEX_REVIEW_REQUIRED | DIRECT_FIX_APPROVED → FIX_APPROVED → IMPLEMENTING → VERIFYING →
VERIFIED_FIXED | FIX_FAILED | NEEDS_MORE_EVIDENCE | HUMAN_DECISION_REQUIRED.

## Relationship with robust-test
robust-test creates per-bug folders and a review-ready bundle. After owner approval, a confirmed bug can be
routed to bug-fix or mh-fix for implementation. bug-fix remains reusable outside browser testing
(QA/lead/user/log/build/review sources).

## Boundaries / status
RCA read-only; fixes only via `/mh-fix` in a worktree (never main fe/be); verification mandatory.
Scaffold + wiring + contract; reuses proven mh-rca + /mh-fix; end-to-end capability UNPROVEN → owner gate.
