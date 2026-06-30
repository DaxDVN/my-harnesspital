# PM Orchestrator Run-State Ledger

The convention for the durable run-state ledger that a long-running PM orchestrator re-derives state from every
tick. Generalized from espresso's `00-espresso-state.md`. The ledger is how the coordinator stays **stateless
over a durable artifact**: it cannot forget across a long session because state lives in the file, not in
context.

## Core Rule

- **Re-read the ledger each tick.** Before deciding the next action, the coordinator re-reads the ledger and
  re-derives current state from it. Never trust in-context memory of run state.
- **Authored ONLY from compact return blobs.** The coordinator writes the ledger from the small status blobs
  subagents return — it NEVER reads worker output md, source, or rules to fill it in (blind coordinator).
- **Regenerable.** The ledger is reconstructable from the per-phase artifact paths it points at. If lost, it can
  be rebuilt from the artifacts (model the `learning_recall` `INDEX.md` rebuild pattern). It carries pointers and
  decisions, not copied content.
- **Path:** `engine/workflows/pm-orchestrator/runs/<scope>/run-NNN/00-pm-state.md`.
- **MUST NOT live under `main-brain/`** — that path is guard-blocked for agent writes. A workflow engine cannot
  write files either (a scribe step writes the md; the engine returns data only).

## Header

```text
task     : <one-line scope of this run>
run_dir  : engine/workflows/pm-orchestrator/runs/<scope>/run-NNN/
recipe   : <phase-recipe preset name, e.g. review-fix-rereview | review-only | custom>
tiers    : coordinator=<(model,effort)> per-phase=<phase:(model,effort), ...>
status   : RUNNING | DONE | CAP_HIT | BLOCKED | PARKED
```

## Per-Phase Row Table

One row per phase the recipe defines. Filled from each phase's compact return blob.

```text
| phase | status_blob | artifact_path | decision | done? |
|---|---|---|---|---|
| <name> | <tiny status, e.g. "3 BLOCK / 1 HIGH open"> | <path to phase artifact md> | <dispatch | escalate | gate-owner | provisional | park | skip> | yes/no |
```

- `status_blob` — the compact blob the subagent returned (counts/flags only, never prose dumps).
- `artifact_path` — pointer to the phase's real output (the coordinator does NOT open it).
- `decision` — what the coordinator did with that blob this tick.
- `done?` — whether the phase satisfied its `done_check`.

## Stop Enum

The run terminates with exactly one of:

```text
DONE     — every phase done_check satisfied; nothing fixable open.
CAP_HIT  — round/phase cap reached with fixable work still open → honest residual (split / new change).
BLOCKED  — no worktree / environment gate failed / required dependency missing.
PARKED   — shippable done, but M findings deferred to owner (irreversible-data / migration / business ambiguity).
```

Record the stop reason in a short `## Stop reason` block with the one-line justification.

## Anti-Forget Coupling

While a run is active, the PM writes the ledger path into `.claude/.pm-run-active`; the
`orchestrator_invariants.py` UserPromptSubmit hook then re-injects the invariants (including "re-derive state from
this ledger each tick") on every turn. The PM removes the marker at run end. See
`engine/rules/context-manifest.md` for how phase inputs are passed to workers by reference.
