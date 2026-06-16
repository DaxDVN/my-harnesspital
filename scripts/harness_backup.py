#!/usr/bin/env python3
"""Snapshot the MyHospital agent/dev-workflow harness files.

The workspace root is not a Git repository, so the harness instruction files,
hooks, scripts, and tooling docs have no version history of their own. This tool
takes a cheap, timestamped, secret-free snapshot of just those harness files so a
bad edit is always recoverable.

It is shell-agnostic (pure Python stdlib) and never touches FE/BE source,
worktrees, DB dumps, node_modules, build output, or secrets.

Usage:
    python scripts/harness_backup.py            # create a snapshot
    python scripts/harness_backup.py --list     # list existing snapshots
    python scripts/harness_backup.py --dest DIR  # custom snapshot root
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


# Harness files/dirs worth versioning. Missing entries are skipped silently.
HARNESS_INCLUDES = [
    "AGENTS.md",
    "CLAUDE.md",
    "justfile",
    ".graphifyignore",
    "graphifyignore",
    ".claude",
    ".codex",
    "scripts",
    "harness",
    "docs/harness",
    "docs/graphify-agent-guide.md",
    # Small graphify metadata kept for forensic/provenance record (not the graph itself).
    "graphify-out/.graphify_root",
    "graphify-out/.graphify_python",
    "graphify-out/manifest.json",
]

# Never copy these (secrets, caches, build output, large/binary, runtime locks).
EXCLUDE_NAMES = {
    "__pycache__",
    ".git",
    "node_modules",
    "dist",
    "build",
    "bin",
    "obj",
    ".next",
    "coverage",
    "scheduled_tasks.lock",
}
EXCLUDE_SUFFIXES = (
    ".pyc",
    ".har",
    ".log",
    ".tmp",
    ".secret",
    ".pem",
    ".key",
    ".env",
)


def workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _ignore(_dir: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name in EXCLUDE_NAMES or name.startswith(".env") or name.endswith(EXCLUDE_SUFFIXES):
            ignored.add(name)
    return ignored


def _copy_one(src: Path, dst: Path) -> tuple[int, int]:
    """Copy a file or directory tree. Returns (files_copied, bytes_copied)."""
    if src.is_dir():
        shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=True)
        files = [p for p in dst.rglob("*") if p.is_file()]
        return len(files), sum(p.stat().st_size for p in files)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return 1, src.stat().st_size


def create_snapshot(dest_root: Path) -> Path:
    root = workspace_root()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    snapshot = dest_root / stamp
    if snapshot.exists():
        raise SystemExit(f"Snapshot folder already exists: {snapshot}")
    snapshot.mkdir(parents=True)

    manifest: list[str] = [f"# harness snapshot {stamp}", f"# source root: {root}", ""]
    total_files = 0
    total_bytes = 0
    for rel in HARNESS_INCLUDES:
        src = root / rel
        if not src.exists():
            manifest.append(f"SKIP (absent)  {rel}")
            continue
        files, size = _copy_one(src, snapshot / rel)
        total_files += files
        total_bytes += size
        manifest.append(f"OK  {rel}  ({files} file(s), {size} bytes)")

    manifest.append("")
    manifest.append(f"TOTAL: {total_files} files, {total_bytes} bytes")
    (snapshot / "MANIFEST.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")

    print(f"Harness snapshot created: {snapshot}")
    print(f"  {total_files} files, {total_bytes} bytes")
    print(f"  manifest: {snapshot / 'MANIFEST.txt'}")
    print()
    print("This snapshot excludes secrets, DB dumps, node_modules, build output, and worktrees.")
    return snapshot


def list_snapshots(dest_root: Path) -> None:
    if not dest_root.exists():
        print(f"No snapshots yet ({dest_root} does not exist).")
        return
    rows = sorted((p for p in dest_root.iterdir() if p.is_dir()), key=lambda p: p.name)
    if not rows:
        print(f"No snapshots in {dest_root}.")
        return
    print(f"Snapshots in {dest_root}:")
    for row in rows:
        files = sum(1 for p in row.rglob("*") if p.is_file())
        print(f"  {row.name}  ({files} files)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Snapshot MyHospital harness files.")
    parser.add_argument("--list", action="store_true", help="List existing snapshots and exit.")
    parser.add_argument("--dest", help="Snapshot root (default: <root>/.harness-backups).")
    args = parser.parse_args(argv)

    dest_root = Path(args.dest).resolve() if args.dest else workspace_root() / ".harness-backups"
    if args.list:
        list_snapshots(dest_root)
        return 0
    create_snapshot(dest_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
