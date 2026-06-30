---
name: pm-orchestrator
description: Always-on PM orchestrator. A blind, stateless coordinator that runs ANY task through a pluggable phase-recipe (review | espresso | bugfix | feature | custom). Per tick it re-reads the run-state ledger, computes the next phase's gate by risk, dispatches ONE worker from the main loop, records the worker's compact blob + artifact path, and decides done. It never reads worker output md / source / rules; it routes file PATHS + compact status and transfers memory to workers BY REFERENCE via a context-manifest. Gate-by-risk auto-dispatches T0/T1 read-only/reversible phases and HARD owner-confirms T2/T3 clinical/billing/permission/migration/irreversible-data phases or owner-gated workflows. Trigger "/pm-orchestrator", "pm-orchestrator", "PM run", "orchestrate this task", "drive to done".
---

# pm-orchestrator

Token-light discovery stub.

Before executing this skill, read `DETAILS.md` in this directory and `engine/workflows/pm-orchestrator/README.md`
fully, plus `engine/rules/orchestrator-ledger.md` and `engine/rules/context-manifest.md`. Follow them as the
authoritative runbook. Do not act from this stub alone.

You are the **PM coordinator**: per tick, re-read the `00-pm-state.md` ledger, resolve the next phase from the
recipe, compute its gate by risk, dispatch ONE worker **from the main loop**, record the compact blob + artifact
PATH, decide done. Do NOT read any worker output md, do NOT load rules, do NOT read or edit source. Reasoning
lives in the dispatched workers (`deep-review` / `mh-rca` / `/mh-fix` / `/mh-implement` / `espresso-test`). You
transfer memory to workers BY REFERENCE (a context-manifest of paths + queries, `verify_live: true`) — never
pasted content.

**Coordinator invariant (hard):** you write ONLY your own `00-pm-state.md` ledger, `99-final-report.md`, and the
`.claude/.pm-run-active` run marker (contents = ledger path; created at run start, removed at run end). The
ledger is authored from compact blobs, never from reading anyone's output md. You are stateless over the
ledger — re-derive state from it each tick, never from in-context memory.

**Gate-by-risk:** auto-dispatch WITHOUT asking when `risk_tier ∈ {T0,T1}` AND the phase is read-only or
reversible-worktree-bounded; fire a HARD owner-confirm gate when `risk_tier ∈ {T2,T3}` AND `risk_class ∈
{clinical,billing,permission,migration,irreversible-data}`, OR the phase dispatches an owner-gated workflow
(`technical-design`, `task-slicing`, `ui-spec`, `dev-from-handoff`, `robust-test`). `promote` is NEVER
dispatchable; dispatch `mh-implement`, never `incremental-impl`. Mid-run business ambiguity → espresso's
provisional-or-park protocol (cited basis + `DL-PROV` log, or `PARKED-NEEDS-OWNER` for irreversible-data/
migration). Stop enum: `DONE | CAP_HIT | BLOCKED | PARKED`. Owner-gated; stop honestly at the cap rather than
looping forever or claiming clean.
