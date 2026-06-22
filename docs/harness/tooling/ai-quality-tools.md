# AI quality tooling

Optional local tools installed for harness quality/time/token support. These tools do not auto-run workflows.

## Installed packages

- `promptfoo`: eval harness prompts/router behavior without relying on chat memory.
- `@ast-grep/cli`: AST structural search/lint/rewrite, useful when a repeated bug class should become a deterministic scanner.
- `ctx7`: Context7 CLI for current library/API docs. Use on demand for external libraries, not for MyHospital source discovery.
- Claude Code project setup is installed as `.claude/rules/context7.md` plus `engine/skills/find-docs/SKILL.md`.

## Commands

```bash
npm run tooling:doctor
npm run promptfoo:router
npm run promptfoo:router:json
npm run ast-grep:version
npm run ctx7:version
```

Context7 examples:

```bash
npx ctx7 library react "hooks" --json
npx ctx7 docs /reactjs/react.dev "useEffect cleanup"
```

## Usage policy

- Keep these tools opt-in; do not add them to default session boot.
- Use CodeGraph first for MyHospital source. Use Context7 only for external library/API docs.
- Promote repeated `bug_class:` patterns into deterministic `ast-grep`/scanner rules when feasible.
- Use promptfoo for router/prompt regression checks before promoting workflow lifecycle status.

## Context7 auth note

`npx ctx7 whoami` should show the authenticated account. The harness uses CLI + Skill mode, not MCP mode, to
avoid MCP tool overhead and keep docs lookup on-demand.

## Footprint note

Local `node_modules/` is intentionally gitignored. `promptfoo` is a large devDependency because it brings
browser/model-eval transitive packages; keep it opt-in and do not load generated eval JSON into agent context.

## Not installed

- `snyk-agent-scan` is intentionally not installed per owner instruction.
- BMAD/SuperClaude/Claude Flow are intentionally not installed because they overlap with the owner-gated harness and encourage autonomous workflow ownership.
