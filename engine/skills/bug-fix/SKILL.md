---
name: bug-fix
description: Owner-invoked bug investigation -> RCA -> fix -> verify, from ANY source (QA / lead / user / log / failed build/test / code-review / E2E). REUSES the mh-rca agent (RCA) + the /mh-fix skill (the fix). Envelope + state-machine driven; the only code edits happen via /mh-fix in a worktree. Trigger "/bug-fix", "investigate bug", "RCA this", "fix bug from <source>".
---

# bug-fix — investigate → RCA → fix → verify (reuse-first)

Owner-invoked. Turns a symptom from ANY source into: reproduction → evidence → root cause → fix-plan →
approved fix → verification. **Reuses `mh-rca` (RCA) + `/mh-fix` (fix) — does NOT duplicate them.** Full
contract + state machine: `engine/workflows/bug-fix/README.md`. (progressive-test's E2E bugs route HERE.)

## Fast-path FIRST (C8 — trivial bug skips the pipeline)
If the bug is **unambiguous + local + low-risk** (typo, label/i18n, obvious off-by-one, wrong constant, missing null-guard — touching **no** API/schema/contract/business-rule/state-machine/billing/insurance/permission, no multi-module blast) → SKIP intake→RCA→Codex: go straight to **`/mh-fix`** in a worktree with a one-line fix-plan, then VERIFY. If anything is unclear, contract-bearing, or the root cause is non-obvious → take the full loop below. (Same TRIVIAL vs NEEDS_RCA split progressive-test's `classify` makes deterministically.)

## Loop (router; artifacts under `engine/workflows/bug-fix/rounds/<id>/`, each payload + envelope — shared schema `engine/workflows/_shared/envelope.schema.json`, validate with `_shared/validate-envelope.py`)
1. **INTAKE** → normalize the report → `01-bug-intake` (id/source/module/observed/expected/env/severity/evidence). No inference, no fix.
2. **REPRODUCE** → by type: FE→agent-browser (or progressive-test); BE/API→the failing request/test; build/test→the exact command; review→the referenced diff. Use the playbook's **triage + FE/BE/contract bisection** here. → `02-reproduction` (REPRODUCED|NOT_REPRODUCED|PARTIAL|BLOCKED). Gate: not-reproduced + thin evidence → `NEEDS_MORE_EVIDENCE`.
3. **RCA** → spawn the **`mh-rca`** agent (Agent tool, `subagent_type: mh-rca`) with the intake+repro paths → it writes `03-rca` (root cause + verdict DIRECT_PATCH|CODEX_REQUIRED|MORE_EVIDENCE|HUMAN_DECISION). **mh-rca follows the bug-trace playbook** (3 governing facts incl. *200≠success* · L1→L6 layered investigation · FE/BE/contract bisection — `docs/harness/plans/bug-trace-workflow-research-2026-06-16.md`). You validate + envelope.
4. **FIX-PLAN** → `04-fix-plan` (allowlist / forbidden / steps / validation / regression scenario / rollback / requires-Codex?). Codex required if: API/schema/data-contract, business rule, multi-module, medium/low RCA confidence, shared util/state, regression-after-recent-change. (Optionally run `/impact-analysis` first if HIGH-risk.)
5. **CODEX gate** (if required) → codex plugin reviews `04` → APPROVE | APPROVE_WITH_CHANGES | REJECT. REJECT → mh-rca revises (max 2) → else HUMAN_DECISION.
6. **FIX** → **`/mh-fix`** with the approved fix-plan, **in a worktree** (never main fe/be). It applies only the allowlist + self-reviews its diff → `07-fix-implementation`. **Boundary gate (deterministic):** `git -C worktrees/<slug>/<fe|be> diff --name-only <base> | python engine/workflows/_shared/allowlist-check.py --stdin --allow '<04 fix-plan allowlist>' --forbid '**/generated-*'` → **exit 2 = the fix touched files OUTSIDE the plan → STOP, revert the overreach, re-scope** (never accept a fix wider than its plan).
7. **VERIFY** → run the plan's validation (unit/integration/typecheck/build/API/agent-browser/manual rerun) → `08-fix-verification` (is the original bug fixed? regression test added?). FAIL → back to RCA or new round.

## State
INTAKE → REPRODUCING → REPRODUCED → RCA_RUNNING → FIX_PLAN_READY → CODEX_REVIEW_REQUIRED|DIRECT_FIX_APPROVED → FIX_APPROVED → IMPLEMENTING → VERIFYING → VERIFIED_FIXED | FIX_FAILED | NEEDS_MORE_EVIDENCE | HUMAN_DECISION_REQUIRED.

## Boundaries
RCA never edits (mh-rca is read-only). Fix only via `/mh-fix` in a worktree, allowlist-bounded. No symptom-fix without root cause; no scope-creep; verification mandatory. Honor the guard.

## Learning loop (feeds review recall)
After VERIFY, if the root cause is a **recurring bug-class** (seen before), promote it to the cheapest layer that would have caught it: guard / ESLint / ast-grep (deterministic) → `engine/rules/*` (convention) → `engine/workflows/deep-review/checklist.md` "Known bug-classes" → `second-brain/` for `/promote`. This is how one fixed bug stops the whole class — the closed loop between `bug-fix` and `deep-review`.

## Status
Scaffold + wiring + contract; reuses proven mh-rca + /mh-fix; full investigate→fix→verify capability UNPROVEN end-to-end → first real run = owner gate.
