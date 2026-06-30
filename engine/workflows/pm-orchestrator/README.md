# PM Orchestrator — always-on, blind, stateless coordinator over a phase-recipe

`pm-orchestrator` is a **PM coordinator** that drives ANY task to done by running it through a pluggable
**phase-recipe**. It generalizes the `espresso-test` coordinator: where espresso is hard-wired to one loop
(review→fix→re-review), the PM runs whatever ordered phase list the recipe names — review-only, the espresso
loop, a bugfix chain, a feature build — through the *same* blind, stateless coordinator.

It invents no new review engine, no new fixer, no new implementer. It is pure orchestration on top of the
existing workers:

- **`deep-review`** (the review engine — nested fan-out, returns findings + verdict),
- **`mh-rca`** + **`/mh-fix`** + **`mh-implementer`** (the fix side — the same path `bug-fix`/`espresso-test` use),
- **`/mh-implement`** (feature implementation — never `incremental-impl` directly),
- **`espresso-test`** (the canonical review→fix→re-review loop, reused verbatim as the `espresso` preset).

> Sibling to `espresso-test`: same blind-coordinator discipline (route paths + compact blobs, never read output
> md), but espresso is one fixed loop while the PM is recipe-driven and **always-on** (the one sanctioned
> gate-by-risk auto-route, per `AGENTS.md §3`).

## What It Is For

- Drive **any** task class to done through a declared phase-recipe, without the owner hand-carrying each phase.
- Keep the coordinator **cheap and blind**: it holds the recipe, the ledger, and the stop decision only — it
  never reads a finding, never opens source, never loads a rule. Reasoning lives in the dispatched workers.
- Let each phase run at its own **(model, effort) tier**, derived deterministically from `risk_tier` via
  `scripts/tier_policy.json` — cheap phases stay cheap, risky phases escalate.
- Stay **stateless over a durable ledger** so a long run cannot forget state across a session.

## Roles

| Role | Tier | May read | May write | Job |
|---|---|---|---|---|
| **Coordinator** | `coordinator` `(sonnet, low)` | workers' compact return blobs only | its own `00-pm-state.md` ledger, `99-final-report.md`, `.claude/.pm-run-active` | per tick: re-read ledger, resolve next phase, compute gate, dispatch ONE worker from the main loop, record blob + artifact path, decide done |
| **Worker** | `from-policy` (by `risk_tier`) | the context-manifest it is handed (paths + queries it hydrates live) | its own bounded scope (worktree + allowlist, or `docs/audit/` findings md) | do one phase's work; return ONLY a compact blob (counts/paths/flags) |

### Coordinator invariant (hard)

The coordinator is a router, not a reader. It MUST NOT:

- open, read, or summarize any review/findings/RCA/fix/implementation output `.md` (it receives only the **path
  string** + a **compact status blob** from each worker);
- read or edit source code;
- load `engine/rules/*`, specs, checklists, or the findings schema;
- run a review/fix/implement phase itself.

It MAY write exactly three things: its own `00-pm-state.md` routing ledger, the `99-final-report.md`, and the
`.claude/.pm-run-active` marker. The ledger is authored **from the compact blobs it is handed**, never from
reading anyone's output md. If the coordinator ever needs to open an output md to decide, that decision belongs
to a worker — re-route it, do not read it.

## The Recipe Mechanism

A recipe is an ordered list of phases. Each phase is data:

```text
{ name, dispatch (entry_skill | workflow | agent), tier (from scripts/tier_policy.json keyed by risk_tier),
  gate (auto | owner-confirm, COMPUTED by gate-by-risk), done_check }
```

The coordinator walks the list one phase per tick. Presets (see `manifest.json → recipes`):

| preset | phases | read-only? |
|---|---|---|
| `review` | scope-freeze → `deep-review` (review tier; pass `args.tier_policy`) → scribe writes findings md | yes |
| `espresso` | pre-sweep → loop{ review → fix → re-review } until `open_block_high == 0` or cap — **reuses `engine/workflows/espresso-test/` verbatim** | no |
| `bugfix` | `mh-rca` → `/mh-fix` → `deep-review` | no |
| `feature` | `distill` (read BA once) → `spec` (`ui-spec`\|`technical-design`) → `slice` (`task-slicing`) → `implement` (fan-out `mh-implementer` per slice) → `converge` (`espresso` loop) | no |

The `espresso` preset **references** the canonical loop in `engine/workflows/espresso-test/` — the PM does not
reimplement or modify any espresso file; it dispatches the espresso workflow as one phase. The `feature` preset
is the token-efficient module-build pipeline detailed below; like `espresso`, its `converge` tail **reuses** the
espresso loop verbatim rather than reimplementing it.

Hard exclusions baked into every recipe: `promote` is **never** a dispatchable phase, and the implement phase
dispatches **`mh-implement`, never `incremental-impl`** (that is `mh-implement`'s internal executor).

## The `feature` Pipeline (token-efficient module build)

`feature` builds a whole module from a BA doc through **five phases**, designed so the expensive long material
(the BA doc, the whole spec) is read the *minimum* number of times and each slice runs at its own cost tier:

| # | phase | dispatch | gate | what it reads | what it writes |
|---|---|---|---|---|---|
| 1 | `distill` | a general read+write worker | **owner-confirm** (hard) | the BA doc **ONCE** | `specs/<m>/02-requirements.md` + per-slice risk index |
| 2 | `spec` | `ui-spec` \| `technical-design` | **owner-confirm** (hard, owner-gated) | `02-requirements` + owner-authored `07-schema` | `03-ui.md` / `08-api.md` |
| 3 | `slice` | `task-slicing` | **owner-confirm** (hard, owner-gated) | `03-ui` + `08-api` + `07-schema` | `10-plan.md` (each task carries normalized `risk_tier`+`risk_class`) |
| 4 | `implement` | `mh-implementer` × N | **computed gate-by-risk PER SLICE** | only its slice, by reference | the diff in `worktrees/<slug>/{fe,be}` |
| 5 | `converge` | `espresso-test` | computed per inner phase | — (the espresso loop owns its own reads) | review/fix diffs until clean |

Four load-bearing design rules:

- **Read the BA doc ONCE.** Only `distill` ever opens the BA doc. It emits `02-requirements.md` (filling a real
  GAP — no SDD skill distills the BA doc today; `02-requirements` was previously owner-authored) plus a per-slice
  **risk index** (`risk_tier`+`risk_class` per prospective slice). The BA doc path goes into *that* worker's
  context-manifest only and is **NEVER** added to any later worker's manifest. Every downstream phase rides on the
  distilled/owner-authored specs (`02-requirements` → `03-ui`/`08-api` → `10-plan`), never the raw BA doc.
- **Per-slice by-reference + per-slice (model, effort).** `implement` hands each `mh-implementer` ONLY its slice
  **by reference** (`engine/rules/context-manifest.md`, via `engine/prompts/subagent-prompt-template.md`):
  `specs/<m>/10-plan.md#task-NN` + the specific `03-ui`/`08-api` rows that task touches + its `rule_card` — never
  the BA doc, never the whole spec. Each slice's `(model, effort)` is keyed deterministically from that slice's
  `risk_tier` via `scripts/tier_policy.json → tiers[risk_tier]`, with the `risk_class_floor` applied when its
  `risk_class ∈ {clinical, billing, permission, migration}`. Cheap slices stay cheap; risky slices escalate.
- **Depth-1 fan-out from the main loop.** The PM **is** the orchestrator for `implement`: it launches ONE
  `mh-implementer` per disjoint slice **directly from the main loop** (depth-1), ordered by `10-plan` dependency
  rounds. It does **NOT** dispatch `mh-implement` (that skill re-fans-out into its own subagents → depth-2, which
  the harness cannot reliably nest — see the execution note below) and **NOT** `incremental-impl`.
- **Espresso tail.** `converge` replaces the old one-shot `deep-review` final phase with the `espresso`
  review→fix→re-review loop, **reused verbatim** from `recipes.espresso` — no espresso file is reimplemented.

**Which phases hard-gate:** `distill`, `spec`, and `slice` always fire the **owner-confirm** gate (`spec`/`slice`
are owner-gated SDD workflows; `distill` anchors the whole build, so it gates too). `implement` computes the gate
**per slice** — a `T0/T1` reversible-worktree-bounded slice auto-dispatches, while a `T2/T3`
clinical/billing/permission/migration/irreversible-data slice raises the hard owner-confirm gate. `converge`
computes its gate per inner espresso phase.

## Gate-By-Risk (the dispatch rule)

Each phase's `gate` is **computed**, not hand-set, from the phase's `risk_tier` + `risk_class` (LOCKED, plan
sec.6.B):

```text
AUTO-DISPATCH (no owner ask) when:
    risk_tier ∈ {T0, T1}  AND  phase is read-only OR reversible-worktree-bounded

HARD OWNER-CONFIRM gate when:
    ( risk_tier ∈ {T2, T3}  AND  risk_class ∈ {clinical, billing, permission, migration, irreversible-data} )
    OR  phase.dispatch ∈ { technical-design, task-slicing, ui-spec, dev-from-handoff, robust-test }
```

Rationale (plan sec.6.B): "auto everything" would silently auto-decide clinical/billing/permission/migration —
forbidden by the harness safety canon. Risk-gating is the optimal steady state, not timidity. The PM is the one
sanctioned auto-route; gated workflows inside a recipe still fire the owner-confirm gate per phase.

**Mid-run business ambiguity** (a question that surfaces *during* a phase, not at a gate) uses espresso's
**provisional-or-park** protocol: PARK if closing it needs an irreversible-data/migration op (status
`PARKED-NEEDS-OWNER`, log BLOCKING, continue on the rest), else decide best-effort with a CITED basis (BA
page/section | safe-default | exemplar), implement, log `DL-PROV-<n>` in `specs/<module>/06-decision-log.md` +
mirror the question to `05-open-questions.md`, mark the finding `PROVISIONAL-FIXED`. Pure invention is forbidden;
the loop never blocks mid-run outside a gate.

## Ledger + Run Marker

Per `engine/rules/orchestrator-ledger.md`:

- **`00-pm-state.md`** — the coordinator's durable run-state ledger (header + per-phase rows + stop reason). The
  coordinator **re-reads it each tick** and re-derives state from it (stateless-over-ledger): it cannot forget
  across a long session because state lives in the file, not in context. Authored ONLY from compact blobs;
  regenerable from the artifact paths it points at; MUST NOT live under `main-brain/`.
- **`.claude/.pm-run-active`** — created at run start with **contents = the ledger path**, removed at run end.
  While it exists, the `orchestrator_invariants.py` UserPromptSubmit hook re-injects the PM invariants (incl.
  "re-derive state from this ledger each tick") every turn. The marker is what gates that injection to
  PM-run turns only (token cost discipline).

**Memory by reference** (`engine/rules/context-manifest.md`): the coordinator hands each worker a manifest of
PATHS + QUERIES (`rule_card` output, `recommended_prompt_file`, recalled notes, ledger path, spec sections) with
`verify_live: true` — never pasted content. The worker self-hydrates from the live references. This keeps the
coordinator blind, payloads tiny, and conventions current.

## Stop Enum

The run terminates with exactly one of (`engine/rules/orchestrator-ledger.md`):

```text
DONE     — every phase done_check satisfied; nothing fixable open.
CAP_HIT  — round/phase cap reached with fixable work still open → honest residual (split / new change).
BLOCKED  — no worktree / environment gate failed / required dependency missing.
PARKED   — shippable done, but M findings deferred to owner (irreversible-data / migration / business ambiguity).
```

Record the stop reason in the ledger's `## Stop reason` block, then remove the run marker.

## Cost

Cost is recipe-dependent. A `review` preset is one `deep-review` fan-out (7 dimensions × multi-pass +
self-adversarial + adversarial verify). The `espresso` preset multiplies that by rounds plus a fix fan-out per
round. The coordinator itself stays cheap (`(sonnet, low)` — blind, count-based, script-backed). There is **no
token-budget guard inside the loop**; the phase/round cap is the only hard ceiling, and the owner owns the cost
decision at invoke. Keep cheap phases at their floor tier and let only risky phases escalate via the policy.

## Run Folder

```text
engine/workflows/pm-orchestrator/runs/<scope>/run-NNN/
  00-pm-state.md        # coordinator's routing ledger (header | per-phase rows | stop reason)
  99-final-report.md    # coordinator's owner-facing summary (built from compact blobs)
```

Review findings live where `deep-review` already writes them — `docs/audit/<YYYY-MM-DD>/<base>.md` — and are
referenced from the ledger by **path**, never copied into the run folder. Fix/feature diffs live in
`worktrees/<slug>/{fe,be}`.

Templates: `templates/pm-state-template.md`, `templates/final-report-template.md`.

## Execution Note — fan-out only from the main loop

Two real harness facts shape how phases execute (the same constraints espresso documents):

1. **`deep-review` is a Workflow-tool JS script**, and the Workflow tool runs in the **main loop**. A scribe
   then writes the findings md (Workflow scripts cannot write files). The coordinator receives only
   `{findings_path, counts, verdict}`.
2. **A plain Agent-tool subagent may not be able to spawn further subagents.** Therefore the PM realizes its
   "deep" fan-out by the **PM (main loop) launching a Workflow**, OR by depth-1 Agent rounds — **never by
   delegating fan-out into a worker that itself re-fans-out**. Confirmed working: parent→child depth-1 and
   `workflow.js` internal `parallel()`.

**Design rule:** dispatch every phase from the main loop. The coordinator launches the Workflow (deep-review /
espresso) or a depth-1 Agent (mh-rca / a scribe) itself; the worker does ITS bounded unit and returns a compact
blob — it does not re-orchestrate.

## Hard Boundary & Safety

Inherits the full `AGENTS.md` Forbidden Actions list, plus:

- **Coordinator reads nothing** (see the invariant above). This is the defining constraint.
- **All source edits inside `worktrees/<slug>/{fe,be}` only.** Never `myhospital-fe/`, `myhospital-be/`,
  generated DTO/client/`Constants.ts`, or EF migrations by hand. The fix/implement phases inherit `/mh-fix` and
  `/mh-implement` safety in full.
- **Gate-by-risk is mandatory** — never auto-dispatch a `T2/T3` clinical/billing/permission/migration/
  irreversible-data phase or an owner-gated workflow without the owner-confirm gate.
- `promote` is never dispatchable; dispatch `mh-implement`, never `incremental-impl`.
- No `git commit` / `push` / `reset` / destructive checkout — leave diffs in the worktree for owner review.
- No DB/data mutation except the approved worktree-slot migration/data path.
- Owner-gated, `manual_only`. The PM may dispatch only the phases its active recipe names — it must not
  self-launch any other workflow, external executor, or browser sweep.

## Status

This workflow is `auto_route_allowed: false` — always available when the owner invokes it. The first validation run is a **READ-ONLY**
`review` preset on the smallest available real changeset (plan sec.6.D) — the lowest-risk proof of
route → dispatch → verify → ledger → stop.

## Relationship To Existing Pieces

- **`espresso-test`** — the canonical review→fix→re-review loop, reused verbatim as the `espresso` preset. The
  PM does not modify any espresso file.
- **`deep-review`** — the review engine. Every recipe with a review phase dispatches it; it owns recall +
  findings md.
- **`mh-rca` / `/mh-fix` / `mh-implementer`** — the fix side (the `bugfix` preset's first two phases).
- **`mh-implementer`** — feature implementation: the `feature` preset's `implement` phase fans out ONE
  `mh-implementer` per disjoint slice (depth-1), so the PM never nests `mh-implement` (depth-2).
- **`ui-spec` / `technical-design` / `task-slicing`** — the SDD design+slice skills, reused verbatim as the
  `feature` preset's `spec` and `slice` phases (owner-gated).
- **`orchestrator-ledger` + `context-manifest`** — the rules that make the coordinator stateless + blind.
