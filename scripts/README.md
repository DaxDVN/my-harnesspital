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

## Source-code search (CodeGraph)

Explore source with **CodeGraph**, not a broad `rg` dump or graphify. Indexes are per code
repo (`myhospital-be/`, `myhospital-fe/`, and an active `worktrees/<slug>/{be,fe}`), never at
root. After creating a worktree, `just codegraph-init-worktree <slug>`; check with
`just codegraph-status`. Full policy + command table: `engine/rules/source-discovery.md`.

## Harness Preflight And Governance

```fish
python scripts/harness_preflight.py "sửa bug sheet nội trú trong worktree fix-bug-noi-tru"
python scripts/codex_preflight.py "sửa bug sheet nội trú trong worktree fix-bug-noi-tru"
python scripts/harness_scanner_promotion.py scan
python scripts/harness_lifecycle_eval.py scan
python scripts/main_brain_promotion_candidates.py scan
python scripts/harness_ready.py
```

These commands are read-only except `main_brain_promotion_candidates.py write-report` and
`harness_lifecycle_eval.py new-template`, which write review/eval artifacts under `docs/harness/`.

## Optional AI Quality Tooling

Root `package.json` installs opt-in local tools for harness quality checks. They are not part of session boot.

```fish
npm run tooling:doctor
npm run promptfoo:router
npx ast-grep -p 'print($A)' -l py scripts/harness_router.py
npx ctx7 library react "hooks" --json
npx ctx7 docs /reactjs/react.dev "useEffect cleanup"
```

Details: `docs/harness/tooling/ai-quality-tools.md`.

## List Worktrees

```fish
python scripts/worktree.py list
```

`list` prints the canonical slug → slot → FE/BE/SQL routing table. Use `--plain`
only for scripts that need legacy slug-only output.

```fish
python scripts/worktree.py info --slug fix-admission-birthdate
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
- Patches local-only BE runtime config so direct `dotnet run` also uses the selected slot:
  `MyHospital/appsettings.Development.json`, `MyHospital/Properties/launchSettings.json`,
  and `MyHospital.Reporting/appsettings.json`.
- Writes `.myhospital-worktree.json` so agents can resolve slug → slot/ports without guessing.
- Optionally syncs slot DB from the main DB, using the new BE worktree migrations by default.

`list` validates both `.env` and the hidden BE runtime files above. If it prints `MISMATCH`,
do not guess ports manually; run `repair-config`.

## Repair Existing Worktree Config

Use this when an existing worktree has stale port/DB settings, or after script changes that affect local runtime config:

```fish
python scripts/worktree.py repair-config --slug fix-admission-birthdate
python scripts/worktree.py repair-config --all
```

This rewrites FE `.env`, BE `.env`, BE appsettings/launchSettings/reporting config, and metadata
from the worktree slot. BE local config patches are marked `skip-worktree` so script-managed local
runtime changes do not make a new task branch dirty.

## After Creating A Worktree

After successful creation, validate:

```fish
python scripts/worktree.py list
test -d worktrees/<slug>/be; and echo "OK be"
test -d worktrees/<slug>/fe; and echo "OK fe"
```

Terminal/session orchestration is owner-manual and intentionally outside the harness.

## Join Existing Worktree

For join existing requests such as `join lại worktree bed`, do not create a new worktree. List/check only:

```fish
python scripts/worktree.py list
```

Then stop. The owner controls terminal/session placement manually.

## Run Backend

```fish
python scripts/worktree.py run-be --slug fix-admission-birthdate
```

Shortcuts:

```fish
just wt-run-be fix-admission-birthdate --no-build
wtrunbe fix-admission-birthdate --no-build
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
