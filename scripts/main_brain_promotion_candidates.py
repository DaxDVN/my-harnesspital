#!/usr/bin/env python3
"""Report second-brain notes that look ready for owner promotion.

This script never writes main-brain. It only scans provisional notes and optionally writes a review report under
docs/harness/notes/.

Usage:
    python scripts/main_brain_promotion_candidates.py scan
    python scripts/main_brain_promotion_candidates.py write-report
    python scripts/main_brain_promotion_candidates.py --self-test
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECOND_BRAIN = ROOT / "second-brain"


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def candidates() -> list[dict[str, str]]:
    rows = []
    paths = list(SECOND_BRAIN.glob("*.md")) + list((SECOND_BRAIN / "grouped").glob("[0-9][0-9]-*.md"))
    for path in sorted(paths):
        if path.name in {"INDEX.md", "README.md"}:
            continue
        fm = frontmatter(path)
        if fm.get("status") != "provisional":
            continue
        target = fm.get("proposed_target", "")
        confidence = fm.get("confidence", "")
        if target == "main-brain" or (confidence == "high" and target not in {"reject", "none"}):
            rows.append({
                "path": str(path.relative_to(ROOT)),
                "title": fm.get("title", path.stem),
                "confidence": confidence,
                "proposed_target": target,
                "scope": fm.get("scope", ""),
            })
    return rows


def render(rows: list[dict[str, str]]) -> str:
    lines = [
        "# Main-Brain Promotion Candidates",
        "",
        "This report is advisory. Agents must not write `main-brain/` directly.",
        "",
    ]
    if not rows:
        lines.append("No promotion candidates found.")
        return "\n".join(lines) + "\n"
    for row in rows:
        lines.extend([
            f"## {row['title']}",
            f"- path: {row['path']}",
            f"- confidence: {row['confidence']}",
            f"- proposed_target: {row['proposed_target']}",
            f"- scope: {row['scope']}",
            "",
        ])
    return "\n".join(lines)


def command_scan() -> int:
    rows = candidates()
    print(render(rows), end="")
    return 0


def command_write_report() -> int:
    out_dir = ROOT / "docs" / "harness" / "notes"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"main-brain-promotion-candidates-{date.today().isoformat()}.md"
    path.write_text(render(candidates()), encoding="utf-8")
    print(path.relative_to(ROOT))
    return 0


def self_test() -> int:
    rows = candidates()
    assert isinstance(rows, list)
    for row in rows:
        assert re.match(r"second-brain/.+\.md$", row["path"])
    print("main_brain_promotion_candidates self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Report second-brain notes ready for owner promotion review")
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("scan")
    sub.add_parser("write-report")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.command == "scan":
        return command_scan()
    if args.command == "write-report":
        return command_write_report()
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
