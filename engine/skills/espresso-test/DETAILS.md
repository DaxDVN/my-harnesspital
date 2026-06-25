# espresso-test

Authoritative workflow doc: `engine/workflows/espresso-test/README.md`.

## Required Behavior

- Owner invocation is required (`manual_only`, `auto_route_allowed=false`).
- Gate inputs before round 1: target module/changeset, review base, **active worktree slug+slot**, model
  tiers (`coordinator_tier`/`review_tier`/`fix_tier`), round cap (default 3), `fix_floor` (default
  BLOCK+HIGH), `decision_mode` (default `provisional`), `ask_window` (default `gate-only`),
  `auto_decide_floor` (default: irreversible-data/migration PARKS). No worktree → STOP.
- **Round 0 — pre-sweep (the ONLY owner-blocking step):** spawn the pre-sweep agent (`review_tier`) → it reads
  the BA doc + scope and returns a question list of every foreseeable business/owner decision. Present it to
  the owner as ONE batch (owner is present at invoke), collect answers into `decision_preseed`. After this the
  run NEVER blocks to ask again.
- You are the **coordinator**. Per round:
  1. spawn the **reviewer** (`review_tier`) with `prior_findings_path` → it warm-starts / suppresses
     REJECTED+PROVISIONAL re-raises, runs `deep-review`, writes findings md to `docs/audit/`, returns ONLY
     `{findings_path, counts, open_block_high, verdict}`;
  2. record the blob in `00-espresso-state.md` (do NOT open the md);
  3. **CONVERGE** (count-based, not string): if `open_block_high == 0` → stop (CONVERGED);
  4. else spawn the **fixer** (`fix_tier`) with `{findings_path, worktree_slug, fix_floor, decision_preseed,
     decision_mode, auto_decide_floor}` → RCA (`mh-rca`) + `/mh-fix` + `mh-implementer` fan-out. For a business
     ambiguity not in `decision_preseed`: **PARK** if closing it needs an irreversible-data/migration op (status
     `PARKED-NEEDS-OWNER`, log BLOCKING), else **PROVISIONAL** (decide with cited basis, implement, log
     `DL-PROV-<n>` in `06-decision-log` + mirror question to `05-open-questions`, status `PROVISIONAL-FIXED`).
     Returns ONLY `{fixed_ids, provisional_ids, parked_ids, residual_fixable_open, validation_summary,
     fix_refs, decision_log_path}`;
  5. `round++`; set `prior_findings_path` = this round's findings path; if `round > cap` → stop with honest
     residual; else re-review. (No deadlock stop — ambiguity is provisional-fixed or parked, never re-looped.)
- Coordinator MUST NOT read any review/findings/fix output md, load rules, or read/edit source. It writes only
  its own `00-espresso-state.md` ledger + `99-final-report.md`, authored from the compact blobs. Its one
  owner-facing act is relaying the round-0 question batch.
- All source edits go inside `worktrees/<slug>/{fe,be}` only (fixer inherits `/mh-fix` safety in full). The
  fixer's only out-of-worktree writes are `specs/<module>/{05-open-questions,06-decision-log}.md`; a provisional
  fix with no logged `DL-PROV` entry is a hard violation.
- No `git commit/push/reset`. No self-launching any workflow/executor/browser beyond the named review+fix steps.
- Tiers are passed at invoke — never bake a model name into the workflow.

## Output Contract

Final chat response should be compact:

```text
Run folder: <path>
Result: CONVERGED | CONVERGED_WITH_PARKED | CAP_HIT | BLOCKED
Rounds: <N>/<cap>
Per round: round-N → open_block_high + fixed/provisional/parked
Worktree: <slug> (diffs left for owner review)
⚠ Provisional decisions: <N> → confirm/correct (clinical/billing/permission first) · log: specs/<module>/06-decision-log.md
Parked (need owner): <M ids — irreversible-data/migration | none>
Residual OPEN (fixable): <ids + severities | none>
Next step: <exact options>
```
