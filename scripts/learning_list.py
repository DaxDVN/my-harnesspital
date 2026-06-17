#!/usr/bin/env python3
"""
learning_list.py — print the provisional learning queue from second-brain/.

Usage:
  python scripts/learning_list.py
  python scripts/learning_list.py --target engine/rules/backend
  python scripts/learning_list.py --confidence high
  python scripts/learning_list.py --stale

Exit 0 always (informational only).
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SECOND_BRAIN   = WORKSPACE_ROOT / "second-brain"
SKIP_FILES     = {"README.md", "INDEX.md"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].strip()
    result = {}
    for line in block.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip().strip('"').strip("'")
    return result


def is_stale(fm: dict) -> bool:
    """An entry is stale if expires is set and today >= that date."""
    expires = fm.get("expires", "").strip().strip('"')
    if not expires:
        return False
    try:
        exp_date = date.fromisoformat(expires[:10])
        return date.today() >= exp_date
    except ValueError:
        return False


def load_entries(sb: Path) -> list[dict]:
    entries = []
    for md in sorted(sb.glob("*.md")):
        if md.name in SKIP_FILES:
            continue
        text = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm is None:
            continue
        if fm.get("status", "").strip() != "provisional":
            continue
        fm["_file"] = md.name
        fm["_stale"] = is_stale(fm)
        entries.append(fm)
    return entries


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="List provisional learnings in second-brain/."
    )
    parser.add_argument("--target",     default=None,
                        help="Filter by proposed_target substring (e.g. engine/rules/backend)")
    parser.add_argument("--confidence", default=None,
                        help="Filter by confidence level: low | medium | high")
    parser.add_argument("--stale",      action="store_true",
                        help="Show only entries whose expires date has passed")
    parser.add_argument("--self-test",  action="store_true",
                        help="Run internal sanity check and exit")
    args = parser.parse_args()

    if args.self_test:
        _self_test()
        return

    if not SECOND_BRAIN.exists():
        print("second-brain/ does not exist — nothing to list.")
        return

    entries = load_entries(SECOND_BRAIN)

    # Apply filters
    if args.target:
        entries = [e for e in entries if args.target.lower() in e.get("proposed_target", "").lower()]
    if args.confidence:
        entries = [e for e in entries if e.get("confidence", "").lower() == args.confidence.lower()]
    if args.stale:
        entries = [e for e in entries if e["_stale"]]

    if not entries:
        print("OPEN provisional: (none matching filters)")
        return

    stale_entries = [e for e in entries if e["_stale"]]

    print(f"OPEN provisional: {len(entries)} entrie(s)")
    if stale_entries:
        print(f"  *** {len(stale_entries)} stale (expires date passed) ***")
    print()

    for e in entries:
        slug   = e["_file"].replace(".md", "")
        target = e.get("proposed_target", "?")
        conf   = e.get("confidence", "?")
        src    = e.get("source", "?")
        title  = e.get("title", "(no title)")
        stale_marker = " [STALE]" if e["_stale"] else ""
        print(f"- {slug}{stale_marker}")
        print(f"    title:  {title}")
        print(f"    target: {target}  |  confidence: {conf}  |  source: {src}")
        print()


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    import tempfile

    print("=== learning_list self-test ===")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        sb = tmp_path / "second-brain"
        sb.mkdir()

        # Write a good provisional entry
        good = sb / "2026-06-17-test-entry.md"
        good.write_text(
            '---\ntitle: "Test Entry"\ndate: "2026-06-17"\nstatus: provisional\n'
            'source: conversation\nscope: workspace\nconfidence: high\n'
            'owner_confirmed: false\nproposed_target: engine/rules/backend\n'
            'tags: []\nexpires: ""\n---\n\n# What\nx\n',
            encoding="utf-8",
        )

        # Write a non-provisional (should be skipped)
        non = sb / "2026-06-17-promoted.md"
        non.write_text(
            '---\ntitle: "Old"\ndate: "2026-06-17"\nstatus: promoted\n'
            'source: conversation\nscope: workspace\nconfidence: high\n'
            'owner_confirmed: true\nproposed_target: main-brain\n'
            'tags: []\nexpires: ""\n---\n\n# What\nOld.\n',
            encoding="utf-8",
        )

        # Patch global
        global SECOND_BRAIN
        orig = SECOND_BRAIN
        SECOND_BRAIN = sb
        try:
            entries = load_entries(sb)
            assert len(entries) == 1, f"expected 1 provisional, got {len(entries)}"
            assert entries[0]["title"] == "Test Entry", "wrong title"
            print("  [PASS] provisional filter works")

            # Confidence filter
            high = [e for e in entries if e.get("confidence") == "high"]
            assert len(high) == 1, "confidence filter failed"
            print("  [PASS] confidence filter works")

            # Target filter
            be = [e for e in entries if "backend" in e.get("proposed_target", "")]
            assert len(be) == 1, "target filter failed"
            print("  [PASS] target filter works")

            # Stale filter — none should be stale
            stale = [e for e in entries if e["_stale"]]
            assert len(stale) == 0, "stale detection wrong on non-stale entry"
            print("  [PASS] stale detection works on non-stale entry")

        finally:
            SECOND_BRAIN = orig

    print("=== All tests passed ===")


if __name__ == "__main__":
    main()
