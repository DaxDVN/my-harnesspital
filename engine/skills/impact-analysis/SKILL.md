---
name: impact-analysis
description: Owner-invoked PREFLIGHT blast-radius analysis before a non-trivial change/fix/slice. READ-ONLY. Wraps CodeGraph (impact/affected) + layers BE/FE/API/business/test dimensions into a risk-assessment + a preflight verdict. Trigger "/impact-analysis", "preflight", "blast radius", "what breaks if".
---

# impact-analysis — preflight (CodeGraph-backed, READ-ONLY)

Owner-invoked. Answers **"if we change this, what else breaks?"** before any implementation. **Reuse
CodeGraph for dependency analysis — never hand-roll it.** Full contract: `engine/workflows/impact-analysis/README.md`.

## Input
The proposed change: target symbol(s)/file(s) — from a fix-plan, a `specs/<m>/07-08` design, a task, or a worktree diff.

## Steps (router; write artifacts under `engine/workflows/impact-analysis/rounds/<id>/`)
1. List the target symbols/files.
2. **Blast radius via CodeGraph** (run from the indexed repo — `myhospital-be` / `myhospital-fe` / the worktree): `codegraph impact <symbol>` + `codegraph affected <path>` per target. This is the dependency engine.
3. Layer the non-code dimensions onto the CodeGraph result: **BE** (entity/schema/migration/service/api/validation/permission/tests) · **FE** (route/component/form/api-client/hooks/cache/testid) · **API contract** (req/resp/error/back-compat/consumers) · **business** (rule/state-machine/audit) · **testing** (affected tests + E2E to rerun + regression candidates).
4. Write `01-risk-assessment.md` (payload) + `01-risk-assessment.envelope.json` (the **shared** schema `engine/workflows/_shared/envelope.schema.json`: `verdict`, `risk_level`, `summary_for_router`, `next_recommended_workflow`, `content_sha256`).
5. **Verdict:** `SAFE_TO_IMPLEMENT` · `REQUIRES_CODEX_REVIEW` · `REQUIRES_BA_DECISION` · `BLOCKED_INSUFFICIENT_CONTEXT`.
   **Risk:** LOW (local, no contract) · MEDIUM (several files/modules, shared state/API/validation) · HIGH (schema/API/business-rule/state-machine/billing/insurance/security/permission).

## Close-out (envelope + routing + fast-path)
- Validate the receipt: `python engine/workflows/_shared/validate-envelope.py rounds/<id>/01-risk-assessment.envelope.json --payload rounds/<id>/01-risk-assessment.md`.
- Set `next_recommended_workflow` from the verdict: `SAFE_TO_IMPLEMENT`→`incremental-impl`/`mh-fix` · `REQUIRES_CODEX_REVIEW`→`bug-fix`/`technical-design` (with the Codex gate) · `REQUIRES_BA_DECISION`→`technical-design` after `05` is answered · `BLOCKED_INSUFFICIENT_CONTEXT`→back to the caller (cannot proceed).
- **Fast-path (C8):** a clearly trivial + local change does NOT need impact-analysis at all — the caller skips straight to `/mh-fix` / `/mh-implement`. Use impact-analysis only for non-trivial / contract-bearing / HIGH-risk changes.
- **Learning loop:** if the same blast-radius surprise recurs (a hidden consumer CodeGraph keeps surfacing late) → `second-brain/` note for `/promote`.

## Boundaries
Read-only. Never implement, never rewrite the plan, never decide business behavior, never broad-scan unrelated to the change. Honor the guard.

## Status
Scaffold + wiring + contract; the **CodeGraph step is REAL**; the risk-framing quality is **UNPROVEN** — first real run = owner gate.
