# Claude Code - MyHospital Workspace

@AGENTS.md
@main-brain/knowledge.md

This file is Claude-specific and intentionally thin. Global rules live in `AGENTS.md`; detailed workflow/rule docs are lazy-loaded through the router and the AGENTS lazy-load index.

## Routing

- For non-trivial natural-language routing, run `python scripts/harness_preflight.py "<user prompt>"` first.
- Present the predicted workflow/skill/agent/rule card and wait for owner confirmation before workflow execution, agent launch, browser sweep, or non-trivial source edit.
- Use `python scripts/harness_router.py "<user prompt>"` when you need raw router details.
- Do not auto-load `engine/agent-shortcuts.md`; it is a lazy legacy shortcut reference.
- `mh-review` and `/promote` remain explicit-only.

## Package Scope

- FE work: load `myhospital-fe/CLAUDE.md`, then run `python scripts/rule_card.py fe "<task>"` and open the returned quick/topic cards. Open full `engine/rules/frontend.md` only for uncovered/high-risk cases.
- BE work: run `python scripts/rule_card.py be "<task>"` and open the returned quick/topic cards. Open full `engine/rules/backend.md` only for uncovered/high-risk cases; `myhospital-be/CONVENTIONS.md` is legacy/advisory.
- Cross-package work: BE contract first, DTO/client regen second, FE validation after.

## Source Discovery

Use CodeGraph first for source code, then bounded exact search. Never use graphify for source code.

Full policy: `engine/rules/source-discovery.md`.

## Claude Wiring

`.claude/{skills,agents,hooks,workflows}` are symlinks to `engine/`. Engine assets remain canonical.

Spawn subagents only for bounded, disjoint work. The parent owns architecture, integration, blocker resolution, and final validation. Multi-agent policy: `engine/rules/multi-agent-execution.md`.

## Memory

`main-brain/knowledge.md` is loaded above because it is mandatory standing memory. Keep it lean. Use `scripts/learning_recall.py` for provisional `second-brain/` notes and open only matched notes per `engine/rules/memory-policy.md`. Never write `main-brain/` directly.

## Graphify

Graphify is optional docs/specs design-intent tooling only. Check trust with `python scripts/harness_doctor.py` before relying on it. Policy: `engine/rules/graphify.md`.
