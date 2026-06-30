#!/usr/bin/env python3
"""
scripts/db_merge.py - row-level MERGE importer (harness tool).

Khac voi myhospital-be/Scripts/import_db_data.py (raw INSERT -> PK conflict ->
can drop_db_objects.py wipe slot truoc), script nay MERGE backup vao target:
  - row co trong backup VA slot (cung PK) -> UPDATE non-PK columns
  - row chi co trong backup              -> INSERT
  - row chi co trong slot (mock seed)    -> GIU NGUYEN
      (KHONG co `WHEN NOT MATCHED BY SOURCE THEN DELETE`)

Ket qua: staging baseline sync vao slot NHUNG giu mock data da seed (mix cung
table). Khong can wipe slot truoc.

Parser reuse tu myhospital-be/Scripts/import_db_data.py (read-only import,
bundled-copy fallback neu import loi). File nay nam trong harness repo
(scripts/); KHONG touch myhospital-be/ source.

Usage:
    python scripts/db_merge.py <backup-file.sql>
        --server localhost --port 1437 --database MyHospital
        --user sa --password <pwd>
        [--dry-run] [--keep-going]
        [--tables schema.table,...] [--exclude-tables schema.table,...]
        [--self-test]

Env (CLI override env): DB_SERVER, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
    DB_TDS_VERSION (optional).
"""

import os
import re
import sys
import time
import argparse
import importlib.util
from pathlib import Path

try:
    import pymssql
except ImportError:
    pymssql = None


# ---------------------------------------------------------------------------
# Parser helpers (bundled copy). Override bang live symbols tu
# myhospital-be/Scripts/import_db_data.py neu import duoc (de stay in sync).
# ---------------------------------------------------------------------------

SECTION_RE = re.compile(r"--\s*=+\s*([\w.]+)\s*\((\d+)\s*rows\)")
INSERT_RE = re.compile(r"INSERT\s+INTO\s+\[(\w+)\]\.\[(\w+)\]", re.IGNORECASE)
INSERT_FULL_RE = re.compile(
    r"^\s*INSERT\s+INTO\s+\[(\w+)\]\.\[(\w+)\]\s*\(([^)]+)\)\s*VALUES\s*\((.+)\)\s*;?\s*$",
    re.IGNORECASE,
)
IDENTITY_ON_RE = re.compile(
    r"SET\s+IDENTITY_INSERT\s+\[(\w+)\]\.\[(\w+)\]\s+ON", re.IGNORECASE
)

REQUIRED_SET_OPTIONS = (
    "SET QUOTED_IDENTIFIER ON; "
    "SET ANSI_NULLS ON; "
    "SET ANSI_WARNINGS ON; "
    "SET ANSI_PADDING ON; "
    "SET ARITHABORT ON; "
    "SET CONCAT_NULL_YIELDS_NULL ON; "
    "SET NUMERIC_ROUNDABORT OFF; "
    "SET NOCOUNT ON; "
    "SET XACT_ABORT ON;"
)

STRING_TYPES = {"char", "varchar", "nchar", "nvarchar", "text", "ntext", "sysname", "xml"}
NUMERIC_TYPES = {
    "tinyint", "smallint", "int", "bigint",
    "decimal", "numeric", "money", "smallmoney", "float", "real",
}


def split_sql_values(s: str):
    """Split VALUES list theo dau ',', ton trong N'...' string co escape ''."""
    parts, buf, in_str = [], [], False
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if in_str:
            if ch == "'":
                if i + 1 < n and s[i + 1] == "'":
                    buf.append("''")
                    i += 2
                    continue
                in_str = False
                buf.append(ch)
            else:
                buf.append(ch)
        else:
            if ch == "'":
                in_str = True
                buf.append(ch)
            elif ch == ",":
                parts.append("".join(buf).strip())
                buf = []
            else:
                buf.append(ch)
        i += 1
    if buf:
        parts.append("".join(buf).strip())
    return parts


def type_default(type_name: str):
    t = type_name.lower()
    if t in STRING_TYPES:
        return "N''"
    if t in NUMERIC_TYPES or t == "bit":
        return "0"
    return None


def get_target_schema(cur, schema: str, table: str):
    """Dict {col: {is_nullable,is_identity,is_computed,type,has_default,is_fk}}.
    Rong neu table khong ton tai."""
    try:
        cur.execute(
            """
            SELECT
                c.name,
                c.is_nullable,
                c.is_identity,
                c.is_computed,
                t.name AS type_name,
                CASE WHEN dc.object_id IS NOT NULL THEN 1 ELSE 0 END AS has_default,
                CASE WHEN EXISTS(
                    SELECT 1 FROM sys.foreign_key_columns fkc
                    WHERE fkc.parent_object_id = c.object_id
                      AND fkc.parent_column_id = c.column_id
                ) THEN 1 ELSE 0 END AS is_fk
            FROM sys.columns c
            JOIN sys.objects o ON o.object_id = c.object_id
            JOIN sys.schemas s ON s.schema_id = o.schema_id
            JOIN sys.types t ON t.user_type_id = c.user_type_id
            LEFT JOIN sys.default_constraints dc
              ON dc.parent_object_id = c.object_id
             AND dc.parent_column_id = c.column_id
            WHERE s.name = %s AND o.name = %s AND o.type = 'U'
            """,
            (schema, table),
        )
        out = {}
        for r in cur.fetchall():
            out[r[0]] = {
                "is_nullable": bool(r[1]),
                "is_identity": bool(r[2]),
                "is_computed": bool(r[3]),
                "type": r[4],
                "has_default": bool(r[5]),
                "is_fk": bool(r[6]),
            }
        return out
    except Exception:
        return {}


def adapt_batch_to_target(batch, schema, table, target_schema):
    """Rewrite INSERT cho schema drift (drop col thua, fill col thieu).
    Tra ve (new_batch, dropped_set, filled_dict, skip_reason)."""
    if not target_schema:
        return batch, set(), {}, None

    target_names = set(target_schema.keys())
    dropped, filled, skip_reason = set(), {}, None
    new_lines, changed = [], False

    for line in batch.split("\n"):
        m = INSERT_FULL_RE.match(line)
        if not m:
            new_lines.append(line)
            continue
        cols_raw = [c.strip().strip("[]") for c in m.group(3).split(",")]
        vals = split_sql_values(m.group(4))
        if len(cols_raw) != len(vals):
            new_lines.append(line)
            continue

        source_set = set(cols_raw)
        kept_cols, kept_vals = [], []
        for c, v in zip(cols_raw, vals):
            if c in target_names:
                kept_cols.append(c)
                kept_vals.append(v)
            else:
                dropped.add(c)
                changed = True

        for tc, info in target_schema.items():
            if tc in source_set:
                continue
            if info["is_identity"] or info["is_computed"] or info["has_default"]:
                continue
            if info["is_nullable"]:
                kept_cols.append(tc)
                kept_vals.append("NULL")
                filled[tc] = "NULL"
                changed = True
                continue
            if info["is_fk"]:
                skip_reason = (
                    f"missing required FK column '{tc}' (NOT NULL) - khong fabricate duoc"
                )
                return batch, dropped, filled, skip_reason
            default = type_default(info["type"])
            if default is None:
                skip_reason = (
                    f"missing NOT NULL column '{tc}' type={info['type']} - khong co default an toan"
                )
                return batch, dropped, filled, skip_reason
            kept_cols.append(tc)
            kept_vals.append(default)
            filled[tc] = f"{default} ({info['type']})"
            changed = True

        if not kept_cols:
            new_lines.append(line)
            continue

        col_list = ", ".join(f"[{c}]" for c in kept_cols)
        val_list = ", ".join(kept_vals)
        new_lines.append(
            f"INSERT INTO [{schema}].[{table}] ({col_list}) VALUES ({val_list});"
        )

    return ("\n".join(new_lines) if changed else batch), dropped, filled, skip_reason


def clean_err(e: Exception) -> str:
    s = str(e)
    m = re.search(r"b['\"](.*?)['\"]\s*\)?$", s, re.DOTALL)
    if m:
        s = m.group(1)
    s = s.split("DB-Lib error")[0].strip().rstrip(".")
    return s


# Best-effort: reuse LIVE parser/drift logic tu BE import_db_data.py (read-only).
# Pre-check pymssql de tranh module-level sys.exit khi pymssql chua cai.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BE_PARSER_FILE = _REPO_ROOT / "myhospital-be" / "Scripts" / "import_db_data.py"
_PARSER_SRC = "bundled copy"

if _BE_PARSER_FILE.is_file() and pymssql is not None:
    try:
        _spec = importlib.util.spec_from_file_location(
            "import_db_data", str(_BE_PARSER_FILE)
        )
        _be = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_be)
        for _n in (
            "SECTION_RE", "INSERT_RE", "INSERT_FULL_RE", "IDENTITY_ON_RE",
            "REQUIRED_SET_OPTIONS", "STRING_TYPES", "NUMERIC_TYPES",
            "split_sql_values", "type_default", "get_target_schema",
            "adapt_batch_to_target", "clean_err",
        ):
            if hasattr(_be, _n):
                globals()[_n] = getattr(_be, _n)
        _PARSER_SRC = "imported from myhospital-be/Scripts/import_db_data.py"
    except BaseException:
        _PARSER_SRC = "bundled copy (BE import failed)"

reconcile_batch = adapt_batch_to_target  # alias theo ten trong spec


# ---------------------------------------------------------------------------
# Backup section parser: split file thanh per-table sections.
# ---------------------------------------------------------------------------

def parse_sections(sql_text: str):
    """Split backup theo section marker `-- === schema.table (N rows) ===`.
    Returns list of dicts:
      {schema, table, full, row_count, identity_on, inserts:[line,...], raw}
    """
    markers = list(SECTION_RE.finditer(sql_text))
    sections = []
    for i, m in enumerate(markers):
        full = m.group(1)
        rows = int(m.group(2))
        start = m.start()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(sql_text)
        chunk = sql_text[start:end]
        schema, _, table = full.partition(".")
        identity_on = bool(IDENTITY_ON_RE.search(chunk))
        inserts = [
            line.rstrip(";").strip()
            for line in chunk.splitlines()
            if INSERT_FULL_RE.match(line)
        ]
        sections.append({
            "schema": schema,
            "table": table,
            "full": full,
            "row_count": rows,
            "identity_on": identity_on,
            "inserts": inserts,
            "raw": chunk,
        })
    return sections


def parse_insert_line(line: str):
    """Tra ve (cols, vals) tu 1 INSERT line, hoac (None, None)."""
    m = INSERT_FULL_RE.match(line)
    if not m:
        return None, None
    cols = [c.strip().strip("[]") for c in m.group(3).split(",")]
    vals = split_sql_values(m.group(4))
    return cols, vals


def reconcile_row(line: str, schema: str, table: str, target_schema: dict):
    """Reconcile 1 INSERT row voi target schema (drop col thua, fill col thieu).
    Returns (cols, vals, dropped, filled, skip_reason)."""
    new_batch, dropped, filled, skip_reason = adapt_batch_to_target(
        line.rstrip("\n") + "\n", schema, table, target_schema
    )
    if skip_reason:
        return None, None, dropped, filled, skip_reason
    m = INSERT_FULL_RE.search(new_batch)
    if not m:
        return None, None, dropped, filled, "reconciled batch unparseable"
    cols = [c.strip().strip("[]") for c in m.group(3).split(",")]
    vals = split_sql_values(m.group(4))
    return cols, vals, dropped, filled, None


# ---------------------------------------------------------------------------
# SQL builders.
# ---------------------------------------------------------------------------

def _qid(name: str) -> str:
    return f"[{name}]"


def build_temp_ddl(temp_name: str, schema: str, table: str, cols):
    col_list = ", ".join(_qid(c) for c in cols)
    return f"SELECT TOP 0 {col_list} INTO {temp_name} FROM {_qid(schema)}.{_qid(table)};"


def build_merge_sql(schema, table, temp_name, pk_cols, all_cols):
    """MERGE WITH (HOLDLOCK). KHONG co WHEN NOT MATCHED BY SOURCE DELETE
    -> mock rows trong slot duoc GIU NGUYEN."""
    target = f"{_qid(schema)}.{_qid(table)}"
    on_clause = " AND ".join(f"t.{_qid(c)} = s.{_qid(c)}" for c in pk_cols)
    non_pk = [c for c in all_cols if c not in pk_cols]
    insert_cols = ", ".join(_qid(c) for c in all_cols)
    insert_vals = ", ".join(f"s.{_qid(c)}" for c in all_cols)
    parts = [
        f"MERGE INTO {target} WITH (HOLDLOCK) AS t",
        f"USING {temp_name} AS s",
        f"ON {on_clause}",
    ]
    if non_pk:
        update_set = ", ".join(f"t.{_qid(c)} = s.{_qid(c)}" for c in non_pk)
        parts.append(f"WHEN MATCHED THEN UPDATE SET {update_set}")
    parts.append(
        f"WHEN NOT MATCHED BY TARGET THEN INSERT ({insert_cols}) VALUES ({insert_vals});"
    )
    return "\n".join(parts)


def build_insert_only_sql(schema, table, temp_name, all_cols):
    """No-PK fallback: INSERT chi nhung row chua co (match ALL columns)."""
    target = f"{_qid(schema)}.{_qid(table)}"
    cols = ", ".join(_qid(c) for c in all_cols)
    sel = ", ".join(f"s.{_qid(c)}" for c in all_cols)
    match = " AND ".join(f"t.{_qid(c)} = s.{_qid(c)}" for c in all_cols)
    return (
        f"INSERT INTO {target} ({cols})\n"
        f"SELECT {sel} FROM {temp_name} s\n"
        f"WHERE NOT EXISTS (SELECT 1 FROM {target} t WHERE {match});"
    )


# ---------------------------------------------------------------------------
# Target DB introspection.
# ---------------------------------------------------------------------------

def get_pk_columns(cur, schema, table):
    cur.execute(
        """
        SELECT kcu.COLUMN_NAME
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
          ON tc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
         AND tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
         AND kcu.TABLE_SCHEMA = tc.TABLE_SCHEMA
         AND kcu.TABLE_NAME = tc.TABLE_NAME
        WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
          AND tc.TABLE_SCHEMA = %s AND tc.TABLE_NAME = %s
        ORDER BY kcu.ORDINAL_POSITION
        """,
        (schema, table),
    )
    return [r[0] for r in cur.fetchall()]


def get_all_fks(cur):
    cur.execute(
        """
        SELECT OBJECT_SCHEMA_NAME(fk.parent_object_id),
               OBJECT_NAME(fk.parent_object_id),
               fk.name
        FROM sys.foreign_keys fk
        WHERE OBJECTPROPERTY(fk.parent_object_id, 'IsMSShipped') = 0
        """
    )
    return list(cur.fetchall())


# ---------------------------------------------------------------------------
# Config.
# ---------------------------------------------------------------------------

def build_config(args) -> dict:
    cfg = {
        "server": args.server or os.getenv("DB_SERVER", ""),
        "port": int(args.port or os.getenv("DB_PORT") or 1433),
        "database": args.database or os.getenv("DB_NAME", ""),
        "user": args.user or os.getenv("DB_USER", ""),
        "password": args.password or os.getenv("DB_PASSWORD", ""),
        "autocommit": False,
    }
    tds = os.getenv("DB_TDS_VERSION")
    if tds:
        cfg["tds_version"] = tds
    return cfg


def missing_config(cfg):
    return [k for k in ("server", "database", "user", "password") if not cfg[k]]


def filter_sections(sections, args):
    want = {s.strip().lower() for s in (args.tables or "").split(",") if s.strip()}
    excl = {s.strip().lower() for s in (args.exclude_tables or "").split(",") if s.strip()}
    out = []
    for sec in sections:
        key = sec["full"].lower()
        if want and key not in want:
            continue
        if key in excl:
            continue
        out.append(sec)
    return out


# ---------------------------------------------------------------------------
# Per-table MERGE.
# ---------------------------------------------------------------------------

def merge_table(cur, conn, sec, keep_going, commit_per_table, results):
    """Merge 1 section vao target. commit_per_table=True -> commit sau khi xong;
    False -> de caller commit 1 lan cuoi. Luon rollback + don IDENTITY_INSERT
    neu loi. keep_going=True -> table fail tra ve fail-summary; False -> re-raise."""
    schema, table, full = sec["schema"], sec["table"], sec["full"]
    temp_name = f"#merge_src_{schema}_{table}"
    target_schema = get_target_schema(cur, schema, table)

    if not target_schema:
        results.append({"table": full, "status": "skip",
                        "reason": "table not in target DB",
                        "rows_source": len(sec["inserts"]),
                        "updated": 0, "inserted": 0, "skipped": len(sec["inserts"])})
        print(f"  SKIP {full}  -> table not in target DB ({len(sec['inserts'])} source rows)")
        return

    pk_cols = get_pk_columns(cur, schema, table)
    identity_cols = [c for c, i in target_schema.items() if i["is_identity"]]
    computed_cols = {c for c, i in target_schema.items() if i["is_computed"]}

    # Parse + reconcile source rows.
    reconciled = []   # list of (cols, vals)
    rows_skipped_drift = 0
    drift_notes = {"dropped": set(), "filled": {}}
    for line in sec["inserts"]:
        cols, vals, dropped, filled, skip_reason = reconcile_row(
            line, schema, table, target_schema
        )
        drift_notes["dropped"] |= dropped
        drift_notes["filled"].update(filled)
        if skip_reason:
            rows_skipped_drift += 1
            if keep_going:
                print(f"    row SKIP -> {skip_reason[:160]}")
                continue
            results.append({"table": full, "status": "fail", "reason": skip_reason,
                            "rows_source": len(sec["inserts"]),
                            "updated": 0, "inserted": 0, "skipped": rows_skipped_drift})
            raise _TableAbort(skip_reason)
        reconciled.append((cols, vals))

    if not reconciled:
        results.append({"table": full, "status": "skip",
                        "reason": "no reconcilable rows",
                        "rows_source": len(sec["inserts"]),
                        "updated": 0, "inserted": 0, "skipped": len(sec["inserts"])})
        print(f"  SKIP {full}  -> no reconcilable rows")
        return

    # Union columns (non-computed). Source export khong bao gom computed col,
    # nhung phong hinh nhu drop neu co.
    all_cols, seen = [], set()
    for cols, _ in reconciled:
        for c in cols:
            if c not in seen and c not in computed_cols:
                seen.add(c)
                all_cols.append(c)

    # PK phai nam trong all_cols; neu thieu (source khong export PK) -> insert-only.
    use_pk = pk_cols and all(c in all_cols for c in pk_cols)

    identity_on_target = False
    identity_on_temp = False
    try:
        # 1. Build temp table (copy schema, no data).
        cur.execute(build_temp_ddl(temp_name, schema, table, all_cols))

        # 2. Insert source rows vao temp (tolerant per-row).
        rows_into_temp = 0
        rows_temp_fail = 0
        needs_temp_identity = any(c in identity_cols for c in all_cols)
        if needs_temp_identity:
            cur.execute(f"SET IDENTITY_INSERT {temp_name} ON;")
            identity_on_temp = True
        for cols, vals in reconciled:
            cl = ", ".join(_qid(c) for c in cols)
            vl = ", ".join(vals)
            try:
                cur.execute(f"INSERT INTO {temp_name} ({cl}) VALUES ({vl});")
                rows_into_temp += 1
            except Exception as e:
                rows_temp_fail += 1
                err = clean_err(e)
                if keep_going:
                    print(f"    temp row SKIP -> {err[:160]}")
                    continue
                raise _TableAbort(f"temp insert fail: {err}")
        if identity_on_temp:
            cur.execute(f"SET IDENTITY_INSERT {temp_name} OFF;")
            identity_on_temp = False

        if rows_into_temp == 0:
            raise _TableAbort("no rows entered temp table")

        # 3. Counts before.
        cur.execute(f"SELECT COUNT(*) FROM {_qid(schema)}.{_qid(table)}")
        total_before = cur.fetchone()[0]
        matched = None
        if use_pk:
            on = " AND ".join(f"t.{_qid(c)}=s.{_qid(c)}" for c in pk_cols)
            cur.execute(
                f"SELECT COUNT(*) FROM {_qid(schema)}.{_qid(table)} t "
                f"WHERE EXISTS (SELECT 1 FROM {temp_name} s WHERE {on})"
            )
            matched = cur.fetchone()[0]

        # 4. IDENTITY_INSERT ON cho target (neu can).
        if identity_cols:
            cur.execute(f"SET IDENTITY_INSERT {_qid(schema)}.{_qid(table)} ON;")
            identity_on_target = True

        # 5. MERGE (hoac insert-only).
        if use_pk:
            merge_sql = build_merge_sql(schema, table, temp_name, pk_cols, all_cols)
        else:
            merge_sql = build_insert_only_sql(schema, table, temp_name, all_cols)
        cur.execute(merge_sql)

        # 6. IDENTITY_INSERT OFF cho target.
        if identity_on_target:
            cur.execute(f"SET IDENTITY_INSERT {_qid(schema)}.{_qid(table)} OFF;")
            identity_on_target = False

        # 7. Counts after.
        cur.execute(f"SELECT COUNT(*) FROM {_qid(schema)}.{_qid(table)}")
        total_after = cur.fetchone()[0]

        inserted = max(0, total_after - total_before)
        if use_pk:
            updated = matched or 0
            skipped_merge = 0
        else:
            updated = 0
            skipped_merge = max(0, rows_into_temp - inserted)

        # 8. Drop temp.
        try:
            cur.execute(f"DROP TABLE {temp_name};")
        except Exception:
            pass

        if commit_per_table:
            conn.commit()

        extra = ""
        if drift_notes["dropped"]:
            extra += f" dropped={sorted(drift_notes['dropped'])}"
        if drift_notes["filled"]:
            extra += f" filled={dict(drift_notes['filled'])}"
        print(
            f"  OK   {full}  ({len(sec['inserts'])} rows) -> "
            f"{updated} updated, {inserted} inserted, "
            f"{skipped_merge + rows_skipped_drift + rows_temp_fail} skipped{extra}"
        )
        results.append({
            "table": full, "status": "ok",
            "rows_source": len(sec["inserts"]),
            "updated": updated, "inserted": inserted,
            "skipped": skipped_merge + rows_skipped_drift + rows_temp_fail,
            "matched": matched,
        })

    except _TableAbort as e:
        _cleanup_on_fail(cur, conn, temp_name, identity_on_target, identity_on_temp,
                         schema, table)
        results.append({"table": full, "status": "fail", "reason": str(e),
                        "rows_source": len(sec["inserts"]),
                        "updated": 0, "inserted": 0, "skipped": 0})
        print(f"  FAIL {full}  -> {str(e)[:200]}")
        if not keep_going:
            raise
    except Exception as e:
        _cleanup_on_fail(cur, conn, temp_name, identity_on_target, identity_on_temp,
                         schema, table)
        err = clean_err(e)
        results.append({"table": full, "status": "fail", "reason": err,
                        "rows_source": len(sec["inserts"]),
                        "updated": 0, "inserted": 0, "skipped": 0})
        print(f"  FAIL {full}  -> {err[:200]}")
        if not keep_going:
            raise


class _TableAbort(Exception):
    pass


def _cleanup_on_fail(cur, conn, temp_name, id_target, id_temp, schema, table):
    """Rollback (clear doomed txn) roi don IDENTITY_INSERT + temp table."""
    try:
        conn.rollback()
    except Exception:
        pass
    if id_target:
        try:
            cur.execute(f"SET IDENTITY_INSERT {_qid(schema)}.{_qid(table)} OFF;")
            conn.commit()
        except Exception:
            try: conn.rollback()
            except Exception: pass
    if id_temp:
        try:
            cur.execute(f"SET IDENTITY_INSERT {temp_name} OFF;")
            conn.commit()
        except Exception:
            try: conn.rollback()
            except Exception: pass
    try:
        cur.execute(f"IF OBJECT_ID('tempdb..{temp_name.lstrip('#')}') IS NOT NULL DROP TABLE {temp_name};")
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass


# ---------------------------------------------------------------------------
# Self-test (no DB).
# ---------------------------------------------------------------------------

def run_self_test():
    sample = (
        "SET NOCOUNT ON;\nGO\n"
        "EXEC sp_MSforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL';\nGO\n"
        "-- ============ dbo.Foo (2 rows) ============\n"
        "SET IDENTITY_INSERT [dbo].[Foo] ON;\n"
        "INSERT INTO [dbo].[Foo] ([Id], [Name]) VALUES (1, N'alpha');\n"
        "INSERT INTO [dbo].[Foo] ([Id], [Name]) VALUES (2, N'bet''a');\n"
        "SET IDENTITY_INSERT [dbo].[Foo] OFF;\nGO\n"
        "-- ============ dbo.Bar (1 rows) ============\n"
        "INSERT INTO [dbo].[Bar] ([Code]) VALUES (N'x');\nGO\n"
    )
    sections = parse_sections(sample)
    assert len(sections) == 2, f"expected 2 sections, got {len(sections)}"
    assert sections[0]["schema"] == "dbo" and sections[0]["table"] == "Foo"
    assert sections[0]["row_count"] == 2, sections[0]["row_count"]
    assert sections[0]["identity_on"] is True
    assert len(sections[0]["inserts"]) == 2
    assert sections[1]["identity_on"] is False
    assert len(sections[1]["inserts"]) == 1

    cols, vals = parse_insert_line(sections[0]["inserts"][0])
    assert cols == ["Id", "Name"], cols
    assert vals == ["1", "N'alpha'"], vals

    cols2, vals2 = parse_insert_line(sections[0]["inserts"][1])
    assert vals2[1] == "N'bet''a'", vals2

    merge = build_merge_sql("dbo", "Foo", "#merge_src_dbo_Foo", ["Id"], ["Id", "Name"])
    assert "MERGE INTO [dbo].[Foo] WITH (HOLDLOCK)" in merge, merge
    assert "WHEN MATCHED THEN UPDATE SET t.[Name] = s.[Name]" in merge, merge
    assert "WHEN NOT MATCHED BY TARGET THEN INSERT" in merge, merge
    assert "WHEN NOT MATCHED BY SOURCE THEN DELETE" not in merge, merge
    assert "t.[Id] = s.[Id]" in merge, merge

    io = build_insert_only_sql("dbo", "Bar", "#merge_src_dbo_Bar", ["Code"])
    assert "INSERT INTO [dbo].[Bar] ([Code])" in io, io
    assert "WHERE NOT EXISTS" in io, io

    ddl = build_temp_ddl("#merge_src_dbo_Foo", "dbo", "Foo", ["Id", "Name"])
    assert "SELECT TOP 0" in ddl and "INTO #merge_src_dbo_Foo" in ddl, ddl
    assert "[Id]" in ddl and "[Name]" in ddl, ddl

    # all-PK table (no non-pk col) -> WHEN MATCHED duoc bo qua, chi INSERT moi.
    merge_pkonly = build_merge_sql("dbo", "P", "#t", ["A"], ["A"])
    assert "WHEN MATCHED" not in merge_pkonly, merge_pkonly
    assert "WHEN NOT MATCHED BY TARGET THEN INSERT" in merge_pkonly, merge_pkonly

    # filter_sections
    class _A:
        tables = "dbo.Foo"
        exclude_tables = None
    f = filter_sections(sections, _A())
    assert len(f) == 1 and f[0]["full"] == "Foo" or (len(f) == 1 and f[0]["table"] == "Foo"), [s["full"] for s in f]

    print("SELF-TEST PASS")
    return True


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

def parse_args(argv):
    p = argparse.ArgumentParser(
        prog="db_merge.py",
        description="Row-level MERGE importer: sync backup vao slot, GIU mock data.",
    )
    p.add_argument("backup_file", nargs="?", help="backup .sql file (export_db_data.py output)")
    p.add_argument("--server", help="DB server (env DB_SERVER)")
    p.add_argument("--port", type=int, help="DB port (env DB_PORT, default 1433)")
    p.add_argument("--database", help="DB name (env DB_NAME)")
    p.add_argument("--user", help="DB user (env DB_USER)")
    p.add_argument("--password", help="DB password (env DB_PASSWORD)")
    p.add_argument("--dry-run", action="store_true",
                   help="parse + print MERGE plan, khong execute")
    p.add_argument("--keep-going", action="store_true",
                   help="table fail -> skip + log, khong abort")
    p.add_argument("--tables", help="chi merge subset (comma-separated schema.table)")
    p.add_argument("--exclude-tables", help="skip tables (comma-separated schema.table)")
    p.add_argument("--self-test", action="store_true", help="run offline self-test")
    return p.parse_args(argv)


def dry_run(sections, cfg):
    print("DRY-RUN: parse + MERGE plan (read-only, khong mutate)\n")
    can_connect = pymssql is not None and not missing_config(cfg)
    cur = conn = None
    if can_connect:
        try:
            conn = pymssql.connect(**cfg)
            cur = conn.cursor()
            cur.execute(REQUIRED_SET_OPTIONS)
            conn.commit()
        except Exception as e:
            print(f"(warn) khong connect duoc de detect PK: {clean_err(e)[:160]}")
            try: conn.close()
            except Exception: pass
            cur = conn = None

    for sec in sections:
        schema, table, full = sec["schema"], sec["table"], sec["full"]
        print(f"--- {full}  ({len(sec['inserts'])} source rows, "
              f"identity={'Y' if sec['identity_on'] else 'N'})")
        if cur is not None:
            ts = get_target_schema(cur, schema, table)
            if not ts:
                print("    SKIP: table not in target DB")
                continue
            pk = get_pk_columns(cur, schema, table)
            computed = [c for c, i in ts.items() if i["is_computed"]]
            identity = [c for c, i in ts.items() if i["is_identity"]]
            print(f"    PK={pk} identity={identity} computed={computed}")
            cols, vals = parse_insert_line(sec["inserts"][0]) if sec["inserts"] else (None, None)
            if cols:
                non_pk = [c for c in cols if c not in pk and c not in computed]
                use_pk = pk and all(c in cols for c in pk)
                if use_pk:
                    sql = build_merge_sql(schema, table,
                                          f"#merge_src_{schema}_{table}", pk, non_pk or cols)
                else:
                    sql = build_insert_only_sql(schema, table,
                                                f"#merge_src_{schema}_{table}",
                                                [c for c in cols if c not in computed])
                print("    " + sql.replace("\n", "\n    "))
        else:
            print("    (PK/computed detection can thiet DB - pass --server/--database/--user/--password)")

    if conn is not None:
        conn.close()
    print(f"\nParser: {_PARSER_SRC}")
    print("DRY-RUN done. Khong thay doi DB.")


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.self_test:
        sys.exit(0 if run_self_test() else 1)

    if not args.backup_file:
        sys.exit("Usage: python scripts/db_merge.py <backup-file.sql> [options]  (or --self-test)")

    if not os.path.isfile(args.backup_file):
        sys.exit(f"File not found: {args.backup_file}")

    print(f"Reading {args.backup_file}...")
    with open(args.backup_file, encoding="utf-8") as f:
        sql_text = f.read()
    sections = parse_sections(sql_text)
    sections = filter_sections(sections, args)
    print(f"Parsed {len(sections)} table sections (parser: {_PARSER_SRC})\n")

    if args.dry_run:
        cfg = build_config(args)
        dry_run(sections, cfg)
        return

    if pymssql is None:
        sys.exit("pymssql chua cai. Run: pip install pymssql")

    cfg = build_config(args)
    miss = missing_config(cfg)
    if miss:
        sys.exit(
            f"Thieu DB config: {miss}. Set DB_SERVER/DB_NAME/DB_USER/DB_PASSWORD "
            f"(env) hoac pass --server/--database/--user/--password."
        )

    print(f"Target: {cfg['server']}:{cfg['port']}/{cfg['database']}")
    keep_going = args.keep_going
    commit_per_table = keep_going  # default: 1 txn cho all; keep-going: commit/table

    conn = pymssql.connect(**cfg)
    cur = conn.cursor()
    cur.execute(REQUIRED_SET_OPTIONS)
    conn.commit()

    results = []
    start = time.time()
    try:
        # Disable all FK constraints (mock rows co the FK le, merge row moi co
        # the FK chua merge -> disable tam thoi -> robust).
        fks = get_all_fks(cur)
        print(f"Disabling {len(fks)} FK constraints...")
        for sch, tbl, fk in fks:
            cur.execute(f"ALTER TABLE {_qid(sch)}.{_qid(tbl)} NOCHECK CONSTRAINT {_qid(fk)};")
        if commit_per_table:
            conn.commit()

        aborted = False
        for sec in sections:
            merge_table(cur, conn, sec, keep_going, commit_per_table, results)

        if not commit_per_table:
            conn.commit()

        # Re-enable FK (WITH NOCHECK: khong validate data cu, tranh fail orphan).
        print(f"Re-enabling {len(fks)} FK constraints (WITH NOCHECK)...")
        for sch, tbl, fk in fks:
            cur.execute(
                f"ALTER TABLE {_qid(sch)}.{_qid(tbl)} WITH NOCHECK CHECK CONSTRAINT {_qid(fk)};"
            )
        conn.commit()

    except _TableAbort:
        aborted = True
        try: conn.rollback()
        except Exception: pass
        print("\nABORT: table fail (default mode). Rollback toan bo.")
    except Exception as e:
        aborted = True
        try: conn.rollback()
        except Exception: pass
        print(f"\nABORT: {clean_err(e)[:200]}")
    finally:
        try:
            if not aborted:
                conn.close()
            else:
                conn.close()
        except Exception:
            pass

    _print_summary(results, time.time() - start, aborted)


def _print_summary(results, elapsed, aborted):
    print(f"\n{'=' * 60}")
    print(f"Done in {elapsed:.1f}s" + (" (ABORTED)" if aborted else ""))
    ok = [r for r in results if r["status"] == "ok"]
    skip = [r for r in results if r["status"] == "skip"]
    fail = [r for r in results if r["status"] == "fail"]
    tot_upd = sum(r["updated"] for r in ok)
    tot_ins = sum(r["inserted"] for r in ok)
    tot_skip = sum(r["skipped"] for r in ok)
    print(f"  Tables OK:   {len(ok)}  ({tot_upd} updated, {tot_ins} inserted, {tot_skip} skipped)")
    print(f"  Tables SKIP: {len(skip)}")
    print(f"  Tables FAIL: {len(fail)}")
    if skip:
        print("\nSkipped tables:")
        for r in skip:
            print(f"  - {r['table']}: {r.get('reason', '')[:160]}")
    if fail:
        print("\nFailed tables:")
        for r in fail:
            print(f"  - {r['table']}: {r.get('reason', '')[:160]}")


if __name__ == "__main__":
    main()
