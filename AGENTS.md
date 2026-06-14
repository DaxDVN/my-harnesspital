# AGENTS.md - MyHospital workspace harness

This file is the root dispatcher for coding agents. It is intentionally short:
load the repo-specific harness before touching code.

## Session Start Protocol

**At the very first prompt of every session**, before doing any code work:

1. Run `python scripts/worktree.py list` from the workspace root to list active worktrees. Do not scan `worktrees/` directly unless the task requires it.
2. Ask the user: **"Bạn muốn làm việc trong worktree nào?"** — show the slug list and slot map below.
3. Wait for confirmation before touching any code.

The user's interactive shell is `fish`, but repository automation must be shell-agnostic Python. For user-facing copy/paste commands, use fish syntax. For bash-only snippets, wrap them as `bash -lc '...'`.

Slot map (for reference when creating or selecting):

| Slot | FE | BE | SQL |
|---|---|---|---|
| 1 | :3001 | :5001 | localhost,1434 |
| 2 | :3002 | :5002 | localhost,1435 |
| 3 | :3003 | :5003 | localhost,1436 |
| 4 | :3004 | :5004 | localhost,1437 |

**`myhospital-fe/` and `myhospital-be/` are main branches — zero code edits there, ever.** All changes go into a worktree under `worktrees/<slug>/fe` or `worktrees/<slug>/be`.

If no worktree exists yet for the task, follow the **Multi-Agent Worktree + Zellij Workflow Protocol** below.

PowerShell is deprecated in this workspace. Do not use `powershell`, `pwsh`, or `*.ps1` as the primary runtime.

## Multi-Agent Worktree + Zellij Workflow Protocol

User-facing rule: the user should not need to remember long worktree commands. When the user asks to create, setup, prepare, join, attach, cleanup, or sync a worktree, treat it as a workflow execution request and run the appropriate command when terminal access is available.

### Intent routing

- `create`, `tạo`, `setup worktree mới`, `chuẩn bị worktree mới`, `mở task <slug> slot <n>` = create worktree. Run `python scripts/worktree.py create`.
- `join`, `mở lại`, `attach`, `vào worktree đang có` = join existing. Do not create. Run `python scripts/worktree.py list`, check the existing worktree, then open sessions.
- `cleanup`, `xóa`, `dọn worktree` = destructive cleanup. Ask/confirm first; kill related Zellij sessions only if requested; then run `python scripts/worktree.py cleanup`.
- `sync DB`, `sync database` = run `python scripts/worktree.py sync-db` with the requested slot/path.
- `sync main`, `sync branch chính` = run `python scripts/worktree.py sync-main`.

### Create worktree behavior

When the user asks to create a worktree and provides enough `slug` + `slot`, the agent must run:

```fish
cd /home/dax/Documents/arabica/roast
python scripts/worktree.py create --slug <slug> --slot <slot>
```

If the user says the worktree should be light, quick, dry, no DB sync, or no FE install, run:

```fish
cd /home/dax/Documents/arabica/roast
python scripts/worktree.py create --slug <slug> --slot <slot> --skip-db-sync --skip-fe-install
```

If the user only wants a preview/check first, run:

```fish
cd /home/dax/Documents/arabica/roast
python scripts/worktree.py create --slug <slug> --slot <slot> --skip-db-sync --skip-fe-install --dry-run
```

Do not respond with “you can run this command” when the current agent has permission to run terminal commands. Run it, then report the result.

### Missing information

- If `slug` is missing, ask the user for the slug.
- If `slot` is missing, first run:

```fish
cd /home/dax/Documents/arabica/roast
python scripts/worktree.py list
```

Then propose a reasonable empty slot. If the slot still cannot be inferred, ask the user to choose one.
- If orchestrator/implementer tools are missing, default to `orchestrator=claude` and `implementer=opencode`, and state that default.

### After create worktree

After successful creation, validate:

```fish
cd /home/dax/Documents/arabica/roast
python scripts/worktree.py list
test -d worktrees/<slug>/be; and echo "OK be"
test -d worktrees/<slug>/fe; and echo "OK fe"
```

Then provide/open the two Zellij sessions. 1 worktree = 2 sessions: orchestrator + implementer.

Open the sessions with the helper functions (defined in
`scripts/fish/myhospital-zellij.fish` — source it once, see
`docs/agent-rules/worktree-workflow.md`):

```fish
zorch <slug> <orchestrator_tool>
zimpl <slug> <implementer_tool>
```

`zorch`/`zimpl` print a clear error if the worktree or `zellij` is missing. If the helpers
are not sourced, use this fish-compatible fallback (references the repo layout files directly):

```fish
cd /home/dax/Documents/arabica/roast/worktrees/<slug>
zellij attach mh-<slug>-orch-<orchestrator_tool> 2>/dev/null; or zellij --session mh-<slug>-orch-<orchestrator_tool> --layout ../../scripts/zellij/myhospital-orch.kdl
```

```fish
cd /home/dax/Documents/arabica/roast/worktrees/<slug>
zellij attach mh-<slug>-impl-<implementer_tool> 2>/dev/null; or zellij --session mh-<slug>-impl-<implementer_tool> --layout ../../scripts/zellij/myhospital-impl.kdl
```

The helpers are only for opening sessions; they do not replace `scripts/worktree.py create`.
Full intent→command map: **`docs/agent-rules/worktree-workflow.md`**.

### Join existing worktree behavior

For requests like `join lại worktree bed`, run/list/check the existing worktree. Do not create:

```fish
cd /home/dax/Documents/arabica/roast
python scripts/worktree.py list
```

Then open sessions with defaults unless the user specified tools:

```fish
zorch bed claude
zimpl bed opencode
```

For requests like `mở implementer bed bằng composer`, do not create. List/check, then open only the requested session:

```fish
zimpl bed composer
```

## Scope Routing

- Work under `myhospital-fe/`: read and obey `myhospital-fe/CLAUDE.md`.
- Work under `myhospital-be/`: read and obey `myhospital-be/CONVENTIONS.md`; if a package-level `AGENTS.md` is later added, obey it too.
- Work spanning FE and BE: load both harnesses, then implement BE contract first, regenerate FE DTO/client second, and validate both sides.
- If a rule conflicts with the user's explicit instruction in the current thread, stop and report the conflict before editing.

## Severity Model

Agents must classify any risky decision before editing:

- `BLOCK`: do not implement. Stop and report the violated rule, the exact file/symbol, and a safe alternative.
- `WARN`: implementation can continue only after choosing the least risky option. Record the warning and rationale in the final response.
- `INFO`: normal convention guidance. Follow it unless local code proves a more specific pattern.

When uncertain whether a rule is `BLOCK` or `WARN`, treat it as `BLOCK` until the local harness says otherwise.

## Stop Protocol

Use this format when stopping:

```text
BLOCKED_RULE: <short rule name>
Evidence: <file/symbol or planned change that violates it>
Why it matters: <project-specific risk>
Recommended path: <safe option>
```

Do not work around a blocked rule by inventing a different pattern.

## Mandatory Discovery

Before implementation:

- Search existing code first with `rg`; reuse project patterns instead of inventing.
- For FE UI/component work, run or read `myhospital-fe/docs/components/component-inventory.generated.md` and update it with `npm run components:index` if stale or missing.
- For BE data access, inspect existing service/query patterns around the target entity before writing queries.

## Knowledge Graph (graphify)

A queryable knowledge graph of `docs/` + `specs/` (BA specs, design decisions, task slices, conventions)
is built at `graphify-out/graph.json`. It maps **design intent and spec relationships — not code**.

- **Optional, not mandatory.** graphify is a convenience for *docs/specs design-intent* questions
  (admission, inpatient, bed-day, BHYT-BHTM relationships, locked decisions). Reading the spec file
  directly is always an acceptable substitute. It is **never** a prerequisite for reading or searching code.
- **Never use graphify for code.** For FE/BE **source** use `rg` / `fd` / `bat`; for `.docx`/`.pdf` use `rga`.
  The graph does **not** contain code.
- When you do use it: `graphify query "<question>"`, `graphify explain "<node>"`,
  `graphify path "A" "B"`, `graphify affected "<node>"` (no API key needed). Treat `INFERRED` edges as unverified.
- **The current graph is STALE and must not be trusted blindly.** It was built on Windows
  (its recorded build root `graphify-out/.graphify_root` is a Windows drive path, not this workspace);
  its `src=` citations are Windows paths that do
  not exist on Linux. Until it is rebuilt on Linux, verify any graph claim against the real source doc.
  Run `python scripts/harness_doctor.py` to see the freshness/trust status.
- **Freshness probe:** the `SessionStart` hook (`python .claude/hooks/graphify_stale_check.py .`) prints a
  `[graphify] … STALE …` line when the recorded build root does not match this workspace (the Windows case
  above) or when it cannot confirm freshness. It only *flags* — it never rebuilds. When it fires, tell the
  user the graph is stale and prefer the source docs; rebuild on Linux with `/graphify` only when a fresh
  graph is actually needed. Build scope is fixed by the root `.graphifyignore`.
- Full usage for every agent (Codex, Antigravity, Grok, Gemini, Cursor — via CLI / MCP / `graphify install`):
  see **`docs/graphify-agent-guide.md`**.

## Spec-Driven Requirement & Design Protocol

Applies to **Requirement Analysis** and **Design** work in `specs/<module>/`. This protocol is
**advisory/WARN only** — there are no new hard hooks. It governs *how* specs are authored, not code.
Agents assist co-authoring (Q&A, source analysis, tradeoffs, open-question tracking, iterative edits);
they do **not** auto-generate finished specs and do **not** invent business/design decisions.

### Canonical module layout (numbered lowercase-kebab — reading order, not workflow gates)

Copy `specs/_TEMPLATE/` to start a module. `00-*` files load every session; numbers are reading slots.

```
specs/<module>/
  00-module-state.md     00-session-handoff.md     (living — read first every session)
  01-source-audit.md     02-requirements.md        03-ui.md
  04-traceability.md     05-open-questions.md      06-decision-log.md     (04/05/06 living)
  07-schema.md           08-api.md
  09-test-cases.md       10-plan.md                11-review-checklist.md
  12-change-log.md       assets/manifest.md        (living)
```

### Source precedence (two-axis)

- **Business truth** (what the system *should* do), highest first: BA DOCX / official business document >
  confirmed user/BA answer (logged in `06-decision-log.md`) > mockup / Figma / screenshot > draft notes >
  agent inference (must be flagged Assumption).
- **Technical truth** (what the system *currently can* do): existing BE APIs/services + FE generated
  client/DTOs/codebase facts, cited as `file:line`.
- **Conflict rule:** when business truth wants behavior technical truth doesn't support, do **not** let code
  silently win. Raise an entry in `05-open-questions.md` **and** record the chosen path in `06-decision-log.md`.
- Mockups are UI evidence, not business-rule authority. A mockup that implies a business rule, or contradicts
  the DOCX, becomes an Open Question — never a silent assumption.

### Requirement states

`Candidate → Confirmed` (source confirmed + acceptance criteria + feasibility checked) ·
`Candidate → Open Question → Confirmed | Deferred` ·
`Confirmed → Assumption` (agent-derived, unverified — must not back a *frozen* baseline) ·
`Confirmed → Deferred` (out of scope) · `Confirmed → Superseded` (replaced; log it in `06-decision-log.md`).

### Three-session workflow (bounds context rot)

Each session reads `00-module-state.md` + `00-session-handoff.md` + only its **primary** files, and ends by
updating both `00-*` files (and `12-change-log.md` if anything changed).

1. **Requirement Discovery & Source Mapping** — primary: `01`, `02` (Candidate), `03` (evidence), `05`,
   `assets/manifest`. Exit: every source fact is a Candidate requirement or an Open Question; no silent assumptions.
2. **Design Contract & Baseline** — primary: `07`, `08`, `03` (contract), `06`. Exit: each Confirmed
   requirement maps to a design element in `04`; non-obvious choices logged as `DL-00x`; baseline set
   `draft|frozen` in `00-module-state.md`.
3. **Delivery Plan & Review** — primary: `10`, `09`, `11`, `12`. Exit: requirement→task→test linked in `04`;
   review checklist passed or exceptions logged.

### module-state / session-handoff rule

Every spec module MUST keep `00-module-state.md` (short, loaded every session) and `00-session-handoff.md`
(append-only). Start a session by reading them; end by updating them. They are the deterministic re-entry point.

### Change-control loop (specs are wrong-then-fixed)

Practical rule: **stop only the affected task; continue unrelated tasks if safe; never let an implementer
invent business/design rules.** When something forces a spec change:

- Add to `05-open-questions.md` when it needs a human/BA answer.
- Add/update `06-decision-log.md` for any chosen path; mark replaced decisions **Superseded**.
- Append to `12-change-log.md` for the chronological history (this file is the history of record while
  `specs/` is not under git).
- Update requirements/schema/api/ui/test/plan **only after** the question is answered / decision logged.
- Use `graphify affected "<node>"` to find every doc impacted by the change.

Implementers (any agent, incl. Codex/opencode) that discover a gap MUST file an **Implementation Discovery
Report** and pause only the affected slice — they do not edit `02/03/06/07/08` themselves. Report template:

```text
# Implementation Discovery Report
Module / affected slice / type (missing-requirement | codebase-constraint | contradiction | infeasible-design)
What I found (evidence: file:line or DOCX §)
Why it blocks/changes the spec (which <PREFIX>-R-00x or DL-00x)
Options (cost/impact) — do NOT pick a business/design rule
Technical recommendation only
Requested routing: open-question? decision from owner/BA? tasks to PAUSE vs CONTINUE
```

### Worktrees and specs

- **Do not** use `scripts/worktree.py` for Requirement/Design sessions. They are documentation-only
  (no build, DB, ports), edited directly on `specs/` in the main workspace.
- Spec sessions are not "code work" for the **Session Start Protocol**; do not ask for or create a worktree
  for Requirement Analysis or Design sessions unless the user explicitly asks.
- **Use** `scripts/worktree.py` for the later **Development** phase that *consumes* a finished spec.

### Advisory vs blocking

All rules in this section are WARN/advisory. Surface a clear warning (do not silently proceed) in only two
cases: (a) editing a `frozen` baseline without a `DL-00x`, and (b) an implementer changing a `Confirmed`
business rule. Neither is a hard hook.

## Multi-Agent Execution

This section is standing user authorization for Codex sessions that read this harness to use subagents for multi-task implementation work.

- The primary agent acts as the implementation orchestrator: read harnesses/specs/tasks, build the dependency order, classify risk, own integration, review, and validation.
- Use `gpt-5.3-codex-spark` workers only for bounded implementation tasks with clear, disjoint file/module ownership.
- Spawn workers by dependency-safe rounds, not all at once. After each round, wait for worker results, review diffs, integrate, validate, then decide the next round.
- Do not delegate architecture, cross-contract decisions, blocker resolution, final validation ownership, or any task that requires violating a `BLOCK`/`WARN` protocol.
- For work spanning FE and BE, implement the BE contract first, regenerate FE DTO/client second, and implement FE usage after the contract is available.
- Each worker prompt must say the worker is not alone in the codebase, must not revert changes made by others, must stay inside its owned scope, and must report files changed plus validation commands run.

## Local Agent Browser Smoke Login

At session start only, remember this local test credential when Agent Browser needs to login: customer code `HMU`, username `admin`, password `123456`.

## Validation Contract

Report actual validation commands run. If a command cannot run, say why. Do not claim the harness is satisfied without either running validation or naming the residual risk.

## Workspace File Organization

The workspace root (`/home/dax/Documents/arabica/roast`) is reserved for harness files only (`AGENTS.md`, `CLAUDE.md`) and repo/tooling folders. Prefer relative paths in docs and scripts. Never save artifacts directly to root.

| Artifact type | Save to |
|---|---|
| Task plans, implementation plans | `docs/tasks/` |
| Session analysis, audit reports, research notes | `docs/session-notes/` |
| Test cases, test setup docs | `docs/testing/` |
| Browser screenshots, UI captures | `docs/testing/screenshots/` |
| DTO dumps, API diffs, BE diffs | `docs/session-notes/` |
| One-off scripts (Python) | `scripts/` |
| Feature specs, BA docs | `specs/<module>/` |

This applies to **all agents** (Claude, Codex, Antigravity): if a tool generates a file as a side-effect (screenshot, report, diff), save it to the correct subfolder before returning.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- graphify is **optional** and scoped to `docs/`+`specs/` **design intent — not code**. Use it only for a
  docs/specs design-decision/relationship question, and only as an alternative to reading the spec directly.
  For code use `rg`/`fd`/`bat`; for `.docx`/`.pdf` use `rga`. Never run graphify before reading source code.
- **Trust check:** the current graph is Windows-built and stale (see *Knowledge Graph (graphify)* above).
  Confirm `graphify-out/.graphify_root` matches this workspace — or run `python scripts/harness_doctor.py` —
  before relying on graph output; if it does not match, read the source docs instead.
- When used: `graphify query "<question>"` / `graphify path "<A>" "<B>"` / `graphify explain "<concept>"`
  return a scoped subgraph. `GRAPH_REPORT.md` is for broad architecture orientation only.
- After materially changing `docs/`/`specs/`, the graph needs a Linux rebuild (`/graphify`) to be fresh; the
  freshness hook only flags staleness. The graph build scope is fixed by the root `.graphifyignore`.
