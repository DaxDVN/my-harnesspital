# Worktree Workflow — Canonical Reference

> Single source of truth for task worktree lifecycle. Terminal/session management is intentionally outside
> the harness; the owner controls sessions manually.

## Model

- Worktree layout: `worktrees/<slug>/fe` and `worktrees/<slug>/be`.
- Source changes go in a task worktree, not directly in `myhospital-fe/` or `myhospital-be/`.
- Each worktree owns one slot: FE port, BE port, and SQL port are resolved by `scripts/worktree.py list`.
- `scripts/worktree.py` is the only harness automation for create/list/repair/sync/run/cleanup.
- Do not infer or guess ports manually when `worktree.py list` reports `MISMATCH`; run `repair-config`.

## User-Driven Boundary

Do not auto-run create/join/setup/cleanup/sync commands on intent words. Print the exact command first,
then run it only if the owner explicitly says to run that command.

Terminal panes and tool session placement are owner-manual. Agents must not propose terminal multiplexer
helpers, repo-managed session layouts, or `just z-*` recipes.

## Command Reference

| Intent | Command |
|---|---|
| list active worktrees | `python scripts/worktree.py list` |
| show one worktree | `python scripts/worktree.py info --slug <slug>` |
| create full worktree | `python scripts/worktree.py create --slug <slug> --slot <slot>` |
| create light worktree | `python scripts/worktree.py create --slug <slug> --slot <slot> --skip-db-sync --skip-db-init --skip-fe-install` |
| preview create | `python scripts/worktree.py create --slug <slug> --slot <slot> --skip-db-sync --skip-db-init --skip-fe-install --dry-run` |
| repair config | `python scripts/worktree.py repair-config --slug <slug>` |
| repair all configs | `python scripts/worktree.py repair-config --all` |
| run BE | `python scripts/worktree.py run-be --slug <slug>` |
| sync slot DB | `python scripts/worktree.py sync-db --slot <slot> --be-path worktrees/<slug>/be` |
| cleanup worktree | `python scripts/worktree.py cleanup --slug <slug>` |
| sync main repos | `python scripts/worktree.py sync-main --dry-run` then `python scripts/worktree.py sync-main` if approved |

## Join Existing Worktree

For "join", "mở lại", or "vào worktree đang có":

1. Run `python scripts/worktree.py list`.
2. Confirm the slug, slot, ports, and status.
3. Check folders exist with `test -d worktrees/<slug>/be` and `test -d worktrees/<slug>/fe`.
4. Stop. Terminal/session orchestration is manual owner control.

## CodeGraph Index

Source-code exploration uses CodeGraph, indexed per code repo. A worktree's `be` and `fe` directories each
need their own index when the worktree becomes active.

| Intent | Command |
|---|---|
| init CodeGraph for worktree | `just codegraph-init-worktree <slug>` |
| status for worktree | `just codegraph-status-worktree <slug>` |
| sync worktree index | `just codegraph-sync-worktree <slug>` |

Never index the workspace root. Root `.gitignore` excludes FE/BE/worktrees, so a root index sees no source
code and can confuse agents.

## Caveats

- `create` defaults to a full DB sync unless `--skip-db-sync` is passed.
- `sync-main` only updates a repo if it is already on its target branch, unless owner explicitly approves
  checkout behavior.
- "sync current worktree with main" is not a `worktree.py` command yet; do it manually after `sync-main`.
- Run `python scripts/harness_doctor.py` or `just doctor` for harness health checks.
