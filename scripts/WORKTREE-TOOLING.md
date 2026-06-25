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
python scripts/worktree.py list          # table: slug, slot, FE/BE/SQL ports
python scripts/worktree.py info --slug fix-admission-birthdate
python scripts/worktree.py init-db-slots
python scripts/worktree.py create --slug fix-admission-birthdate --slot 1
python scripts/worktree.py repair-config --slug fix-admission-birthdate
python scripts/worktree.py repair-config --all
python scripts/worktree.py sync-db --slot 1 --be-path worktrees/fix-admission-birthdate/be
python scripts/worktree.py cleanup --slug fix-admission-birthdate
python scripts/worktree.py sync-main --dry-run
```

Use `--dry-run` before risky commands. `sync-db`, `cleanup`, and `sync-main` have confirmation prompts unless a `--yes` or dry-run path is used.
`list` checks `.env` plus local-only BE runtime files (`appsettings.Development.json`, `launchSettings.json`, reporting appsettings). A `MISMATCH` status means the worktree may run on the wrong FE/BE/SQL port even if `.env` looks correct; run `repair-config` before starting FE/BE.

## Create vs Join

- `create`, `tạo`, `setup worktree mới`, `chuẩn bị worktree mới`, `mở task <slug> slot <n>`: run `python scripts/worktree.py create --slug <slug> --slot <slot>`.
- New default experience: **export your DB details once**, then just `python scripts/worktree.py create --slug xxx --slot N` and it auto does create + make migrate-data (recreate schema) + sync data from main. See "Export Once" section below.
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

## Sessions

The harness stops at worktree lifecycle and runtime config. Terminal/session management is owner-manual.

## Run A Worktree

```fish
python scripts/worktree.py run-be --slug fix-admission-birthdate
```

```fish
cd worktrees/fix-admission-birthdate/fe
npm install
npm run dtos:update
npm run client:generate
npm run dev
```

## Summary of New Recommended Process

For every new worktree (especially when you care about not leaking DB config):

1. `python scripts/worktree.py create ... --skip-db-sync --skip-db-init`
2. Use the key-value patch commands below (or your own secure method) to configure the exact DB connection in the worktree files.
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
