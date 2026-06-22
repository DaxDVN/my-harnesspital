#!/usr/bin/env python3
"""Find repeated bug classes that should become deterministic scanners/guards.

This is advisory by default. It scans lightweight markdown artifacts for stable `bug_class:` markers and reports
classes seen at least twice.

Usage:
    python scripts/harness_scanner_promotion.py scan
    python scripts/harness_scanner_promotion.py scan --fail-on-promote
    python scripts/harness_scanner_promotion.py --self-test
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GLOBS = [
    "docs/audit/**/*.md",
    "engine/workflows/robust-test/runs/**/*.md",
    "second-brain/**/*.md",
]
BUG_CLASS_RE = re.compile(r"^\s*-?\s*bug[_-]class\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


def normalize(value: str) -> str:
    key = re.sub(r"`|\[|\]|\(|\)", "", value.strip().lower())
    key = re.sub(r"[^a-z0-9_.:-]+", "-", key).strip("-")
    return key[:120]


def scan_paths(paths: list[Path]) -> dict[str, list[Path]]:
    hits: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in BUG_CLASS_RE.finditer(text):
            key = normalize(match.group(1))
            if key:
                hits[key].append(path)
    return dict(hits)


def default_paths() -> list[Path]:
    paths: list[Path] = []
    for pattern in DEFAULT_GLOBS:
        paths.extend(ROOT.glob(pattern))
    return sorted(set(paths))


def command_scan(fail_on_promote: bool) -> int:
    hits = scan_paths(default_paths())
    promotable = {key: paths for key, paths in hits.items() if len(paths) >= 2}
    if not promotable:
        print("Scanner promotion: no repeated bug_class markers found")
        return 0
    for key, paths in sorted(promotable.items()):
        print(f"PROMOTE_TO_SCANNER {key} count={len(paths)}")
        for path in paths[:5]:
            print(f"  - {path.relative_to(ROOT)}")
        if len(paths) > 5:
            print(f"  - ... {len(paths) - 5} more")
    return 1 if fail_on_promote else 0


def self_test() -> int:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        a = root / "a.md"
        b = root / "b.md"
        c = root / "c.md"
        a.write_text("- bug_class: fe-raw-fetch\n", encoding="utf-8")
        b.write_text("bug_class: fe raw fetch\n", encoding="utf-8")
        c.write_text("bug_class: be-missing-scope\n", encoding="utf-8")
        hits = scan_paths([a, b, c])
        assert len(hits["fe-raw-fetch"]) == 2
        assert len(hits["be-missing-scope"]) == 1
    print("harness_scanner_promotion self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Report repeated bug classes that should become scanners")
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="command")
    scan = sub.add_parser("scan")
    scan.add_argument("--fail-on-promote", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.command == "scan":
        return command_scan(args.fail_on_promote)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
