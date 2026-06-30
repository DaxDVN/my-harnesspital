#!/usr/bin/env python3
"""Add a DL-PROV-<n> / DL-<n> entry to a module's decision log + mirror.

Appends a provisional or decided decision entry to
specs/dev-specs/<module>/06-decision-log.md and mirrors a row into
05-open-questions.md. Numbering is a single shared counter across DL- and
DL-PROV-. Stdlib only.

Usage:
    python scripts/decision_log_add.py <module> --provisional "<text>" --basis "<src>" [--dry-run]
    python scripts/decision_log_add.py <module> --decided "<text>" --rationale "<src>" [--dry-run]
    python scripts/decision_log_add.py --self-test
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS = ROOT / "specs" / "dev-specs"

MIRROR_HEADER = "| ID | Decision | Status |"
MIRROR_SEP = "| --- | --- | --- |"
MIRROR_SECTION = "## Decision Log Mirror"


class ToolError(RuntimeError):
    pass


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def next_dl_number(text: str) -> int:
    nums = [int(n) for n in re.findall(r"##\s+DL-(?:PROV-)?(\d+)", text)]
    return max(nums) + 1 if nums else 1


def provisional_entry(n: int, today: str, text: str, basis: str) -> str:
    return (
        f"\n## DL-PROV-{n:03d} — {today}\n"
        f"**Decision**: {text}\n"
        f"**Basis**: {basis}\n"
        f"**Status**: PROVISIONAL (owner to confirm)\n"
    )


def decided_entry(n: int, today: str, text: str, rationale: str) -> str:
    return (
        f"\n## DL-{n:03d} — {today}\n"
        f"**Decision**: {text}\n"
        f"**Rationale**: {rationale}\n"
        f"**Status**: DECIDED\n"
    )


def append_entry(path: Path, entry: str, *, dry_run: bool) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    text += entry
    print(f"> append {rel(path)}")
    if not dry_run:
        path.write_text(text, encoding="utf-8")


def append_mirror_row(path: Path, row: str, *, dry_run: bool) -> None:
    text = path.read_text(encoding="utf-8")
    if MIRROR_HEADER in text:
        # Insert the row after the last table row that follows the header.
        header_idx = text.index(MIRROR_HEADER)
        # Find the end of the table block (first blank line after header).
        after = text[header_idx:]
        lines = after.splitlines(keepends=True)
        insert_at = header_idx
        seen_sep = False
        offset = header_idx
        for i, line in enumerate(lines):
            offset += len(line)
            stripped = line.strip()
            if stripped == MIRROR_SEP.strip():
                seen_sep = True
                insert_at = offset
                continue
            if seen_sep and stripped.startswith("|"):
                insert_at = offset
                continue
            if seen_sep and stripped == "":
                break
            if seen_sep and not stripped.startswith("|"):
                break
        updated = text[:insert_at] + row + "\n" + text[insert_at:]
    else:
        block = f"\n{MIRROR_SECTION}\n\n{MIRROR_HEADER}\n{MIRROR_SEP}\n{row}\n"
        updated = text.rstrip("\n") + "\n" + block
    print(f"> mirror {rel(path)}")
    if not dry_run:
        path.write_text(updated, encoding="utf-8")


def add_decision(args: argparse.Namespace) -> int:
    module = args.module
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", module):
        raise ToolError(f"Bad module slug {module!r}.")
    if bool(args.provisional) == bool(args.decided):
        raise ToolError("Provide exactly one of --provisional or --decided.")
    dl_path = SPECS / module / "06-decision-log.md"
    oq_path = SPECS / module / "05-open-questions.md"
    if not dl_path.exists():
        raise ToolError(f"Decision log not found: {rel(dl_path)}")
    if not oq_path.exists():
        raise ToolError(f"Open questions not found: {rel(oq_path)}")

    today = date.today().isoformat()
    dl_text = dl_path.read_text(encoding="utf-8")
    n = next_dl_number(dl_text)

    if args.provisional:
        entry = provisional_entry(n, today, args.provisional, args.basis or "")
        row = f"| DL-PROV-{n:03d} | {args.provisional} | NEEDS-OWNER-CONFIRM |"
        label = f"DL-PROV-{n:03d}"
    else:
        entry = decided_entry(n, today, args.decided, args.rationale or "")
        row = f"| DL-{n:03d} | {args.decided} | DECIDED |"
        label = f"DL-{n:03d}"

    if args.dry_run:
        print("[dry-run] entry to append:")
        print(entry.rstrip("\n"))
        print("[dry-run] mirror row:")
        print(row)
        return 0

    append_entry(dl_path, entry, dry_run=False)
    append_mirror_row(oq_path, row, dry_run=False)
    print()
    print(f"Added {label} -> {rel(dl_path)} + {rel(oq_path)}")
    return 0


def self_test() -> int:
    assert next_dl_number("# nothing") == 1
    assert next_dl_number("## DL-001\n...\n## DL-PROV-003\n") == 4
    assert next_dl_number("## DL-010\n## DL-002\n") == 11
    e = provisional_entry(1, "2026-06-29", "use json", "src")
    assert "DL-PROV-001" in e and "PROVISIONAL" in e
    e2 = decided_entry(2, "2026-06-29", "use json", "why")
    assert "DL-002" in e2 and "DECIDED" in e2
    # mirror insertion into a file without the table creates the section.
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Open Questions\n\n## Group\n- Q1\n")
        tmp = Path(f.name)
    try:
        append_mirror_row(tmp, "| DL-PROV-001 | x | NEEDS-OWNER-CONFIRM |", dry_run=False)
        content = tmp.read_text(encoding="utf-8")
        assert MIRROR_HEADER in content
        assert "| DL-PROV-001 | x | NEEDS-OWNER-CONFIRM |" in content
        # second append lands inside the existing table.
        append_mirror_row(tmp, "| DL-PROV-002 | y | NEEDS-OWNER-CONFIRM |", dry_run=False)
        content = tmp.read_text(encoding="utf-8")
        assert "| DL-PROV-002 | y | NEEDS-OWNER-CONFIRM |" in content
        assert content.count(MIRROR_HEADER) == 1
    finally:
        tmp.unlink()
    print("decision_log_add self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Add a DL/DL-PROV entry to a module decision log + open questions mirror",
    )
    parser.add_argument("module", nargs="?", help="module slug")
    parser.add_argument("--provisional", help="provisional decision text")
    parser.add_argument("--basis", help="basis/source for a provisional decision")
    parser.add_argument("--decided", help="decided decision text")
    parser.add_argument("--rationale", help="rationale/source for a decided decision")
    parser.add_argument("--dry-run", action="store_true", help="print entry, do not write")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.module:
        parser.error("provide a module slug")
    try:
        return add_decision(args)
    except ToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
