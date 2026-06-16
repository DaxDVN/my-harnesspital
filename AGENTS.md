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

**Default:** `myhospital-fe/` and `myhospital-be/` are main branches — do not edit them directly. All normal changes go into a worktree under `worktrees/<slug>/fe` or `worktrees/<slug>/be`.

### Owner-Authorized Bypass Protocol

The workspace owner may explicitly authorize bypassing harness rules for the current session, including
direct work in `myhospital-fe/` or `myhospital-be/`, when maintenance or recovery requires it.

When the user explicitly says they allow bypass (for example: "cho phép bypass", "bypass rule",
"override harness", or equivalent wording):

- Treat the relevant harness block as `WARN` instead of `BLOCK` for that session and continue.
- State the bypassed rule and the reason in the final response.
- Keep the smallest practical scope: do only the requested maintenance/recovery work.
- Continue to avoid needless destructive actions. If an action is destructive and not explicitly requested,
  ask for confirmation first.
- Generated/managed files should still be regenerated rather than hand-edited unless the owner explicitly
  asks for emergency manual intervention.

Worktree/Zellij is **user-driven** (manual) — see **`docs/guides/worktree-zellij-manual.md`**. Agents must **not** auto-create or auto-open worktrees/sessions; print the command for the user to run.

PowerShell is deprecated in this workspace. Do not use `powershell`, `pwsh`, or `*.ps1` as the primary runtime.

## Self-Learning — main-brain · engine · second-brain (the harness's memory)

The harness is organized like a person who cannot remember everything: a concise **brain**, a detailed
**recipe library**, and **scratch notebooks**. Every agent + every compaction MUST keep these straight.

| Tier | Role | Holds | Loaded? | Who writes |
|---|---|---|---|---|
| **`main-brain/`** | the BRAIN — source of truth | distilled lessons + durable cross-cutting truths/decisions + "what exists & when to use it"; **refers down** to `engine/` (which holds the skills/agents/rules) | **always** (lean — bloat burns tokens) | **owner only, via `/promote`** (guard BLOCKS all agent writes) |
| **`engine/`** | the recipe library / governing core — **CANONICAL HOME for every asset** | rules (convention canon + policies), review protocol, routing, **AND the skills / agents / hooks / workflows themselves** — the ONE source every coding tool shares | on-demand | maintenance |
| `.claude/` · `.codex/` · `.opencode/` | per-tool **pointers + config** (NOT copies) | reach engine's assets via each tool's own mechanism — Claude: `.claude/{skills,agents,hooks,workflows}` are **symlinks → `engine/…`**; Codex: `[[skills.config]]` / symlink; opencode: `instructions` glob. Add a new tool = add pointers, once | on invocation | the pointer only (assets live in `engine/`) |
| **`second-brain/`** | scratch notebooks — learning buffer | provisional learnings ("remember this / pay attention / idea"); may be right OR wrong | never (on-demand) | **any agent, freely (no gate)** |
| `docs/` · `specs/` · `scripts/` | reference · SDD · commands | (unchanged) | freely |

**Write rules (BINDING):**
- Append to **`second-brain/`** freely when the owner says "nhớ cái này / để ý cái này", or you discover a
  durable cross-cutting fact worth keeping (one file per learning, `status: provisional`). This is the
  **in-repo, cross-tool** learning store — NOT `~/.claude/.../memory/` (Claude-only, ephemeral).
- **NEVER write `main-brain/`.** It is the gated source of truth; the guard hook blocks every agent write.
  Knowledge reaches it ONLY through the owner-invoked **`/promote`** skill (owner authorizes with
  `! touch main-brain/.promote-unlock`). `/promote` is **explicit-only — never self-invoke it.**

**Boundary test (which tier?):** "always use BaseService" → coding convention → `engine/rules/`. "admission
step 3 confirms BHYT; owner decided never auto-patch public-endpoint auth" → durable cross-cutting
truth/decision → `main-brain/` (via promote). "decision scoped to one module" → `specs/<m>/06-decision-log.md`.
"I suspect bed-day double-counts" → provisional → `second-brain/`.

**Lifecycle of a learning:** drop it in `second-brain/` (detailed) → owner reviews → `/promote` either
**distills it into `main-brain/`** (a lean truth/lesson) or **graduates it into a new `.claude/skills/<x>`**
(a reusable recipe). It lives until promoted/graduated OR the owner deletes it.

## Worktree + Zellij — USER-DRIVEN (manual; agents do NOT auto-run)

Worktree and Zellij are **driven by the user**, not automated by the agent. The user wants explicit
control over creating / opening / cleaning worktrees and Zellij sessions.

**Agent rules:**
- Do **NOT** auto-run `worktree.py` (create/cleanup/sync), `zorch`, `zimpl`, `zkillwt`, or any Zellij
  command in response to intent words ("create / join / setup / cleanup / sync worktree").
- When the user asks about worktrees/Zellij: **print the exact command for them to run** (fish syntax)
  and/or point to the manual guide. Execute a command **only** if the user explicitly says "run it /
  do it for me" for that specific command.
- Step-by-step the user follows: **`docs/guides/worktree-zellij-manual.md`**. Low-level command
  reference: `engine/rules/worktree-workflow.md` (reference only — not an auto-execution mandate).

The default safety rule still holds: **do not edit `myhospital-fe/` or `myhospital-be/` directly — all
normal code changes go in a `worktrees/<slug>/…`** that the user created manually, unless the
Owner-Authorized Bypass Protocol above is explicitly invoked.

## Agent Shortcuts & Tool Routing (proactive — so the user need not memorize commands)

The user should speak naturally or use short prompts; the agent maps intent → the right harness tool
and **uses it proactively**. Full cheat-sheet + short-prompt aliases: **`engine/agent-shortcuts.md`**
— read it and treat its aliases as triggers.

Compact routing (intent → tool; auto-use unless marked user-driven):

| Intent | Tool the agent uses |
|---|---|
| scaffold endpoint/service/listing/error path · new FE page/list/form/module | skill **`/mh-scaffold`** |
| implement / build a feature/page/module | skill **`/mh-implement`** (in a worktree the user opened) |
| fix a bug / a review finding before merge | skill **`/mh-fix`** |
| BE convention scan (bug-classes) | **`just mh-scan`** (signal-first; `--advisory` full; `--fail-on high` CI) |
| FE structural rules (raw fetch / dead dtos / name-compare / no-axios) | **`just mh-scan`** (ast-grep bridge, FE-gated) |
| harness health · convention drift · snapshot | **`just doctor`** · **`just convention-truth`** · **`just harness-backup`** |
| "where/how/what-calls X", locate code | **CodeGraph** (`codegraph_explore` / `codegraph explore`) then bounded `rg` |
| CodeGraph index status / sync | **`just codegraph-status`** / **`just codegraph-sync-main`** |
| regenerate FE DTOs / client | **`npm run dtos:update`** / **`client:generate`** (FE worktree) |

**USER-DRIVEN — never auto-run (print the command / point to the guide):**
- **Review** — `/mh-review` is **explicit only**: run it solely when the user asks for a review/audit by
  name (confirm scope first). Do **not** auto-trigger it after implement/fix.
- **Worktree / Zellij** — see the user-driven rule above + `docs/guides/worktree-zellij-manual.md`.

## Scope Routing

- Work under `myhospital-fe/`: read and obey `myhospital-fe/CLAUDE.md`.
- Work under `myhospital-be/`: read and obey `myhospital-be/CONVENTIONS.md`; if a package-level `AGENTS.md` is later added, obey it too.
- Work spanning FE and BE: load both harnesses, then implement BE contract first, regenerate FE DTO/client second, and validate both sides.
- If a rule conflicts with the user's explicit instruction in the current thread, stop and report the conflict before editing, unless the Owner-Authorized Bypass Protocol has been explicitly invoked for this session.

## Severity Model

Agents must classify any risky decision before editing:

- `BLOCK`: do not implement. Stop and report the violated rule, the exact file/symbol, and a safe alternative.
- `WARN`: implementation can continue only after choosing the least risky option. Record the warning and rationale in the final response.
- `INFO`: normal convention guidance. Follow it unless local code proves a more specific pattern.

When uncertain whether a rule is `BLOCK` or `WARN`, treat it as `BLOCK` until the local harness says otherwise.

## Forbidden Actions (ALL agents & tools)

Hard `BLOCK` rules for **every** agent — Claude Code, Codex, opencode, Cursor, and any other, unless
the Owner-Authorized Bypass Protocol has been explicitly invoked for the relevant action in the current
session.
Obey them **by instruction even where no enforcement hook exists** (hooks are per-tool; this file
is the cross-tool source of truth). Claude Code *also* enforces them via
`.claude/hooks/myhospital_guard.py` (PreToolUse); the same script is payload-tolerant and can be
wired into another tool's hook system — see `engine/rules/cross-tool-enforcement.md`.

- **No git history mutation:** `git commit`, `git push`, `git reset --hard`, `git clean -f…`,
  `git checkout -- <file>` — **including the `git -C <path> …` form.** (Allowed: `git pull`,
  `git status`, `git add`, `git worktree …`, `git branch -D`, `git checkout <branch>`.)
- **No recursive delete:** `rm -r` / `-rf` / `-fr` / `--recursive` without explicit user approval.
- **No new dependencies:** `npm|pnpm|yarn|bun install|add <pkg>`, `dotnet add package` without
  approval. (Allowed: bare `npm install` / `npm ci` to restore an existing lockfile.)
- **No hand-editing generated/managed files:** generated FE DTO/client/`Constants.ts` and BE EF
  migrations — regenerate instead (`npm run dtos:update`, `npm run client:generate`;
  `dotnet ef migrations add`). Applies in the main repos **and** in `worktrees/<slug>/…`.
- **No direct edits to `myhospital-fe/` or `myhospital-be/` by default** — all normal changes go in a worktree. Owner-authorized bypass may permit direct maintenance/recovery work in main repos for the current session.

Explicitly ALLOWED (never block — implementers need these): run/kill/restart dev servers
(`npm run dev`, `dotnet run`, `kill`, `pkill`), build/test, and DTO/client regen.

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

- Find existing code with **CodeGraph first** (broad "how/where/what-calls/what-breaks" exploration), then a **bounded** `rg -l` for exact strings — never broad-scan all of FE/BE and dump output. Reuse project patterns instead of inventing. Full policy + command table: **`engine/rules/source-discovery.md`**.
- For FE UI/component work, run or read `myhospital-fe/docs/components/component-inventory.generated.md` and update it with `npm run components:index` if stale or missing.
- For BE data access, inspect existing service/query patterns around the target entity before writing queries.

## Review Harness (mh-review) — cross-tool

When a module / dirty worktree / changeset is finished and needs an audit before merge, use the
**`mh-review`** harness. Goal: maximize first-pass recall so review converges in **≤3 rounds**
(1 round = audit → fix → verify), instead of many. Tool-neutral policy lives in
**`engine/workflows/deep-review/`** (plain `.md`, every tool reads it by path; the conventions it checks against live in `engine/rules/`) —
every tool (Claude, Codex, opencode) follows the same protocol and emits the same findings file:

- **`protocol.md`** — the ≤3-round runbook (scope freeze → partitioned audit → adversarial verify →
  dedup → bounded completeness check → fix with self-review → verify → learning loop).
- **`checklist.md`** — the 10 review dimensions (D1–D10) + accumulated bug-classes (the *maturing*
  rule fabric; bug-classes get promoted here / into the convention docs / into guard+ESLint after
  each module so recall rises over time).
- **`findings-schema.md`** — the single findings `.md` interchange format + status lifecycle +
  coverage ledger. Output goes to `docs/audit/<module>-review-v<round>-<date>.md`.

Key principle: **recall comes from partition** (one focused reviewer per dimension), **not from
re-auditing many times** — a single broad reviewer hits an attention bottleneck and surfaces only the
most salient issues. Audit rounds are **read-only**; fixes happen only in a worktree.

- **Claude:** invoke the **`/mh-review`** skill (orchestrates the partition via the `mh-reviewer`
  subagent; optional `workflow.js` power-mode needs the Workflow tool).
- **Codex / opencode / others:** follow `protocol.md` directly; fan out reviewers by dimension; write
  the findings file per `findings-schema.md` so the fix session (any tool) can consume it.

Rationale + feasibility analysis: `docs/harness/notes/review-harness-feasibility-2026-06-16.md`.

## Source-Code Discovery (CodeGraph)

Source code is explored with **CodeGraph** — a local, pre-indexed code knowledge graph — **not** graphify and **not** a broad `rg` dump. Canonical policy + full command table: **`engine/rules/source-discovery.md`**.

- **Order:** CodeGraph first for any "how does X work / where is X / what calls X / what breaks if I change X" question → bounded `rg -l` / `ast-grep` for an exact string in a known small scope → read files only after narrowing to a few candidates. Treat CodeGraph-returned source as already read unless you need exact lines to edit/quote.
- **Tools:** MCP tools `codegraph_explore` / `codegraph_node` / `codegraph_search` / `codegraph_callers` when the agent has them; otherwise the CLI `codegraph explore|query|node|callers|callees|impact|affected` from inside an indexed repo.
- **Indexes are per code repo**, never at root (the root `.gitignore` excludes `myhospital-fe/`, `myhospital-be/`, `worktrees/`): `myhospital-be/`, `myhospital-fe/`, and an **active** `worktrees/<slug>/{be,fe}`. CodeGraph honors each repo's `.gitignore`, skips `node_modules`/build output/files > 1 MB, and auto-syncs on edit (~2 s debounce). `just codegraph-status` checks them; `just doctor` includes CodeGraph health.
- **Never** broad-scan all of FE/BE with `rg`/`fd` and dump output. **Never** use graphify for source code — graphify is docs/specs design intent only (and currently stale).

## Knowledge Graph (graphify)

A queryable knowledge graph of `docs/` + `specs/` (BA specs, design decisions, task slices, conventions)
is built at `graphify-out/graph.json`. It maps **design intent and spec relationships — not code**.

- **Optional, not mandatory.** graphify is a convenience for *docs/specs design-intent* questions
  (admission, inpatient, bed-day, BHYT-BHTM relationships, locked decisions). Reading the spec file
  directly is always an acceptable substitute. It is **never** a prerequisite for reading or searching code.
- **Never use graphify for code.** For FE/BE **source** use **CodeGraph** (broad exploration) plus a
  bounded `rg` / `fd` / `bat` (exact strings); for `.docx`/`.pdf` use `rga`. The graph does **not**
  contain code. Source-code discovery policy: `engine/rules/source-discovery.md`.
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
- Full usage for every supported agent (Codex, Antigravity, Grok, Cursor — via CLI / MCP / `graphify install`):
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
  For source code use **CodeGraph** (broad) + bounded `rg`/`fd`/`bat` (exact) — see
  `engine/rules/source-discovery.md`; for `.docx`/`.pdf` use `rga`. Never run graphify before reading source code.
- **Trust check:** the current graph is Windows-built and stale (see *Knowledge Graph (graphify)* above).
  Confirm `graphify-out/.graphify_root` matches this workspace — or run `python scripts/harness_doctor.py` —
  before relying on graph output; if it does not match, read the source docs instead.
- When used: `graphify query "<question>"` / `graphify path "<A>" "<B>"` / `graphify explain "<concept>"`
  return a scoped subgraph. `GRAPH_REPORT.md` is for broad architecture orientation only.
- After materially changing `docs/`/`specs/`, the graph needs a Linux rebuild (`/graphify`) to be fresh; the
  freshness hook only flags staleness. The graph build scope is fixed by the root `.graphifyignore`.
