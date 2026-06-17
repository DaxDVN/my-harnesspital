# engine/workflows/_shared/ — primitives every workflow composes

`_shared/` is **support, not a workflow** (the `_` prefix + no `manifest.json` means `harness_doctor.py
check_registry` skips it). It holds the small deterministic pieces the SDLC workflows reuse so they don't
each reinvent gates, receipts, or state. One source → no drift.

| file | purpose | used by |
|---|---|---|
| `envelope.schema.json` | the ONE receipt schema (A1) | all workflows that emit a round receipt |
| `validate-envelope.py` | validate a receipt + detect payload drift (`--payload`) | all (CI + skill close-out) |
| `gate-check.py` | deterministic SDD precondition gate (B) | technical-design · task-slicing · incremental-impl |
| `module-state.py` | per-module SDLC state on `00-module-state.md` (C9) | technical-design · task-slicing · incremental-impl |

Each script self-tests: `python engine/workflows/_shared/<script>.py --self-test` (run by `harness_doctor`).

## 1. Envelope — the shared receipt (A1)
Every workflow round writes a short `<artifact>.envelope.json` next to its payload. The orchestrator reads
the **envelope** (cheap) instead of the payload (expensive); `content_sha256` binds the two so a stale
receipt pointing at a changed payload is caught; `next_recommended_workflow` drives chaining. Required
fields + enums live in `envelope.schema.json`. Validate (and bind-check):

```bash
python engine/workflows/_shared/validate-envelope.py <round>/x.envelope.json --payload <round>/x.md
```

`progressive-test`'s own `.agentflow` envelope predates this and keeps its own validator; it is the **same
shape** — new workflows use this shared schema so there is one contract going forward.

## 2. Gate-check — gates that are code, not prose (B)
The "Gate FIRST" line used to be a sentence the orchestrator was trusted to honor. Now it is runnable:

```bash
python engine/workflows/_shared/gate-check.py <module> --require 02-requirements,03-ui --no-blocking 05-open-questions
```

Exit `0` = gate OPEN (proceed) · `2` = gate CLOSED → **STOP** (reasons printed) · `1` = usage error.
A required input that is missing or a template stub closes the gate; a `BLOCKING` / `BLOCKING_SCHEMA` /
`BLOCKING_API` line in the `--no-blocking` file closes it. Fail-**closed** for the gate, fail-**open** for
the tool (a crash never fabricates an OPEN gate). Tag blocking open-questions with `BLOCKING*` so the gate
can see them.

## 3. Module-state — the SDLC lifecycle (C9)
State lives on the file every session already reads first (`specs/<module>/00-module-state.md`) as ONE
machine-readable marker — no parallel store. GPT's `DOC_INTAKE → … → RELEASE` maps onto:

```
DISCOVERY → DESIGN → DESIGN_REVIEW → SLICED → IMPLEMENTING → VERIFYING → DONE
   side states: BLOCKED_BA · BLOCKED_DESIGN · BLOCKED_PLAN
```

```bash
python engine/workflows/_shared/module-state.py <module> --get
python engine/workflows/_shared/module-state.py <module> --set DESIGN --by technical-design
```

`--set` rewrites only the marker line; the rest of `00-module-state.md` stays human-authored. Writes
`specs/` only (never `myhospital-fe|be` / `worktrees`).

## 4. Fast-path (C8) — convention, not a script
A genuinely trivial + local change skips the heavy chain:
- trivial **bug** → `/bug-fix` fast-path → `/mh-fix` directly (skip RCA/Codex).
- trivial **feature change** → `/mh-implement` directly (skip technical-design → task-slicing).
- trivial change → **no** `/impact-analysis`.
"Trivial" = no API/schema/contract/business-rule/state-machine/billing/insurance/permission impact, no
multi-module blast, obvious root cause. Anything else takes the full pipeline. (Same split
`progressive-test`'s `classify` makes deterministically.)

## 5. Learning loop (C10) — convention, not a script
Each workflow closes by asking "did this surface a recurring gap?" If yes, capture it in `second-brain/`
(the open buffer) for later owner-gated `/promote` to `main-brain/` or graduation into a rule/skill.
Promote to the **cheapest** layer that prevents recurrence: guard/ESLint/ast-grep → `engine/rules/*` →
`deep-review/checklist.md` "Known bug-classes" → `second-brain/`.
