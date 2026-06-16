---
name: mh-fix
description: Safe bug-fix companion to the mh-review harness. Drives fixing a finding from an mh-review findings file, or a standalone bug, without introducing regressions or convention drift. Use when a review findings file exists and you need to work through OPEN findings, or when fixing a single known bug before merge. Trigger: "fix this finding", "fix bug X", "apply review fixes", "fix before merge", "/mh-fix".
---

# mh-fix — safe-fix driver

Companion to `mh-review`. The review harness produces a findings file and a Coverage ledger; this skill **works off that file** to close findings safely — one at a time, severity-ordered, with a mandatory self-review of every fix-diff before marking FIXED. It is the dedicated Round-2 driver that `mh-review` protocol §4 describes but does not fully specify.

Source-of-truth bundle: [`engine/review/protocol.md`](engine/review/protocol.md) · [`engine/review/findings-schema.md`](engine/review/findings-schema.md) · [`engine/review/checklist.md`](engine/review/checklist.md) · `AGENTS.md` Forbidden Actions.

---

## 1. Scope & safety pre-flight

**Before touching any file:**

1. Confirm the fix target: either a findings file (`docs/audit/<module>-review-v<n>-<YYYY-MM-DD>.md`) OR a plainly stated bug + its `file:line`. If neither is clear, ask.
2. Confirm a worktree is active. Run:
   ```fish
   python scripts/worktree.py list
   ```
   All edits go into `worktrees/<slug>/fe` or `worktrees/<slug>/be` ONLY. If no worktree exists, **stop** and tell the user:
   ```
   BLOCKED_RULE: worktree-required
   Evidence: no active worktree for this task
   Why it matters: AGENTS.md forbids direct edits to myhospital-fe/ or myhospital-be/
   Recommended path: python scripts/worktree.py create --slug <slug> --slot <slot>
   ```
3. If a findings file is the input, **read only that file** — it is the complete cross-round memory per findings-schema. Do not re-audit the scope; do not invent findings. The file is the contract.
4. Read-only research (CodeGraph, spec files, rule docs) may happen anywhere; edits happen only in the confirmed worktree.

---

## 2. Per-finding fix loop (BLOCK → HIGH → MED; skip LOW/NIT)

Iterate findings with `status: OPEN` (or `REOPENED`), severity-first. For each:

### 2a. Locate

Use **CodeGraph** to locate the symbol/call-path (if indexed: `codegraph node <symbol>` or `codegraph explore "<question>"`). Fall back to a bounded `rg -l` in the worktree scope only. Do not broad-scan. Confirm the exact `file:line` matches the finding's `location` field.

### 2b. Research the correct fix

Convention canon — highest authority first:

1. `engine/rules/backend-rules-conventions-patterns.md` (BE) or `engine/rules/frontend-rules-conventions-patterns.md` (FE) — **these are the live convention spine**. Do NOT rely primarily on `myhospital-be/CONVENTIONS.md`; a prior audit found it wrong in places (audit record: `/home/dax/Documents/arabica/velvet/notes/myhospital-be-conventions-audit-2026-06-15.md`).
2. `specs/<module>/{02-requirements,06-decision-log,07-schema,08-api}.md` for business/contract truth.
3. Existing live code as exemplar — CodeGraph `callers`/`callees` to find the canonical pattern already in the codebase. Prefer reusing an existing helper or shape over inventing a new one. The `mh-scaffold` skill defines the right structural shape for new BE/FE artifacts when a new file is warranted.
4. The finding's own `fix:` field is a recommendation, not a mandate — apply it only if it aligns with the above canon. If the finding's suggested fix conflicts with live conventions, use the canon and note the deviation.

For **D1 business-logic findings**: do NOT invent a business/design rule. If fixing requires a business decision not logged in `specs/<module>/06-decision-log.md`, treat it as a `DEFERRED-Q` (step 4 below).

### 2c. Apply the minimal fix

Edit only the file(s) necessary to close this specific finding. Do not refactor unrelated code in the same pass. Keep the fix surgical — the self-review in step 3 catches collateral damage.

---

## 3. Self-review the fix-diff (the regression killer — M3)

**Before marking any finding FIXED**, run the deterministic scanner on the changed files:

```fish
python scripts/mh_scan --scope <space-separated changed files> --format summary
```

The scanner pack catches (non-exhaustive): raw `Exception` catch/throw (V12), literal error code strings (V3), legacy listing patterns (V4), missing `[RequireAuth]` (V1), new `BeginTransactionAsync`/`IProcessLockService` (V6), hard-delete instead of soft-delete (V10), `Dictionary<>` in DTO (V13), N+1 patterns.

**A fix that introduces a new scanner hit is not done.** Resolve the hit or explain why it is a false positive before proceeding.

Then re-check the **relevant checklist dimension(s)** (`engine/review/checklist.md` D1–D10) on the diff only — not the whole scope. Confirm:

- No new bug in the same dimension the finding lived in.
- No cross-dimension regression (especially: D2/D5 for BE data-access, D3/D10 for FE state/reuse, D6 for auth).

If the self-review uncovers a new issue, open a new finding in the findings file (F-00N+1, `status: OPEN`, `round_found: current`) and fix it in the same session if severity >= HIGH, or log it for the next round otherwise.

---

## 4. Status update in the findings file

After a successful fix + clean self-review, update the findings file:

- Set `status: OPEN → FIXED` for the finding.
- Append a brief note under the finding: diff location (worktree-relative path), what was changed, scanner result (`CLEAN` or FP rationale).

For business-question findings (BHYT/admission/bed-day ambiguity, missing `DL-00x`, requirement not Confirmed):

- Do **not** invent a business rule. Do **not** leave a guess in the code.
- Set `status: DEFERRED-Q`.
- File an **Implementation Discovery Report** in `specs/<module>/05-open-questions.md` (template in `AGENTS.md §Change-control loop`). Include: module, affected finding ID, what the ambiguity is, technical options with cost/impact, and explicit routing (which decision needs a human/BA).
- `DEFERRED-Q` is not a review miss; it is correct routing.

Status lifecycle (from findings-schema):

```
OPEN ──fix──▶ FIXED ──verify──▶ VERIFIED       (main path)
  │                  └─regression─▶ REOPENED
  ├─ adversarial bác bỏ ─▶ REJECTED  (keep for learning)
  └─ business question  ─▶ DEFERRED-Q (→ 05-open-questions + Discovery Report)
```

Setting `FIXED` is this skill's output. `VERIFIED` is set by the subsequent `mh-review` Round 3 verify pass.

---

## 5. Hand-off report

After processing all eligible findings in the session, report:

```
Files changed: <worktree-relative paths>
Findings fixed: <IDs> → FIXED
Findings deferred: <IDs> → DEFERRED-Q (routed to specs/<module>/05-open-questions.md)
Findings skipped (LOW/NIT): <IDs> — backlog, no round spent
Scanner result: CLEAN on all changed files | <exceptions with FP rationale>
Validation commands run: <exact commands + output summary>
Remaining OPEN/REOPENED: <IDs + severities>
Next step: Round 3 verify via mh-review | BA answer needed for DEFERRED-Q | nothing — module ready
```

**Never** run `git commit`, `git push`, or `git reset`. The guard hook blocks these. Leave the diff in the worktree for the user to review and commit.

---

## 6. Learning loop (protocol §7 — promote recurring bug-classes)

After closing findings, for each bug-class that is **new** or **recurring** across modules, suggest promotion at the cheapest layer that can catch it:

1. **Deterministic?** → propose a guard-hook rule (`.claude/hooks/myhospital_guard.py`) or ESLint rule — catches it free forever. Name the exact pattern to match.
2. **Convention gap?** → propose an addition to `engine/rules/backend-rules-conventions-patterns.md` or `engine/rules/frontend-rules-conventions-patterns.md` — shifts the error left to implementers.
3. **New dimension pattern?** → propose a "Known bug-class" line in `engine/review/checklist.md` under the correct D1–D10 dimension (with `file:line` exemplar if available) — raises Round-1 recall for future modules.
4. **Agent mistake pattern?** → propose an auto-memory entry (`type: feedback`).

Report suggestions as a numbered list; do not apply them unless the user confirms. Promotion decisions belong to the user.

---

## Safety

- Read-only research (CodeGraph, spec files, rule docs, `git diff`, `git status`) is allowed anywhere in the workspace.
- **Edits happen ONLY inside a confirmed `worktrees/<slug>/{fe,be}` path.** Any edit path outside a worktree is a hard stop — report `BLOCKED_RULE: worktree-required`.
- Never auto-commit, auto-push, or auto-merge. Git history mutation is guard-blocked.
- Never edit generated files by hand (`generated-dtos.ts`, `generated-api-client.ts`, `Constants.ts`, EF migrations). If a fix requires a contract change, regenerate: `npm run dtos:update` / `npm run client:generate` / `dotnet ef migrations add`.
- Never edit `myhospital-fe/` or `myhospital-be/` directly (main branches).
- Honor the full Forbidden Actions list in `AGENTS.md`.
- Report actual validation commands run. If a command cannot run, say why. Do not claim the fix is clean without either running the scanner or naming the residual risk.
