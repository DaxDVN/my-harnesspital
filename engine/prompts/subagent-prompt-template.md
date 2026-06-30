# Subagent Prompt Template — canonical orchestrator→worker shape

The **one** fill-in-the-blanks structure the PM orchestrator (and any dispatcher) uses to prompt **every**
worker it spawns — whether that worker is a **Claude subagent** (Task tool) or an **OpenCode model**
(`scripts/oc_worker.py` → `mh-reviewer-oc` / `mh-fixer`). It encodes Anthropic's current prompting guidance
so each worker is prompted per best practice for its `(model, effort)` tier. The orchestrator transfers
memory **by reference** (paths/queries — never pasted bodies); see `engine/rules/context-manifest.md`.

## Machine-enforced — this template is now a LINT GATE (not advisory)

Authoring a worker prompt that does NOT follow this template is **blocked at dispatch**. The PreToolUse hook
`engine/hooks/subagent_prompt_guard.py` lints every prompt the orchestrator sends to a **Claude subagent**
(`Task` tool) or to an **external coding tool** (`agent_exec.py` / `oc_worker.py` → opencode/grok/agy) using
`scripts/subagent_prompt_lint.py`, and **exits 2 (BLOCK)** on a sub-standard *mutating-worker* prompt, naming the
missing guideline elements. Read-only/search/review dispatches (Explore, mh-reviewer, `--read-only`, …) get a
light advisory bar and are never hard-blocked.

The deterministic bar (worker profile, threshold 0.80; `intent` + `allowlist` are CRITICAL; a destructive
delete/remove/drop must carry a stop/verify gate):

| Signal the linter requires | This template's section | PREAMBLE-covered on the `oc` channel? |
|---|---|---|
| GOAL/INTENT — the why **(critical)** | ZONE B §1 | no — author must write it |
| write-allowlist / scope boundary **(critical)** | ZONE B §3 | no — author must write it |
| XML-tagged structure (`<document>`/`<scope>`/…) | ZONE A + §3 | no — author must write it |
| validation commands | ZONE B §6 / DoD | no — author must write it |
| output contract / lead-with-TLDR | ZONE B §6 | yes (`oc_worker.PREAMBLE`) |
| anti-hallucination grounding | ZONE A / §2 | yes |
| ponytail / minimal-diff | ZONE B §5 | yes |
| subagent identity + no-ask autonomy | ZONE B §0/§4 | yes |

On the `task` channel (Claude subagent) there is NO PREAMBLE, so **all** of the above must be in the prompt you
author. Self-check before dispatch: `python scripts/subagent_prompt_lint.py --prompt-file <file> --channel {task|oc}`.

## The 3 invariants EVERY subagent prompt must carry

1. **SUBAGENT MARKER** — the worker MUST know it is a subagent (not the main agent, not interactive with a human).
   It must NOT ask the parent agent or any human mid-task. If it hits ambiguity → STOP + report, never ask.
2. **CONVENTION HYDRATION IS MANDATORY** — before any review/write/test, the worker MUST read the injected
   rule_card paths + the recommended_prompt_file. Skipping convention hydration is a BLOCK, not a shortcut.
3. **ANTHROPIC PROMPTING BEST PRACTICES** — the worker prompt is shaped per
   `docs/anthropic-guideline/build-with-claude-prompt-engineering-claude-prompting-best-practices.md`
   + `docs/anthropic-guideline/build-with-claude-prompt-engineering-prompting-claude-opus-4-8.md`
   + `docs/anthropic-guideline/build-with-claude-prompt-engineering-prompting-claude-fable-5.md`.
   This file distills them; the orchestrator does NOT paste the guideline bodies — it cites them.

Derived from (read + cite when tuning this file):
`docs/anthropic-guideline/build-with-claude-prompt-engineering-claude-prompting-best-practices.md`,
`docs/anthropic-guideline/build-with-claude-prompt-engineering-prompting-claude-opus-4-8.md`,
`docs/anthropic-guideline/build-with-claude-prompt-engineering-prompting-claude-fable-5.md`.

## Render order (load-bearing)

Assemble the worker prompt in **two zones, top to bottom**. Long reference material goes FIRST, the actual ask
goes LAST — queries placed at the end improve response quality up to ~30% on multi-document inputs
(best-practices.md §Long context prompting). Wrap every referenced doc in `<document>`/`<source>` XML tags so the
worker parses reference vs. instruction unambiguously (best-practices.md §Structure prompts with XML tags).

```text
ZONE A — CONTEXT MANIFEST (by reference, long material, top)
ZONE B — THE ASK (identity → intent → task → scope → autonomy → ponytail → output, bottom)
```

---

## ZONE A — CONTEXT MANIFEST  (paths/queries only, never pasted bodies)

> By reference per `engine/rules/context-manifest.md`. The worker hydrates itself by loading each entry **live**
> and treating it as current truth. A named path it cannot find/verify is a STOP, not a guess.
> Order: longest/most-foundational reference first; the ask follows in ZONE B.
>
> **MANDATORY HYDRATION (BLOCK if skipped)**: the worker MUST read every `<document>` below BEFORE any review,
> write, test, or scaffold action. Convention hydration is not optional — a worker that dives into code without
> reading its rule cards WILL violate conventions and produce rework. Only after hydration may it act.

```xml
<documents>
  <document index="1">
    <source><FILL: rule_card — output of `python scripts/rule_card.py fe "<task>"` AND `... be "<task>"`></source>
    <load>both cards, both sides, always — non-negotiable</load>
  </document>
  <document index="2">
    <source><FILL: recommended_prompt_file — engine/prompts/<role>.md the route picked></source>
  </document>
  <document index="3">
    <source><FILL: recalled_notes — second-brain note PATHS from learning_recall.py (paths only)></source>
  </document>
  <document index="4">
    <source><FILL: ledger_path — engine/workflows/pm-orchestrator/runs/<scope>/run-NNN/00-pm-state.md></source>
  </document>
  <document index="5">
    <source><FILL: spec_slice — the SPECIFIC specs/<module>/NN-*.md#section for THIS phase, not the whole spec></source>
  </document>
</documents>
verify_live: true
hydration_is_block: true
```

If the task spans long source/spec, instruct the worker to **quote the relevant lines first** before acting, to
cut through noise (best-practices.md §Long context prompting — ground responses in quotes).

---

## ZONE B — THE ASK

### 0. SUBAGENT IDENTITY  (load-bearing — top of ZONE B)

> This is the marker that tells the worker it is a SUBAGENT, not the main interactive agent. Without it, the
> worker may try to "ask the user" mid-task, which is fatal in a headless dispatch (no human is watching, and
> asking the parent agent creates a feedback loop).

```text
You are a SUBAGENT dispatched by the PM orchestrator (Opus 4.8 low). You are NOT the main interactive agent.
- The owner is NOT watching this turn. There is no human to answer you mid-task.
- Do NOT ask the parent agent or any human for clarification, worktree choice, or scope expansion.
- Do NOT pause to "check with the user" — that path is closed.
- If you hit genuine ambiguity (business/clinical/billing/permission rule unclear, schema unclear, scope
  ambiguous): STOP, report the ambiguity as a `NEEDS-OWNER-DECISION` finding in your output, and end the turn.
  Do NOT invent an answer, do NOT guess, do NOT ask.
- For everything else (reversible actions that follow from this request, tool choice, file reads within scope,
  validation commands): proceed autonomously without asking.
- HYDRATION FIRST: read every <document> in ZONE A before any review/write/test/scaffold action. Skipping
  convention hydration is a BLOCK, not a shortcut — you WILL violate conventions and produce rework.
```

### 1. GOAL + INTENT  (the reason, not only the request)
> fable-5.md §Give the reason, not only the request.

```text
I'm working on <larger task> for <who it's for>. They need <what the output enables>.
With that in mind: <one-line statement of what this worker is for>.
```

### 2. TASK  (imperative — act, don't suggest)
> best-practices.md §Tool usage — "Change this function", not "can you suggest changes".

```text
<Imperative directive>. <e.g. "Change X to do Y." / "Apply the fix in <file>." — never "could you look at…">
```

### 3. SCOPE + BOUNDARIES  (literal — state scope explicitly)
> opus-4-8.md §More literal instruction following (Opus 4.8 does NOT generalize an instruction from one item to
> the next — state the scope literally); fable-5.md §State the boundaries.

```text
allowlist:        <worktree + the EXACT files/dirs this worker may write>
do_not_touch:     <files/areas explicitly off-limits — e.g. generated DTO/client, EF migrations, other agents' slices>
scope_is_literal: <e.g. "Apply to EVERY occurrence of X, not just the first." — never leave 'all' implicit>
worktree:         <the resolved worktree slug + slot — do NOT ask the parent agent to pick a worktree; it is given>
assessment_only:  When the owner is thinking out loud / describing a problem / asking a question rather than
                  requesting a change, the deliverable is your ASSESSMENT. Report findings and STOP — do not
                  apply changes until asked.
```
A too-broad or missing allowlist → the worker stops and reports `NEEDS-TIGHTER-SCOPE`, never asks.

### 4. AUTONOMY  (subagent-tuned — NO interactive pause)
> fable-5.md §Rare cases of early stopping + §State the boundaries; best-practices.md §Balancing autonomy and
> safety. (Tier hard-confirm policy is gate-by-risk — see PER-TIER NOTES.)
>
> **Subagent override**: the standard autonomy clause says "pause and ask" — for subagents, asking is removed.
> The only allowed stop is a `NEEDS-OWNER-DECISION` finding for genuine irreversible ambiguity.

```text
You are operating autonomously as a SUBAGENT; no human is watching and no parent agent will answer you. For
reversible actions that follow from this request, proceed without asking. The ONLY allowed stop condition is
a genuine business/clinical/billing/permission/migration ambiguity that you cannot resolve from the hydrated
conventions or the spec slice — in that case, emit a `NEEDS-OWNER-DECISION` finding with the exact question +
the options + your recommended default, then end the turn. Do NOT use destructive shortcuts (no --no-verify,
no discarding unfamiliar in-progress files). Do NOT end on a promise ("I'll…") — either do it or report it.
```

### 5. PONYTAIL  (no over-engineering)
> `engine/rules/ponytail.md`; best-practices.md §Overeagerness; fable-5.md §Consider all effort levels.

```text
Reuse first; smallest correct diff. Do NOT add scope, abstractions, helpers, config, defensive error handling for
cases that can't happen, or docs/comments/type annotations beyond what THIS task needs. A bug fix doesn't need
surrounding cleanup. Validate only at real boundaries (user input, external APIs); trust internal guarantees.
Never simplify away validation, security, permission, clinical/billing correctness, generated-code discipline, or
required artifacts. (See engine/rules/ponytail.md.)
```

### 6. OUTPUT CONTRACT
> fable-5.md §Strong instruction following (lead with the outcome) + §Ground progress claims during long runs;
> context-manifest.md `return_format`; harness blind-coordinator rule.

```text
Lead with the outcome: first sentence = the TLDR the owner would ask for ("what happened / what you found").
Supporting detail after. Be selective, not compressed (no arrow-chains/jargon/fragments).
GROUND every claim against a tool result from THIS session — if something isn't verified, say so; if a check
failed, show the output. Return a COMPACT blob (counts / paths / flags) + the artifact PATH. Do NOT paste long
output (full diffs / file dumps / md bodies) back into your message — write it to the artifact and return its path.
If you stopped on `NEEDS-OWNER-DECISION`, the TLDR is exactly that + the question + options + recommended default.
return_format: <FILL: the exact compact shape the coordinator authors the ledger from>
```

---

## PER-TIER NOTES  (orchestrator dispatch tuning — not pasted into the worker prompt)

How to fill/dispatch this template for the worker's `(model, effort)` tier. Tiers map to `(model, effort)` via
`scripts/tier_policy.json` — never bake a model name into the template.

1. **Effort ladder** (opus-4-8.md §Calibrating effort and thinking depth; fable-5.md §Consider all effort levels):
   - `low` — short, scoped, latency-sensitive work that is **not** intelligence-sensitive.
   - `high` — the **minimum** for intelligence-sensitive work.
   - `xhigh` — default for coding / agentic use cases.
   - `max` — correctness-over-cost; intelligence-demanding tasks where you accept diminishing token returns.
   If you see shallow reasoning on a complex task, **raise effort** rather than prompting around it.

2. **Fan-out calibration by model:**
   - **Opus 4.8 UNDER-spawns** subagents by default (opus-4-8.md §Controlling subagent spawning) — when the
     phase fans out across items / multiple files, **explicitly encourage** appropriate parallel spawning.
   - **Fable 5 / Opus 4.6 OVER-spawn** (fable-5.md §Parallel subagents; best-practices.md §Subagent
     orchestration) — **limit** them: "work directly for single-file or sequential tasks; spawn only for
     parallel, isolated, independent workstreams."

3. **Never instruct a worker to echo / transcribe / explain its reasoning as response text.** On Fable 5 this
   can trigger the `reasoning_extraction` refusal and elevate fallbacks (fable-5.md §Recommended scaffolding
   changes). If the orchestrator needs reasoning visibility, read the worker's structured `thinking` blocks — do
   not ask it to reproduce them in prose.

4. **Coverage-first review framing.** For review/audit workers on Opus 4.8: instruct "report every issue
   including low-severity/uncertain, with confidence + severity; a downstream step filters" — its literalism
   makes "be conservative / only high-severity" silently DROP real bugs (opus-4-8.md §Code review harnesses).

5. **Dispatching a non-Anthropic (OpenCode) worker — via `scripts/oc_worker.py` ONLY** (applies to EVERY recipe
   that uses an OpenCode model: batch-bugfix fix, feature implement, espresso fix, refactor, trivial,
   review/triage — not just deep-review). `agent()` spawns Anthropic only; OpenCode-Go models
   (deepseek/glm/kimi/minimax/mimo) run through `oc_worker.py`, which already loads the right scaffolding — do
   NOT hand-roll a bare `opencode run`. The run-001 failure (glm replied a one-line plan, zero tool calls) was a
   CALLING-METHOD bug, not the model. Rules:
   - oc_worker sets `OPENCODE_CONFIG=.opencode/worker.json` + the proper agent (`mh-reviewer-oc` read-only /
     `mh-fixer` mutating — each has a real system prompt). NEVER `--agent plan` (opencode plan-mode = outline + stop).
   - The worker runs in `--dir <worktree>` and CANNOT see harness-root files. The worker `--prompt` MUST be
     worktree-relative — never tell it to read `engine/...`, a checklist, or a rule-card PATH. Inject that
     context with `oc_worker --rule-card <file>` (oc_worker reads it from the harness root and inlines the
     CONTENT) or inline it directly.
   - The worker OUTPUTS its result as its final reply (oc_worker captures it to `--out`); never tell it to "write
     to a file path".
   - Verify-output gate: an OpenCode worker that returns empty / no coverage / a planning-only stub is FAILED →
     auto-fall-back to the Anthropic reviewer/implementer for that unit (never silently lose coverage).

6. **OpenCode worker subagent marker** — `oc_worker.py`'s PREAMBLE + the `.opencode/worker.json` agent prompts
   carry the SAME subagent identity marker as Claude subagents (see §0 above). OpenCode models MUST know they
   are dispatched workers, not interactive agents. The marker is in the agent system prompt (worker.json) +
   the PREAMBLE (oc_worker.py), so the orchestrator does not need to repeat it in the per-task prompt.
