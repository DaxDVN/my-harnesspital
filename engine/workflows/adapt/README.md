# adapt — owner-gated semi-automated harness adaptation

`adapt` is a **meta-workflow**: it repairs or extends the harness itself. It is the only workflow
whose `allowed_writes` include `engine/workflows/`, `engine/skills/`, `engine/prompts/`, and the
canon indexes (`REGISTRY.md`, `AGENTS.md`, `HARNESS-GUIDE.md`). Every other workflow is forbidden
from touching harness machinery — `adapt` is the sanctioned channel for harness change.

It is **NOT autonomous self-evolution**. It is a semi-automated pipeline with six hard safety gates
(see §3): it detects + RCA + proposes + drafts, but the **owner approves + commits** before any
change takes effect. The harness never silently mutates mid-session.

## What it is for

- **Mode A — adapt-on-failure:** a workflow's *machinery* (not the task it was running) failed
  during a run — a manifest ref broke, a state template drift, a prompt contradicted the canon, a
  gate mis-fired. `adapt` RCAs the workflow bug and patches the workflow files. Threshold: the same
  `root_cause_signature` has failed ≥2 times (no adapt on first fail — could be data, not machinery).
- **Mode B — adapt-on-repetition:** a task pattern has recurred ≥3 times (signal from
  `learning_recall`, `harness_scanner_promotion`, or agent observation) and has no workflow
  automating it yet. `adapt` designs + builds a new workflow. Conflict-checked: refuses to build a
  name that already exists in `harness_doctor` registry or `REGISTRY.md` (prevents bloat).

## What it is NOT

- **Not MID-run.** Adapt runs AFTER the target workflow ends. If `pm-orchestrator` is dispatching
  `bug-fix` and `bug-fix` fails, adapt runs after the pm-orch run records the failure — never while
  pm-orch is still dispatching. (Rationale: a workflow editing another workflow that the PM is
  currently dispatching breaks the blind-PM discipline + ledger invariants.)
- **Not self-fixing.** `adapt` NEVER modifies `engine/workflows/adapt/`, `engine/skills/adapt/`, or
  `engine/prompts/adapt.md` (bootstrap paradox — the workflow that fixes workflows cannot fix its
  own broken fixing-logic without infinite regression). If `adapt` itself is broken, the owner
  fixes it by hand.
- **Not auto-spawned.** No intent word, no hook, no router auto-fires `adapt`. The owner invokes
  `/adapt` or approves a trigger report (see §4). `auto_route_allowed: false`, `manual_only: true`,
  `owner_invocation_required: true`.
- **Not a substitute for `/promote`.** `/promote` graduates a *learning* into `main-brain/` SoT.
  `adapt` changes *workflow machinery*. They are orthogonal: a learning may prompt an adapt, but
  adapt does not write `main-brain/`.

## Roles

| Role | Tier | May read | May write | Job |
|---|---|---|---|---|
| **Coordinator** | `coordinator` `(sonnet, low)` | workers' compact blobs + the target workflow's manifest/README/prompt (metadata, NOT task output) | its own `00-adapt-state.md` ledger, `99-adapt-report.md`, `stop-reason.txt` | per tick: re-read ledger, resolve next phase, compute gate, dispatch ONE worker, record blob + path, decide done |
| **RCA / Design worker** | `opus/high` (`mh-rca`) | the target workflow's machinery files (manifest/README/prompt/state-template/runs ledger for Mode A; registry + REGISTRY + repetition evidence for Mode B) | `03-rca` (Mode A) or `design doc` (Mode B) under the adapt run dir | root-cause the workflow bug (A) or design the new workflow (B); return a compact plan blob |
| **Fix / Build worker** | `sonnet/high` (`mh-fix`) | the RCA/design plan + the workflow files on the allowlist | only the allowlist files | patch the workflow (A) or create the new workflow files (B); self-review-diff; return a compact change blob |

### Coordinator invariant (hard)

Same blind discipline as `pm-orchestrator`: the coordinator routes PATHs + compact blobs, never
reads worker output md / task source / rules. It authors the ledger ONLY from blobs. It DOES read
workflow *machinery* files (manifest/README/prompt) when it needs to verify a blob against the
canon — those are harness metadata, not task content, and the guard's blind-PM block exempts
`engine/workflows/**` (SRC_TREE is `myhospital-{fe,be}` + `worktrees/<slug>/{fe,be}`, not `engine/`).

## Mode A — adapt-on-failure (5 phases)

```text
1. intake     (coordinator, auto)     — record failure_evidence + root_cause_signature + fail_count(>=2)
2. rca        (mh-rca, opus/high, auto) — root-cause the workflow bug → 03-rca (DIRECT_PATCH | REDESIGN | HUMAN_DECISION)
3. fix-plan   (coordinator, OWNER-CONFIRM) — 04-adapt-plan: allowlist of workflow files + validation + rollback; OWNER approves
4. fix        (mh-fix, sonnet/high, OWNER-CONFIRM) — patch workflow files per allowlist; harness_backup snapshot pre-apply
5. validate   (coordinator, auto)     — harness_doctor --strict green + target workflow self-test + replay passes OR residual risk stated
```

**HUMAN_DECISION** from rca (the bug is not machinery, it is a canon contradiction or an owner
policy question) → stop `BLOCKED`, hand to owner. **REDESIGN** (the workflow's design is wrong, not
a patchable bug) → owner decides whether to redesign (may escalate to a Mode B build-and-deprecate).

## Mode B — adapt-on-repetition (5 phases)

```text
1. intake     (coordinator, auto)     — verify repetition_signal (>=3 occurrences cited); conflict-check proposed name vs registry + REGISTRY (refuse if dup)
2. design     (mh-rca, opus/high, OWNER-CONFIRM) — design doc: manifest draft + README skeleton + recipe/phases + entry skill stub + prompt + reuse map; OWNER approves design
3. build      (mh-fix, sonnet/high, OWNER-CONFIRM) — create workflow files per design allowlist; self-review-diff; harness_backup snapshot pre-apply
4. wire       (coordinator, OWNER-CONFIRM) — update REGISTRY.md + AGENTS.md §3 + HARNESS-GUIDE.md §2/§6 with the new workflow row + owner-gated entry; OWNER approves wiring
5. validate   (coordinator, auto)     — harness_doctor --strict green (registry resolves) + new workflow self-test + dry-run passes OR residual risk stated
```

**Conflict-check (gate 6)** fires in `intake`: `python scripts/harness_doctor.py check_registry`
must NOT already list `proposed_workflow_name`. If it does → stop `BLOCKED`, suggest extending the
existing workflow instead of adding a duplicate. This is the bloat-prevention gate.

## The six safety gates (LOCKED)

1. **Owner-gated.** No auto-spawn from intent words. Owner invokes `/adapt` or approves a trigger
   report (§4). `auto_route_allowed: false`.
2. **POST-run.** Adapt runs after the target workflow ends. The coordinator verifies the target
   workflow's run is not active (no `.claude/.pm-run-active` pointing at it, no active ledger
   `status: RUNNING`) before entering `intake`.
3. **No-self-fix.** The `allowed_writes` list excludes `engine/workflows/adapt/**`,
   `engine/skills/adapt/**`, `engine/prompts/adapt.md`. A fix/build worker that tries to edit
   adapt's own files → guard block + stop `BLOCKED`.
4. **Pin-version.** Before any `fix`/`build` phase applies, the coordinator runs
   `python scripts/harness_backup.py --snapshot` and records the snapshot id in the ledger. The
   diff is presented to the owner; owner approves + commits before the change is live. No silent
   mutate mid-session. Rollback = restore the snapshot.
5. **Threshold.** Mode A: `fail_count >= 2` with the same `root_cause_signature`. Mode B: ≥3
   occurrences cited with paths (learning_recall note seen ≥3, scanner_promotion bug_class ≥3, or
   agent-observed task-type repeated ≥3). No adapt on first fail / first repetition.
6. **Conflict-check (Mode B only).** `harness_doctor check_registry` + `REGISTRY.md` must not
   already list `proposed_workflow_name`. Refuse duplicate.

## Reuse map (no reinvention)

| Need | Reuse |
|---|---|
| RCA a workflow bug | `mh-rca` agent (Opus, read-only) with `engine/prompts/adapt.md` as the workflow-engineer runbook |
| Fix workflow files | `/mh-fix` (sonnet, allowlist-bounded, self-review-diff) — same path `bug-fix` uses for source |
| Detect repetition signal | `scripts/learning_recall.py` + `scripts/harness_scanner_promotion.py scan` + agent observation |
| Validate registry + governance | `scripts/harness_doctor.py --strict` (check_registry + workflow-governance + runtime-contract) |
| Pin a backup before apply | `scripts/harness_backup.py --snapshot` (rollback anchor) |
| Detect a failing workflow run | the run's ledger `status` field + `harness_doctor` + the workflow's own self-test |
| Owner approval gate | the existing preflight-confirmation pattern (`engine/rules/preflight-confirmation.md`) |

`adapt` invents NO new engine. It orchestrates existing pieces against a new scope (harness
machinery instead of product source).

## Stop Enum

```text
DONE     — every phase done_check satisfied; harness_doctor green; owner approved + committed.
CAP_HIT  — phase cap reached with fixable work still open → honest residual (new adapt run or hand-fix).
BLOCKED  — conflict-check refused (Mode B dup) | rca returned HUMAN_DECISION | no backup could be pinned | target workflow is still active (POST-run violated).
PARKED   — shippable done but a finding deferred to owner (e.g. REDESIGN recommended, owner will decide later).
```

Record the stop reason in the ledger's `## Stop reason` block.

## Run Folder

```text
engine/workflows/adapt/runs/<scope>/run-NNN/
  00-adapt-state.md        # coordinator's routing ledger (header | per-phase rows | stop reason)
  03-rca.md                # Mode A: workflow bug RCA (mh-rca output)
  design.md                # Mode B: new workflow design (mh-rca output)
  04-adapt-plan.md         # fix/build allowlist + validation + rollback (Mode A) or build+wire allowlist (Mode B)
  99-adapt-report.md       # owner-facing summary (diff pointer + snapshot id + validation results)
  stop-reason.txt          # one line: <iso-ts>\t<stop>\t<note>
```

Workflow file edits (Mode A) / creations (Mode B) land in `engine/workflows/<target>/`,
`engine/skills/<target>/`, `engine/prompts/<target>*.md`, and the canon indexes — referenced from
the ledger by path, never copied into the run folder.

## Trigger report (how an adapt run starts)

Three entry paths — **the first two are auto-detection (the system proposes), the third is direct** — but ALL three are owner-gated for APPLY:

1. **Auto-detect on workflow failure (MID-session):** the `adapt_fail_watch` PostToolUse hook fires whenever a Write/Edit lands on a run-state ledger (`engine/workflows/*/runs/**/00-*-state.md`) whose `status` is BLOCKED / CAP_HIT / FAILED with a machinery root-cause hint. It queues a trigger into the dedup store. The owner sees it in the next SessionEnd report (or by running `adapt_detect` manually).
2. **Auto-detect at session end (broad scan):** the `adapt_trigger` SessionEnd hook runs `scripts/adapt_detect.py`, which scans `harness_doctor` (FAIL/WARN), run ledgers (bad status + machinery hint), `harness_scanner_promotion` (bug_class ≥3), and `second-brain` notes (stem ≥3) for NEW adapt signals. It prints a dedup'd trigger report (a trigger already reported is NOT re-printed until cleared). The owner acts on a trigger with `/adapt`.
3. **Direct invoke:** owner types `/adapt` or "adapt workflow X" / "build a workflow for Y".

```text
ADAPT-TRIGGER (mode=A, target=bug-fix, key=311573b55c63)
  source: post-tool-fail-watch:engine/workflows/bug-fix/runs/.../00-bug-fix-state.md
  detail: bug-fix machinery failure — see evidence
  evidence: engine/workflows/bug-fix/runs/.../00-bug-fix-state.md
  suggestion: /adapt mode=A target=bug-fix root_cause_signature=run:bug-fix:BLOCKED:... fail_count=2
```

The owner approves by running `/adapt` with the cited inputs. The report NEVER auto-fires the apply — detection + proposal is automatic, application is owner-gated (AGENTS.md §3). Clear a trigger the owner has handled: `python scripts/adapt_detect.py --clear <key>` (or `--clear-all`).

## Relationship to existing pieces

- **`pm-orchestrator`** — adapt is a sibling orchestrator (same blind discipline, ledger, gate-by-
  risk). pm-orch drives *tasks*; adapt drives *harness health*. pm-orch may print an ADAPT-TRIGGER
  at run end but does NOT dispatch adapt (owner-gated).
- **`bug-fix`** — adapt is the harness-machinery analogue of bug-fix: same RCA→plan→fix→verify
  shape, same `mh-rca` + `/mh-fix` reuse, but the "source" is `engine/workflows/**` not
  `worktrees/<slug>/{fe,be}`.
- **`/promote`** — orthogonal. Promote graduates a learning into `main-brain/`. Adapt changes
  workflow machinery. A learning may be the *signal* for an adapt, but adapt never writes
  `main-brain/`.
- **`harness_doctor`** — adapt consumes doctor output (drift detection, registry errors) as Mode A
  failure evidence, and uses doctor as the Mode A/B final validator.
- **`harness_scanner_promotion`** — its `bug_class >=3` output is a Mode B repetition signal.

## Status

`auto_route_allowed: false` — owner-invoked only. First validation = a Mode A dry-run on a synthetic
workflow bug (lowest-risk proof of intake→rca→plan→owner-gate→fix→validate). Mode B first run =
owner hand-carries a real repetition signal through the pipeline.
