#!/usr/bin/env python3
"""migrate_harness.py — one-time harness migration packager.

Packs the MyHospital agent/dev harness workspace into a portable tarball for a
one-time move to a freshly-installed machine (e.g. a new CachyOS PC) WITHOUT
pushing confidential content (specs / DB / code) to any git remote. Move the
output by USB or direct rsync/scp, then restore on the target.

It captures the WORKING TREE (tracked **and** untracked harness edits) plus the
gitignored `specs/`, because a plain `git clone` would drop the untracked
harness dirs (`.agents/`, `.opencode/`, `.codex/config.toml`, new
`harness/rules/*`, `scripts/opencode/`, `skills-lock.json`).

It does NOT pack (handle these separately on the target):
  - myhospital-fe / myhospital-be  -> re-clone from GitHub
  - _db-backups                    -> recreate via worktree.py sync-db (or --include-db)
  - graphify-out                   -> rebuild on Linux (current build is stale/Windows)
  - node_modules / build output / caches / secrets

Subcommands:
    python scripts/migrate_harness.py plan            # dry-run: what is included + sizes
    python scripts/migrate_harness.py pack            # build tarballs + MANIFEST
    python scripts/migrate_harness.py pack --include-db
    python scripts/migrate_harness.py fixup --old-root A --new-root B   # on target only
    python scripts/migrate_harness.py verify          # on target: run harness_doctor
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Top-level entries NOT shipped in the workspace tarball (re-clone / regenerate / local).
EXCLUDE_DIRS = [
    "myhospital-fe",            # re-clone from GitHub
    "myhospital-be",            # re-clone from GitHub
    "worktrees",                # recreate via worktree.py
    "graphify-out",             # rebuild on Linux (current build is stale Windows)
    ".harness-backups",         # local-only backups
    ".linux-migration-backups", # local-only backups
]
# _db-backups is excluded by default, added back with --include-db.
DB_DIR = "_db-backups"

# Patterns dropped anywhere in the tree (secrets, caches, build output).
EXCLUDE_GLOBS = [
    "node_modules", "dist", "build", "bin", "obj", ".next", "coverage",
    "__pycache__", "*.pyc",
    "*.log", "*.tmp", "*.har", "*-auth.json", "session-auth.json",
    "*.cookies.json", ".env", ".env.*", "*.secret", "*.pem", "*.key",
]


def root() -> Path:
    return Path(__file__).resolve().parent.parent


def _which(name: str) -> str | None:
    return shutil.which(name)


def _run(argv: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(argv, text=True, **kw)


def _git_head(repo: Path) -> str:
    try:
        p = _run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        head = p.stdout.strip()
        b = _run(["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return f"{b.stdout.strip()}@{head}" if head else "(no commits)"
    except Exception:
        return "(not a git repo)"


def _du(path: Path) -> str:
    if not path.exists():
        return "-"
    p = _run(["du", "-sh", str(path)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return p.stdout.split("\t")[0].strip() if p.stdout else "?"


def _tar_tool() -> tuple[str, str]:
    """Return (compress_flag, suffix). Prefer zstd, fall back to gzip."""
    if _which("zstd"):
        return "--zstd", "tar.zst"
    return "-z", "tar.gz"


def _exclude_args(include_db: bool) -> list[str]:
    args: list[str] = []
    for d in EXCLUDE_DIRS:
        args += [f"--exclude=./{d}"]
    if not include_db:
        args += [f"--exclude=./{DB_DIR}"]
    for g in EXCLUDE_GLOBS:
        args += [f"--exclude={g}"]
    return args


def _claude_home() -> Path:
    return Path(os.path.expanduser("~/.claude"))


def _project_slug() -> str:
    # Claude Code stores per-project state under ~/.claude/projects/<slug>
    # where slug is the absolute repo path with '/' replaced by '-'.
    return str(root()).replace("/", "-")


def cmd_plan(_args) -> int:
    r = root()
    print(f"Source workspace : {r}")
    print(f"Root harness git : {_git_head(r)}")
    print()
    print("INCLUDED in workspace tarball (top-level):")
    for entry in sorted(p.name for p in r.iterdir()):
        path = r / entry
        if entry in EXCLUDE_DIRS or (entry == DB_DIR and not getattr(_args, "include_db", False)):
            continue
        print(f"  + {entry:<26} {_du(path)}")
    print()
    print("EXCLUDED (re-clone / regenerate / local):")
    for entry in EXCLUDE_DIRS + ([] if getattr(_args, "include_db", False) else [DB_DIR]):
        path = r / entry
        print(f"  - {entry:<26} {_du(path)}  (excluded)")
    print()
    print("~/.claude essentials that travel:")
    for item in ["CLAUDE.md", "settings.json", "skills", f"projects/{_project_slug()}/memory"]:
        path = _claude_home() / item
        print(f"  + ~/.claude/{item:<40} {_du(path)}")
    print()
    print("Code repos to RE-CLONE on target:")
    print(f"  myhospital-fe  {_git_head(r / 'myhospital-fe')}")
    print(f"  myhospital-be  {_git_head(r / 'myhospital-be')}")
    return 0


def cmd_pack(args) -> int:
    r = root()
    if not _which("tar"):
        print("ERROR: tar not found", file=sys.stderr)
        return 2
    stamp = _dt.date.today().isoformat()
    out_dir = Path(args.out).expanduser() if args.out else Path(
        os.path.expanduser(f"~/harness-migration-{stamp}"))
    out_dir.mkdir(parents=True, exist_ok=True)

    cflag, suffix = _tar_tool()
    ws_tar = out_dir / f"harness-workspace.{suffix}"
    ch_tar = out_dir / "claude-home.tar.gz"

    # 1) workspace working tree (tracked + untracked + specs), with excludes
    print(f"[1/3] packing workspace -> {ws_tar}")
    tar_argv = ["tar", "-C", str(r), "-c", cflag, "-f", str(ws_tar),
                "--totals", *_exclude_args(args.include_db), "."]
    rc = _run(tar_argv).returncode
    if rc != 0:
        print("ERROR: workspace tar failed", file=sys.stderr)
        return rc

    # 2) ~/.claude essentials (skip caches/plugins/credentials)
    print(f"[2/3] packing ~/.claude essentials -> {ch_tar}")
    ch = _claude_home()
    members = [m for m in ["CLAUDE.md", "settings.json", "skills",
                           f"projects/{_project_slug()}/memory"]
               if (ch / m).exists()]
    if members:
        _run(["tar", "-C", str(ch), "-czf", str(ch_tar), *members])
    else:
        print("  (nothing found under ~/.claude to pack)")

    # 3) manifest + restore runbook
    print(f"[3/3] writing MANIFEST")
    manifest = out_dir / "MANIFEST.txt"
    manifest.write_text(_manifest_text(r, ws_tar.name, ch_tar.name, args.include_db, stamp))

    print()
    print("DONE. Move this whole folder to the target by USB or rsync:")
    print(f"  {out_dir}")
    print(f"    {ws_tar.name}   ({_du(ws_tar)})")
    if ch_tar.exists():
        print(f"    {ch_tar.name}   ({_du(ch_tar)})")
    print(f"    MANIFEST.txt")
    print()
    print("Direct transfer over LAN/SSH (no cloud), e.g.:")
    print(f"  rsync -avh --progress {out_dir}/ dax@<target>:~/harness-migration-{stamp}/")
    return 0


def _manifest_text(r: Path, ws_name: str, ch_name: str, include_db: bool, stamp: str) -> str:
    return f"""\
MyHospital harness migration bundle
===================================
created      : {stamp}
source root  : {r}
root git     : {_git_head(r)}
fe git       : {_git_head(r / 'myhospital-fe')}
be git       : {_git_head(r / 'myhospital-be')}
db included  : {include_db}

CONTENTS
  {ws_name}   workspace working tree (harness tracked+untracked + specs/),
              excludes code repos, graphify-out, backups, caches, secrets{'' if include_db else ', _db-backups'}
  {ch_name}   ~/.claude essentials: CLAUDE.md, settings.json, skills/, project memory

RESTORE ON TARGET (fresh CachyOS) — confidential content stays off all remotes
------------------------------------------------------------------------------
0. Install tools (CachyOS / Arch):
     sudo pacman -S --needed git python just ripgrep fd bat ripgrep-all zellij \\
                            nodejs npm rsync zstd
     # dotnet SDK for BE, plus claude-code / opencode / codex / codegraph per their installers

1. Recreate the workspace path (keep username 'dax' + same path => zero fixup):
     mkdir -p {r}
     tar -C {r} -xf <bundle>/{ws_name}

2. Restore ~/.claude essentials:
     tar -C ~/.claude -xzf <bundle>/{ch_name}
     claude   # then /login to re-auth (credentials are NOT in the bundle)

3. Re-clone code repos (authorized GitHub remotes):
     git clone https://github.com/MyHospital-Vn/myhospital-fe {r}/myhospital-fe   # checkout master
     git clone https://github.com/MyHospital-Vn/myhospital-be {r}/myhospital-be   # checkout main
     cd {r}/myhospital-fe && npm ci

4. Regenerate the rest:
     # DB: python scripts/worktree.py sync-db  (or copy _db-backups if office has no DB)
     # graphify-out: rebuild on Linux via the /graphify skill (old build was stale Windows)

5. If the target user/home differ from this source path, rewrite hardcoded paths:
     python scripts/migrate_harness.py fixup --old-root {r} --new-root /home/<you>/path/roast

6. Verify:
     python scripts/migrate_harness.py verify   # == python scripts/harness_doctor.py
     just doctor
"""


# Files that hardcode the absolute workspace path (from grep of tracked tree).
FIXUP_FILES = [
    "AGENTS.md",
    ".claude/settings.local.json",
    "harness/rules/worktree-workflow.md",
    "docs/graphify-agent-guide.md",
    "scripts/fish/myhospital-zellij.fish",
    "scripts/README.md",
    "scripts/WORKTREE-TOOLING.md",
]


def cmd_fixup(args) -> int:
    r = root()
    old, new = args.old_root.rstrip("/"), args.new_root.rstrip("/")
    if old == new:
        print("old-root == new-root, nothing to do")
        return 0
    changed = 0
    for rel in FIXUP_FILES:
        f = r / rel
        if not f.exists():
            print(f"  skip (missing): {rel}")
            continue
        text = f.read_text(encoding="utf-8", errors="surrogateescape")
        if old in text:
            f.write_text(text.replace(old, new), encoding="utf-8", errors="surrogateescape")
            n = text.count(old)
            changed += n
            print(f"  fixed {n:>2} in {rel}")
        else:
            print(f"  none in {rel}")
    print(f"done: {changed} path(s) rewritten {old} -> {new}")
    print("note: also check ~/.claude/settings.json and ~/.local/bin/graphify by hand")
    return 0


def cmd_verify(_args) -> int:
    doctor = root() / "scripts" / "harness_doctor.py"
    if not doctor.exists():
        print("harness_doctor.py not found", file=sys.stderr)
        return 2
    return _run([sys.executable, str(doctor)]).returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="One-time harness migration packager")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="dry-run: show what would be packed")
    p_plan.add_argument("--include-db", action="store_true", help="include _db-backups")
    p_plan.set_defaults(func=cmd_plan)

    p_pack = sub.add_parser("pack", help="build tarballs + MANIFEST")
    p_pack.add_argument("--include-db", action="store_true", help="include _db-backups (412M)")
    p_pack.add_argument("--out", help="output dir (default ~/harness-migration-<date>)")
    p_pack.set_defaults(func=cmd_pack)

    p_fix = sub.add_parser("fixup", help="rewrite hardcoded workspace path (target machine)")
    p_fix.add_argument("--old-root", required=True)
    p_fix.add_argument("--new-root", required=True)
    p_fix.set_defaults(func=cmd_fixup)

    p_ver = sub.add_parser("verify", help="run harness_doctor on the target")
    p_ver.set_defaults(func=cmd_verify)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
