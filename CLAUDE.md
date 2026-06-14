# Claude Code - MyHospital workspace

@AGENTS.md

## Routing

- When working under `myhospital-fe/`, load and obey `myhospital-fe/CLAUDE.md`.
- When working under `myhospital-be/`, load and obey `myhospital-be/CONVENTIONS.md` (there is no `myhospital-be/CLAUDE.md`).
- For cross-package work, treat the BE contract and BE conventions as the source of truth first, then regenerate FE contract artifacts and validate FE rules second.

## Operating rules

- Keep tasks small enough that Claude can stay inside one package when possible.
- Use plan mode before edits that affect routing, provider hierarchy, shared contracts, or migrations.
- Prefer the package-specific CLAUDE file over chat memory for long-lived conventions.
- A graphify knowledge graph of `docs/`+`specs/` lives at `graphify-out/`. It is an **optional aid for docs/specs design questions only** (admission, inpatient, bed-day, BHYT/BHTM, conventions) and is **never required before reading or searching code**. For code use `rg`/`fd`/`bat`; for `.docx`/`.pdf` use `rga`; reach for `graphify query "<q>"` only when a design-intent/relationship question is faster answered by the graph than by reading the spec.
- **The current graph is STALE: it was built on Windows (its recorded build root `graphify-out/.graphify_root` is a Windows drive path, not this Linux workspace) and its node citations point at Windows paths that do not exist on Linux.** Until it is rebuilt on Linux, do not trust its `src=` file paths and do not present graph output as authoritative — verify against the real `docs/`/`specs/` files. The `SessionStart` hook prints a `[graphify] … STALE …` line when it detects this cross-root mismatch; when you see it, say the graph is stale and prefer reading the source docs. Run `python scripts/harness_doctor.py` to see the exact recorded root.
- At session start only, remember this local Agent Browser smoke-test login: customer code `HMU`, username `admin`, password `123456`.
- At session start only, follow the **Session Start Protocol** in AGENTS.md: use `python scripts/worktree.py list`, ask which slot/worktree before doing code work, and use fish syntax for user-facing commands. Never edit `myhospital-fe/` or `myhospital-be/` directly.
- For worktree workflow requests, follow **Multi-Agent Worktree + Zellij Workflow Protocol** in AGENTS.md. Create/setup/new worktree requests mean execute `python scripts/worktree.py create`; join/attach/open-existing requests mean list/check and open Zellij sessions without creating. Default tools are `claude` orchestrator and `opencode` implementer unless the user specifies otherwise.
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
- **Scope:** graphify covers `docs/`+`specs/` **design intent only — not code.** Never run graphify before reading/searching FE/BE source. Use `rg`/`fd`/`bat` for code and `rga` for `.docx`/`.pdf`.
- **Optional, not mandatory:** for a docs/specs *design-decision/relationship* question you may run `graphify query "<question>"` / `graphify explain "<concept>"` / `graphify path "<A>" "<B>"` to get a scoped subgraph — but reading the spec file directly is always an acceptable alternative.
- **Trust check first:** the current graph is Windows-built and stale (see Operating rules). Run `python scripts/harness_doctor.py` (or check `graphify-out/.graphify_root` == this workspace root) before relying on graph output. If the root does not match, treat the graph as untrusted and read the source docs instead.
- After materially changing `docs/`/`specs/`, a rebuild is needed to refresh the graph; the freshness hook only *flags* staleness, it does not rebuild. Rebuild on Linux with the `/graphify` skill when you actually need a fresh graph.
