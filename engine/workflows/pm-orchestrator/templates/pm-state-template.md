# PM Orchestrator State — `<scope>` run-NNN

> Coordinator-owned routing ledger. Authored ONLY from the compact return blobs of dispatched workers.
> The coordinator does NOT read any worker output md to fill this in. Re-read this file every tick and
> re-derive run state from it (stateless-over-ledger). Convention: `engine/rules/orchestrator-ledger.md`.

```text
task     : <one-line scope of this run>
run_dir  : engine/workflows/pm-orchestrator/runs/<scope>/run-NNN/
recipe   : <preset name: review | espresso | bugfix | feature | custom>
base     : <branch/sha for review/scope-freeze>
worktree : <slug> (slot <n>)   # required for any source-editing recipe; — for read-only
tiers    : coordinator=(sonnet,low)  per-phase=<phase:(model,effort), ... from scripts/tier_policy.json>
cap      : <phase/round cap>
status   : RUNNING | DONE | CAP_HIT | BLOCKED | PARKED
run_marker: .claude/.pm-run-active  (contents = this ledger path; created at start, removed at end)
```

## Gate log (owner-confirm decisions)

> One line per phase that fired the HARD owner-confirm gate (gate-by-risk: T2/T3 ∧
> clinical/billing/permission/migration/irreversible-data, OR an owner-gated workflow). Auto-dispatched phases
> are NOT listed here — they appear only in the phase rows below.

```text
<phase> : risk_tier=<T2|T3> risk_class=<...> → owner answered: <approve | revise | abort>  @ <when>
```

## Phase ledger

One row per phase the recipe defines. Filled from each phase's compact return blob (counts/paths/flags only).

| phase | status_blob | artifact_path | decision | done? |
|---|---|---|---|---|
| <name> | <tiny status, e.g. "3 BLOCK / 1 HIGH open" or "RCA: root cause X"> | <path to phase artifact md> | dispatch \| escalate \| gate-owner \| provisional \| park \| skip | yes/no |

- `status_blob` — the compact blob the worker returned (never a prose dump).
- `artifact_path` — pointer to the phase's real output (the coordinator does NOT open it).
- `decision` — what the coordinator did with that blob this tick.
- `done?` — whether the phase satisfied its `done_check`.

## Provisional / Parked (if any phase used the provisional-or-park protocol)

```text
provisional : <DL-PROV-<n> ids → specs/<module>/06-decision-log.md (confirm/correct later)>  | none
parked      : <finding ids — irreversible-data/migration deferred to owner>                   | none
```

## Stop reason

```text
<one of:
  DONE     — every phase done_check satisfied; nothing fixable open.
  CAP_HIT  — cap reached with fixable BLOCK/HIGH still open → honest residual (split / new change).
  BLOCKED  — no worktree / environment gate failed / required dependency missing.
  PARKED   — shippable done; M findings deferred to owner (irreversible-data / migration / business ambiguity).>

justification: <one line — why this terminal state>
```
