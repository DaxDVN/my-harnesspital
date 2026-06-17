# Super-Test — MiMo-led exploratory E2E bug-harvesting (contract)

**One line:** OpenCode/MiMoCode sweeps a module with agent-browser, logs the **maximum** bugs it can find
(bug-catalog + coverage-map + bypass-log + blocked-flows), then file-hands-off to **Opus 4.8 (max effort)**
for **batch cluster-RCA** + repair batches, **Codex** reviews risky batches, MiMo implements the approved
plan, then **targeted retest + module-sweep retest**.

Sibling of `progressive-test`, NOT a replacement:
```
progressive-test = repair loop (test → 1 bug → RCA/fix → retest, converge)   ← fix-first
super-test       = harvest the module's bug surface, THEN batch-repair        ← harvest-first
```
Use Super-Test when a module is ~implemented and you want its full bug map before final review. After a
Super-Test repair batch, progressive-test is still useful for the long tail.

## Topology B — MiMo-led (the load-bearing decision)
- **MiMo/OpenCode = entrypoint + DRIVER.** It self-drives the entire HARVEST phase and, after harvest, the
  IMPLEMENT + RETEST phases. The owner starts MiMo (via `bin/sweep`), not Claude.
- **Claude/Opus = a CALLED specialist, never the orchestrator.** It enters ONLY after HARVEST stops, as the
  batch-RCA / repair-planner, via short **file-handoff**. If Claude routed each flow/bug, Super-Test would
  collapse back into progressive-test (fix-first) — the exact thing it exists to avoid.
- **Codex = reviewer/gate** for risky repair batches. Not an implementer, not an orchestrator.
- **File-state = MiMo's memory/checklist, NOT an external orchestrator.**

## Actors + boundaries
| Actor | Phase | MAY | MUST NOT |
|---|---|---|---|
| **MiMo/OpenCode** | HARVEST | agent-browser sweep · log bug/evidence/bypass/coverage/blocked · update state · call Opus wrapper at stop-condition | edit source · RCA · fix · treat bypass as pass · drop a bug unlogged · change expected behavior |
| **MiMo/OpenCode** | IMPLEMENT | read approved plan · edit allowlisted files · run validation · write report | edit outside allowlist · fix unapproved bugs · change plan/schema/API unless approved |
| **MiMo/OpenCode** | RETEST | agent-browser retest · append NEW bugs found | fix · RCA during retest |
| **Claude/Opus** (`mh-batch-rca`, M2) | after HARVEST | read catalog/coverage/bypass/blocked + code · cluster by root cause · batch repair plan · call Codex on risky batches | implement · run the browser sweep · route per-flow · emit an unbounded "fix-everything" plan |
| **Codex** (M2) | repair-plan gate | review plan vs codebase/convention/side-effects · approve/reject | implement · browser · orchestrate |

## File-handoff (prompts short, content in files, return = status+path)
```
MiMo → Opus:   read 07-opus-request.md → write 08-opus-batch-rca.md(+envelope) → return STATUS=OPUS_RCA_READY ARTIFACT=… ENVELOPE=…
Opus → Codex:  read 08 → write 09-codex-review.md → return STATUS=CODEX_REVIEW_READY VERDICT=… ARTIFACT=…
Opus → MiMo:   write 10-approved-repair-plan.md → return STATUS=APPROVED_REPAIR_PLAN_READY ARTIFACT=… NEXT=MIMO_IMPLEMENT
```
No full RCA/plan in stdout/chat (context-rot guard). Envelopes use the shared `engine/workflows/_shared/envelope.schema.json` + `validate-envelope.py`.

## Run folder (`engine/workflows/super-test/runs/<module>/run-NNN/`)
```
00-super-test-state.md      01-module-test-map.md     02-coverage-map.md     03-current-frontier.md
04-bug-catalog.md(+.envelope.json)   05-bypass-log.md   06-blocked-flows.md
07-opus-request.md          08-opus-batch-rca.md(+env) 09-codex-review.md     10-approved-repair-plan.md(+env)
11-implementation-report.md 12-targeted-retest-report.md  13-module-sweep-retest-report.md  14-final-super-test-report.md
evidence/{screenshots,snapshots,network,console}/    logs/
```
Schemas + validators: `lib/supertest.py`. Harvest protocol MiMo follows: `protocol/harvest-sweep.md`.

## State machine (driven by MiMo; file-state is the memory)
```
INIT → LOAD_TEST_MAP → HARVESTING
  HARVESTING: flow_pass→coverage++ · bug→log+bypass(→continue | →blocked) · stop_condition→write 07 → CALLING_OPUS
CALLING_OPUS → (M2) OPUS_BATCH_RCA → [CODEX if risky → revise≤2] → APPROVED_REPAIR_PLAN
APPROVED_REPAIR_PLAN → (M3) IMPLEMENTING → TARGETED_RETEST → MODULE_SWEEP_RETEST → FINAL_REPORT → DONE
  any mismatch/fail → re-file-handoff to Opus (never improvise)
```
Stop conditions (HARVEST): COVERAGE_COMPLETE · MAX_BUGS_REACHED · MAX_BLOCKERS_REACHED · MAX_TIME_REACHED · NO_MORE_REACHABLE_FLOWS · CRITICAL_SYSTEMIC_BUG.

## Reuse (no duplication)
agent-browser layer + OpenCode/MiMoCode invocation pattern ← `progressive-test`; the shared envelope +
`validate-envelope.py` + `allowlist-check.py` (implement boundary) ← `engine/workflows/_shared/`; `frontend.md`/`backend.md` canon.
NEW here: the harvest sweep + the 6 harvest/repair artifact schemas + the `mh-batch-rca` Opus agent (M2).

## MiMoCode readiness
Run the preflight before the first real module run, after changing MiMoCode CLI config, or when Super-Test
starts behaving differently than expected:

```bash
bash engine/workflows/super-test/bin/mimocode-preflight --strict
```

Required runtime inputs for a real sweep/retest:

```bash
export AGENTFLOW_TARGET_URL="<running app url>"
export SUPERTEST_TARGET_REPO="<workspace>/worktrees/<slug>/fe-or-be"
```

The OpenCode model is configurable. Defaults come from `config.yaml`; per-run overrides use
`SUPERTEST_CLI_MODEL` for the actual OpenCode `--model` value and `SUPERTEST_EXECUTOR_MODEL` for logical
metadata. If the MiMoCode binary is not named `mimo`, configure one of:

```bash
export SUPERTEST_MIMO_CODE_BIN="<binary-name>"
export SUPERTEST_MIMO_CODE_CMD='<command that consumes {prompt_file}>'
```

OpenCode/MiMo executor wrappers now auto-retry the specific upstream `Request Error status 400 · non-retryable`
failure once after a short delay, and they also retry a stuck `opencode run` after a timeout. If you need to tune
that behavior, set:

```bash
export SUPERTEST_OPENCODE_RETRY_ATTEMPTS=2
export SUPERTEST_OPENCODE_RETRY_DELAY_SECS=5
export SUPERTEST_OPENCODE_RUN_TIMEOUT_SECS=1800
export SUPERTEST_OPENCODE_TIMEOUT_KILL_AFTER_SECS=30
```

The generated executor prompts include `integrations/mimocode-super-test.md` so MiMo/OpenCode receives the
same Super-Test guardrails even when the runtime does not automatically load project instructions.

## Enforced boundaries (deterministic, not just instruction)
- **HARVEST = no source edits:** after a sweep, the target worktree `git diff` MUST be empty — `sweep`
  asserts it; non-empty → the sweep is rejected (MiMo broke harvest-mode).
- **IMPLEMENT = allowlist:** the implement diff must be within the approved-plan allowlist via
  `_shared/allowlist-check.py`; otherwise STOP.

## Milestones
- **M1 (this):** scaffold + schemas/validators + `sweep` harvest. Nghiệm thu: does MiMo log every
  bug + honest bypass + correct coverage + leave source untouched? First real sweep = owner gate.
- **M2:** `mh-batch-rca` Opus agent + `call-opus-batch-rca` + `call-codex-review` wrappers (file-handoff).
- **M3:** implement (allowlist-bounded) + targeted retest + module-sweep retest + final report + REGISTRY/doctor wiring.
