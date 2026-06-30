#!/usr/bin/env python3
"""Composite 4-command session-start ritual (AGENTS.md §1 + §6).

Runs the four read-only commands every source-edit session should start from,
parses their stdout, and renders ONE unified card (or `--json`):

  1. `python scripts/worktree.py list`      -> current worktree + slot/ports/DB
  2. `python scripts/rule_card.py fe "<task>"` -> FE rule card paths
  3. `python scripts/rule_card.py be "<task>"` -> BE rule card paths
  4. `python scripts/learning_recall.py --context "<task>"` -> recalled note paths

Usage:
    python scripts/harness_session_start.py "<task>" [--worktree <slug>] [--dry-run] [--json] [--self-test]

`--worktree <slug>` overrides the current-worktree selection (still must be a
listed active worktree). `--dry-run` prints the plan without invoking the four
commands (uses empty placeholders). The script never edits files; it only
captures subprocess stdout.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

def _run_capture(argv: list[str], *, dry_run: bool, timeout: int = 60) -> tuple[int, str, str]:
    """Run a command, capture stdout/stderr. Returns (rc, stdout, stderr)."""
    if dry_run:
        print(f"> (dry-run) {' '.join(argv)}", file=sys.stderr)
        return 0, "", ""
    print(f"> {' '.join(argv)}", file=sys.stderr)
    try:
        proc = subprocess.run(
            argv,
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_worktree_list(stdout: str) -> list[dict[str, Any]]:
    """Parse `worktree.py list` table into rows.

    Each row: {slug, slot, fe_url, be_url, sql, status, current}.
    """
    rows: list[dict[str, Any]] = []
    lines = stdout.splitlines()
    # Skip header (first non-blank line containing 'slug' and 'FE').
    data_lines = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("slug") and "FE" in s:
            continue
        if s.startswith("No ") or s.startswith("WARN:"):
            continue
        data_lines.append(line)
    for line in data_lines:
        current = "(current)" in line
        cleaned = line.replace("(current)", " ").rstrip()
        parts = cleaned.split()
        if len(parts) < 5:
            continue
        # slug slot FE BE SQL status...
        rows.append({
            "slug": parts[0],
            "slot": parts[1],
            "fe_url": parts[2],
            "be_url": parts[3],
            "sql": parts[4],
            "status": " ".join(parts[5:]) if len(parts) > 5 else "",
            "current": current,
        })
    return rows


def select_current(rows: list[dict[str, Any]], override: str | None) -> dict[str, Any] | None:
    """Pick the current worktree row, honoring --worktree override."""
    if override:
        for row in rows:
            if row["slug"] == override:
                return row
        return None
    currents = [r for r in rows if r["current"]]
    if len(currents) == 1:
        return currents[0]
    if len(currents) > 1:
        # Multiple markers — deterministic pick (first).
        return currents[0]
    return None


def parse_rule_card_json(stdout: str) -> list[str]:
    """Parse `rule_card.py --json` output into card paths."""
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    cards = data.get("cards") if isinstance(data, dict) else None
    if not isinstance(cards, list):
        return []
    return [str(c) for c in cards if isinstance(c, str)]


def parse_learning_recall(stdout: str) -> list[str]:
    """Parse `learning_recall.py` text output for note paths (lines after '→')."""
    paths: list[str] = []
    for line in stdout.splitlines():
        # Path lines look like: "        → second-brain/grouped/01-...md"
        m = re.search(r"→\s+(\S+\.md)\s*$", line)
        if m:
            paths.append(m.group(1))
    return paths


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(task: str, *, worktree: str | None, dry_run: bool) -> dict[str, Any]:
    """Run the 4-command ritual and return a structured result."""
    result: dict[str, Any] = {
        "task": task,
        "worktree": None,
        "fe_cards": [],
        "be_cards": [],
        "recalled_notes": [],
        "warnings": [],
        "infos": [],
    }

    # 1. worktree list
    rc, out, err = _run_capture([PYTHON, "scripts/worktree.py", "list"], dry_run=dry_run)
    if rc != 0:
        result["warnings"].append(f"worktree.py list failed (rc={rc}): {err.strip() or out.strip()}")
    else:
        rows = parse_worktree_list(out)
        if not rows:
            result["warnings"].append("no active worktrees found")
        else:
            current = select_current(rows, worktree)
            if current is None:
                if worktree:
                    result["warnings"].append(
                        f"--worktree {worktree!r} not found among {len(rows)} active worktree(s)"
                    )
                else:
                    n = len(rows)
                    if n == 1:
                        # Single worktree, no marker — use it but warn.
                        current = rows[0]
                        result["warnings"].append(
                            "single active worktree has no (current) marker; using it. "
                            "Run `python scripts/worktree.py set-current <slug>` to mark it."
                        )
                    else:
                        result["warnings"].append(
                            f"{n} active worktrees, none marked (current). "
                            "Run `python scripts/worktree.py set-current <slug>` to disambiguate."
                        )
            result["worktree"] = current
            # Surface non-current worktrees count for the card.
            result["_all_rows"] = rows

    # 2. FE rule cards (--json for robust parsing)
    rc, out, err = _run_capture(
        [PYTHON, "scripts/rule_card.py", "fe", task, "--json"], dry_run=dry_run
    )
    if rc != 0:
        result["warnings"].append(f"rule_card.py fe failed (rc={rc}): {err.strip()}")
    else:
        result["fe_cards"] = parse_rule_card_json(out)
        if not result["fe_cards"]:
            result["warnings"].append("rule_card.py fe returned 0 cards")

    # 3. BE rule cards
    rc, out, err = _run_capture(
        [PYTHON, "scripts/rule_card.py", "be", task, "--json"], dry_run=dry_run
    )
    if rc != 0:
        result["warnings"].append(f"rule_card.py be failed (rc={rc}): {err.strip()}")
    else:
        result["be_cards"] = parse_rule_card_json(out)
        if not result["be_cards"]:
            result["warnings"].append("rule_card.py be returned 0 cards")

    # 4. learning_recall
    rc, out, err = _run_capture(
        [PYTHON, "scripts/learning_recall.py", "--context", task], dry_run=dry_run
    )
    if rc != 0:
        result["warnings"].append(f"learning_recall.py failed (rc={rc}): {err.strip()}")
    else:
        result["recalled_notes"] = parse_learning_recall(out)
        if not result["recalled_notes"]:
            result["infos"].append("learning_recall returned 0 matching notes")

    return result


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render_card(result: dict[str, Any]) -> str:
    task = result["task"]
    lines: list[str] = []
    lines.append(f'=== Session start: "{task}" ===')
    lines.append("")

    wt = result.get("worktree")
    if wt:
        marker = " (current)" if wt.get("current") else ""
        lines.append(f"Worktree: {wt['slug']}{marker}  [slot {wt['slot']}]")
        lines.append(f"  FE: {wt['fe_url']}")
        lines.append(f"  BE: {wt['be_url']}")
        lines.append(f"  DB: {wt['sql']}")
        all_rows = result.get("_all_rows") or []
        if len(all_rows) > 1:
            others = [r for r in all_rows if r is not wt]
            lines.append(f"  (other active: {', '.join(r['slug'] for r in others)})")
    else:
        lines.append("Worktree: (none selected)")
    lines.append("")

    fe_cards = result.get("fe_cards") or []
    lines.append(f"FE rule cards (open these):" + ("" if fe_cards else "  (none)"))
    for c in fe_cards:
        lines.append(f"  {c}")
    lines.append("")

    be_cards = result.get("be_cards") or []
    lines.append(f"BE rule cards (open these):" + ("" if be_cards else "  (none)"))
    for c in be_cards:
        lines.append(f"  {c}")
    lines.append("")

    notes = result.get("recalled_notes") or []
    if notes:
        lines.append("Recalled notes (open if relevant):")
        for n in notes:
            lines.append(f"  {n}")
    else:
        lines.append("Recalled notes: (none matched)")
    lines.append("")

    for w in result.get("warnings", []):
        lines.append(f"WARN: {w}")
    for i in result.get("infos", []):
        lines.append(f"INFO: {i}")
    if result.get("warnings") or result.get("infos"):
        lines.append("")

    lines.append(f'Next: run `python scripts/harness_preflight.py "{task}"` for route card.')
    return "\n".join(lines)


def to_json(result: dict[str, Any]) -> dict[str, Any]:
    wt = result.get("worktree")
    return {
        "task": result["task"],
        "worktree": wt,
        "fe_cards": result.get("fe_cards", []),
        "be_cards": result.get("be_cards", []),
        "recalled_notes": result.get("recalled_notes", []),
        "warnings": result.get("warnings", []),
        "infos": result.get("infos", []),
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def self_test() -> int:
    # parse_worktree_list
    sample = (
        "slug                       slot FE                     BE                     SQL                      status\n"
        "combine-his-pacs (current) 3    http://localhost:3003  http://localhost:5003  localhost,1436/MyHospital OK\n"
        "ipd-improve-v5             4    http://localhost:3004  http://localhost:5004  localhost,1437/MyHospital OK\n"
    )
    rows = parse_worktree_list(sample)
    assert len(rows) == 2, f"expected 2 rows, got {len(rows)}"
    assert rows[0]["slug"] == "combine-his-pacs" and rows[0]["current"] is True, rows[0]
    assert rows[0]["fe_url"] == "http://localhost:3003", rows[0]
    assert rows[1]["current"] is False and rows[1]["slot"] == "4", rows[1]
    assert "OK" in rows[0]["status"], rows[0]

    # select_current: single marker
    cur = select_current(rows, None)
    assert cur and cur["slug"] == "combine-his-pacs", cur
    # override
    cur = select_current(rows, "ipd-improve-v5")
    assert cur and cur["slug"] == "ipd-improve-v5", cur
    # override missing
    assert select_current(rows, "nope") is None
    # no marker
    rows_none = [dict(r, current=False) for r in rows]
    assert select_current(rows_none, None) is None

    # parse_rule_card_json
    cards = parse_rule_card_json('{"package": "fe", "cards": ["engine/rules/frontend/quick.md", "engine/rules/frontend/forms.md"]}')
    assert cards == ["engine/rules/frontend/quick.md", "engine/rules/frontend/forms.md"], cards
    assert parse_rule_card_json("not json") == []
    assert parse_rule_card_json('{"cards": []}') == []

    # parse_learning_recall
    lr = (
        "[learning_recall] 1 candidate note(s) — open ONLY these; provisional, VERIFY before acting:\n\n"
        "  [  5] be-listing-rule  (kw:listing)\n"
        "        Filter by hospital.\n"
        "        → second-brain/grouped/01-freshness-before-diagnosis.md\n"
    )
    notes = parse_learning_recall(lr)
    assert notes == ["second-brain/grouped/01-freshness-before-diagnosis.md"], notes
    assert parse_learning_recall("no matches") == []

    # render_card smoke (no crash with empty)
    card = render_card({"task": "x", "worktree": None, "fe_cards": [], "be_cards": [],
                        "recalled_notes": [], "warnings": [], "infos": []})
    assert "Session start" in card and "Worktree: (none selected)" in card, card

    # render with a worktree
    card = render_card({
        "task": "fix listing", "worktree": rows[0], "fe_cards": ["a.md"], "be_cards": ["b.md"],
        "recalled_notes": ["n.md"], "warnings": [], "infos": [], "_all_rows": rows,
    })
    assert "combine-his-pacs (current)" in card and "[slot 3]" in card, card
    assert "harness_preflight" in card, card

    print("harness_session_start self-test: OK")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Composite 4-command session-start ritual (worktree + rule cards + recall)."
    )
    parser.add_argument("task", nargs="*", help='Task text (e.g. "fix listing hospital-scope in BE").')
    parser.add_argument("--worktree", help="Override current-worktree selection by slug.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON dict instead of the card.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    task = " ".join(args.task).strip()
    if not task:
        parser.error('provide a task text, e.g. python scripts/harness_session_start.py "fix listing in BE"')

    result = run_pipeline(task, worktree=args.worktree, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(to_json(result), indent=2, ensure_ascii=False))
    else:
        print(render_card(result))

    # Exit 0 even on warnings (warnings are non-fatal). Exit 1 only if worktree
    # resolution explicitly failed AND an override was requested-but-missing,
    # which signals an owner typo rather than a soft state.
    if args.worktree and result.get("worktree") is None:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
