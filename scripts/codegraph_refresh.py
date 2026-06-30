#!/usr/bin/env python3
"""Check CodeGraph index age vs last commit; re-index if stale.

Per engine/rules/source-discovery.md. The CodeGraph index lives per-repo under
.codegraph/. This script compares the index mtime against the last git commit
timestamp and, if stale (older than --max-age-hours OR last commit newer than
the index), runs `codegraph init` to re-index. Stdlib only.

Usage:
    python scripts/codegraph_refresh.py --repo <be|fe|worktree-path> [--max-age-hours 24] [--dry-run] [--self-test]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ToolError(RuntimeError):
    pass


def resolve_repo(spec: str) -> Path:
    if spec in {"be", "backend"}:
        return ROOT / "myhospital-be"
    if spec in {"fe", "frontend"}:
        return ROOT / "myhospital-fe"
    p = Path(spec)
    if not p.is_absolute():
        p = (ROOT / spec)
    p = p.resolve()
    if not p.exists():
        raise ToolError(f"Repo path not found: {p}")
    return p


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def is_git_repo(repo: Path) -> bool:
    return (repo / ".git").exists() or (repo / ".git").is_file()


def last_commit_time(repo: Path) -> float:
    proc = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%ct"],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise ToolError(f"Not a git repo or no commits: {repo}")
    try:
        return float(proc.stdout.strip())
    except ValueError:
        raise ToolError(f"Cannot parse last commit time for {repo}")


def index_mtime(repo: Path) -> float | None:
    cg = repo / ".codegraph"
    if not cg.exists():
        return None
    mtimes = [f.stat().st_mtime for f in cg.rglob("*") if f.is_file()]
    if not mtimes:
        return cg.stat().st_mtime
    return max(mtimes)


def is_stale(idx_t: float, commit_t: float, now: float, max_age_hours: float) -> tuple[bool, str]:
    idx_age = now - idx_t
    if idx_age > max_age_hours * 3600:
        return True, f"index age {fmt_age(idx_age)} exceeds {max_age_hours}h"
    if commit_t > idx_t:
        return True, "last commit is newer than the index"
    return False, f"index age {fmt_age(idx_age)} within {max_age_hours}h"


def fmt_age(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h{m}m"


def fmt_time(t: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))


def refresh(args: argparse.Namespace) -> int:
    repo = resolve_repo(args.repo)
    print(f"Repo: {rel(repo)}")
    if not is_git_repo(repo):
        raise ToolError(f"Not a git repo: {repo}")
    if shutil.which("codegraph") is None:
        raise ToolError("'codegraph' CLI not found on PATH. Install it first.")
    idx_t = index_mtime(repo)
    if idx_t is None:
        print(".codegraph/ not found. Suggested: cd <repo> && codegraph init")
        return 1
    commit_t = last_commit_time(repo)
    now = time.time()
    stale, reason = is_stale(idx_t, commit_t, now, args.max_age_hours)
    print(f"Index age:  {fmt_age(now - idx_t)}")
    print(f"Index mtime: {fmt_time(idx_t)}")
    print(f"Last commit: {fmt_time(commit_t)}")
    print(f"Stale: {'yes' if stale else 'no'} — {reason}")
    if not stale:
        print("Index is current; no refresh needed.")
        return 0
    if args.dry_run:
        print("[dry-run] would run: codegraph init (in repo)")
        return 0
    print("Re-indexing...")
    proc = subprocess.run(["codegraph", "init"], cwd=str(repo))
    if proc.returncode != 0:
        print(f"codegraph init failed (exit {proc.returncode})", file=sys.stderr)
        return proc.returncode
    print("Refreshed: yes")
    return 0


def self_test() -> int:
    # stale by age
    s, _ = is_stale(idx_t=0.0, commit_t=0.0, now=100000.0, max_age_hours=24)
    assert s is True
    # stale by commit newer than index
    s, _ = is_stale(idx_t=1000.0, commit_t=2000.0, now=2000.0, max_age_hours=24)
    assert s is True
    # fresh
    s, _ = is_stale(idx_t=1000.0, commit_t=500.0, now=1000.0, max_age_hours=24)
    assert s is False
    assert fmt_age(3661) == "1h1m"
    assert fmt_age(-5) == "0h0m"
    # resolve_repo maps short names
    assert resolve_repo("be") == (ROOT / "myhospital-be")
    assert resolve_repo("fe") == (ROOT / "myhospital-fe")
    print("codegraph_refresh self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Check CodeGraph index age vs last commit; re-index if stale",
    )
    parser.add_argument("--repo", help="be | fe | worktree-path (e.g. worktrees/slug/be)")
    parser.add_argument("--max-age-hours", type=float, default=24.0,
                        help="max acceptable index age in hours (default 24)")
    parser.add_argument("--dry-run", action="store_true", help="print plan, do not re-index")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.repo:
        parser.error("provide --repo")
    try:
        return refresh(args)
    except ToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
