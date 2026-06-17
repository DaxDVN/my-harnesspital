# Agent Shortcuts & Tool Routing

> **Auto-loaded** (referenced by `AGENTS.md`; `@`-imported by `CLAUDE.md`). Purpose: the user should
> **not** have to memorize commands. When the user's message matches an intent or a short prompt below,
> the agent **proactively uses the mapped tool** — *except* items marked **USER-DRIVEN** (there the
> agent prints the command / points to a guide and runs it only on an explicit "do it").

## 1. Short-prompt aliases (terse trigger → action)
| You type (VN / EN) | Agent runs |
|---|---|
| `doctor` · `health` · `kiểm tra harness` | `just doctor` |
| `scan` · `scan be` · `quét be` · `check convention` | `just mh-scan` (signal-first: actionable on top) |
| `scan full` · `scan advisory` · `xem hết finding` | `just mh-scan --advisory` |
| `ci scan` · `gate` | `just mh-scan --fail-on high` (exit 1 on BLOCK/HIGH) |
| `drift` · `convention truth` | `just convention-truth` |
| `scaffold <X>` · `tạo endpoint/service/listing/page/form/module` | skill **`/mh-scaffold`** |
| `implement <X>` · `làm feature <X>` · `build page <X>` | skill **`/mh-implement`** (inside a worktree) |
| `fix <bug/finding>` · `sửa <X>` | skill **`/mh-fix`** |
| `preflight` · `blast radius` · `what breaks if <X>` | skill **`/impact-analysis`** (READ-ONLY, CodeGraph-backed) |
| `investigate bug` · `RCA this` · `bug from <source>` | skill **`/bug-fix`** (trivial bug → `/mh-fix` fast-path) |
| `ui spec <X>` · `reuse audit` · `from docx/mockup` | skill **`/ui-spec`** → views mockups + deep FE reuse-audit → `specs/<m>/03-ui.md` |
| `build FE <X>` · `triển khai FE <X>` | **`/mh-implement` FE-mode** (`fe-flow`) — consumes `03-ui.md` from `/ui-spec`; `incremental-impl` runs per task internally |
| `api contract <X>` · `design api` | skill **`/technical-design`** → drafts API `08` (schema = OWNER-authored, UI = `/ui-spec`) |
| `slice tasks` · `implementation plan` | skill **`/task-slicing`** → `specs/<m>/10-plan` (LARGE / cross-cutting modules) |
| `where/how/what-calls <X>` · `tìm <X>` · `<X> gọi ở đâu` | **CodeGraph** `codegraph_explore` / `codegraph explore` → then bounded `rg` |
| `cg status` · `index ok?` | `just codegraph-status` |
| `dtos` · `regen dto` | `npm run dtos:update` then `npm run client:generate` (FE worktree) |
| `backup` · `snapshot harness` | `just harness-backup` |
| `nhớ cái này` · `remember this` · `để ý cái này` · `từ giờ` · `always/never` | **`python scripts/learning_capture.py …`** → structured provisional `second-brain/` entry (schema; NEVER `main-brain/`). `learning_list`/`learning_check` to review. |

## 2. Intent → tool (fuller)
- **New canonical pattern** (BE endpoint/service/listing/error path; FE page/list/form/module) → `/mh-scaffold`.
- **Build a feature** → `/mh-implement` (convention-safe; self-reviews its own diff).
- **Fix a bug / a review finding before merge** → `/mh-fix`.
- **Mechanical BE convention bugs** (error-code literal, transactions, soft/hard-delete, raw exception,
  swallow catch, contract dict, magic status, fat api, legacy listing, hospital-scope) → `just mh-scan`.
- **FE structural rules** (raw `fetch`, dead `@/lib/dtos` import, master-data name-compare, no-`axios`)
  → also `just mh-scan` (ast-grep bridge, auto-gated to FE scope).
- **Find / understand code** → CodeGraph first, then a bounded `rg`. Never broad-scan FE/BE and dump.
- **Harness health / drift / backup** → `just doctor` / `just convention-truth` / `just harness-backup`.
- **FE feature pipeline (owner decision 2026-06-16):** owner authors `02-requirements` + `07-schema` (agents
  NEVER author schema) → **`/ui-spec`** (DOCX + mockups → `03-ui.md` reuse-map) → **`/mh-implement` FE-mode**
  (`fe-flow`, consumes `03-ui.md`; folds `incremental-impl` per task). `/technical-design` drafts only the API
  contract (`08`); `/task-slicing` only for LARGE modules. Each SDD phase has a deterministic gate
  (`_shared/gate-check.py`, exit 2 = STOP); state on `specs/<m>/00-module-state.md`; `/impact-analysis` is the
  preflight before any risky change.
- **Fast-path (skip the chain)** → a trivial + local change with **no** contract/schema/business-rule/
  multi-module impact: go DIRECT to `/mh-implement` (feature) or `/mh-fix` (bug) — no design/slice/preflight.
  "Trivial" mirrors `progressive-test`'s deterministic `classify`.

## 3. USER-DRIVEN — never auto-run (print the command / point to the guide)
- **Review / audit** (`/mh-review`): **explicit only**. Run it solely when the user asks for a review
  by name, and confirm scope first. Do **not** auto-trigger it after implement/fix.
- **Promote learning** (`/promote`): **owner-invoked only** — the agent NEVER self-invokes. Moves a
  `second-brain/` entry into the gated `main-brain/` (or graduates it into a new skill). The owner
  authorizes by typing `! touch main-brain/.promote-unlock`. Agents **must never write `main-brain/`**.
- **Worktree / Zellij** (`just wt-*`, `zorch`, `zimpl`, `zkillwt`, `worktree.py`): user-driven. Print
  the exact fish command and/or point to **`docs/guides/worktree-zellij-manual.md`**; run only on an
  explicit "do it for me".
- **`git commit`/`push`, dependency installs, recursive delete**: blocked by the guard / require an
  explicit user action regardless.

## Notes
- This file is the source of truth for shortcuts — edit it freely; the agent re-reads it each session.
- If a mapped tool is missing (`just doctor` confirms presence), say so — don't silently skip.
