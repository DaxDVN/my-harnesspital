# Claude Code - MyHospital workspace

@AGENTS.md
@engine/agent-shortcuts.md
@main-brain/knowledge.md

## Routing

- When working under `myhospital-fe/`, load and obey `myhospital-fe/CLAUDE.md`.
- When working under `myhospital-be/`, **`engine/rules/backend.md` is the BE canon (read it first)**; `myhospital-be/CONVENTIONS.md` is legacy/advisory only (known drift — see `engine/rules/README.md`; there is no `myhospital-be/CLAUDE.md`).
- For cross-package work, treat the BE contract + **`engine/rules/backend.md` (canon)** as the source of truth first, then regenerate FE contract artifacts and validate FE rules (`engine/rules/frontend.md`) second.

## Operating rules

- Keep tasks small enough that Claude can stay inside one package when possible.
- Use plan mode before edits that affect routing, provider hierarchy, shared contracts, or migrations.
- Prefer the package-specific CLAUDE file over chat memory for long-lived conventions.
- **Source code: CodeGraph first.** Explore source with **CodeGraph** (local pre-indexed code graph — MCP tools `codegraph_explore`/`_node`/`_search`/`_callers`, or CLI `codegraph explore|query|node|callers|callees|impact|affected`), then a *bounded* `rg -l`/`ast-grep` for exact strings. **Never** broad-scan all of FE/BE with `rg` and dump output; **never** use graphify for code. Indexes live per code repo (`myhospital-be/`, `myhospital-fe/`, active `worktrees/<slug>/{be,fe}`), never at root. Full policy + commands: `engine/rules/source-discovery.md`. Quick checks: `just codegraph-status`, `just doctor`.
- A graphify knowledge graph of `docs/`+`specs/` (**when present**, at `graphify-out/` — currently ABSENT). It is an **optional aid for docs/specs design questions only** (admission, inpatient, bed-day, BHYT/BHTM, conventions) and is **never required before reading or searching code**. For source code use CodeGraph + bounded `rg`/`fd`/`bat` (see `engine/rules/source-discovery.md`); for `.docx`/`.pdf` use `rga`; reach for `graphify query "<q>"` only when a design-intent/relationship question is faster answered by the graph than by reading the spec.
- **The graph may be ABSENT (currently `graphify-out/` does not exist) or Windows-stale.** `python scripts/harness_doctor.py` reports `no graph.json` when absent. **If absent, skip graphify entirely and read the source docs.** (Any earlier graph was a Windows build whose `src=` paths don't exist on Linux — untrusted anyway.) Do not present graph output as authoritative; verify against the real `docs/`/`specs/` files. Rebuild on Linux with `/graphify` only when a fresh graph is actually needed.
- At session start only, remember this local Agent Browser smoke-test login: customer code `bvtest3`, username `lynkhanh9822@gmail.com`, password `12.[s7HXZQ;NfAoF`.
- At session start only, follow the **Session Start Protocol** in AGENTS.md: use `python scripts/worktree.py list`, ask which slot/worktree before doing code work, and use fish syntax for user-facing commands. Never edit `myhospital-fe/` or `myhospital-be/` directly.
- **Worktree/Zellij are USER-DRIVEN — do NOT auto-run.** Never auto-execute `worktree.py`, `zorch`, `zimpl`, or any Zellij/worktree command on intent words ("create/join/setup/cleanup/sync worktree"). Print the exact fish command and/or point to `docs/guides/worktree-zellij-manual.md`; run a command only if the user explicitly says "do it for me". (If asked to run: default orchestrator `claude`, implementer `opencode`.)
- **Proactively use the harness tools** in `engine/agent-shortcuts.md` (auto-imported above): map the user's intent / short prompts to the right skill (`/mh-scaffold`, `/mh-implement`, `/mh-fix`), `just` recipe, or CLI so the user need not memorize commands — **except `/mh-review`, which is explicit-only**.
- **Self-learning tiers** (full model in AGENTS.md → "Self-Learning"): `main-brain/knowledge.md` (auto-loaded above) is the lean **source of truth** — **never write `main-brain/`** (the guard hook blocks it); it changes ONLY via the owner-invoked **`/promote`** skill (explicit-only, like `/mh-review`). Capture durable cross-cutting learnings in **`second-brain/`** freely (in-repo, all tools); exact detail lives in `engine/` + `engine/skills/` (`.claude/skills` is only a symlink/pointer).
- PowerShell is deprecated in this workspace. Do not use `powershell`, `pwsh`, or `*.ps1` as the primary runtime.

## Subagents v1.0

Spawn subagents to isolate context, parallelize independent work, or offload bulk mechanical tasks. Don't spawn when the parent needs the reasoning, when synthesis requires holding things together, or when spawn overhead dominates.

Pick the cheapest model that can do the subtask well:
- Haiku: bulk mechanical work, no judgment
- Sonnet: scoped research, code exploration, in-scope synthesis
- Opus: subtasks needing real planning or tradeoffs

If a subagent realizes it needs a higher tier than itself, return to the parent.

Parent owns final output and cross-spawn synthesis. User instructions override.

## Spec-Driven Development (Claude routing)

The full protocol lives in **AGENTS.md → "Spec-Driven Requirement & Design Protocol"** (layout, source
precedence, requirement states, 3-session workflow, change-control). Do not duplicate it here — this section
is only Claude-specific *how-to*.

- **Template:** start a module by copying `specs/_TEMPLATE/` to `specs/<module>/` (documentation only; never a worktree for spec sessions).
- **Skills (planned, not yet created — do not invoke until they exist):**
  - `spec-session <discovery|design|delivery>` — load `00-module-state` + `00-session-handoff` + that phase's primary files; run the session; update the `00-*` files at the end.
  - `spec-change-control` — when a gap/contradiction/Implementation Discovery Report surfaces; route it to `05-open-questions` / `06-decision-log` / `12-change-log` without rewriting business/design content.
  - `spec-design-reviewer` — run `11-review-checklist.md` (read-only) at the S2 baseline gate and S3 delivery gate.
  Until these skills exist, follow the AGENTS.md protocol manually.
- **graphify in SDD:** orient with `graphify query` before a session; `graphify affected "<node>"` for change impact; after editing specs, let the `SessionStart` staleness check drive a rebuild. Do not use graphify for single-file reads.
- **Subagent/model mapping (per "Subagents v1.0"):** codebase-investigator (verify technical truth, `file:line`) → Explore/Sonnet; design-reviewer → read-only subagent. The main session is the spec co-author/orchestrator (Opus).

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- **Scope:** graphify covers `docs/`+`specs/` **design intent only — not code.** Never run graphify before reading/searching FE/BE source. For source code use **CodeGraph** (broad) + bounded `rg`/`fd`/`bat` (exact) per `engine/rules/source-discovery.md`; use `rga` for `.docx`/`.pdf`.
- **Optional, not mandatory:** for a docs/specs *design-decision/relationship* question you may run `graphify query "<question>"` / `graphify explain "<concept>"` / `graphify path "<A>" "<B>"` to get a scoped subgraph — but reading the spec file directly is always an acceptable alternative.
- **Trust check first:** the graph may be **absent** (currently `graphify-out/` does not exist) or Windows-stale. Run `python scripts/harness_doctor.py` (reports `no graph.json` when absent) before relying on graph output. If absent or the root doesn't match this workspace, treat it as unavailable and read the source docs instead.
- After materially changing `docs/`/`specs/`, a rebuild is needed to refresh the graph; the freshness hook only *flags* staleness, it does not rebuild. Rebuild on Linux with the `/graphify` skill when you actually need a fresh graph.
