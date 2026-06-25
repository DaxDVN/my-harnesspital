# Espresso-Test Final Report — `<module>` (`<base>`)

> Owner-facing summary. Built by the coordinator from compact subagent blobs + its own ledger.
> Not a re-read of any output md.

```text
Result        : CONVERGED | CONVERGED_WITH_PARKED | CAP_HIT | BLOCKED
Rounds run    : <N> / <cap>
Worktree      : <slug> (slot <n>) — diffs left for owner review, not committed
Tiers         : coordinator=<tier> review=<tier> fix=<tier>
Decision mode : <provisional|ask> · ask_window=<gate-only|...> · floor=<irreversible-data/migration>
```

## Per-round trail

| round | review md | open_block_high | fixed | provisional | parked | residual fixable | validation |
|---|---|---|---|---|---|---|---|
| 1 | <path> | <n> | <ids> | <ids> | <ids> | <ids> | <scanner/build/typecheck summary> |

## ⚠ Provisional business decisions — CONFIRM OR CORRECT

> The agent decided these on a documented assumption while you were away. Review each; where reality differs,
> update the decision-log entry + the worktree code. Sorted clinical/billing/permission first by risk-if-wrong.
> Full entries: `specs/<module>/06-decision-log.md` · questions mirrored to `05-open-questions.md`.

| id | risk_class | finding | question (short) | decision taken | basis | confidence | risk if wrong | how to override |
|---|---|---|---|---|---|---|---|---|
| DL-PROV-1 | clinical/billing/permission/other | <fid> | <q> | <chosen> | ba:pg/§ \| safe-default \| exemplar:file:line | LOW/MED/HIGH | <reversible? impact> | <what to change> |

## Parked — NEED OWNER BEFORE PROCEEDING (not shipped)

> Irreversible-data/migration business ambiguities the agent refused to guess. The loop continued on
> everything else; these are left OPEN.

| id | finding | what it needs (hard-delete / migration / reshape) | the question | why parked (irreversible) |
|---|---|---|---|---|
| <fid> | <title> | <op> | <q> | data loss not undoable |

## Residual (if not converged)

```text
Still OPEN/REOPENED (fixable) : <finding ids + severities>
Why not closed               : scope-too-big-split | architecture-wide-change | other
Recommended path             : <split module / new change request / owner decision>
```

## Next step

```text
<confirm/correct provisional decisions | decide the parked items | merge-ready review of worktree diffs |
 split + re-run | nothing — module ready (provisionals stand until you say otherwise)>
```
