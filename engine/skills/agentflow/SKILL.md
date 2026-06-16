---
name: agentflow
description: Owner-invoked ONLY — autonomous FE-bug-fix loop. Claude is the LEAN state-machine ORCHESTRATOR (reads envelopes + validator results, NEVER long payloads) routing OpenCode/mimo-v2.5 (test/implement/retest via bash wrappers + agent-browser) ↔ Opus RCA subagent ↔ Codex review gate, over file artifacts. Trigger "/agentflow". Do NOT self-invoke (long, token-heavy, edits source).
---

# agentflow — orchestrator (envelope-router)

Drive the agentflow loop in `engine/workflows/agentflow-opencode/`. **Owner-invoked, explicit-only** (like
`/mh-review`): never self-trigger — it's a long autonomous loop that spends tokens and edits source.

## Your role: ROUTER, not reader
You are a **state-machine router**. You read ONLY: `state.json`, the latest `*.envelope.json` (the short
receipt), and `validate-artifact`/`validate-envelope` exit results. You **must NOT read the long payloads**
(`*-bug-packet.json`, `*-rca-plan.json`, `*-codex-review.json`, `*-implementation-report.json` bodies) —
the specialized agent reads those. (Only exception: explicit DEBUG when something is stuck.) This keeps your
context lean over many rounds. You decide the next step from the envelope's `verdict`/`next` + validator pass.

`BIN=engine/workflows/agentflow-opencode/.agentflow/bin`. You call OpenCode ONLY through `$BIN/*` wrappers
(never raw `opencode run`). RCA and Codex are NOT OpenCode — you spawn them directly (below).

## Preconditions
- Confirm the owner asked. Ask for: the **scenario** (what to test) and the **target** (URL + repo path).
- **Safety:** if the target is MyHospital, IMPLEMENT_ONLY edits source → the harness guard FORBIDS editing
  `myhospital-fe|be` outside a worktree. So the target repo MUST be a **worktree** the owner opened (set its
  path/URL via the agentflow config/env). Never point implement at the main repos.
- `$BIN/doctor` → PASS (opencode + agent-browser present). `$BIN/init-round round-NNN "<scenario>"`.

## Loop (route by state + latest envelope; bounds: max_rounds=5, max_codex_reviews=2, max_rca_revisions=2)
1. **TEST** → `AGENTFLOW_TARGET_URL=<url> $BIN/test-with-opencode <round>` → writes `01-bug-packet.json`+envelope.
   `$BIN/validate-envelope …/01-bug-packet.envelope.json`. If bug envelope `verdict=PASS` → **DONE** (no bug). If `FAIL` → step 2.
2. **CLASSIFY** → `$BIN/classify <round>` (deterministic). Output:
   - `TRIVIAL` → it already wrote `04-approved-plan.md` (constrained import-only fix). `$BIN/write-envelope approved-plan …/04-approved-plan.md`; `$BIN/update-state <round> DIRECT_PATCH_APPROVED approved_plan=…` → go to **IMPLEMENT** (skip RCA + Codex).
   - `NEEDS_RCA` → `$BIN/update-state <round> RCA_RUNNING` → step 3.
3. **RCA (Opus subagent)** → spawn an **Agent** (model opus) with the bug-packet *path* + `…/.agentflow/prompts-or-instructions/rca-agent-instructions.md`. It reads the payload + targeted code (CodeGraph/rg) and writes `02-rca-plan.json`. Then YOU: `$BIN/validate-artifact rca-plan …` + `$BIN/write-envelope rca-plan …` + `$BIN/validate-envelope …`. Read the rca envelope:
   - `verdict=DIRECT_PATCH` (`requires_codex_review=false`) → `$BIN/build-approved-plan <round>` → step 5.
   - `verdict=CODEX_REQUIRED` → `$BIN/update-state <round> CODEX_REVIEW_REQUIRED` → step 4.
   - `MORE_EVIDENCE` → back to TEST (more evidence). `HUMAN_DECISION` → stop, report to owner.
4. **CODEX gate** → invoke the **codex plugin** (`codex:codex-rescue` / codex review) with the rca-plan *path*
   + `…/codex-review-instructions.md`. It writes `03-codex-review.json`. YOU: validate-artifact + write-envelope + validate-envelope. Read the codex envelope `verdict`:
   - `APPROVE`/`APPROVE_WITH_CHANGES` → `$BIN/build-approved-plan <round>` (picks up `03` → approval=APPROVED_BY_CODEX) → step 5.
   - `REJECT` → if `rca_revision_count < 2`: re-spawn RCA (revise, with the codex review path) → step 3; else **HUMAN_DECISION**.
5. **BUILD PLAN** → after build-approved-plan: `$BIN/write-envelope approved-plan …/04-approved-plan.md` + validate-envelope + `$BIN/update-state <round> CODEX_APPROVED` (or `DIRECT_PATCH_APPROVED`).
6. **IMPLEMENT** → `$BIN/implement-with-opencode <round>` → `05-implementation-report.json`+envelope. validate-envelope. Read verdict: `IMPLEMENTED` → step 7; `PLAN_MISMATCH` → back to RCA (revise) or HUMAN; `FAILED` → report.
7. **RETEST** → `$BIN/retest-with-opencode <round>` → `06-retest-report.json`+envelope. validate-envelope. Read verdict: `PASS` → `$BIN/summarize-round <round>` → **DONE**; `FAIL` → if rounds remain, `$BIN/init-round` a new round (the failure is re-caught) or escalate to RCA; else **HUMAN_DECISION**.

## Discipline
- Forward **paths**, not contents, to RCA/Codex. Trust the envelope `verdict` + the validator pass; if an
  envelope is invalid (sha256 drift / missing fields) → treat as a failed step, do not proceed.
- Honor the guard (no git mutation, no editing generated files, worktree-only source edits). Respect the
  bounds; when a bound is hit, set `HUMAN_DECISION_REQUIRED` and hand back to the owner with the round dir.
- mimo's retest PASS is trusted ONLY through evidence in the retest report; a false PASS is re-caught when
  the scenario re-runs in a later round (the owner accepted this tradeoff).

## Honest note
Mock (`AGENTFLOW_MOCK_OPENCODE=1`) proves the wiring; the FIRST real end-to-end run (real mimo fix quality +
agent-browser on the owner's FE) is the owner's gate. See `engine/workflows/agentflow-opencode/WORKFLOW.md`.
