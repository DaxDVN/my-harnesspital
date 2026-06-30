#!/usr/bin/env python3
"""Generate idempotent SQL Server INSERT scripts from MyHospital seed CSV files."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


TABLE_MAP = {
    "MedicalVisitLabTestService": "MedicalVisitLabTestServices",
    "MedicalVisitDiagnosticImagingService": "MedicalVisitDiagnosticImagingServices",
}

EXTRA_COLUMNS = {
    "BedReservation": {
        "LinkedSurgeryServiceIds": "N'[]'",
    },
    "MedicalVisitBedStay": {
        "LinkedSurgeryServiceIds": "N'[]'",
    },
}


def sql_literal(value: str) -> str:
    value = value.strip()
    if value == "":
        return "NULL"
    lowered = value.lower()
    if lowered == "true":
        return "1"
    if lowered == "false":
        return "0"
    return "N'" + value.replace("'", "''") + "'"


def table_name(csv_path: Path) -> str:
    return TABLE_MAP.get(csv_path.stem, csv_path.stem)


def emit_table(csv_path: Path) -> str:
    table = table_name(csv_path)
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = list(reader)

    if not headers or "Id" not in headers or not rows:
        return ""

    extra_columns = {
        name: value
        for name, value in EXTRA_COLUMNS.get(table, {}).items()
        if name not in headers
    }
    insert_headers = headers + list(extra_columns)

    columns = ", ".join(f"[{header}]" for header in insert_headers)
    lines = [
        f"PRINT N'Seeding {table} from {csv_path.name}';",
        f"IF OBJECT_ID(N'[{table}]', N'U') IS NOT NULL",
        "BEGIN",
        f"    SET IDENTITY_INSERT [{table}] ON;",
    ]

    for row in rows:
        row_id = row.get("Id", "").strip()
        if not row_id:
            continue
        values = ", ".join(
            [sql_literal(row.get(header, "")) for header in headers]
            + list(extra_columns.values())
        )
        lines.extend(
            [
                f"    IF NOT EXISTS (SELECT 1 FROM [{table}] WHERE [Id] = {sql_literal(row_id)})",
                f"        INSERT INTO [{table}] ({columns}) VALUES ({values});",
            ]
        )

    lines.extend(
        [
            f"    SET IDENTITY_INSERT [{table}] OFF;",
            "END",
            "GO",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--table", action="append", required=True, dest="tables")
    parser.add_argument("--extra-sql", action="append", default=[])
    args = parser.parse_args()

    parts = [
        "SET NOCOUNT ON;",
        "SET XACT_ABORT ON;",
        "GO",
        "",
    ]

    for table in args.tables:
        csv_path = args.csv_root / f"{table}.csv"
        if not csv_path.exists():
            raise FileNotFoundError(csv_path)
        parts.append(emit_table(csv_path))

    for extra in args.extra_sql:
        extra_path = Path(extra)
        parts.append(extra_path.read_text(encoding="utf-8"))
        parts.append("\nGO\n")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(parts), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
