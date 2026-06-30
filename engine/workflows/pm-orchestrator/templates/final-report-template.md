# PM Orchestrator Final Report — `<scope>` (`<recipe>`)

> Owner-facing summary. Built by the coordinator from compact worker blobs + its own `00-pm-state.md` ledger.
> Not a re-read of any worker output md.

```text
Result    : DONE | CAP_HIT | BLOCKED | PARKED
Recipe    : <preset name | custom>  (phases: <phase, phase, ...>)
Phases run: <N> / <cap>
Worktree  : <slug> (slot <n>) — diffs left for owner review, not committed   | — (read-only run)
Tiers     : coordinator=(sonnet,low) · per-phase=<phase:(model,effort), ...>
Gates     : <N owner-confirm gates fired | none>
```

## Per-phase trail

| phase | dispatch | status_blob | artifact path | gate | done? |
|---|---|---|---|---|---|
| <name> | <deep-review \| mh-rca \| mh-fix \| mh-implement \| espresso-test \| scribe> | <counts/flags> | <path> | auto \| owner-confirm | yes/no |

## ⚠ Provisional decisions — CONFIRM OR CORRECT

> The agent decided these on a documented assumption mid-run (not at a gate). Review each; where reality differs,
> update the decision-log entry + the worktree code. Sorted clinical/billing/permission first by risk-if-wrong.
> Full entries: `specs/<module>/06-decision-log.md` · questions mirrored to `05-open-questions.md`.

| id | risk_class | phase/finding | question (short) | decision taken | basis | confidence | risk if wrong | how to override |
|---|---|---|---|---|---|---|---|---|
| DL-PROV-1 | clinical/billing/permission/migration/other | <fid> | <q> | <chosen> | ba:pg/§ \| safe-default \| exemplar:file:line | LOW/MED/HIGH | <reversible? impact> | <what to change> |

## Parked — NEED OWNER BEFORE PROCEEDING (not shipped)

> Irreversible-data/migration business ambiguities the agent refused to guess. The run continued on everything
> else; these are left OPEN.

| id | phase/finding | what it needs (hard-delete / migration / reshape) | the question | why parked (irreversible) |
|---|---|---|---|---|
| <fid> | <title> | <op> | <q> | data loss not undoable |

## Residual (if not DONE)

```text
Still OPEN (fixable) : <phase/finding ids + severities>
Why not closed       : scope-too-big-split | architecture-wide-change | environment-blocked | other
Recommended path     : <split scope / new change request / fix environment / owner decision>
```

## Next step

```text
<confirm/correct provisional decisions | decide the parked items | merge-ready review of worktree diffs |
 split + re-run | fix environment + resume | nothing — task DONE>
```
