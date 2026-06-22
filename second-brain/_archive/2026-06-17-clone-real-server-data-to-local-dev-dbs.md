---
title: "Clone real server data to local dev DBs"
date: "2026-06-17"
status: provisional
source: conversation
scope: backend / dev-data
confidence: high
owner_confirmed: false
proposed_target: engine/skills (a `clone-server-data` recipe) or main-brain
applies_when:
  tasks: ["seed local db with real data", "clone server data", "refresh dev database", "test with realistic data"]
  globs: ["myhospital-be/Scripts/export_db_data.py", "myhospital-be/Scripts/import_db_data.py", "myhospital-be/Makefile"]
  keywords: ["clone data", "real data", "seed", "backup-data", "restore-data", "db-clear", "1433", "slot", "docker mssql"]
---

# Clone REAL server data → local dev DBs (instead of CSV seed)

CSV seed (`make seed-local`) is sample data with a large skip-list (VitalSigns, MedicalVisitClinicalService, Inventory, Bid*, Transfer* …) → unrealistic for business testing. To get realistic data, **clone the real SQL Server** at the data level (dump INSERTs, not a `.bak`). Repo ships the tooling; no native `BACKUP/RESTORE DATABASE`.

**Why:** the import script (`import_db_data.py`) is schema-drift tolerant (drops extra cols, fills nullable/default, skips tables missing a NOT NULL FK), so a real-data dump survives local schema differences far better than CSV seed.

**How to apply** (verified 2026-06-17, cloned 46,005 rows / 252 tables):

Prereqs — pymssql in a venv (Arch blocks system pip, PEP 668):
```
python3 -m venv myhospital-be/.venv
myhospital-be/.venv/bin/pip install pymssql
```
Makefile auto-uses `myhospital-be/.venv/bin/python3` if present (`PYTHON := ...`).

1. **Export from source (READ-ONLY, SELECT only — never edits server):** all scripts read `DB_SERVER/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD` env (priority over `.env`).
   ```
   DB_SERVER=<host> DB_PORT=1433 DB_NAME=MyHospital DB_USER=sa DB_PASSWORD='***' \
     OUTPUT_FILE=/tmp/server-data.sql .venv/bin/python3 Scripts/export_db_data.py
   ```
2. **Load into a target DB** (clear → schema → data):
   - `Scripts/drop_db_objects.py` (= `make db-clear`) — drops FKs/tables/views/SPs, keeps DB.
   - schema: `dotnet ef database update --project MyHospital.ServiceInterface --startup-project MyHospital --connection "<connstr>"`
   - data: `Scripts/import_db_data.py /tmp/server-data.sql`
   `restore-data` does NOT clear first → always `db-clear` before, else PK conflicts.

**Multi-DB / docker slots:** containers `mssql-hospital`(1433 main), `mssql-hospital-wt2`(1435), `-wt3`(1436), `-wt4`(1437) — all `sa/Hospital123!`. To clone into a non-1433 port, drop+import via `DB_PORT=<p>` env, and migrate via `dotnet ef ... --connection "Server=localhost,<p>;...;Password=Hospital123!;TrustServerCertificate=True"`. Loop script: `/tmp/clone-to-slots.sh`.

**Gotchas:**
- pymssql needs sandbox OFF (it timed out under the Bash sandbox even though raw TCP connected).
- EF design-time factory (`MyHospitalContextDesignFactory.cs`) prioritizes env `ConnectionStrings__DefaultConnection` but `Env.Load(.env)` may clobber it → use `dotnet ef --connection` to override a non-default port reliably.
- `[User]` is a reserved word — bracket it in raw queries.
- Expected skips on a clean target: `InpatientRelativeType` (PK already seeded by migration), `LisIntegrationLogs` (table not in local schema). Harmless.
