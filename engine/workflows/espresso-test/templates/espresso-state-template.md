# Espresso-Test State — `<scope>` run-NNN

> Coordinator-owned routing ledger. Authored ONLY from the compact return blobs of subagents.
> The coordinator does NOT read any review/findings/fix output md to fill this in.

```text
module      : <name>
base        : <branch/sha>
worktree    : <slug> (slot <n>)
tiers       : coordinator=<tier> review=<tier> fix=<tier>
round_cap   : <default 3>
fix_floor   : <default BLOCK+HIGH>
decision    : mode=<provisional|ask>  ask_window=<gate-only|gate+first-review|none>  floor=<irreversible-data/migration>
status      : RUNNING | CONVERGED | CONVERGED_WITH_PARKED | CAP_HIT | BLOCKED
```

## Pre-sweep (round 0 — owner answered once at invoke)

```text
questions asked : <N>
decision_preseed: <short id → answer list, or path>
```

## Round ledger

| round | review findings_path | BLOCK | HIGH | open_block_high | fixed | provisional | parked | residual_fixable | validation |
|---|---|---|---|---|---|---|---|---|---|
| 1 | docs/audit/<date>/<base>.round-1.md | 0 | 0 | 0 | — | — | — | — | — |

## Stop reason

```text
<one of:
  CONVERGED             — open_block_high == 0 (may carry N provisional decisions to confirm)
  CONVERGED_WITH_PARKED — shippable done; M findings PARKED (irreversible-data/migration) → route to owner
  CAP_HIT               — round cap reached with fixable BLOCK/HIGH still open → honest residual (split / new change)
  BLOCKED               — no worktree / environment gate failed>
```
