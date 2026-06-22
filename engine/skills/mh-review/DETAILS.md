---
name: mh-review
description: Exhaustive ≤3-round code review for a MyHospital module, dirty worktree changeset, or explicit file set. Coverage-first partitioned audit that maximizes first-pass recall so review converges in ≤3 rounds instead of many. Use when a module/feature is finished (e.g. after spec-driven dev) and you need to find business-rule, convention, correctness, security, and contract issues before merge. Trigger: "/mh-review", "review module X", "audit dirty changes", "review before merge".
---

# mh-review — orchestrator

> Full runbook. `SKILL.md` is the token-light discovery stub for this skill.

Run the harness. The cross-tool review knowledge lives in **`engine/workflows/deep-review/`** (neutral — Codex/opencode read it natively too): `engine/workflows/deep-review/protocol.md` (the ≤3-round runbook), `engine/workflows/deep-review/checklist.md` (10 dimensions D1–D10), `engine/workflows/deep-review/findings-schema.md` (output format). This skill (`SKILL.md`) is the Claude driver; the optional power-mode workflow lives at `engine/workflows/deep-review/workflow.js`. Full rationale: `docs/harness/notes/review-harness-feasibility-2026-06-16.md`.

**Core idea:** recall comes from **partition + repeated cheap passes**. A weak model may review the same dimension multiple times from different angles and union candidate findings. A stronger model/session adjudicates BLOCK/HIGH or contested candidates before fix. Rounds 2–3 mop up fixes/verifications, not random re-review.

## Step 0 — Determine scope & round
Ask the user (or infer from their message) only what's missing:
- **What:** a worktree slug, a module name (`specs/<module>/`), or explicit files? (Default: the active worktree's dirty set.)
- **Which round:** 1 (audit), 2 (you assist fixing from an existing findings file), or 3 (verify)? Default 1.

Do NOT trigger the Session Start worktree question — review is read-only analysis, not a worktree-creating code task.

## Step 1 — Scope freeze (read-only)
1. Dirty set: `git -C <repo> diff --name-only <base>` (worktree base = its parent branch). For a whole module with no diff, scope = the module's source files.
2. Blast radius: if CodeGraph is active (`.codegraph/`), `codegraph impact`/`affected` on changed symbols → add risky dependents. Otherwise a bounded `rg -l` for the changed symbols.
3. **Nghiệp vụ source:** `specs/Tài liệu Nội trú.md` (hoặc `.docx`) — nguồn rule nghiệp vụ duy nhất. **KHÔNG** dùng `specs/<module>/02-requirements.md` làm nguồn rule nghiệp vụ.
4. Spec set (design/contract): gather `specs/<module>/{03,07,08,04}.md` if a spec module exists.
Print the frozen scope (file-groups + business rules from Tài liệu BA) before proceeding.

## Step 2 — Partitioned audit (the fan-out)
For each dimension D1–D10 that **applies** to the scope (check `applies-to` in checklist):
- Spawn repeated `mh-reviewer` passes via the **Agent tool**. Default for weak-model review: P1 direct rules, P2 regression/callers, P3 reuse/edge-cases; add optional P4/P5 for business/contract/UI.
- Inject into each prompt: the dimension id+name, pass variant, the scope file-list, and "read your dimension's entry in engine/workflows/deep-review/checklist.md".
- Instruct the reviewer to write any long per-dimension report to an audit artifact and return only a compact summary plus artifact path. Do not let full reports accumulate in the parent chat.
- **Spawn applicable passes in batches** so they run concurrently without breaking tool-call limits. For D1 (business-logic) on a high-risk module, add 2–3 independent passes and union their findings.

Collect each reviewer's compact output (artifact path + counts + top findings + coverage gaps). Read full artifacts only for merge/dedup or contested findings.

## Step 3 — Adversarial verify (M2)
For every **BLOCK/HIGH** finding, spawn a stronger skeptic/adjudicator prompted: "Try to REFUTE this finding using the live code AND `specs/Tài liệu Nội trú.md`; default to refuted=true if evidence is weak or doc-only." Mark `review_status=CONFIRMED` or `REJECTED`; do not silently drop candidates. Batch these in parallel.

## Step 4 — Dedup, severity, coverage ledger
- Dedup findings by `(file, line-range, dimension)`; merge cross-dimension duplicates (e.g. N+1 reported by D2 and D5 → one finding).
- Assign global IDs F-001…; sort by severity.
- Build the **Coverage ledger** `(file-group × D1–D10)` from the COVERAGE attestations. Any cell that is neither a finding nor `CLEAN`/`N/A` = `UNATTESTED`.

## Step 5 — Completeness check (bounded, M1 anti-roulette)
If any cell is `UNATTESTED`, or any Confirmed requirement has neither a finding nor `verified-present`: re-spawn reviewers for **only those cells/requirements** (one mini-wave). Repeat at most **K=2** times. After K, mark residual `UNATTESTED` honestly — do not pretend coverage. **Do not re-audit the whole scope.**

## Step 6 — Write findings file
Write **one** file `docs/audit/<module>-review-v<round>-<YYYY-MM-DD>.md` using the findings-schema template (summary counts + verdict + coverage ledger + findings). This file is the sole input to the fix session and the cross-round memory.

Then give the user a terse summary: counts by severity, the verdict (ĐÓNG / CHƯA ĐÓNG), top BLOCK/HIGH titles, and the file path.

## Rounds 2 & 3
- **Round 2 (fix):** the user usually drives this in a separate high-effort session, in a **worktree** (never `myhospital-fe|be` main). If asked to assist: read ONLY the findings file, fix by severity, set `status` per schema, and **self-review the fix-diff** with the checklist before closing. Route business-question findings to `05-open-questions.md` as `DEFERRED-Q`.
- **Round 3 (verify):** re-confirm each `FIXED`→`VERIFIED` (or `REOPENED`), and run a partitioned audit on **only the fix-diff** (new code = new surface), warm-started from the prior coverage ledger. Then close the module.

## After closure — learning loop (protocol §7)
Offer to promote each new/recurring bug-class to the cheapest layer: guard-hook/ESLint rule (deterministic) → `engine/rules/backend.md` or `engine/rules/frontend.md` (convention) → checklist "Known bug-classes" (new dimension/class) → auto-memory (agent mistake). This is how the harness gets more exhaustive over time and rounds drop across modules.

## Safety
Audit (rounds 1 & 3) is **strictly read-only** — never edit code. Honor the guard hook (no git history mutation, no recursive delete, no editing generated files). Never edit `myhospital-fe/` or `myhospital-be/` directly. Report actual commands run (Validation Contract).

## Optional power-mode
`engine/workflows/deep-review/workflow.js` is a deterministic Workflow-tool version of Steps 2–5 (parallel fan-out + adversarial verify + loop-until-dry completeness) — invoke via the Workflow tool with `scriptPath: engine/workflows/deep-review/workflow.js`. It needs the Workflow tool (explicit opt-in / "ultracode"). The skill path above works without it. (Composition: `engine/workflows/deep-review/manifest.json` + `engine/REGISTRY.md`.)
