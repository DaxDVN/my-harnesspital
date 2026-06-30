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
python scripts/main_brain_promotion_candidates.py scan
python scripts/harness_ready.py
```

These commands are read-only except `main_brain_promotion_candidates.py write-report`, which writes review artifacts under `docs/harness/`.

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

## Create vs Join Intent Map

- `create`, `tạo`, `setup worktree mới`, `chuẩn bị worktree mới`, `mở task <slug> slot <n>`: run `python scripts/worktree.py create --slug <slug> --slot <slot>`.
- New default experience: **export your DB details once**, then just `python scripts/worktree.py create --slug xxx --slot N` and it auto does create + make migrate-data (recreate schema) + sync data from main. See "Export Once" below.
- Light/no DB sync requests: add `--skip-db-sync --skip-db-init --skip-fe-install` (touches no Docker/SQL).
- Preview requests: add `--skip-db-sync --skip-fe-install --dry-run`.
- `repair`, `fix port`, `config sai`, `BE đọc nhầm DB/port`: run `python scripts/worktree.py repair-config --slug <slug>` or `--all`.
- `join`, `mở lại`, `attach`, `vào worktree đang có`: join existing; do not create. Run `python scripts/worktree.py list`, use the printed slot/ports, and check the folders. Terminal/session orchestration is owner-manual.
- `cleanup`, `xóa`, `dọn worktree`: confirm because this is destructive, then run cleanup.
- `sync`: run `sync-main` or `sync-db` depending on whether the user asked about branches or database.

`create` and `repair-config` keep direct `dotnet run` aligned with `worktree.py run-be` by syncing
the slot-aware `.env` values into the BE launch profile. That includes CORS, Redis, JWT/Firebase,
ServiceStack/license prerequisites, FE login URL, BE port, and SQL slot connection strings.

## "Export Once" Flow (Recommended - Set config in env, then one create command)

**Chỉ export cái của main server thôi** (đúng theo ý bạn):

Local slot config của bạn giống nhau hết (kể cả password), không public network nên không cần giấu.

Chỉ cần export cái của **main DB server** (source) là đủ:

```fish
export MYHOSPITAL_SOURCE_DB_SERVER="localhost"
export MYHOSPITAL_SOURCE_DB_PORT="1433"
export MYHOSPITAL_SOURCE_DB_NAME="MyHospital"
export MYHOSPITAL_SOURCE_DB_USER="sa"
export MYHOSPITAL_SOURCE_DB_PASSWORD="your-main-server-password"
```

Sau đó chỉ cần chạy:

```fish
python scripts/worktree.py create --slug ipd-improve-v3 --slot 1
```

Script sẽ tự:
- Tạo worktree
- Chạy `make migrate-data CONFIRM=yes` (recreate schema trong slot container, dùng default local trong code)
- Sync data từ main server (dùng SOURCE_* env) vào slot DB

Local target để mặc định trong code (vì local giống nhau). Chỉ main server mới cần private.

### Want a light worktree (no DB touch)?
```fish
python scripts/worktree.py create --slug light-task --slot 2 --skip-db-sync --skip-db-init
```

The script now reads source DB from `MYHOSPITAL_SOURCE_*` env vars and target slot DB from slot config + `MYHOSPITAL_TARGET_DB_PASSWORD`. They can be completely independent.

## Manual / Legacy Config Patching (only for --skip-db-sync cases)

The export-once + auto flow now handles writing all DB connection strings automatically.

Use the old patch commands only if you deliberately created a worktree with `--skip-db-sync` for a one-off test.

### For .env (BE + FE)

```bash
WT="worktrees/my-task-v2"

# BE .env - set full connection string (recommended to use env var for password)
CONN="Server=localhost,1434;Initial Catalog=MyHospital;User ID=sa;Password=$MYHOSPITAL_SQL_PASSWORD;MultipleActiveResultSets=true;Encrypt=false;TrustServerCertificate=true"
sed -i "s|^ConnectionStrings__DefaultConnection=.*|ConnectionStrings__DefaultConnection=$CONN|" "$WT/be/.env"
sed -i "s|^ConnectionStrings__ReadOnlyConnection=.*|ConnectionStrings__ReadOnlyConnection=$CONN|" "$WT/be/.env"

# Optional: other keys
sed -i "s|^ASPNETCORE_ENVIRONMENT=.*|ASPNETCORE_ENVIRONMENT=Development|" "$WT/be/.env"
```

### For appsettings.Development.json (BE)

```bash
python3 - <<'PY'
import json, os
p = "worktrees/my-task-v2/be/MyHospital/appsettings.Development.json"
with open(p) as f: data = json.load(f)
conn = f"Server=localhost,1434;Initial Catalog=MyHospital;User ID=sa;Password={os.environ.get('MYHOSPITAL_SQL_PASSWORD','')};MultipleActiveResultSets=true;Encrypt=false;TrustServerCertificate=true"
data.setdefault("ConnectionStrings", {})["DefaultConnection"] = conn
data.setdefault("ConnectionStrings", {})["ReadOnlyConnection"] = conn
with open(p, "w") as f: json.dump(data, f, indent=2, ensure_ascii=False)
print("Updated appsettings.Development.json")
PY
```

### For launchSettings.json (optional, for dotnet run)

```bash
python3 - <<'PY'
import json, os
p = "worktrees/my-task-v2/be/MyHospital/Properties/launchSettings.json"
with open(p) as f: data = json.load(f)
conn = f"Server=localhost,1434;Initial Catalog=MyHospital;User ID=sa;Password={os.environ.get('MYHOSPITAL_SQL_PASSWORD','')};MultipleActiveResultSets=true;Encrypt=false;TrustServerCertificate=true"
for profile in data.get("profiles", {}).values():
    ev = profile.setdefault("environmentVariables", {})
    ev["ConnectionStrings__DefaultConnection"] = conn
    ev["ConnectionStrings__ReadOnlyConnection"] = conn
with open(p, "w") as f: json.dump(data, f, indent=2, ensure_ascii=False)
print("Updated launchSettings.json")
PY
```

After setting, you can run `python scripts/worktree.py repair-config --slug my-task-v2` to sync other runtime files if needed.

**Security tip**: Export password only in current shell:
```bash
export MYHOSPITAL_SQL_PASSWORD="your-secure-pass-here"
# then run the set commands above
unset MYHOSPITAL_SQL_PASSWORD   # when done
```

Never commit real passwords. Worktree files live only locally.

## Summary of New Recommended Process

For every new worktree (especially when you care about not leaking DB config):

1. `python scripts/worktree.py create ... --skip-db-sync --skip-db-init`
2. Use the key-value patch commands above (or your own secure method) to configure the exact DB connection in the worktree files.
3. `cd worktrees/<slug>/be && make migrate-data CONFIRM=yes`  → this recreates the schema in the slot's container DB.
4. `python scripts/worktree.py sync-db ...` with explicit source (main DB) and your password (via env var).

This gives you recreate slot schema + data sync from main DB server, with config set separately.

## Local Requirements

The Python CLI expects the normal Linux toolchain:

- `git`
- `python`
- `docker`
- `dotnet`
- `npm` when FE dependency install is not skipped

SQL password defaults to `MYHOSPITAL_SQL_PASSWORD` or `Hospital123!`.
