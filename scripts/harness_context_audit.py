#!/usr/bin/env python3
"""Read-only context footprint audit for the MyHospital harness.

The goal is not exact tokenizer accounting. It is a stable, cheap baseline for
comparing harness optimization phases: entry docs, skill stubs, and large files
that are easy to drag into context by accident.

Usage:
    python scripts/harness_context_audit.py scan
    python scripts/harness_context_audit.py scan --json
    python scripts/harness_context_audit.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

ENTRY_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "main-brain/knowledge.md",
    "engine/rules/README.md",
    "engine/router/README.md",
    "engine/REGISTRY.md",
    "engine/rules/ponytail.md",
    ".opencode/opencode.json",
    ".claude/settings.json",
    ".codex/hooks.json",
]

CONTEXT_TRAP_MARKERS = (
    "/node_modules/",
    "/rounds/",
    "/runs/",
)

DOC_SUFFIXES = {".md", ".json", ".toml", ".yaml", ".yml"}


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace(os.sep, "/")


def word_count(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 0
    return len(text.split())


def summarize_paths(paths: list[Path]) -> tuple[list[dict[str, Any]], int]:
    rows = [{"path": rel(path), "words": word_count(path)} for path in paths if path.exists()]
    rows.sort(key=lambda item: (-int(item["words"]), str(item["path"])))
    return rows, sum(int(item["words"]) for item in rows)


def iter_docs() -> list[Path]:
    paths: list[Path] = []
    for base in ("engine", ".claude", ".codex", ".opencode"):
        root = ROOT / base
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in DOC_SUFFIXES:
                paths.append(path)
    return paths


def is_context_trap(path: Path) -> bool:
    value = "/" + rel(path)
    return any(marker in value for marker in CONTEXT_TRAP_MARKERS)


def collect() -> dict[str, Any]:
    entry_rows, entry_total = summarize_paths([ROOT / item for item in ENTRY_FILES])
    skill_rows, skill_total = summarize_paths(sorted((ROOT / "engine" / "skills").glob("*/SKILL.md")))
    docs = iter_docs()
    trap_rows, trap_total = summarize_paths([path for path in docs if is_context_trap(path)])
    active_rows, active_total = summarize_paths([path for path in docs if not is_context_trap(path)])

    return {
        "entry": {
            "total_words": entry_total,
            "files": entry_rows,
        },
        "skill_stubs": {
            "total_words": skill_total,
            "files": skill_rows,
        },
        "active_docs": {
            "total_words": active_total,
            "top_files": active_rows[:20],
        },
        "context_traps": {
            "total_words": trap_total,
            "top_files": trap_rows[:20],
            "markers": list(CONTEXT_TRAP_MARKERS),
        },
    }


def print_table(title: str, rows: list[dict[str, Any]], *, limit: int | None = None) -> None:
    print(title)
    shown = rows[:limit] if limit else rows
    for item in shown:
        print(f"  {int(item['words']):5d}  {item['path']}")
    if limit and len(rows) > limit:
        print(f"  ... {len(rows) - limit} more")


def command_scan(json_output: bool) -> int:
    data = collect()
    if json_output:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    print("Harness context audit")
    print(f"Entry footprint: {data['entry']['total_words']} words")
    print(f"Skill stubs: {data['skill_stubs']['total_words']} words")
    print(f"Active docs/configs: {data['active_docs']['total_words']} words")
    print(f"Context traps: {data['context_traps']['total_words']} words")
    print()
    print_table("Entry files", data["entry"]["files"])
    print()
    print_table("Top active docs/configs", data["active_docs"]["top_files"], limit=12)
    print()
    print_table("Top context traps", data["context_traps"]["top_files"], limit=12)
    print()
    print("Policy: load router-selected files only; never broad-dump trap paths into an agent turn.")
    return 0


def self_test() -> int:
    data = collect()
    assert data["entry"]["total_words"] > 0, "entry footprint should be non-empty"
    assert any(item["path"] == "AGENTS.md" for item in data["entry"]["files"]), "AGENTS.md missing"
    assert data["skill_stubs"]["total_words"] > 0, "skill stubs should be non-empty"
    print("harness_context_audit self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Audit MyHospital harness context footprint")
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="command")
    scan = sub.add_parser("scan")
    scan.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.command == "scan":
        return command_scan(args.json)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
