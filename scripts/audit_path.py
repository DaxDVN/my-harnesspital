#!/usr/bin/env python3
"""Resolve the versioned, date-foldered output path for an audit document.

Rule (overrides whatever filename a prompt/skill asks for):
- Audit docs live under ``docs/audit/<YYYY-MM-DD>/`` (today's folder, auto-created).
- They are versioned by ROUND: ``<base>.round-<N>.md``.
- ``N`` = 1 if NO existing ``<base>.round-*.md`` anywhere under ``docs/audit/`` (any date);
  otherwise ``max(existing round) + 1``. The Vietnamese clone ``<base>.round-<N>.vi.md`` does
  NOT count as a separate round.

Usage:
    python scripts/audit_path.py "full-audit-vital-signs"
        -> docs/audit/2026-06-19/full-audit-vital-signs.round-3.md   (and mkdir -p the folder)

    python scripts/audit_path.py "full-audit-vital-signs" --vi
        -> docs/audit/2026-06-19/full-audit-vital-signs.round-3.vi.md   (same round, .vi.md)

    python scripts/audit_path.py "full-audit-vital-signs" --dry-run   # print path, don't mkdir
    python scripts/audit_path.py "full-audit-vital-signs" --current   # highest EXISTING round (no bump); 0 if none

The base name is sanitized to the bare stem: any trailing ``.md`` / ``.vi.md`` /
``.round-N`` / date folder is stripped, so passing ``full-audit-x.md`` or
``full-audit-x.round-2.md`` all resolve to base ``full-audit-x``.
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

AUDIT_DIR_NAME = "audit"
ROUND_RE = re.compile(r"^(?P<base>.+?)\.round-(?P<n>\d+)(?:\.vi)?\.md$")


def workspace_root() -> Path:
    # scripts/ lives directly under the workspace root.
    return Path(__file__).resolve().parent.parent


def normalize_base(raw: str) -> str:
    name = Path(raw).name  # drop any directory part
    m = ROUND_RE.match(name)
    if m:
        return m.group("base")
    # strip plain .vi.md / .md if present
    name = re.sub(r"\.vi\.md$", "", name)
    name = re.sub(r"\.md$", "", name)
    # strip a dangling .round-N with no extension
    name = re.sub(r"\.round-\d+$", "", name)
    return name


def highest_round(audit_root: Path, base: str) -> int:
    """Max round N across ALL date-folders (and any legacy flat files) for this base."""
    best = 0
    if not audit_root.exists():
        return best
    for path in audit_root.rglob(f"{base}.round-*.md"):
        m = ROUND_RE.match(path.name)
        if m and m.group("base") == base:
            best = max(best, int(m.group("n")))
    return best


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve the versioned audit output path.")
    parser.add_argument("base", help="Base audit name, e.g. 'full-audit-vital-signs' (extensions/round stripped).")
    parser.add_argument("--vi", action="store_true", help="Return the Vietnamese clone path (.vi.md, same round).")
    parser.add_argument("--dry-run", action="store_true", help="Print the path but do not create the date folder.")
    parser.add_argument("--current", action="store_true", help="Print the highest EXISTING round number (no bump). 0 if none.")
    parser.add_argument("--date", default=None, help="Override the date folder (YYYY-MM-DD); defaults to today.")
    args = parser.parse_args(argv)

    root = workspace_root()
    audit_root = root / "docs" / AUDIT_DIR_NAME
    base = normalize_base(args.base)

    existing = highest_round(audit_root, base)
    if args.current:
        print(existing)
        return 0

    next_round = existing + 1
    day = args.date or datetime.date.today().isoformat()
    folder = audit_root / day
    suffix = ".vi.md" if args.vi else ".md"
    target = folder / f"{base}.round-{next_round}{suffix}"

    if not args.dry_run:
        folder.mkdir(parents=True, exist_ok=True)

    # Print path relative to the workspace root for easy copy-paste in prompts.
    print(target.relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
