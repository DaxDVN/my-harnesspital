---
name: incremental-impl
description: INTERNAL per-task executor invoked BY the dev flow (/mh-implement's fe-flow / BE flow) to run ONE approved task/slice from specs/<module>/10-plan.md — worktree + file-allowlist + validation + self-review-diff + implementation envelope; on plan-mismatch STOPs. The owner does NOT invoke it standalone in normal use (the fast-path /mh-implement covers trivial work directly). Trigger "/incremental-impl", "implement slice", "do task <id>".
---

# incremental-impl (W9) — the per-task executor (called BY the dev flow)

> Full runbook. `SKILL.md` is the token-light discovery stub for this skill.

**Role:** the **internal per-task executor** of the dev flow — `/mh-implement` (its **`fe-flow.md`** FE path or
its BE B-flow) calls this **once per approved task** to carry that task's file-allowlist, validation, and
`PLAN_MISMATCH`→STOP envelope. **The owner does NOT invoke it standalone in normal use** — drive features via
`/mh-implement` (or the SDD chain `/technical-design → /task-slicing → /mh-implement`); for genuinely trivial
work the **fast-path `/mh-implement`** (feature) or `/mh-fix` (bug) is the direct entry. This wrapper exists to
make a per-task execution **deterministic and bounded** when there is a real `10-plan.md` task to honor.

**Input:** ONE approved task from `specs/<module>/10-plan.md` (allowlist + steps + validation).
**It does NOT reimplement implementation logic — it WRAPS `/mh-implement`.** Full contract: `engine/workflows/incremental-impl/README.md`.

## STEP 0 — input gate (deterministic; run BEFORE implementing)
```bash
python engine/workflows/_shared/gate-check.py <module> --require 10-plan
```
Exit `2` = **STOP `REQUIRES_TASK_SLICING`** (no approved plan). Then confirm the named task id exists in `10-plan.md` **and** carries a non-empty allowlist + validation; if not → **STOP**, route back to `/task-slicing` (a missing allowlist is a slicing defect, not something to improvise). Gate open → `module-state.py <module> --set IMPLEMENTING --by incremental-impl`.

## Steps (envelope artifacts under `engine/workflows/incremental-impl/rounds/<id>/` — get `<id>` via `python engine/workflows/_shared/run-init.py incremental-impl` → run-NNN + `00-run-meta` + `logs/`, per `_shared/run-memory.md`)
1. Read the ONE task (id · allowlist · steps · validation) from `10-plan.md`. Refuse a vague/whole-module task — that's a task-slicing failure.
2. (optional) `/impact-analysis` if the task is HIGH-risk.
3. **Delegate to `/mh-implement`** in the worktree — it already does convention preflight, reuse discovery, allowlist-bounded edits, validation (`tsc`/`eslint`/`mh_scan`), and self-review-diff. Do NOT duplicate that.
4. Capture `01-task-implementation` + `02-validation` (+ `03-e2e` if FE-visible) + a completion envelope.
5. **PLAN_MISMATCH** (file missing · code differs from `01-source-audit` · allowlist insufficient · needs an API not in `08` · validation reveals a missing design decision) → **STOP**: write the mismatch + an envelope with `status: PLAN_MISMATCH` and `next_recommended_workflow: task-slicing` (or `technical-design`), set `module-state.py <module> --set BLOCKED_PLAN`, and route back. **Do NOT improvise** a fix outside the allowlist.
6. If FE-visible → run owner-approved `robust-test targeted` or a targeted browser/manual scenario; a bug → `/bug-fix`.

## Completion criteria
**Boundary gate (deterministic — run it, don't trust the worker):** `git -C worktrees/<slug>/<fe|be> diff --name-only <base> | python engine/workflows/_shared/allowlist-check.py --stdin --allow '<task files-allowed globs>' --forbid '**/generated-*'` → **exit 2 = the executor edited outside the task allowlist → STOP, revert the out-of-scope edits, `PLAN_MISMATCH`** (overreach = context-rot + scope-creep; never accept it). Then: code matches the allowlist · validation ran (or documented why not) · report exists · FE-visible → E2E exists · no unresolved plan-mismatch.

## Boundaries
Only `/mh-implement` edits — in a **worktree**, allowlist-bounded; never main `myhospital-fe|be`; never change schema/API/business beyond the task; never reinterpret the design.

## Close-out (envelope + state + learning)
1. Write `rounds/<id>/task-implementation.envelope.json` (shared schema, `artifact_type: task-implementation`) → validate with the shared validator.
2. State: on pass `module-state.py <module> --set VERIFYING`; when the slice's tasks are all verified → `--set DONE`. On mismatch the STEP-5 `BLOCKED_PLAN` stands until re-sliced.
3. **Fast-path (C8):** a genuinely trivial change with no design impact does NOT need the W7→W8→W9 chain — the owner goes to `/mh-implement` (feature) or `/mh-fix` (bug) directly; the dev flow does not call this executor for it. This wrapper is invoked (by the dev flow) only when there is a real `10-plan.md` task to honor.
4. **Learning loop:** a plan-mismatch root cause that recurs (slicing keeps under-scoping allowlists, design keeps omitting an API) → `second-brain/` note for `/promote`.

## Status
Thin WRAPPER over the proven `/mh-implement`, used as its **per-task executor** (not a standalone owner entry); the wrapper wiring (task→implement→envelope→mismatch-stop) is new + UNPROVEN → first real run = owner gate. **Input-dependency: an approved `specs/<module>/10-plan.md` (from `/task-slicing`).**
