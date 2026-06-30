# Espresso-Test — owner-gated review→fix→re-review loop

`espresso-test` is an **agent-orchestrated convergence loop**. A thin coordinator agent drives the
`mh-review` ≤3-round cycle to completion *autonomously within one owner-approved session*: it runs a
review, routes the resulting findings file to a stronger fixer, then re-reviews — repeating until a round
comes back clean (0 BLOCK/HIGH OPEN) or the round cap is hit.

It does not invent a new review engine or a new fixer. It is pure orchestration on top of:

- **`deep-review`** (the review engine — nested fan-out, returns findings + verdict),
- **`mh-rca`** + **`/mh-fix`** + **`mh-implementer`** (the fix side — the same path `bug-fix` uses).

> Sibling to `robust-test`: same owner-gated, manual-only, artifact-backed discipline, but where
> `robust-test` *stops at a review-ready bundle for a human*, `espresso-test` *closes the loop itself*
> by feeding each review round into a fix round and re-reviewing.

## What It Is For

- Drive a finished module/changeset to **0 BLOCK/HIGH** without the owner hand-carrying each round.
- Keep the orchestrator **cheap and blind**: the coordinator holds the loop and the overall situation only —
  it never reads a finding, never opens source, never loads a rule. Reasoning lives in the subagents.
- Let the **review tier stay cheap** and the **fix tier go strong**, because the model split is per-role.

## Roles

Three roles. The split is the whole point — keep them disjoint.

| Role | Tier | May read | May write | Job |
|---|---|---|---|---|
| **Coordinator** | `coordinator_tier` (thin) | subagents' compact return blobs (incl. the pre-sweep question list) | only its own `00-espresso-state.md` ledger | spawn subagents, route file PATHS + status, **relay the round-0 question batch to the owner once**, decide stop |
| **Pre-sweep** | `review_tier` | BA doc (`specs/Tài liệu Nội trú.md`) + changeset scope | — | round 0: return the list of every foreseeable owner/business decision as questions (blob) |
| **Reviewer** | `review_tier` | review scope + rules + specs + **prior-round findings md** (warm-start) | findings md under `docs/audit/` | run `deep-review`, return `{findings_path, counts, open_block_high, verdict}` |
| **Fixer** | `fix_tier` (stronger) | findings md + `decision_preseed` + source + rules + BA doc | worktree source + findings-md statuses + `specs/<module>/{05-open-questions,06-decision-log}.md` | RCA + `mh-fix`, fan out `mh-implementer`, **resolve unanswered ambiguity via the provisional protocol (or PARK)**, validate, return compact status |

### Coordinator invariant (hard)

The coordinator is a router, not a reader. It MUST NOT:

- open, read, or summarize any review/findings/RCA/fix output `.md` (it only receives the **path string**
  and a **compact status blob** from each subagent);
- read or edit source code;
- load `engine/rules/*`, specs, checklists, or the findings schema;
- run the review or the fix itself.

It MAY write exactly one file — its own `00-espresso-state.md` routing ledger (round → review_path →
counts → fix_status → verdict). That ledger is authored *from the compact blobs it is handed*, not from
reading anyone's output md. If the coordinator ever needs to open an output md to make a decision, the
decision belongs to a subagent — re-route it, do not read it.

## Model Tiers (no baked model names)

The workflow file set contains **no model name**. Tiers are supplied at invoke time and default to the
session model when omitted:

```text
coordinator_tier : thin orchestrator (cheap)
review_tier      : runs deep-review
fix_tier         : RCA + fix + implementers (stronger)
```

Pick tiers per task. A typical split is a cheap coordinator + cheap reviewer + strong fixer, but that is an
owner choice at invoke, not a property of the workflow.

## Process

```text
0. Owner invokes espresso-test. Gate inputs: module/changeset, review base, ACTIVE worktree slug+slot,
   tiers, round cap (default 3), fix_floor (default BLOCK+HIGH), decision_mode (default provisional),
   ask_window (default gate-only), auto_decide_floor (default: irreversible-data/migration PARKS).
   No worktree -> STOP (fixes have nowhere legal to land).
1. ROUND-0 PRE-SWEEP — the ONLY owner-blocking step. Coordinator spawns the pre-sweep agent (review_tier):
   it reads the BA doc + changeset scope and returns every foreseeable business/owner decision as a question
   list. Coordinator presents that list to the owner as ONE batch (the gate — owner is present at invoke),
   collects answers into `decision_preseed`, then proceeds. From here the run is fire-and-forget and NEVER
   blocks to ask again. round = 1; prior_findings_path = none. Create run folder + 00-espresso-state.md.
2. REVIEW. Coordinator spawns the reviewer (review_tier) with {module, base, scope, round,
   prior_findings_path}. The REVIEWER (not the coordinator) reads prior_findings_path to warm-start and
   suppress re-raising REJECTED/PROVISIONAL findings. It runs deep-review (nested fan-out), writes
   docs/audit/<date>/<base>.round-<N>.md, returns ONLY
   {findings_path, counts:{BLOCK,HIGH,MED,LOW,NIT}, open_block_high, verdict}.
3. Coordinator records the blob in 00-espresso-state.md (no md read).
4. CONVERGE CHECK (count-based, not string). If open_block_high == 0 -> CONVERGED, go to 7.
5. FIX. Coordinator spawns the fixer (fix_tier) with {findings_path, worktree_slug, fix_floor,
   decision_preseed, decision_mode, auto_decide_floor}. Fixer reads ONLY that findings file (+ BA doc for
   provenance), runs RCA + mh-fix, fans out mh-implementer per cluster, self-reviews each diff (scanner +
   dimension recheck). For a business ambiguity NOT answered by decision_preseed:
     - if closing it needs an irreversible-data/migration op (hard-delete / non-backfilled migration /
       table reshape) -> PARK it (status PARKED-NEEDS-OWNER, log BLOCKING in 06-decision-log) and move on;
     - else -> PROVISIONAL: decide with a cited basis (BA page/section | safe-default | live exemplar),
       implement it, log DL-PROV-<n> in 06-decision-log + mirror the detailed question to 05-open-questions,
       mark the finding PROVISIONAL-FIXED.
   Validate, update findings statuses, return ONLY {fixed_ids, provisional_ids, parked_ids,
   residual_fixable_open, validation_summary, fix_refs, decision_log_path}.
6. round++; prior_findings_path = this round's findings_path. If round > round_cap -> go to 7 with an
   honest residual. Else go to 2. (No deadlock stop: ambiguity is resolved provisionally or parked, so it
   is never re-looped — the old DEFERRED-Q deadlock cannot occur.)
7. Coordinator writes 99-final-report.md from the blobs — including the consolidated PROVISIONAL list
   (clinical/billing/permission sorted first by risk-if-wrong) and the PARKED list — and reports to owner.
```

One **round** = review → (fix if needed) → re-review, matching `deep-review/protocol.md` §0. The loop is the
protocol's ≤3-round cycle made self-driving. The only owner interaction is the round-0 batch; everything after
is provisional-or-parked, so the loop never stalls waiting for an absent owner.

## Autonomy & Business Decisions

The whole point of espresso-test is to run while the owner is away. Two policies make it self-driving without
turning into a silent rule-inventing machine.

### Front-loaded asks (`ask_window`, default `gate-only`)

There is exactly **one** owner-blocking moment: the **round-0 pre-sweep batch**, presented at invoke while the
owner is present. The pre-sweep agent reads the BA doc + scope and surfaces every *foreseeable* business
decision; the owner answers once → `decision_preseed`. After that the run is **fire-and-forget** — it never
blocks to ask again. Anything that surfaces later (round-1+ review findings, fix-induced questions) is handled
by the provisional protocol, not a question. (Other windows exist as options: `gate+first-review` asks one
larger batch after round-1 review; `none` asks nothing and makes everything provisional from the start.)

> Why this matters: a mid-implementation question with the owner absent = a stuck run. `gate-only` guarantees
> the only place the loop can wait on a human is at the very start, when the human is there.

### Provisional decision protocol (`decision_mode`, default `provisional`)

A business ambiguity not answered by `decision_preseed` does **not** stop the loop. The fixer:

1. **Decides best-effort, with cited provenance** — `ba-source:<page/section of Tài liệu Nội trú.md>` OR a safe
   reversible default OR `exemplar:<file:line>`. Pure invention stays forbidden — provisional ≠ unfounded.
2. **Implements it** so the loop can converge.
3. **Logs it** to `specs/<module>/06-decision-log.md` with a real id `DL-PROV-<n>` (a real id → it passes the
   fabricated-authority gate; the id is real, the *answer* is unconfirmed), and mirrors the **detailed
   question** to `specs/<module>/05-open-questions.md`. Entry fields: question · options A/B/C + cost ·
   decision · basis/evidence · `risk_class` (clinical | billing | permission | other) · `risk_if_wrong` ·
   `confidence` · how-to-override · `status: PROVISIONAL`.
4. Marks the finding **`PROVISIONAL-FIXED`**.

At the end, the final report gathers **all** provisional decisions into one **"⚠ Confirm or correct"** batch,
clinical/billing/permission sorted to the top by `risk_if_wrong`. The owner reviews them later; where reality
differs they update the decision + the code. Because every fix lands as a **worktree diff reviewed before
merge**, a provisional clinical/billing/permission call is reversible — that is why those are allowed to be
provisional.

### Safety floor (`auto_decide_floor`, default = irreversible-data/migration)

One class is **never** silently guessed: when closing an ambiguous business finding would require an
**irreversible data op** — hard-delete, a non-backfilled migration, a table reshape that loses data — the fixer
**PARKS** it: status **`PARKED-NEEDS-OWNER`**, logged BLOCKING, **and the loop continues on every other
finding**. The dangerous guess is never shipped, but the run does not stall. Parked items are a dedicated
section in the final report. ("Review later and update" cannot undo deleted data — so the irreversible class
gets a hard stop on *that finding only*, not on the loop.)

## Stop Condition

Terminal states, decided by the coordinator from compact blobs — never from md.

- **CONVERGED:** a review round returns `open_block_high == 0` (0 BLOCK/HIGH in `OPEN`/`REOPENED`). Decide on
  the **count**, not the verdict string. MED/LOW/NIT remaining are backlog (protocol §6). May carry N flagged
  PROVISIONAL decisions for the owner to confirm.
- **CONVERGED_WITH_PARKED:** everything shippable is closed, but M findings are `PARKED-NEEDS-OWNER`
  (irreversible-data/migration ambiguity). Route to the owner — the loop never stalled on them, it parked and
  finished the rest.
- **Round cap:** default 3 (the protocol ceiling, not a quota — most modules close in 1–2). On exceeding the
  cap with **fixable** BLOCK/HIGH still open, **stop and tell the truth** per protocol §8: scope too large for
  one audit (split the module) or an architecture-wide fix (a new change, not a miss). Never loop forever;
  never claim clean.

There is no DEFERRED-Q deadlock state anymore: in `provisional` mode every business ambiguity becomes a
provisional fix or a parked finding, so it is resolved once and never re-looped. (In `decision_mode: ask` the
old behaviour returns — a business question blocks for the owner — use it only when the owner stays present.)

**Churn warning (why warm-start matters):** `deep-review` re-audits the worktree **fresh** each round — its
JS does not read prior rounds — so a REJECTED false positive or a PROVISIONAL finding can resurface. The
coordinator hands `prior_findings_path` to the next reviewer precisely so the *reviewer* reads the prior
REJECTED/PROVISIONAL markers and suppresses re-raising them. That is the only warm-start mechanism here.

## Cost

A round is heavy: `deep-review` fans out 7 dimensions × multi-pass + self-adversarial + adversarial verify
(dozens of subagent calls), and a fix round fans out one `mh-implementer` per cluster plus RCA + validation.
A 3-round run multiplies that. There is **no token-budget guard inside the loop** — the round cap is the only
hard ceiling, and the owner owns the cost decision at invoke. Keep `review_tier` cheap and reserve the strong
tier for `fix_tier`; the convergence check stops the moment `open_block_high == 0`, so a clean module costs one
review round, not three.

## Run Folder

```text
engine/workflows/espresso-test/runs/<scope>/run-NNN/
  00-espresso-state.md      # coordinator's routing ledger (round | review_path | counts | fix_status | verdict)
  99-final-report.md        # coordinator's owner-facing summary (built from compact blobs)
```

Review findings live where `deep-review` already writes them — `docs/audit/<YYYY-MM-DD>/<base>.round-<N>.md`
— and are referenced from the ledger by **path**, never copied into the run folder by the coordinator.
Fix diffs live in `worktrees/<slug>/{fe,be}`.

Templates: `templates/espresso-state-template.md`, `templates/final-report-template.md`.

## Hard Boundary & Safety

Inherits the full `AGENTS.md` Forbidden Actions list, plus:

- **Coordinator reads nothing** (see the invariant above). This is the defining constraint of this workflow.
- **All source edits inside `worktrees/<slug>/{fe,be}` only.** Never `myhospital-fe/`, `myhospital-be/`,
  generated DTO/client/`Constants.ts`, or EF migrations by hand. The fixer inherits `/mh-fix` safety in full.
- **Decision provenance is the only write outside the worktree:** the fixer may append to
  `specs/<module>/06-decision-log.md` (`DL-PROV-<n>` entries) and `specs/<module>/05-open-questions.md`. Every
  provisional business decision MUST be logged there before its finding is marked `PROVISIONAL-FIXED` — an
  unlogged provisional fix is a hard violation (silent rule invention).
- No `git commit` / `push` / `reset` / destructive checkout — leave diffs in the worktree for owner review.
- No DB/data mutation except the approved worktree-slot migration/data path (`make migrate-data`).
- Owner-gated, `manual_only`, `auto_route_allowed=false`. The coordinator may loop **review→fix→review**, but
  only the review and fix sub-steps that this runbook names — it must not self-launch any other workflow,
  external executor, or browser sweep.

## Execution Notes (harness constraints — read before first run)

This workflow is owner-gated (`auto_route_allowed: false`). Two real harness facts shape how the roles execute:

1. **`deep-review` is a Workflow-tool JS script**, and the Workflow tool runs in the main loop. The cleanest
   realization of the review step is therefore: the coordinator launches the reviewer, and the reviewer (or
   the coordinator on the reviewer's behalf) runs `deep-review`'s `workflow.js`; a small scribe then writes
   the findings md per `findings-schema.md` (Workflow scripts cannot write files). Either way the coordinator
   receives only `{findings_path, counts, verdict}` — it never sees finding bodies.
2. **A plain Agent-tool subagent may not be able to spawn further subagents.** The reviewer's "nested
   fan-out" is supplied by `deep-review` itself (its `parallel()` passes), and the fixer's implementer
   fan-out is supplied by `mh-implementer` invocations. If your runtime forbids subagent→subagent spawning,
   realize the fan-out at the layer that can (the Workflow tool for review; sequential/`parallel` implementer
   calls for fix) — the role contract above is unchanged; only the spawning layer moves.

**If you actually run this today:** given (1)+(2), the faithful realization is — the coordinator launches the
`deep-review` Workflow itself (Workflow tool, main loop) with a scribe writing the findings md, then spawns the
fixer subagent. That moves the *spawning layer* toward the deterministic variant, but the **role contract above
still holds**: whoever runs review returns only the compact blob, and the entity that decides stop reads no
finding body. Do **not** assume "coordinator spawns a reviewer subagent that itself runs a nested Workflow" is
executable until the runtime is confirmed to allow subagent→Workflow / subagent→subagent. This is the single
biggest unknown for this workflow — validate it on the first real run.

## Relationship To Existing Pieces

- **`deep-review`** — the review engine. `espresso-test` calls it once per round; it owns recall + findings md.
- **`mh-fix` / `mh-rca` / `mh-implementer`** — the fix side. `espresso-test` wires the same path `bug-fix`
  uses, but driven by a review findings file each round instead of a single bug.
- **`robust-test`** — sibling owner-gated test protocol. `robust-test` ends at a human-handoff bundle;
  `espresso-test` closes the audit→fix→audit loop itself.
- **`mh-review` (skill)** — the manual ≤3-round entry. `espresso-test` is its self-driving loop variant.
