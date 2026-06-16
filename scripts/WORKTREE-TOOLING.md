# MyHospital Worktree Tooling

Workspace-level commands are provided by `scripts/worktree.py`.

PowerShell scripts from the Windows workflow are deprecated. Keep new automation in Python so it works from fish, bash, CI, and agent shells.

## Slot Map

| Slot | FE | BE | SQL container | SQL port |
|---|---:|---:|---|---:|
| 1 | 3001 | 5001 | `mssql-hospital-wt1` | 1434 |
| 2 | 3002 | 5002 | `mssql-hospital-wt2` | 1435 |
| 3 | 3003 | 5003 | `mssql-hospital-wt3` | 1436 |
| 4 | 3004 | 5004 | `mssql-hospital-wt4` | 1437 |

Main FE/BE keep using `mssql-hospital` on `localhost,1433`.

## Source-code search (CodeGraph)

Source code is explored with **CodeGraph** (per-repo index), not a broad `rg` scan or graphify.
`just codegraph-init-main` (one-time, main repos), `just codegraph-init-worktree <slug>` after
creating a worktree, `just codegraph-status`. Policy: `engine/rules/source-discovery.md`.

## Commands

Agents should execute these commands directly when users ask for worktree workflow actions. The user should not need to remember long create commands.

```fish
python scripts/worktree.py --help
python scripts/worktree.py list
python scripts/worktree.py init-db-slots
python scripts/worktree.py create --slug fix-admission-birthdate --slot 1
python scripts/worktree.py sync-db --slot 1 --be-path worktrees/fix-admission-birthdate/be
python scripts/worktree.py cleanup --slug fix-admission-birthdate
python scripts/worktree.py sync-main --dry-run
```

Use `--dry-run` before risky commands. `sync-db`, `cleanup`, and `sync-main` have confirmation prompts unless a `--yes` or dry-run path is used.

## Create vs Join

- `create`, `tạo`, `setup worktree mới`, `chuẩn bị worktree mới`, `mở task <slug> slot <n>`: run `python scripts/worktree.py create --slug <slug> --slot <slot>`.
- Light/no DB sync requests: add `--skip-db-sync --skip-db-init --skip-fe-install` (touches no Docker/SQL).
- Preview requests: add `--skip-db-sync --skip-fe-install --dry-run`.
- `join`, `mở lại`, `attach`, `vào worktree đang có`: join existing; do not create. Run `python scripts/worktree.py list`, check the folder, then open Zellij sessions.
- `cleanup`, `xóa`, `dọn worktree`: confirm because this is destructive, then run cleanup.
- `sync`: run `sync-main` or `sync-db` depending on whether the user asked about branches or database.

## Zellij Sessions

1 worktree = 2 sessions: orchestrator + implementer.

Defaults when the user does not specify tools:

- orchestrator: `claude`
- implementer: `opencode`

Helpers live in `scripts/fish/myhospital-zellij.fish` (source once; see
`engine/rules/worktree-workflow.md` for the full intent→command map):

```fish
zorch <slug> <orchestrator_tool>
zimpl <slug> <implementer_tool>
```

Fallback:

```fish
cd /home/dax/Documents/arabica/roast/worktrees/<slug>
zellij attach mh-<slug>-orch-<orchestrator_tool> 2>/dev/null; or zellij --session mh-<slug>-orch-<orchestrator_tool> --layout myhospital-orch
```

```fish
cd /home/dax/Documents/arabica/roast/worktrees/<slug>
zellij attach mh-<slug>-impl-<implementer_tool> 2>/dev/null; or zellij --session mh-<slug>-impl-<implementer_tool> --layout myhospital-impl
```

Zellij helpers do not replace `scripts/worktree.py create`; they run after a worktree exists.

## Run A Worktree

```fish
python scripts/worktree.py run-be --be-path worktrees/fix-admission-birthdate/be
```

```fish
cd worktrees/fix-admission-birthdate/fe
npm install
npm run dtos:update
npm run client:generate
npm run dev
```

## Local Requirements

The Python CLI expects the normal Linux toolchain:

- `git`
- `python`
- `docker`
- `dotnet`
- `npm` when FE dependency install is not skipped

SQL password defaults to `MYHOSPITAL_SQL_PASSWORD` or `Hospital123!`.
