#!/usr/bin/env python3
"""Build a context-manifest YAML for PM-orchestrator worker dispatch.

Per `engine/rules/context-manifest.md`, the orchestrator transfers memory to a
worker BY REFERENCE (paths only, never pasted content). This script gathers the
references a worker needs for one phase and emits a compact YAML manifest:

  - FE/BE rule cards (from `rule_card.py`)
  - recalled second-brain notes (from `learning_recall.py`)
  - workflow manifest fields (recommended_prompt_file, rules, skills, agents)
  - worktree FE/BE/DB paths
  - the latest run-state ledger path for the workflow

No external YAML dependency — the emitter is a tiny hand-rolled writer for the
flat structure (strings + lists) the manifest uses.

Usage:
    python scripts/context_manifest_build.py "<task>" --workflow <wf> --phase <phase> \
        [--worktree <slug>] [--output <path>] [--dry-run] [--self-test]
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
    if dry_run:
        print(f"> (dry-run) {' '.join(argv)}", file=sys.stderr)
        return 0, "", ""
    print(f"> {' '.join(argv)}", file=sys.stderr)
    try:
        proc = subprocess.run(
            argv, cwd=str(ROOT), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# Parsers (shared shape with harness_session_start, kept local for independence)
# ---------------------------------------------------------------------------

def parse_worktree_list(stdout: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        s = line.strip()
        if not s or s.startswith("slug") or s.startswith("No ") or s.startswith("WARN:"):
            continue
        current = "(current)" in line
        cleaned = line.replace("(current)", " ").rstrip()
        parts = cleaned.split()
        if len(parts) < 5:
            continue
        rows.append({
            "slug": parts[0], "slot": parts[1], "fe_url": parts[2],
            "be_url": parts[3], "sql": parts[4],
            "status": " ".join(parts[5:]) if len(parts) > 5 else "",
            "current": current,
        })
    return rows


def select_current(rows: list[dict[str, Any]], override: str | None) -> dict[str, Any] | None:
    if override:
        for row in rows:
            if row["slug"] == override:
                return row
        return None
    currents = [r for r in rows if r["current"]]
    return currents[0] if currents else (rows[0] if len(rows) == 1 else None)


def parse_rule_card_json(stdout: str) -> list[str]:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    cards = data.get("cards") if isinstance(data, dict) else None
    return [str(c) for c in cards if isinstance(c, str)] if isinstance(cards, list) else []


def parse_learning_recall(stdout: str) -> list[str]:
    paths: list[str] = []
    for line in stdout.splitlines():
        m = re.search(r"→\s+(\S+\.md)\s*$", line)
        if m:
            paths.append(m.group(1))
    return paths


# ---------------------------------------------------------------------------
# Workflow manifest + ledger
# ---------------------------------------------------------------------------

def load_workflow_manifest(workflow: str) -> dict[str, Any]:
    path = ROOT / "engine" / "workflows" / workflow / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"workflow manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def latest_ledger_path(workflow: str) -> str:
    """Find the most recent 00-*-state.md under the workflow's runs/ tree."""
    runs_root = ROOT / "engine" / "workflows" / workflow / "runs"
    if not runs_root.exists():
        return ""
    candidates: list[tuple[float, Path]] = []
    for p in runs_root.rglob("00-*-state.md"):
        try:
            candidates.append((p.stat().st_mtime, p))
        except OSError:
            continue
    if not candidates:
        return ""
    candidates.sort(key=lambda t: t[0], reverse=True)
    try:
        return candidates[0][1].relative_to(ROOT).as_posix()
    except ValueError:
        return str(candidates[0][1])


def resolve_worktree_paths(row: dict[str, Any]) -> dict[str, str]:
    """Resolve fe/be/db paths from a worktree list row."""
    slug = row["slug"]
    fe_path = f"worktrees/{slug}/fe"
    be_path = f"worktrees/{slug}/be"
    return {
        "slug": slug,
        "slot": str(row["slot"]),
        "fe_url": row["fe_url"],
        "be_url": row["be_url"],
        "db": row["sql"],
        "fe_path": fe_path,
        "be_path": be_path,
    }


# ---------------------------------------------------------------------------
# YAML emitter (flat: scalars + lists + nested dicts)
# ---------------------------------------------------------------------------

def _yaml_value(val: Any) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    return _yaml_scalar(str(val))


def _yaml_scalar(value: str) -> str:
    if value == "":
        return '""'
    # Quote if it contains chars that need quoting in YAML flow context.
    if re.search(r"[:#\[\]\{\},&*?|\-<>=!%@`\"\n\\]", value) or value.lower() in {"true", "false", "null", "~"}:
        return json.dumps(value)  # JSON quoting is valid YAML for strings
    return value


def _emit(value: Any, indent: int = 0) -> list[str]:
    pad = "  " * indent
    lines: list[str] = []
    if isinstance(value, dict):
        for key, val in value.items():
            if isinstance(val, dict):
                lines.append(f"{pad}{key}:")
                lines.extend(_emit(val, indent + 1))
            elif isinstance(val, list):
                if not val:
                    lines.append(f"{pad}{key}: []")
                else:
                    lines.append(f"{pad}{key}:")
                    for item in val:
                        if isinstance(item, dict):
                            lines.append(f"{pad}  -")
                            sub = _emit(item, indent + 2)
                            # align first sub-line after the dash
                            if sub:
                                lines.append(f"{pad}  " + sub[0].lstrip())
                                lines.extend(sub[1:])
                        else:
                            lines.append(f"{pad}  - {_yaml_scalar(str(item))}")
            else:
                lines.append(f"{pad}{key}: {_yaml_value(val)}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                lines.append(f"{pad}-")
                lines.extend(_emit(item, indent + 1))
            else:
                lines.append(f"{pad}- {_yaml_scalar(str(item))}")
    else:
        lines.append(f"{pad}{_yaml_scalar(str(value))}")
    return lines


def to_yaml(data: dict[str, Any]) -> str:
    return "\n".join(_emit(data, 0)) + "\n"


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_manifest(
    task: str, workflow: str, phase: str,
    *, worktree: str | None, dry_run: bool,
) -> dict[str, Any]:
    # Rule cards
    rc, out, _ = _run_capture([PYTHON, "scripts/rule_card.py", "fe", task, "--json"], dry_run=dry_run)
    fe_cards = parse_rule_card_json(out) if rc == 0 else []
    rc, out, _ = _run_capture([PYTHON, "scripts/rule_card.py", "be", task, "--json"], dry_run=dry_run)
    be_cards = parse_rule_card_json(out) if rc == 0 else []

    # Recalled notes
    rc, out, _ = _run_capture([PYTHON, "scripts/learning_recall.py", "--context", task], dry_run=dry_run)
    notes = parse_learning_recall(out) if rc == 0 else []

    # Workflow manifest
    wf_manifest: dict[str, Any] = {}
    wf_error = ""
    try:
        wf_manifest = load_workflow_manifest(workflow)
    except FileNotFoundError as exc:
        wf_error = str(exc)

    prompt_file = wf_manifest.get("recommended_prompt_file", "") if wf_manifest else ""
    wf_rules = wf_manifest.get("rules", []) or [] if wf_manifest else []
    wf_skills = wf_manifest.get("skills_used", []) or [] if wf_manifest else []
    wf_agents = wf_manifest.get("agents", []) or [] if wf_manifest else ""

    # Worktree resolution
    rc, out, _ = _run_capture([PYTHON, "scripts/worktree.py", "list"], dry_run=dry_run)
    wt: dict[str, Any] | None = None
    if rc == 0:
        rows = parse_worktree_list(out)
        wt = select_current(rows, worktree)

    wt_paths = resolve_worktree_paths(wt) if wt else {}
    ledger = latest_ledger_path(workflow)

    manifest: dict[str, Any] = {
        "task": task,
        "workflow": workflow,
        "phase": phase,
        "worktree": wt_paths.get("slug", worktree or ""),
        "zone_a": {
            "rule_cards": fe_cards + be_cards,
            "fe_cards": fe_cards,
            "be_cards": be_cards,
            "prompt_file": prompt_file,
            "recalled_notes": notes,
            "ledger": ledger,
            "workflow_manifest": f"engine/workflows/{workflow}/manifest.json",
            "workflow_rules": wf_rules,
            "workflow_skills": wf_skills,
            "workflow_agents": wf_agents,
        },
        "zone_b": [
            "schema unclear? ask owner",
            "missing spec section? ask owner",
            "worktree not listed? ask owner",
        ],
        "verify_live": True,
    }
    if wt_paths:
        manifest["worktree_paths"] = wt_paths
    if wf_error:
        manifest["warnings"] = [wf_error]
    return manifest


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def self_test() -> int:
    # YAML emitter
    y = to_yaml({"a": "b", "list": ["x", "y"], "nested": {"k": "v"}, "empty": [], "q": 'has: colon'})
    assert "a: b" in y, y
    assert "list:" in y and "- x" in y and "- y" in y, y
    assert "nested:" in y and "k: v" in y, y
    assert "empty: []" in y, y
    assert '"has: colon"' in y, y  # quoted because of colon

    # latest_ledger_path: real pm-orchestrator has runs/
    led = latest_ledger_path("pm-orchestrator")
    assert led.endswith("00-pm-state.md") and "pm-orchestrator/runs/" in led, led
    # unknown workflow -> empty
    assert latest_ledger_path("no-such-workflow-zzz") == ""

    # load_workflow_manifest error
    try:
        load_workflow_manifest("no-such-workflow-zzz")
        raise AssertionError("expected FileNotFoundError")
    except FileNotFoundError:
        pass

    # resolve_worktree_paths
    paths = resolve_worktree_paths({"slug": "ipd-v5", "slot": "4", "fe_url": "http://localhost:3004",
                                    "be_url": "http://localhost:5004", "sql": "localhost,1437/MyHospital",
                                    "current": True, "status": "OK"})
    assert paths["fe_path"] == "worktrees/ipd-v5/fe", paths
    assert paths["be_path"] == "worktrees/ipd-v5/be", paths
    assert paths["db"] == "localhost,1437/MyHospital", paths

    # parsers
    rows = parse_worktree_list(
        "slug                       slot FE                     BE                     SQL                      status\n"
        "ipd (current) 4    http://localhost:3004  http://localhost:5004  localhost,1437/MyHospital OK\n"
    )
    assert rows[0]["slug"] == "ipd" and rows[0]["current"] is True, rows
    assert parse_rule_card_json('{"cards":["a.md"]}') == ["a.md"]
    assert parse_learning_recall("        → second-brain/x.md") == ["second-brain/x.md"]

    print("context_manifest_build self-test: OK")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Build a context-manifest YAML for PM-orchestrator worker dispatch."
    )
    parser.add_argument("task", nargs="*", help="Task text.")
    parser.add_argument("--workflow", required=False, help="Workflow name (e.g. pm-orchestrator, bug-fix).")
    parser.add_argument("--phase", required=False, help="Phase name (e.g. rca, fix, review).")
    parser.add_argument("--worktree", help="Worktree slug (overrides current marker).")
    parser.add_argument("--output", help="Write manifest to this path instead of stdout.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without running subcommands.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    task = " ".join(args.task).strip()
    if not task:
        parser.error('provide a task text')
    if not args.workflow or not args.phase:
        parser.error("--workflow and --phase are required")

    manifest = build_manifest(task, args.workflow, args.phase, worktree=args.worktree, dry_run=args.dry_run)
    yaml_text = to_yaml(manifest)

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        print(f"> write {out_path}", file=sys.stderr)
        if not args.dry_run:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(yaml_text, encoding="utf-8")
        print(f"manifest written to {out_path}", file=sys.stderr)
    else:
        print(yaml_text, end="")

    return 1 if manifest.get("warnings") else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
