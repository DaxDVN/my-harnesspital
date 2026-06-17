---
name: super-test
description: LAUNCHER for the MiMo-led Super-Test workflow (module-level exploratory E2E bug-harvesting). This skill does NOT orchestrate — it inits a run + prints the OpenCode/MiMo command, then MiMo DRIVES the harvest. Claude/Opus enters later only as a file-handoff batch-RCA specialist. Trigger "/super-test", "super test", "harvest bugs", "exploratory sweep".
---

# super-test — LAUNCHER (Topology B: MiMo-led, Claude is NOT the orchestrator)

**Read this first:** Super-Test is **MiMo-driven**. Unlike `/mh-review` or `/agentflow`, this skill is **not** a
phase-orchestrator — if Claude routed each flow/bug it would collapse into progressive-test (fix-first) and
lose the whole point. Claude/Opus appears **only** later, as a **called** batch-RCA specialist (file-handoff).
Full contract: `engine/workflows/super-test/README.md`. Harvest protocol MiMo follows: `engine/workflows/super-test/protocol/harvest-sweep.md`.

## What Super-Test is (vs progressive-test)
- **progressive-test:** test → 1 bug → RCA/fix → retest (converge, fix-first). Gets stuck on early bugs.
- **super-test:** MiMo sweeps MANY flows → logs EVERY bug + bypasses to keep going → bug-catalog + coverage-map
  → only THEN Opus batch-clusters root causes → Codex → MiMo implements batch → targeted + module-sweep retest.
  Goal = **harvest the module's bug surface before fixing**.

## When to use
Module already implemented + has a runnable FE flow; you want to audit it deeply before final review.
NOT for: a single known bug (use `/bug-fix`), a small task, or a module with no runnable UI yet.

## PRIMARY path — run from MiMoCode (MiMo-led, no headless)
MiMoCode is an opencode-fork that auto-loads `AGENTS.md`, so it already reaches the harness. The owner opens
MiMoCode in the repo and **MiMo itself drives** — no headless wrapper. Driver brief (the pointer MiMo follows):
`engine/workflows/super-test/integrations/mimocode-super-test.md`. In MiMoCode just say `super-test <module> at <url>`.
MiMo self-drives: `supertest init-run` → harvest (it **shells the `agent-browser` CLI**) → `bash bin/call-opus-batch-rca`
(**this is where MiMo calls Claude/Opus**) → implement (allowlist self-checked) → retest → `supertest final-report`.
Before the first real module run or after changing MiMoCode runtime config, run:
```fish
bash engine/workflows/super-test/bin/mimocode-preflight --strict
```
If MiMoCode does not actually auto-load `AGENTS.md`, inject `AGENTS.md` plus
`engine/workflows/super-test/integrations/mimocode-super-test.md` as the startup/project instruction.
*(The `/super-test` Claude skill below + `bin/sweep` opencode wrapper are the ALTERNATIVE launcher/executor — not needed when MiMoCode drives.)*

## How to launch (this skill's whole job)
1. **Init a run** (deterministic): `python engine/workflows/super-test/lib/supertest.py init-run <module>` →
   creates `engine/workflows/super-test/runs/<module>/run-NNN/` with `00-super-test-state` + `01-module-test-map` skeleton.
2. **Ask** the owner for: app URL / local route, login/precondition, module scope, any known flow list + test data.
   Fill `01-module-test-map.md` (the flows/features to sweep; mark inferred ones).
3. **Print the MiMo command for the OWNER to run** (Claude does NOT run the sweep — MiMo is the driver):
   ```fish
   set -x AGENTFLOW_TARGET_URL <url>
   bash engine/workflows/super-test/bin/sweep <module> run-NNN
   ```
   MiMo loads `protocol/harvest-sweep.md` and self-drives HARVEST: sweep flows → log bugs → bypass → update
   coverage/blocked → stop on a stop-condition → write `07-opus-request.md` + set state `CALLING_OPUS`.
4. **Hand off.** When HARVEST stops, the next phase (M2) is the Opus batch-RCA — invoked **by MiMo via a wrapper**
   (`call-opus-batch-rca`, file-handoff), not by this skill. This skill's job ends at launch + handoff guidance.

## Boundaries (this skill)
Launcher only — never drive the sweep, never route per-flow/per-bug, never RCA/fix here. Honor the guard.
Source edits happen ONLY in MiMo's IMPLEMENT phase (M3), allowlist-bounded, against an approved repair plan.

## Status
**M1** (scaffold + schemas + harvest sweep) — launchable; harvest-discipline quality is the owner gate (first
real sweep). M2 (opus batch-rca + codex) and M3 (repair + 2-stage retest) follow. See README "Milestones".
