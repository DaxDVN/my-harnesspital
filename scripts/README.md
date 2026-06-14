# MyHospital Worktree Workflow

Workspace-level tooling for isolated FE/BE task worktrees with dedicated local SQL Server slots.

The current runtime is Python, not PowerShell. The user shell is fish, but scripts in this folder should stay shell-agnostic and be callable from any shell.

## Slot Map

| Slot | FE URL | BE URL | SQL container | SQL port |
|---|---|---|---|---|
| 1 | `http://localhost:3001` | `http://localhost:5001` | `mssql-hospital-wt1` | `1434` |
| 2 | `http://localhost:3002` | `http://localhost:5002` | `mssql-hospital-wt2` | `1435` |
| 3 | `http://localhost:3003` | `http://localhost:5003` | `mssql-hospital-wt3` | `1436` |
| 4 | `http://localhost:3004` | `http://localhost:5004` | `mssql-hospital-wt4` | `1437` |

Main FE/BE keep using `mssql-hospital` on `localhost,1433`.

## List Worktrees

```fish
python scripts/worktree.py list
```

## First-Time Setup DB Slots

```fish
python scripts/worktree.py init-db-slots
```

This starts SQL Server slot containers. It does not modify FE/BE code.

## Create A Task Worktree

When the user asks an agent to create/setup/prepare a new worktree and gives `slug` + `slot`, the agent should run the command directly. Do not make the user copy/paste it manually when the agent has terminal access.

Example task `fix-admission-birthdate`, slot 1:

```fish
python scripts/worktree.py create --slug fix-admission-birthdate --slot 1
```

Useful flags:

```fish
# light: no DB data sync, no Docker/SQL slot init, no FE install
python scripts/worktree.py create --slug fix-admission-birthdate --slot 1 --skip-db-sync --skip-db-init --skip-fe-install
python scripts/worktree.py create --slug fix-admission-birthdate --slot 1 --dry-run
```

`--skip-db-sync` still ensures the slot SQL container exists; add `--skip-db-init` to touch no DB infra at all.

The command:

- Creates FE worktree from `myhospital-fe/master` at `worktrees/<slug>/fe`.
- Creates BE worktree from `myhospital-be/main` at `worktrees/<slug>/be`.
- Creates branch `feature/<slug>` in both repos.
- Writes FE `.env` for the selected FE/BE ports.
- Writes BE `.env` for the selected BE port and SQL slot.
- Optionally syncs slot DB from the main DB.

## Multi-Agent Zellij Sessions

After successful creation, validate:

```fish
python scripts/worktree.py list
test -d worktrees/<slug>/be; and echo "OK be"
test -d worktrees/<slug>/fe; and echo "OK fe"
```

Then open two sessions. 1 worktree = 2 sessions: orchestrator + implementer.

Default tools:

- orchestrator: `claude`
- implementer: `opencode`

Helpers (`zorch`/`zimpl`/`zls`/`zkillwt`/`wtlist`/`wtcreate`/`wtjoin`) live in
`scripts/fish/myhospital-zellij.fish` — source it once (see
`docs/agent-rules/worktree-workflow.md`), then:

```fish
zorch <slug> <orchestrator_tool>
zimpl <slug> <implementer_tool>
```

Fallback without helpers:

```fish
cd /home/dax/Documents/arabica/roast/worktrees/<slug>
zellij attach mh-<slug>-orch-<orchestrator_tool> 2>/dev/null; or zellij --session mh-<slug>-orch-<orchestrator_tool> --layout myhospital-orch
```

```fish
cd /home/dax/Documents/arabica/roast/worktrees/<slug>
zellij attach mh-<slug>-impl-<implementer_tool> 2>/dev/null; or zellij --session mh-<slug>-impl-<implementer_tool> --layout myhospital-impl
```

`zorch` and `zimpl` only open sessions. They do not replace `python scripts/worktree.py create`.

## Join Existing Worktree

For join existing requests such as `join lại worktree bed`, do not create a new worktree. List/check and open sessions:

```fish
python scripts/worktree.py list
zorch bed claude
zimpl bed opencode
```

For a targeted implementer request:

```fish
python scripts/worktree.py list
zimpl bed composer
```

## Run Backend

```fish
cd worktrees/fix-admission-birthdate/be
dotnet run --project MyHospital --no-launch-profile
```

## Run Frontend

```fish
cd worktrees/fix-admission-birthdate/fe
npm install
npm run dtos:update
npm run client:generate
npm run dev
```

Open FE at `http://localhost:3001`.

## Re-sync Slot DB

Use this when you want to reset a slot DB from main DB data:

```fish
python scripts/worktree.py sync-db --slot 1 --be-path worktrees/fix-admission-birthdate/be
```

Use `--yes` for non-interactive execution and `--dry-run` to preview commands:

```fish
python scripts/worktree.py sync-db --slot 1 --be-path worktrees/fix-admission-birthdate/be --dry-run
```

If the target BE worktree does not contain `MyHospital.ServiceInterface/Migrations`, pass a separate migration source:

```fish
python scripts/worktree.py sync-db --slot 2 --be-path worktrees/schedule-shift-ux-audit/be --migration-be-path myhospital-be
```

## Cleanup After Review/Merge

Cleanup refuses to run if FE or BE still has Git-visible changes.

```fish
python scripts/worktree.py cleanup --slug fix-admission-birthdate
```

Preview first:

```fish
python scripts/worktree.py cleanup --slug fix-admission-birthdate --dry-run
```

## Sync Main Branches

This command is intentionally guarded because it can discard un-stashed tracked changes while preserving the `pre-config-before-dev` stash pattern.

```fish
python scripts/worktree.py sync-main --dry-run
python scripts/worktree.py sync-main
```

## Legacy PowerShell Files

The old `*.ps1` files are kept as deprecated reference material only. Do not use PowerShell or `pwsh` as the primary runtime in Linux sessions.
