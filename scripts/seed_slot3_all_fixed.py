#!/usr/bin/env python3
"""Universal seed data generator for MyHospital slot 2 (qms-v1).
Pre-fetches schema and FK data, generates >=20 English records per table.
Target: localhost,1435/MyHospital
"""

from __future__ import annotations

import subprocess
import random
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

OUTPUT = Path("/home/dax/Documents/arabica/roast/scripts/seed_slot3_all.sql")
CONTAINER = "mssql-hospital-wt3"
DB = "MyHospital"
SA_PASS = "Hospital123!"
TENANT = 13
HOSPITAL = 15
USER_ADMIN = 176
MIN_RECORDS = 20

random.seed(42)

MALE_NAMES = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles",
              "Daniel", "Matthew", "Anthony", "Mark", "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin"]
FEMALE_NAMES = ["Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan", "Jessica", "Sarah", "Karen",
                "Nancy", "Lisa", "Betty", "Margaret", "Sandra", "Ashley", "Dorothy", "Kimberly", "Emily", "Donna"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
              "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
ADDRESSES = ["123 Main St", "456 Oak Ave", "789 Pine Rd", "321 Elm Blvd", "654 Maple Dr", "987 Cedar Ln",
             "147 Birch Ct", "258 Walnut Way", "369 Spruce Pl", "741 Ash Ter"]
CITIES = ["Springfield", "Riverside", "Greenville", "Fairview", "Madison", "Franklin", "Clinton", "Georgetown"]
PHONE_PFX = ["090", "091", "093", "094", "096", "097", "098", "032", "033", "034", "035", "036", "037", "038", "039"]
NOW = datetime(2026, 6, 22, 8, 0, 0)


def sql_cmd(query: str, timeout: int = 30) -> str:
    cmd = ["docker", "exec", CONTAINER,
           "/opt/mssql-tools18/bin/sqlcmd",
           "-S", "localhost", "-U", "sa", "-P", SA_PASS,
           "-C", "-d", DB, "-W", "-w", "400", "-Q", query]
    return subprocess.check_output(cmd, text=True, timeout=timeout)


def sql_str(val) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return f"{val:.2f}"
    if isinstance(val, datetime):
        return sql_dt(val)
    s = str(val).replace("'", "''")
    return f"N'{s}'"


def sql_dt(dt: datetime) -> str:
    return f"N'{dt.strftime('%Y-%m-%d %H:%M:%S')}'"


def parse_rows(output: str) -> list[list[str]]:
    """Parse sqlcmd output into rows of column values."""
    lines = output.strip().splitlines()
    if not lines:
        return []
    rows = []
    for line in lines:
        line = line.rstrip()
        if not line or line.startswith("---") or line.startswith("TABLE") or line.startswith("COLUMN"):
            continue
        # Try pipe separator first, then space
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
        else:
            parts = line.split()
        if parts and parts[0]:
            rows.append(parts)
    return rows


# ============================================================
# Pre-fetch all schema info
# ============================================================

print("Fetching schema from slot 2...")

# Get all tables
tables_output = sql_cmd(
    "SET NOCOUNT ON; SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
    "WHERE TABLE_TYPE='BASE TABLE' AND TABLE_NAME NOT LIKE '__EF%' ORDER BY TABLE_NAME;"
)
ALL_TABLES = []
for line in tables_output.strip().splitlines():
    name = line.strip()
    if name and name not in ("TABLE_NAME", "----------") and not name.startswith("-"):
        ALL_TABLES.append(name)

print(f"Found {len(ALL_TABLES)} tables")

# Get row counts for all tables
print("Fetching row counts...")
count_query_parts = []
for t in ALL_TABLES:
    count_query_parts.append(f"SELECT '{t}' as T, COUNT(*) as C FROM [{t}]")
count_query = " UNION ALL ".join(count_query_parts)
count_output = sql_cmd(f"SET NOCOUNT ON; {count_query};", timeout=120)
ROW_COUNTS = {}
for line in count_output.strip().splitlines():
    line = line.strip()
    if not line or line.startswith("-") or line.startswith("T "):
        continue
    # Parse "TableName  Count" format
    parts = line.rsplit(None, 1)
    if len(parts) == 2:
        try:
            ROW_COUNTS[parts[0]] = int(parts[1])
        except ValueError:
            pass

# Get all columns for all tables
print("Fetching columns...")
cols_output = sql_cmd(
    "SET NOCOUNT ON; SELECT TABLE_NAME + '|' + COLUMN_NAME + '|' + DATA_TYPE + '|' + "
    "ISNULL(CAST(CHARACTER_MAXIMUM_LENGTH AS VARCHAR), 'NULL') + '|' + "
    "IS_NULLABLE + '|' + ISNULL(CAST(COLUMNPROPERTY(OBJECT_ID(TABLE_NAME), COLUMN_NAME, 'IsIdentity') AS VARCHAR), '0') + '|' + "
    "ISNULL(CAST(NUMERIC_PRECISION AS VARCHAR), '0') + '|' + "
    "ISNULL(CAST(NUMERIC_SCALE AS VARCHAR), '0') "
    "FROM INFORMATION_SCHEMA.COLUMNS ORDER BY TABLE_NAME, ORDINAL_POSITION;",
    timeout=60
)
COLUMNS = defaultdict(list)
for line in cols_output.strip().splitlines():
    parts = [p.strip() for p in line.split("|")]
    if len(parts) >= 8 and parts[0] and parts[0] not in ("TABLE_NAME", "----------", ""):
        max_len = None
        if parts[3] != "NULL":
            try:
                max_len = int(parts[3])
            except ValueError:
                pass
        precision = 18
        scale = 2
        try:
            precision = int(parts[6])
        except (ValueError, IndexError):
            pass
        try:
            scale = int(parts[7])
        except (ValueError, IndexError):
            pass
        COLUMNS[parts[0]].append({
            "name": parts[1],
            "type": parts[2],
            "max_len": max_len,
            "nullable": parts[4] == "YES",
            "identity": parts[5] == "1",
            "precision": precision,
            "scale": scale,
        })

# Get all FKs
print("Fetching foreign keys...")
fk_output = sql_cmd(
    "SET NOCOUNT ON; SELECT OBJECT_NAME(fc.parent_object_id) + '|' + "
    "COL_NAME(fc.parent_object_id, fc.parent_column_id) + '|' + "
    "OBJECT_NAME(fc.referenced_object_id) "
    "FROM sys.foreign_key_columns fc ORDER BY OBJECT_NAME(fc.parent_object_id);",
    timeout=60
)
FKS = defaultdict(dict)  # {table: {col: ref_table}}
FK_REFS = {}  # {table: [ids]}
for line in fk_output.strip().splitlines():
    parts = [p.strip() for p in line.split("|")]
    if len(parts) >= 3 and parts[0] and parts[0] not in ("----------", ""):
        FKS[parts[0]][parts[1]] = parts[2]

# Pre-fetch reference IDs for FK targets
print("Fetching FK reference IDs...")
ref_tables = set()
for t, fks in FKS.items():
    for col, ref in fks.items():
        ref_tables.add(ref)
for ref_t in ref_tables:
    if ref_t in ROW_COUNTS and ROW_COUNTS[ref_t] > 0:
        try:
            out = sql_cmd(f"SET NOCOUNT ON; SELECT Id FROM [{ref_t}] ORDER BY Id;", timeout=10)
            ids = []
            for line in out.strip().splitlines():
                line = line.strip()
                if line.isdigit():
                    ids.append(int(line))
            FK_REFS[ref_t] = ids
        except:
            pass

print("Schema loaded. Generating SQL...")


# ============================================================
# Data generation helpers
# ============================================================

def gen_phone() -> str:
    return random.choice(PHONE_PFX) + "".join([str(random.randint(0, 9)) for _ in range(7)])


def gen_name(gender: str = None) -> str:
    if gender == "Female":
        return f"{random.choice(FEMALE_NAMES)} {random.choice(LAST_NAMES)}"
    elif gender == "Male":
        return f"{random.choice(MALE_NAMES)} {random.choice(LAST_NAMES)}"
    return f"{random.choice(MALE_NAMES + FEMALE_NAMES)} {random.choice(LAST_NAMES)}"


def gen_code(prefix: str, idx: int) -> str:
    return f"{prefix}{idx:06d}"


def gen_address() -> str:
    return f"{random.randint(1, 999)} {random.choice(ADDRESSES)}, {random.choice(CITIES)}"


def gen_email(idx: int) -> str:
    return f"user{idx}@hospital.com"


def gen_date(start: datetime = None, end: datetime = None) -> datetime:
    if start is None:
        start = datetime(2025, 1, 1)
    if end is None:
        end = NOW
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(1, delta)))


def gen_value(col: dict, idx: int, table: str) -> str | None:
    """Generate appropriate value for a column."""
    cn = col["name"].lower()
    ct = col["type"]
    ml = col["max_len"]

    # Identity columns are handled separately
    if col["identity"]:
        return None

    # Nullable - sometimes skip
    if col["nullable"] and cn not in ("tenantid", "hospitalid", "createdby", "updatedby", "languagecode"):
        if random.random() < 0.2:
            return None

    # TenantId / HospitalId
    if cn == "tenantid":
        return TENANT
    if cn == "hospitalid":
        return HOSPITAL
    if cn in ("createdby", "updatedby", "measuredbyuserid", "orderedbyid", "assigneddoctorid",
              "concludedby", "prescribedby", "signedbydoctorid", "receivedby", "settledby",
              "issuedby", "submittedby", "approvedby", "rejectedby", "cancelledby",
              "reservedbyid", "confirmedbyid", "startedby", "endedby", "generatedby",
              "statusupdatedby", "cashierid", "examiningdoctorid", "attendinguserid",
              "assignednurseuserid"):
        return USER_ADMIN

    # FK columns
    if cn in FKS.get(table, {}):
        ref_table = FKS[table][cn]
        if ref_table in FK_REFS and FK_REFS[ref_table]:
            return random.choice(FK_REFS[ref_table])
        return None

    # Bit columns
    if ct == "bit":
        if "isactive" in cn:
            return True
        if "isdefault" in cn:
            return idx == 0
        return random.choice([True, False])

    # Integer columns
    if ct in ("bigint", "int", "smallint", "tinyint"):
        if cn == "id":
            return None
        if "tenantid" in cn:
            return TENANT
        if "hospitalid" in cn:
            return HOSPITAL
        if cn in ("createdby", "updatedby", "measuredbyuserid", "orderedbyid", "assigneddoctorid",
                  "concludedby", "prescribedby", "signedbydoctorid", "receivedby", "settledby",
                  "issuedby", "submittedby", "approvedby", "rejectedby", "cancelledby",
                  "reservedbyid", "confirmedbyid", "startedby", "endedby", "generatedby",
                  "statusupdatedby", "cashierid", "examiningdoctorid", "attendinguserid",
                  "assignednurseuserid", "staffid", "personid", "orderedbyuserid"):
            return USER_ADMIN
        if "quantity" in cn:
            return random.randint(1, 10)
        if "count" in cn:
            return random.randint(0, 5)
        if "sortorder" in cn or "displayorder" in cn:
            return idx + 1
        if "maxcapacity" in cn:
            return random.randint(1, 4)
        if "year" in cn:
            return random.randint(1950, 2005)
        if "pulse" in cn or "heartrate" in cn:
            return random.randint(60, 100)
        if "bp" in cn or "bloodpressure" in cn:
            if "sys" in cn:
                return random.randint(110, 150)
            if "diz" in cn or "dia" in cn:
                return random.randint(60, 90)
        if "respiratoryrate" in cn:
            return random.randint(14, 24)
        if "vasscore" in cn:
            return random.randint(0, 6)
        if "duration" in cn:
            return random.randint(1, 30)
        if "totaldays" in cn:
            return random.randint(1, 14)
        if "queuenumber" in cn:
            return random.randint(1, 100)
        if "rating" in cn or "overallrating" in cn:
            if ct == "tinyint":
                return random.randint(1, 5)
        if "status" in cn and ct == "tinyint":
            return random.randint(0, 3)
        if "daysofweekmask" in cn:
            return random.randint(1, 127)
        if "mintolerance" in cn or "maxtolerance" in cn or "threshold" in cn:
            return random.randint(0, 120)
        if "coefficient" in cn:
            return random.randint(1, 3)
        if ct == "tinyint":
            return random.randint(0, 100)
        return random.randint(1, 100)
        return random.randint(1, 100)

    # Decimal columns
    if ct in ("decimal", "numeric", "float", "real"):
        # Get precision/scale from column metadata
        precision = col.get("precision", 18)
        scale = col.get("scale", 2)
        max_val = 10 ** (precision - scale) - 1
        if max_val > 999999:
            max_val = 999999

        if "price" in cn or "amount" in cn or "cost" in cn:
            return round(random.uniform(100, min(50000, max_val)), scale)
        if "rate" in cn or "percent" in cn:
            return round(random.uniform(0, min(100, max_val)), scale)
        if "weight" in cn:
            return round(random.uniform(40, 100), scale)
        if "height" in cn:
            return round(random.uniform(140, 190), scale)
        if "temperature" in cn:
            return round(random.uniform(36.0, 38.5), min(1, scale))
        if "spo2" in cn:
            return round(random.uniform(95, 100), min(1, scale))
        if "bmi" in cn:
            return round(random.uniform(18, 35), scale)
        if "bsa" in cn:
            return round(random.uniform(1.4, 2.2), scale)
        if "totalquantity" in cn:
            return round(random.uniform(1, 50), scale)
        if "coefficient" in cn:
            return round(random.uniform(0.5, 3.0), scale)
        if "surcharge" in cn or "folding" in cn:
            return round(random.uniform(0, min(100, max_val)), scale)
        return round(random.uniform(0, min(100, max_val)), scale)

    # Date columns
    if ct in ("datetime", "datetime2", "date", "smalldatetime"):
        if "createdat" in cn or "updatedat" in cn:
            return NOW
        if "issuedat" in cn or "startedat" in cn or "startat" in cn:
            return gen_date(datetime(2026, 6, 1), NOW)
        if "completedat" in cn or "endedat" in cn or "endat" in cn:
            return gen_date(datetime(2026, 6, 1), NOW) if random.random() < 0.6 else None
        if "receptiontime" in cn:
            return gen_date(datetime(2026, 6, 15), NOW)
        if "measuredat" in cn:
            return gen_date(datetime(2026, 6, 15), NOW)
        if "birth" in cn:
            return datetime(random.randint(1950, 2010), random.randint(1, 12), random.randint(1, 28))
        return gen_date()

    # Time columns
    if ct == "time":
        return datetime(2026, 1, 1, random.randint(6, 22), random.randint(0, 59), 0)

    # String columns
    if ct in ("nvarchar", "varchar", "nchar", "char"):
        eff = min(ml or 500, 500)

        if cn == "code":
            return gen_code("CD-", idx)[:eff]
        if cn in ("name", "fullname", "patientname"):
            return gen_name()[:eff]
        if cn == "firstname":
            return random.choice(MALE_NAMES + FEMALE_NAMES)[:eff]
        if cn == "lastname":
            return random.choice(LAST_NAMES)[:eff]
        if cn in ("patienttypecode", "code"):
            return gen_code("PT-", idx)[:eff]
        if "phone" in cn:
            return gen_phone()[:eff]
        if "email" in cn:
            return gen_email(idx)[:eff]
        if "address" in cn:
            return gen_address()[:eff]
        if cn == "gender":
            return random.choice(["Male", "Female"])[:eff]
        if "status" in cn:
            return random.choice(["Active", "Completed", "Pending", "InProgress", "Cancelled"])[:eff]
        if "type" in cn and "code" not in cn and "name" not in cn:
            return random.choice(["Standard", "Premium", "Basic", "Advanced"])[:eff]
        if "note" in cn or "notes" in cn:
            return f"Note for record {idx}"[:eff]
        if "description" in cn:
            return f"Description for record {idx}"[:eff]
        if "reason" in cn:
            return random.choice(["Routine checkup", "Follow-up", "Emergency", "Consultation", "Screening"])[:eff]
        if "languagecode" in cn:
            return f"seed-wt2-{idx}"[:eff]
        if "sharescope" in cn or "scope" in cn:
            return "All"[:eff]
        if "howtouse" in cn:
            return random.choice(["Take 1 tablet 3x daily after meals", "Apply twice daily", "Take before bed"])[:eff]
        if "color" in cn:
            return random.choice(["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF"])[:eff]
        if "unit" in cn:
            return random.choice(["tablet", "capsule", "ml", "vial", "tube"])[:eff]
        if "option" in cn:
            return random.choice(["Disabled", "Optional", "Required"])[:eff]
        if "condition" in cn:
            return random.choice(["Stable", "Moderate", "Critical"])[:eff]
        if "mode" in cn:
            return random.choice(["Cash", "Card", "Insurance"])[:eff]
        if "itemtype" in cn:
            return "Service"[:eff]
        if "breathingstatus" in cn:
            return random.choice(["Normal breathing", "Supplemental O2"])[:eff]
        if "painpoint" in cn:
            return random.choice(["None", "Mild", "Moderate", "Severe"])[:eff]
        if "measuredarm" in cn:
            return random.choice(["right", "left"])[:eff]
        if cn == "occupation":
            return random.choice(["Engineer", "Teacher", "Doctor", "Nurse", "Business"])[:eff]
        if cn == "workplace":
            return random.choice(["Hospital", "Clinic", "University", "Company"])[:eff]
        if "identitynumber" in cn:
            return f"ID{random.randint(100000000, 999999999)}"[:eff]
        if "passport" in cn:
            return f"P{random.randint(10000000, 99999999)}"[:eff]
        if "contract" in cn:
            return f"CON-{idx:04d}"[:eff]
        if "serial" in cn:
            return f"SN{random.randint(100000, 999999)}"[:eff]
        if "template" in cn or "pattern" in cn:
            return f"Template-{idx}"[:eff]
        if "json" in cn or (ml and ml == -1):
            return "{}"[:eff]

        # Default
        return f"Value-{idx}"[:eff]

    # JSON
    if ct == "ntext" or (ct == "nvarchar" and ml == -1):
        return "{}"

    return None


# ============================================================
# Main generation
# ============================================================

def main():
    all_sql = [
        "SET NOCOUNT ON;",
        "SET XACT_ABORT OFF;",
        "SET QUOTED_IDENTIFIER ON;",
        "SET ANSI_NULLS ON;",
        "",
        "-- Disable all FK constraints for seeding",
        "DECLARE @sql NVARCHAR(MAX) = '';",
        "SELECT @sql = @sql + 'ALTER TABLE ' + QUOTENAME(TABLE_NAME) + ' NOCHECK CONSTRAINT ALL; ' FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' AND TABLE_NAME NOT LIKE '__EF%';",
        "EXEC sp_executesql @sql;",
        "",
        "-- Universal seed data for slot 2 (qms-v1)",
        f"-- Target: {DB}, TenantId={TENANT}, HospitalId={HOSPITAL}",
        f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"-- Minimum records per table: {MIN_RECORDS}",
        "",
    ]

    stats = {"seeded": 0, "already_ok": 0, "skipped": 0, "errors": 0}

    skip_tables = {
        "__EFMigrationsHistory", "MultiLanguage", "CodeSequence",
        "BffRefreshToken", "OtpAttempt", "ZaloMessageLog", "ZaloOaToken",
        "IpnInbox", "TransactionStatusHistory", "MasterDiseases",
        "MasterWard", "MasterCountry", "MasterActiveIngredient",
        "MasterOccupation", "MasterDiseaseCategories",
        "UserRolePermission", "ActiveIngredient",
        "Company", "MultiLanguage",
    }

    for table in ALL_TABLES:
        if table in skip_tables:
            stats["skipped"] += 1
            continue

        count = ROW_COUNTS.get(table, 0)
        if count >= MIN_RECORDS:
            stats["already_ok"] += 1
            continue

        cols = COLUMNS.get(table, [])
        if not cols:
            stats["skipped"] += 1
            continue

        # Determine if identity
        is_identity = any(c["identity"] for c in cols)
        max_id = 0
        if is_identity:
            try:
                out = sql_cmd(f"SET NOCOUNT ON; SELECT ISNULL(MAX(Id),0) FROM [{table}];")
                for line in out.strip().splitlines():
                    line = line.strip()
                    if line.isdigit():
                        max_id = int(line)
            except:
                pass

        needed = max(0, MIN_RECORDS - count)
        lines = []
        lines.append(f"-- Seed {table}: +{needed} (existing: {count})")

        if is_identity:
            lines.append(f"SET IDENTITY_INSERT [{table}] ON;")

        for i in range(needed):
            idx = count + i
            row_id = max_id + i + 1

            col_names = []
            val_parts = []

            for c in cols:
                if c["identity"]:
                    continue
                # For non-identity tables, include Id column with generated value
                if c["name"].lower() == "id" and not is_identity:
                    col_names.append(c["name"])
                    val_parts.append(str(row_id))
                    continue
                val = gen_value(c, idx, table)
                col_names.append(c["name"])
                if val is None:
                    val_parts.append("NULL")
                elif isinstance(val, datetime):
                    val_parts.append(sql_dt(val))
                elif isinstance(val, bool):
                    val_parts.append("1" if val else "0")
                elif isinstance(val, (int, float)):
                    val_parts.append(str(val))
                else:
                    val_parts.append(sql_str(val))

            if not col_names:
                continue

            col_str = ", ".join(f"[{c}]" for c in col_names)
            val_str = ", ".join(val_parts)

            if is_identity:
                lines.append(f"IF NOT EXISTS (SELECT 1 FROM [{table}] WHERE [Id] = {row_id})")
                lines.append(f"    INSERT INTO [{table}] ([Id], {col_str}) VALUES ({row_id}, {val_str});")
            else:
                lines.append(f"INSERT INTO [{table}] ({col_str}) VALUES ({val_str});")

        if is_identity:
            lines.append(f"SET IDENTITY_INSERT [{table}] OFF;")
        lines.append("")

        all_sql.extend(lines)
        stats["seeded"] += 1
        print(f"  {table}: {count} -> {MIN_RECORDS}")

    all_sql.append(f"-- Done. Seeded {stats['seeded']} tables.")
    all_sql.append("")
    all_sql.append("-- Re-enable FK constraints")
    all_sql.append("DECLARE @sql2 NVARCHAR(MAX) = '';")
    all_sql.append("SELECT @sql2 = @sql2 + 'ALTER TABLE ' + QUOTENAME(TABLE_NAME) + ' CHECK CONSTRAINT ALL; ' FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' AND TABLE_NAME NOT LIKE '__EF%';")
    all_sql.append("EXEC sp_executesql @sql2;")
    all_sql.append("GO")

    OUTPUT.write_text("\n".join(all_sql), encoding="utf-8")
    print(f"\nOutput: {OUTPUT}")
    print(f"Seeded: {stats['seeded']}, Already OK: {stats['already_ok']}, Skipped: {stats['skipped']}, Errors: {stats['errors']}")


if __name__ == "__main__":
    main()
