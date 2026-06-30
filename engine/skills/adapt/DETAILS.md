---
name: adapt
description: Owner-invoked semi-automated harness adaptation. Two modes: (A) RCA + fix a workflow whose machinery failed during a run (threshold same root-cause >=2); (B) design + build a new workflow for a repeated task pattern (threshold >=3, conflict-checked). POST-run only; six safety gates. Reuses mh-rca + mh-fix + harness_doctor + harness_backup. Trigger "/adapt", "adapt workflow X", "build a workflow for Y".
---

# adapt — owner-gated harness adaptation (Mode A fix / Mode B build)

> Full runbook. `SKILL.md` is the token-light discovery stub. Full contract + state machine:
> `engine/workflows/adapt/README.md`. Read it before the first run.

Owner-invoked. **Meta-workflow** — its `allowed_writes` are harness machinery
(`engine/workflows/<target>/**`, `engine/skills/<target>/**`, `engine/prompts/<target>*.md`,
`engine/REGISTRY.md`, `AGENTS.md`, `engine/HARNESS-GUIDE.md`), not product source. Six safety gates
apply (see §Gates). Owner approves every apply; harness never silently mutates mid-session.

## Fast-path NONE

There is no fast-path. Every adapt run goes through intake → RCA/design → plan → owner-gate →
fix/build → validate. Metawork is always T3 (harness safety) → every phase that mutates is
owner-confirm. Skipping gates is BLOCK.

## Coordinator discipline (blind, same as pm-orchestrator)

You are the blind coordinator. Per tick:
1. Re-read `00-adapt-state.md` (stateless-over-ledger — state lives in the file, not your context).
2. Resolve the next phase from the active mode (A or B).
3. Compute the phase's gate (every mutating phase = owner-confirm; intake/validate = auto).
4. Dispatch ONE worker from the main loop (Agent `mh-rca` for rca/design, `mh-fix` skill for
   fix/build). Never fan-out into a worker that re-fans-out (depth-1 only).
5. Record the worker's compact return blob + artifact path in the ledger. Author the ledger ONLY
   from blobs — never read worker output md / task source / rules.
6. Decide done (phase done_check satisfied) or next tick or stop.

You MAY read workflow *machinery* files (manifest/README/prompt) when verifying a blob against the
canon — those are harness metadata, not task content. The guard's blind-PM block exempts
`engine/workflows/**` (SRC_TREE is product source only).

## Mode A — adapt-on-failure

**Enter when:** owner invokes `/adapt mode=A target=<wf> root_cause_signature=<key> fail_count=<n>=2>`.

```text
1. intake     (auto)     — record failure_evidence path + root_cause_signature + fail_count>=2 in the ledger.
                           Verify POST-run: the target workflow's run is not active (no ledger status=RUNNING).
2. rca        (mh-rca, auto) — dispatch mh-rca with engine/prompts/adapt.md as runbook + the target workflow's
                           machinery paths. It returns 03-rca: root cause + verdict (DIRECT_PATCH | REDESIGN |
                           HUMAN_DECISION). Record the blob.
3. fix-plan   (OWNER)    — from the rca blob, author 04-adapt-plan: allowlist of workflow files to edit +
                           validation commands + rollback (snapshot id). Present to owner. Owner approves
                           before fix. If REDESIGN → stop BLOCKED (owner decides). If HUMAN_DECISION → stop
                           BLOCKED.
4. fix        (mh-fix, OWNER) — pin harness_backup snapshot; dispatch mh-fix with the allowlist + 04-adapt-plan.
                           It patches the workflow files + self-reviews its diff. Record the change blob +
                           snapshot id.
5. validate   (auto)     — run `python scripts/harness_doctor.py --strict` (must be green) + the target
                           workflow's self-test (must pass) + replay the failed run on synthetic input.
                           Record results. Done OR residual risk stated.
```

## Mode B — adapt-on-repetition

**Enter when:** owner invokes `/adapt mode=B proposed_workflow_name=<slug> pattern="<one-line>"` with
a `repetition_signal` (learning_recall note ≥3 | scanner_promotion bug_class ≥3 | agent-observed
task-type ≥3 with paths).

```text
1. intake     (auto)     — verify repetition_signal (≥3 occurrences cited with paths). Conflict-check:
                           run `python scripts/harness_doctor.py check_registry` + grep REGISTRY.md for
                           proposed_workflow_name. Refuse if duplicate → stop BLOCKED (suggest extending
                           the existing workflow). Record the signal + conflict-check result.
2. design     (mh-rca, OWNER) — dispatch mh-rca with engine/prompts/adapt.md (design section) + the
                           repetition evidence + registry + REGISTRY + HARNESS-GUIDE as context. It returns
                           design.md: manifest draft + README skeleton + recipe/phases + entry skill stub +
                           prompt skeleton + reuse map. Present to owner. Owner approves the design before
                           any file is created.
3. build      (mh-fix, OWNER) — pin harness_backup snapshot; dispatch mh-fix with the design allowlist
                           (engine/workflows/<new>/ + engine/skills/<new>/ + engine/prompts/<new>.md). It
                           creates the files + self-reviews its diff. Record the change blob + snapshot id.
4. wire       (OWNER)    — update engine/REGISTRY.md (add the new workflow row + skill row) + AGENTS.md §3
                           (add to owner-gated list) + engine/HARNESS-GUIDE.md §2/§6 (add the recipe row +
                           the location entry). Present to owner. Owner approves the wiring.
5. validate   (auto)     — run `python scripts/harness_doctor.py --strict` (registry must resolve,
                           governance clean) + the new workflow's self-test (must pass) + dry-run on a
                           synthetic input. Record results. Done OR residual risk stated.
```

## Gates (six, LOCKED)

1. **Owner-gated** — no auto-spawn. Owner invokes `/adapt` or approves a trigger report.
2. **POST-run** — intake verifies the target workflow's run is not active before entering.
3. **No-self-fix** — `allowed_writes` exclude `engine/workflows/adapt/**`, `engine/skills/adapt/**`,
   `engine/prompts/adapt.md`. A worker that tries to edit adapt's own files → guard block + stop BLOCKED.
4. **Pin-version** — before fix/build apply, run `python scripts/harness_backup.py --snapshot`,
   record the snapshot id in the ledger. Owner approves + commits before live. Rollback = snapshot.
5. **Threshold** — Mode A: `fail_count >= 2` same `root_cause_signature`. Mode B: ≥3 occurrences cited.
6. **Conflict-check** (Mode B) — `harness_doctor check_registry` + REGISTRY.md must not already list
   `proposed_workflow_name`. Refuse duplicate.

## State

```text
INTAKE → RCA_RUNNING (A) / DESIGN_RUNNING (B) → PLAN_READY → OWNER_GATE → FIX_RUNNING (A) / BUILD_RUNNING (B) →
  (B only) WIRE_RUNNING → VALIDATING → DONE | CAP_HIT | BLOCKED | PARKED
```

## Boundaries

- RCA/design (mh-rca) is read-only — it writes only `03-rca.md` / `design.md` under the adapt run dir.
- Fix/build (mh-fix) is allowlist-bounded — it touches only the files in `04-adapt-plan` / design.
- No edit to `adapt/` own files (gate 3). No edit to `main-brain/` (use `/promote`). No edit to
  product source (`myhospital-{fe,be}` / `worktrees/`) — adapt is metawork, not dev.
- No auto-commit. The owner commits after approving the diff.
- Honor the guard (myhospital_guard + drift_guard + subagent_prompt_guard).

## Reuse (no reinvention)

- RCA a workflow bug → `mh-rca` + `engine/prompts/adapt.md`
- Fix/build workflow files → `/mh-fix` (allowlist-bounded, self-review-diff)
- Detect repetition → `scripts/learning_recall.py` + `scripts/harness_scanner_promotion.py scan`
- Validate → `scripts/harness_doctor.py --strict`
- Backup/rollback → `scripts/harness_backup.py --snapshot`
- Owner approval gate → `engine/rules/preflight-confirmation.md` pattern

## Status

`auto_route_allowed: false` — owner-invoked only. First validation = a Mode A dry-run on a synthetic
workflow bug. Mode B first run = owner hand-carries a real repetition signal.
