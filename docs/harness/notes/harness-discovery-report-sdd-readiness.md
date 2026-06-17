# Harness Discovery Report — Spec-Driven Requirement & Design Readiness

> Read-only discovery session. Generated 2026-06-14. Nothing in the workspace was modified or created during discovery. Two convenience commands were run against `worktree.py` (`--help`, `list`) and `git`-status checks only.

**One-line verdict:** You have a strong *implementation-safety* and *worktree-infra* harness, a good *graphify* knowledge layer, and one genuinely mature spec module (`admission/`) — but there is **no codified Spec-Driven harness for the Requirement Analysis and Design phases**. Every spec module reinvents its own structure, there are no templates, no traceability matrix, no module-state/handoff convention, and no guard protecting spec integrity. SDD readiness is "proven by example, not by harness."

---

## 1. Current workspace map

Root: `/home/dax/Documents/arabica/roast`

| Path | Role | Classification |
|---|---|---|
| `AGENTS.md` (12.6 KB) | Root dispatcher / harness for all coding agents | **Active, behavior-controlling** |
| `CLAUDE.md` (3.9 KB) | Claude-specific routing; `@AGENTS.md` import | **Active, behavior-controlling** |
| `.claude/settings.json` | Hook registrations (guard + graphify) | **Active, behavior-controlling** |
| `.claude/settings.local.json` | `{}` empty | Active, no-op |
| `.claude/hooks/myhospital_guard.py` | PreToolUse safety/convention guard | **Active, behavior-controlling** |
| `.claude/hooks/graphify_stale_check.py` | SessionStart staleness warning | Active |
| `.claude/agents/myhospital-rule-auditor.md` | Read-only convention auditor subagent (Haiku) | Active |
| `.codex/hooks.json` | Codex PreToolUse → `graphify hook-check` | Active |
| `scripts/worktree.py` (36 KB) | Worktree/slot/DB automation | **Active, core infra** |
| `scripts/README.md`, `scripts/WORKTREE-TOOLING.md` | Worktree docs | Active |
| `scripts/careflow_ba_fixes_smoke.py` | One-off smoke test | Active, niche |
| `scripts/legacy-powershell/` (8 `.ps1` + `claude-hooks/`) | Pre-Linux-migration scripts | **Legacy (deprecated)** |
| `justfile` (410 B) | 4 recipes: `status`, `graphify-help`, `worktree-help`, `agent-audit` | Active, thin |
| `harness/rules/` | FE/BE convention rule docs | Active |
| `docs/graphify-agent-guide.md` | Graphify usage guide | Active |
| `docs/tasks/`, `docs/session-notes/`, `docs/testing/` | Plans, audit reports, QA artifacts | Active (mixed dev/test, mostly out-of-scope) |
| `specs/` (7 modules) | The actual spec corpus | **Active, in-scope core** |
| `graphify-out/` | Knowledge graph (`graph.json`, `GRAPH_REPORT.md`, `wiki/`) | Active, generated |
| `.graphifyignore` (55 lines) | Canonical graph scope | Active |
| `graphifyignore` (48 lines) | Compatibility shim; header says "Prefer `.graphifyignore`" | **Redundant/legacy-ish** |
| `myhospital-be/`, `myhospital-fe/` | Main package repos (both real git repos) | **Active, code — edits forbidden** |
| `_db-backups/`, `.linux-migration-backups/` | Backup archives | Active data, not behavior |
| `.obsidian/` | Editor vault config (specs are an Obsidian vault) | Active, editor-only |

**Files that control agent behavior:** `AGENTS.md`, `CLAUDE.md`, `.claude/settings.json`, the two hooks, the auditor agent, `.codex/hooks.json`, and (by reference) the package-level `myhospital-be/CONVENTIONS.md`, `myhospital-fe/CLAUDE.md`, `harness/rules/*`.

**Legacy / candidates for retirement:** `scripts/legacy-powershell/` (explicitly deprecated by CLAUDE.md: "PowerShell is deprecated"), and the duplicate `graphifyignore` (vs `.graphifyignore`).

**Project-specific vs user/global:** Everything here is **project-specific** (workspace-scoped). There is no evidence of user-global `~/.claude` rules bleeding in except the model/runtime context. Spec conventions are entirely local to this repo.

---

## 2. Current agent instruction model

**AGENTS.md** is the root dispatcher. It is deliberately broad and operational. Key codified blocks:
- **Session Start Protocol** — agents must run `python scripts/worktree.py list` and ask *"Bạn muốn làm việc trong worktree nào?"* before code work.
- **Multi-Agent Worktree + Zellij Protocol** — intent routing for `create`/`join`/`cleanup`/`sync` verbs → exact `worktree.py` commands.
- **Scope Routing** — FE → `myhospital-fe/CLAUDE.md`; BE → `myhospital-be/CONVENTIONS.md`; cross-cutting → "BE contract first, regenerate FE DTO/client second."
- **Severity Model** — `BLOCK` / `WARN` / `INFO`, with "when uncertain, treat as BLOCK."
- **Stop Protocol** — a fixed `BLOCKED_RULE / Evidence / Why it matters / Recommended path` format.
- **Mandatory Discovery, Multi-Agent Execution, Validation Contract, Workspace File Organization** (the table that dictates `docs/tasks/`, `docs/session-notes/`, `specs/<module>/`).

**CLAUDE.md** imports AGENTS.md (`@AGENTS.md`) and adds Claude-specific layers: routing, operating rules, the graphify SessionStart-hook behavior, the `bvtest3/lynkhanh9822@gmail.com/12.[s7HXZQ;NfAoF` smoke login, a "Subagents v1.0" model-tier policy (Haiku/Sonnet/Opus selection), and a graphify rules block.

**Duplication / conflict / delegation:**
- Mostly **clean delegation** (CLAUDE.md → AGENTS.md → package files).
- **Duplication exists** and is real: the graphify rules are stated *three times* (AGENTS.md "Knowledge Graph", CLAUDE.md "Routing" bullet, CLAUDE.md "graphify" section), the worktree slot map appears in both AGENTS.md and `scripts/README.md`/`WORKTREE-TOOLING.md`, and the "PowerShell deprecated" rule is repeated in both AGENTS.md and CLAUDE.md. This is drift-prone — three copies of a rule means three places to forget to update.
- No hard *conflicts* found, but the redundancy is a maintenance liability for an SDD upgrade.

**Source-priority rules:** Present but **narrow**. AGENTS.md says: cross-FE/BE work treats "the BE contract and BE conventions as the source of truth first." That is a *code-contract* priority, **not** a *requirement-source* priority. There is **no codified precedence for requirement sources** (BA DOCX vs mockup vs existing code vs user answer vs assumption). The only place a source precedence appears is *inside* a single spec file (`specs/admission/requirements.md` §1 documents a precedence) — i.e., convention by example, not a harness rule.

**Rules confirmed present:** no PowerShell ✅, use fish for user-facing commands ✅, worktree-only edits (never touch `myhospital-fe/`/`myhospital-be/` main) ✅, avoid destructive commands ✅ (enforced by hook, see §3), orchestrator-vs-implementer ✅ (`claude` orchestrator + `opencode` implementer defaults, Zellij `mh-<slug>-orch-*` / `mh-<slug>-impl-*` sessions).

---

## 3. Current hook and guard model

**Claude hooks** (`.claude/settings.json`):

| Event | Matcher | Action |
|---|---|---|
| `PreToolUse` | Bash / Write / Edit / MultiEdit | `myhospital_guard.py` (10s) |
| `PreToolUse` | Bash | Inline advisory: if `grep/find/rg/fd/...` detected and graph exists → "run graphify first" |
| `PreToolUse` | Read / Glob | Inline advisory: reading source extensions → graphify-first reminder |
| `SessionStart` | — | `graphify_stale_check.py` (20s) |

`myhospital_guard.py` **blocks/warns** on 7 categories: git history ops (`reset --hard`, `checkout --`, `clean`, `commit`, `push`), dependency installs (`npm/pnpm/yarn/bun add`, `dotnet add package`), recursive deletes (`rm -rf`, `Remove-Item -Recurse`), edits to generated FE files (`generated-dtos.ts`, `generated-api-client.ts`, `Constants.ts`), hand-edits to BE migrations, FE forbidden patterns (`fetch`/`axios`/`Bearer`/`"use client"`/zustand/jotai/redux), and BE forbidden patterns (`BeginTransactionAsync`, `SaveChangesAsync`, `throw new Exception`, `return null`, `AllowAnonymous`, `dynamic`, …).

`graphify_stale_check.py` (SessionStart, **non-blocking**): diffs `docs/`+`specs/` against the last graph manifest; prints `[graphify] … STALE …` only when files changed, else silent.

**Codex hooks** (`.codex/hooks.json`): single `PreToolUse`/Bash → `graphify hook-check`. Thinner than the Claude side; **no convention guard for Codex** — the safety net is Claude-only.

**What they cover:** safety (destructive/git/deps), code-convention enforcement (FE/BE patterns + generated-file integrity), shell migration (catches `Remove-Item -Recurse`), and graphify freshness.

**Gaps relevant to SDD documentation workflow (important):**
- **Nothing guards spec/requirement/design integrity.** No rule like "don't promote an open question to a confirmed requirement without a decision-log entry," "don't write a design baseline while open-questions remain," or "spec edits must bump a version/changelog." The guard matches `.ts`/`.cs`/shell — never `.md` under `specs/`.
- **No "spec-before-code" gate.** Nothing blocks implementation when the relevant spec section is missing or stale.
- **No assumption/decision provenance check.** The harness can't tell a confirmed fact from an agent assumption inside a spec.
- **Codex parity gap** — Codex has no convention/safety guard, only graphify.

---

## 4. Current worktree/session harness

`scripts/worktree.py` is a **mature, fully-automated** infra tool. Subcommands:

| Cmd | Does | Automated? |
|---|---|---|
| `list` | List active worktrees (excludes `_db-backups`) | ✅ |
| `init-db-slots` | Create/start SQL Server containers for slots 1–4 | ✅ docker |
| `create --slug --slot` | Create FE+BE git worktrees, write `.env` (ports), `npm ci/install`, DB sync; flags `--skip-db-sync`, `--skip-fe-install`, `--dry-run` | ✅ |
| `sync-db --slot --be-path` | Backup→clear→`dotnet ef database update`→restore a slot DB | ✅ |
| `cleanup --slug` | Remove worktree (refuses if git-dirty; confirm unless `--yes`) | ✅ |
| `sync-main` | Pull main FE/BE + reapply skip-worktree stash | ✅ |

**Structure on disk:** `worktrees/<slug>/fe` and `worktrees/<slug>/be`, each a git worktree on branch `feature/<slug>`, with auto-generated `.env`. **Slot map:** slot _n_ → FE `300n`, BE `500n`, SQL `localhost,143(3+n)`, container `mssql-hospital-wt<n>`. Main DB is `localhost,1433`.

**Worktree ↔ orchestrator ↔ implementer relationship:** 1 worktree = 2 Zellij sessions: `mh-<slug>-orch-<tool>` (default `claude`) + `mh-<slug>-impl-<tool>` (default `opencode`). The orchestrator plans/reviews/integrates; the implementer writes code. This is **documented in AGENTS.md and `scripts/README.md`/`WORKTREE-TOOLING.md`**.

**Automated vs documented split:**
- **Automated:** worktree creation, env/ports, FE install, DB sync, cleanup, main sync.
- **Documented only (NOT automated by the script):** Zellij session creation. `zorch <slug> <tool>` / `zimpl <slug> <tool>` are referenced as *preferred helpers "if they exist"* with a raw `zellij --session … --layout myhospital-orch/impl` fallback — **the helper functions and the Zellij layouts are not defined anywhere in this repo.** So the multi-agent session topology is convention + user-environment, not reproducible infra.

**SDD implication:** the worktree harness is built around *Development* (code branches, DB, ports). There is **no worktree/session concept for a Requirement-Analysis or Design session** — those phases currently happen ad-hoc against the main checkout in `specs/`, with no isolation, no per-phase session naming, and no "spec worktree."

---

## 5. Current documentation/spec setup

**7 spec modules**, wildly inconsistent in maturity and naming:

| Module | Maturity | Naming style |
|---|---|---|
| `admission/` | **Mature** (requirements + design + api + decisions + tasks + e2e plan; implementation in progress) | kebab-case + `_PREFIXED` index files |
| `ipd_bed/` | Req-analysis/design draft (entities, features, open-questions) | `NN_SCREAMING.md` |
| `ipd_bed_design_pack/` | Design *review* pack — its own `00_INDEX.md` says "NOT final spec" | `NN_SCREAMING.md` |
| `ipd_bed_review/` | Agent session notes (`06a–06e SESSION_*`) — not canonical spec | `NN_SCREAMING.md` |
| `ipd_bed_learning/` | Vietnamese learning/BA-concept docs — not SDD artifacts | `NN_snake.md` |
| `ipd_consultation/` | Requirement *seeds* (source audit + seeds + open-questions) | `NN_SCREAMING.md` |
| `ipd_vital_signs/` | Requirement *seeds* (same shape as consultation) | `NN_SCREAMING.md` |

**Canonical SDD artifact coverage** (which artifacts exist *somewhere*, mapped from bespoke filenames):

| Artifact | Exists? | Best example(s) |
|---|---|---|
| requirements.md | Partial | `admission/requirements.md` ✅; others use "seeds" (`ipd_consultation/02_REQUIREMENT_SEEDS.md`) or none |
| schema / domain model | Yes (scattered) | `admission/design.md`, `ipd_bed/01_ENTITIES.md`, `ipd_bed_design_pack/02_DOMAIN_MODEL_SCHEMA.md` |
| api.md | Rare | `admission/api.md` ✅ only |
| ui.md / mockup mapping | Rare/implicit | `admission/step1-2/.../fields/*.md`, `ipd_bed_review/07_MOCKUP_ANALYSIS.md` |
| plan.md | Yes | `admission/reconciliation/_CONSOLIDATED-PLAN.md`, `ipd_bed/05_ROADMAP_PHASES.md`, `*/0X_PHASE_PLAN.md` |
| test-cases.md | Rare | `admission/reconciliation/_E2E-TEST-PLAN.md` only |
| **traceability.md** | **None** | **Absent in every module** (only implicit back-refs in slices) |
| open-questions | Yes (3 schemas) | `ipd_bed/99_OPEN_QUESTIONS.md`, `ipd_bed_design_pack/10_OPEN_QUESTIONS_FOR_BA_LEAD.md`, `admission/step1-2/ambiguity-questions.md` |
| decision-log | Yes (3 schemas) | `admission/reconciliation/_DECISIONS.md` (D1…), `ipd_bed_design_pack/09_DECISION_LOG.md` (DL-001…) |
| review-checklist | Rare | `ipd_bed_design_pack/08_AUDIT_CHECKLIST_AND_PROMPTS.md` |
| **assets/manifest.md** | **None** | DOCX/PNG referenced inline, never inventoried |
| source-audit / inventory | Yes (newer modules) | `ipd_consultation/01_SOURCE_AUDIT.md`, `ipd_vital_signs/01_SOURCE_AUDIT.md` |
| **module-state / session-handoff** | **Implicit only** | `admission/handoff.md`, `*/99_AGENT_BRIEF.md` — not a standard phase-status file |

**Organized by module:** Yes, but inconsistently — and two "modules" (`ipd_bed_learning`, `ipd_bed_review`) are actually reference/session noise living under `specs/`.

**Module-state / session-handoff file:** No standard one. `admission/handoff.md`, `fe-integration-handoff.md`, and `*/99_AGENT_BRIEF.md` partially fill this role but are bespoke per module.

**Docs as source of truth:** Stated as intent (AGENTS.md: "treat the BE contract and BE conventions as source of truth"; graphify indexes specs as design intent). In practice specs *are* treated as the working source for `admission/`, but there is no enforcement and no versioning.

**Templates:** **None.** This is the single biggest structural gap. There is no `specs/_TEMPLATE/`, no skeleton, no canonical filename set. The good patterns exist only as one-off files in `admission/` and the newer `ipd_consultation`/`ipd_vital_signs` "pack" shape — recoverable as templates, but not yet templated.

---

## 6. Current project conventions

Documented in three layers (all code-phase oriented):

- **BE** — `myhospital-be/CONVENTIONS.md` + `harness/rules/backend-rules-conventions-patterns.md`: MUST/WARN/INFO severity. Headline rules: *"No transaction, no locking"* (design via write-order/idempotency/derived values), no N+1 ("each table queried once per API"), mandatory tenant/hospital scoping, soft-delete + audit auto, `BaseService`, `BusinessException`/ErrorCodes, typed DTOs, auth attributes (no `AllowAnonymous`).
- **FE** — `myhospital-fe/CLAUDE.md` + `harness/rules/frontend-rules-conventions-patterns.md`: 3 generated files are read-only (`generated-dtos.ts`, `generated-api-client.ts`, `Constants.ts`); use module adapters/generated hooks (no raw `fetch`/`axios`), existing state/context (no zustand/jotai/redux), lucide icons; stack React 19 / TS 5.9 / Vite 7.2 / TanStack Query v5 / ServiceStack.
- **DB/API/UI inferable from docs only:** DB = SQL Server, EF migrations (model-first, never hand-edit), soft-delete + tenant columns. API = ServiceStack request/response DTO contract, BE-first then FE codegen. UI = component-inventory-driven reuse (`npm run components:index` — though the generated inventory file is **currently absent**).

These are **Development-phase** conventions. There is no documented convention for *what a good requirement looks like*, *what a design baseline must contain*, or *acceptance-criteria format* — i.e., the Design-phase output conventions are missing even though the BE/FE input conventions are rich.

---

## 7. Current source-ingestion capability

- **DOCX:** Handled, but bespoke per module. `specs/admission/_extract_docx.py` uses `python-docx` to convert `Tài liệu Nội trú.docx` → markdown (`Tai_lieu_Noi_tru_extracted.md`), preserving headings/tables/Vietnamese. This is a **one-off script copied into one spec folder**, not a reusable harness tool. Newer modules (`ipd_consultation`, `ipd_vital_signs`) cite the same DOCX by **section number** (`§5.2`, `§5.3–5.5`) in their `01_SOURCE_AUDIT.md` — good practice, but manual.
- **Mockups/screenshots:** Present as raw PNGs (`specs/admission/step3-5/*.png`, reconciliation crema references) and analyzed in `07_MOCKUP_ANALYSIS.md` / field files. **No asset manifest, no stable IDs.**
- **PDF:** No tooling, no references.
- **ripgrep-all / rga / pandoc / mammoth:** **None present.** The only ingestion library in the repo is `python-docx`. DOCX images are not extracted (the script handles text+tables only).
- **DOCX/mockup → requirement mapping process:** Exists *by example* in `ipd_consultation/01_SOURCE_AUDIT.md` → `02_REQUIREMENT_SEEDS.md` (source audit → seeds), and admission field files map mockup ↔ contract. But it's **not a documented, repeatable process** and not consistent across modules.
- **Traceability matrix convention:** **None.** Traceability is implicit (back-refs in slices/design), never a matrix linking source → requirement → design → task → test.
- **graphify** is the real ingestion strength: indexes 133 docs/specs files (~250K words) into a queryable graph with `query / explain / path / affected / update`. It maps **design intent, not code, and not raw source binaries** — so DOCX/PNG content only enters the graph after a human/agent transcribes it into markdown.

---

## 8. Spec-Driven Development readiness (Requirement Analysis + Design only)

**Requirement Analysis:**

| Capability | Status | Evidence |
|---|---|---|
| Source inventory | ⚠️ Partial | `01_SOURCE_AUDIT.md` in 2 newer modules; no manifest, no harness rule |
| Candidate requirement extraction | ⚠️ Partial | `02_REQUIREMENT_SEEDS.md` (consultation/vital_signs) — good, not templated |
| Source priority | ❌ Missing as harness | Only inside `admission/requirements.md §1`; no global rule |
| Confirmed vs assumption vs open | ⚠️ Inconsistent | 3 different open-question schemas; `assumed-contract-ledger.md` exists for FE only |
| BA/user Q&A loop | ⚠️ Partial | `ambiguity-questions.md`, `10_OPEN_QUESTIONS_FOR_BA_LEAD.md` — no standard loop/status lifecycle |
| Mockup-to-UI mapping | ⚠️ Partial | admission field files; no asset IDs |
| Traceability | ❌ Missing | no matrix anywhere |
| Acceptance criteria | ⚠️ Rare | embedded in slices, not a requirement-level convention |
| Change control | ❌ Missing | see §10 |

**Design:**

| Capability | Status | Evidence |
|---|---|---|
| Schema design | ✅ Present | `01_ENTITIES.md`, `02_DOMAIN_MODEL_SCHEMA.md`, `admission/design.md` |
| API contract design | ⚠️ Rare | `admission/api.md` only |
| UI contract design | ⚠️ Partial | field files / mockup analysis; no standard ui.md |
| Decision log | ✅ Present (fragmented) | `_DECISIONS.md`, `09_DECISION_LOG.md` — 3 schemas |
| Design baseline | ❌ Missing | no concept of a frozen/versioned baseline |
| Open-question gating | ❌ Missing | nothing prevents design proceeding with open questions |
| Impact analysis | ⚠️ Tool-only | `graphify affected "<node>"` exists but no process |
| Design review checklist | ⚠️ Rare | `08_AUDIT_CHECKLIST_AND_PROMPTS.md` (one module) + `myhospital-rule-auditor` (code-only) |

**Bottom line:** The *artifacts* of good SDD exist as proof-of-concept in `admission/` and the newer "pack" modules. The *harness* (templates, gates, precedence rules, traceability, baselining, change-control) does **not** exist. You are doing SDD by discipline and copy-paste, not by tooling.

---

## 9. Context-rot control

| Mechanism | Present? |
|---|---|
| Module-state file | ❌ No standard one (bespoke `handoff.md`, `99_AGENT_BRIEF.md`) |
| Session-handoff file | ⚠️ Ad-hoc (`admission/handoff.md`, `fe-integration-handoff.md`) |
| Phase status | ❌ No explicit phase field (Req-Analysis / Design / Baselined) |
| Spec version | ❌ None (some files carry a date in prose, e.g. "v0.3, 2026-06-05", but not enforced) |
| Confirmed-decisions summary | ⚠️ Per-module decision logs exist but no rolled-up summary |
| Unresolved-questions summary | ⚠️ Per-module open-questions exist; no cross-module rollup |
| Next-session agenda | ❌ None standard (sometimes embedded in `PROMPT.md`/`_AGENT_BRIEF.md`) |

**Verdict:** Cross-session continuity is **carried by long bespoke handoff/brief files and the graphify graph**, not by a structured module-state contract. For multi-agent, multi-session SDD this is the second-biggest gap after templates. There is no single file an orchestrator can read to know "what phase is this module in, what's frozen, what's open, what's next."

---

## 10. Change-control model

| Scenario | Supported? |
|---|---|
| Dev agent discovers missing spec | ❌ No defined route (no "stop and file an open-question" rule for implementers) |
| Codebase reveals a constraint | ⚠️ Captured ad-hoc (`assumed-contract-ledger.md`, `ipd-bed-be-backlog-from-ui.md`) but no loop back into requirements |
| New BA answer changes prior design | ❌ No supersede process |
| Decision-log update | ⚠️ Logs exist; no rule requiring an entry on change |
| Requirements/schema/api/ui/test/plan update propagation | ❌ No defined propagation; relies on graphify staleness warning |
| Impact analysis | ⚠️ `graphify affected` available; not wired into a change process |
| Superseding old decisions | ⚠️ Only `ipd_bed_design_pack/09_DECISION_LOG.md` even has a "Superseded" status; not standard |

**Verdict:** There is **no codified change-control workflow.** The pieces (decision logs, a "Superseded" status in one module, graphify impact analysis) exist but are not assembled into a process. The Stop Protocol in AGENTS.md is for *rule violations*, not *spec changes*.

---

## 11. Multi-agent role model

| Role | Codified? | Where |
|---|---|---|
| Human owner | ✅ | "ask the user which worktree", BA-lead open-questions |
| Orchestrator | ✅ | `claude` default, `mh-<slug>-orch-*`, "primary agent acts as implementation orchestrator" (AGENTS.md Multi-Agent Execution) |
| Reviewer / auditor | ✅ | `myhospital-rule-auditor` subagent (read-only, Haiku) + `harness/rules/*` |
| Implementer | ✅ | `opencode` default, `mh-<slug>-impl-*`, codex workers |
| Codebase investigator | ⚠️ Implicit | "Mandatory Discovery" + graphify; no named role |
| **BA / spec co-author** | ❌ Not defined | open-questions address a "BA lead" but no agent role owns requirement authoring |
| **Design reviewer** | ❌ Not defined | auditor reviews *code* conventions, not *design* quality/completeness |

**Verdict:** Roles are clearly separated **for the Development phase** (orchestrator ↔ implementer ↔ code-auditor ↔ human). They are **undefined for the Requirement & Design phases** — there is no "BA/spec co-author" role and no "design reviewer" role. The code-auditor cannot substitute: it checks `BaseService`/N+1/generated-files, not "is this requirement testable" or "is this design baseline complete."

---

## 12. Questions I need answered before final recommendations

**Workflow**
1. Do you want the Requirement/Design phases to run **inside the existing worktree/Zellij model** (e.g., a doc-only "spec worktree" + an orchestrator/spec-reviewer session pair), or as a **separate, lighter flow** that operates directly on `specs/` in the main checkout? — *This decides whether `worktree.py` needs a `spec`/doc mode or whether SDD stays out of the worktree system entirely.*
2. Which tools play which role in SDD sessions — is `claude` the BA co-author/orchestrator and `opencode`/codex the design reviewer, or do you want dedicated subagents? — *Determines whether I propose new `.claude/agents/*` (spec-author, design-reviewer) vs reuse.*

**Agent / tool**
3. Should new behavior be enforced by **hooks** (hard gates, e.g. "no design baseline while open questions are 🔴") or remain **advisory** in AGENTS.md/CLAUDE.md? — *You currently hard-gate code safety but only advise on graphify; SDD gating is a philosophy choice with real friction cost.*
4. Is **Codex** a first-class SDD agent? If so it needs guard/role parity (today it only has `graphify hook-check`). — *Affects whether I duplicate rules into `.codex/`.*

**Spec / documentation**
5. Pick a **canonical structure**: numbered SCREAMING (`00_INDEX.md`, `09_DECISION_LOG.md`, the `ipd_*` style) **or** kebab (`requirements.md`, `api.md`, the `admission` style)? They currently coexist and can't both be the template. — *Everything downstream (template, graphify scope, tooling) keys off this.*
6. Should `ipd_bed_learning/` and `ipd_bed_review/` be **moved out of `specs/`** (to `specs/_learning/`, `specs/_archive/`) so `specs/` contains only canonical SDD artifacts? — *Affects graphify signal-to-noise and "docs as source of truth" credibility.*

**Requirement Analysis**
7. What is your **canonical requirement-source precedence** (e.g., BA DOCX > confirmed user answer > mockup > existing code > agent assumption)? — *Right now it lives in one spec file; SDD needs it as a harness rule. Only you can rank these.*
8. Do you want a strict **Confirmed / Assumption / Open** state machine on every requirement and a Q&A lifecycle (Open → Asked → Answered → Folded-in)? — *Defines the open-questions/decision-log schema I'd standardize.*

**Design**
9. What must a **Design Baseline** contain to be "frozen," and what's allowed to change it afterward? — *Without your definition I can't design the baseline/gating artifact.*
10. Do you want **open-question gating** to be a hard rule ("design can't be baselined while any 🔴 open question touches it") or a checklist reminder? — *Hard gate needs a machine-checkable open-question format.*

**Source / materials**
11. Are mockups arriving as **Figma** (the Figma MCP is connected) or only as exported PNGs/DOCX images? — *Determines whether mockup-to-UI mapping can pull live Figma context vs needs an image/asset-manifest pipeline + DOCX image extraction (current `_extract_docx.py` drops images).*
12. Should DOCX→markdown extraction become a **shared `scripts/` tool** (with image extraction) replacing the per-module copy in `specs/admission/_extract_docx.py`? — *Decides if I propose a reusable ingestion script.*

**Risk tolerance**
13. How much **friction** is acceptable? Are you willing to be *blocked* from writing a design baseline by a hook, or do you want guidance-only so velocity stays high? — *Sets the BLOCK/WARN line for all new SDD rules.*

**Update / change-control**
14. When an implementer discovers the spec is wrong/missing, what should happen — **hard stop + file open-question**, or **note-and-continue**? — *Defines the change-control loop and whether the code-side guard should detect "implementing beyond spec."*
15. Do you want a **cross-module rollup** (one dashboard of every module's phase, open-question count, last decision) or is per-module state enough? — *Decides whether I propose a top-level `specs/_STATE.md` index.*

---

## 13. Preliminary recommendations (DRAFT — no files created)

> Draft, evidence-based, no implementation yet. Each waits on the §12 answers noted.

**R1 — Canonical SDD template set under `specs/_TEMPLATE/`**
- *Problem:* every module reinvents structure; two naming schemes coexist; no skeleton.
- *Why it matters:* templates are the cheapest, highest-leverage fix — they make Req-Analysis & Design repeatable and graphify-friendly.
- *Direction:* one skeleton (requirements / schema / api / ui / decision-log / open-questions / traceability / source-audit / assets-manifest / module-state / review-checklist), derived from the best existing examples (`admission/` + `ipd_consultation` pack).
- *Files affected:* new `specs/_TEMPLATE/*`; AGENTS.md "Workspace File Organization" table.
- *Confidence:* **High.** *Needs first:* Q5 (naming), Q9 (baseline contents).

**R2 — Standard `module-state.md` (phase + version + confirmed + open + next-agenda)**
- *Problem:* no structured cross-session state; continuity rides on bespoke handoff/brief files + graphify.
- *Why it matters:* directly attacks context-rot in multi-agent/multi-session SDD (§9).
- *Direction:* one front-matter'd state file per module (phase, spec-version, frozen?, open-question count, last 5 decisions, next-session agenda); optional top-level rollup.
- *Files affected:* `specs/<module>/module-state.md`, maybe `specs/_STATE.md`; CLAUDE.md SessionStart guidance.
- *Confidence:* **High.** *Needs first:* Q15 (rollup yes/no).

**R3 — Codify requirement-source precedence + Confirmed/Assumption/Open state machine**
- *Problem:* source priority lives in one spec file; three different open-question/decision schemas.
- *Why it matters:* this is the heart of Requirement Analysis discipline; ambiguity here is what later forces rework.
- *Direction:* a harness rule in AGENTS.md + a fixed open-questions/decision-log schema (status lifecycle, supersede) reused by the template.
- *Files affected:* AGENTS.md; `specs/_TEMPLATE/{open-questions,decision-log}.md`.
- *Confidence:* **Medium.** *Needs first:* Q7, Q8.

**R4 — Traceability convention (source → requirement → design → task → test)**
- *Problem:* zero traceability matrices; only implicit back-refs.
- *Why it matters:* without it, change-impact (§10) and "is every requirement designed/tested" are unanswerable.
- *Direction:* a `traceability.md` table convention per module with stable IDs (REQ-/D-/UI-), leveraging `graphify affected` for impact.
- *Files affected:* template + AGENTS.md; possibly a small validator script later.
- *Confidence:* **Medium.** *Needs first:* Q5, Q8.

**R5 — Spec-integrity / phase-gating guard (optional hard gate)**
- *Problem:* the guard protects code, nothing protects specs; no open-question gating or spec-before-code rule.
- *Why it matters:* closes the §3/§10 gaps; makes "docs are source of truth" enforceable rather than aspirational.
- *Direction:* extend `myhospital_guard.py` (or a new hook) to warn/block on: baselining with open 🔴 questions, editing a frozen baseline without a decision-log entry, implementing a slice whose spec section is missing.
- *Files affected:* `.claude/hooks/`, `.claude/settings.json`, `.codex/hooks.json` (parity).
- *Confidence:* **Low–Medium.** *Needs first:* Q3, Q10, Q13, Q14 (friction tolerance is decisive).

**R6 — Dedicated SDD agent roles: spec/BA co-author + design reviewer**
- *Problem:* roles defined only for Development; `myhospital-rule-auditor` reviews code, not design.
- *Why it matters:* §11 gap — no agent owns requirement authoring or design-completeness review.
- *Direction:* new `.claude/agents/spec-author.md` and `.claude/agents/design-reviewer.md` (read-mostly), mirroring the auditor pattern.
- *Files affected:* `.claude/agents/*`; AGENTS.md role table.
- *Confidence:* **Medium.** *Needs first:* Q2, Q3.

**R7 — Reusable source-ingestion tooling (DOCX+images, mockup/asset manifest)**
- *Problem:* `_extract_docx.py` is a per-module copy that drops images; no asset manifest; no Figma wiring.
- *Why it matters:* Req-Analysis quality is bounded by how well BA DOCX/mockups become structured, ID'd sources.
- *Direction:* promote a single `scripts/ingest_docx.py` (text+images), add an `assets-manifest.md` convention with stable asset IDs; if mockups are Figma, use the Figma MCP instead of PNG export.
- *Files affected:* `scripts/`, template `assets-manifest.md`.
- *Confidence:* **Medium.** *Needs first:* Q11, Q12.

**R8 — Harness hygiene: de-duplicate rules; quarantine non-spec folders; drop `graphifyignore` shim**
- *Problem:* graphify/PowerShell/slot-map rules duplicated across AGENTS.md, CLAUDE.md, scripts docs; `ipd_bed_learning`/`ipd_bed_review` pollute `specs/`; two `graphifyignore` files.
- *Why it matters:* duplication causes drift; noise dilutes graphify and "source of truth."
- *Direction:* single-source each rule (link, don't copy); move learning/review under `specs/_learning/` `specs/_archive/`; retire `graphifyignore`.
- *Files affected:* AGENTS.md, CLAUDE.md, `specs/` layout, `.graphifyignore`.
- *Confidence:* **Medium-High** (hygiene). *Needs first:* Q6.

---

## Next best action

**Answer the §12 questions — and answer Q5 (canonical naming) and Q13 (friction/BLOCK-vs-WARN tolerance) first.** Those two are gating: nearly every recommendation (template R1, state R2, schemas R3/R4, the guard R5) forks on whether you standardize on the numbered-SCREAMING or kebab structure, and on whether you want SDD rules to *block* or merely *advise*.

Once those two are decided, the highest-leverage concrete deliverable is **R1 + R2 together**: a `specs/_TEMPLATE/` skeleton plus a `module-state.md` standard — they convert your proven-by-example `admission/` discipline into a reusable harness and fix the worst context-rot gap, with no code risk. Hold R5 (hooks) and R6 (new agents) until after the templates exist, since they enforce/serve the template.

This was a read-only discovery session. No source files were modified or created beyond this report.
