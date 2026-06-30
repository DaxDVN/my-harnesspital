#!/usr/bin/env python3
"""Stand up the MyHospital harness on a fresh machine with one command.

The tracked harness is small (~4 MB). Everything heavy is *regenerated or fetched*
on the new machine, never copied: node_modules, the product repos
(myhospital-fe / myhospital-be), worktrees, DB slots, and the machine-specific
graphify / CodeGraph indexes (see .gitignore for the full excluded set). This
script brings those up idempotently — it detects what already exists and skips it,
auto-runs only the safe non-destructive installs, and prints the exact command for
anything it will not run for you (clones, worktree creation, index builds, DB
slots). It finishes by running the harness doctor so you see health on the new box.

Portability:
  * ROOT is derived from this file's location — no hardcoded home/user paths.
  * Nothing machine-specific is copied; indexes/deps are rebuilt locally.

Usage:
    python scripts/bootstrap.py            # full bootstrap (idempotent)
    python scripts/bootstrap.py --check    # prereqs + doctor only, NO mutation
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ROOT = the harness workspace root (this file lives in <root>/scripts/).
ROOT = Path(__file__).resolve().parent.parent

# Public product repos. Discovered from the live workspace remotes (2026-06-26).
# Override with MYHOSPITAL_FE_REPO_URL / MYHOSPITAL_BE_REPO_URL for a fork.
DEFAULT_FE_REPO_URL = "https://github.com/MyHospital-Vn/myhospital-fe"
DEFAULT_BE_REPO_URL = "https://github.com/MyHospital-Vn/myhospital-be"

# Required tools for a working harness (the one-command goal). Each: (name, hint).
REQUIRED_TOOLS = [
    ("git", "system package manager (pacman -S git / apt install git)"),
    ("node", "https://nodejs.org or nvm (https://github.com/nvm-sh/nvm)"),
    ("npm", "ships with Node.js (see node)"),
    ("just", "https://github.com/casey/just (cargo install just / pacman -S just)"),
]
# Recommended but not required to boot; harness_doctor reports these in depth too.
RECOMMENDED_TOOLS = [
    ("graphify", "graphify CLI (optional docs/specs design-intent tooling; lands on PATH, e.g. ~/.local/bin/graphify). See docs/graphify-agent-guide.md"),
    ("codegraph", "curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh"),
    ("docker", "needed for worktree DB slots (https://docs.docker.com/engine/install/)"),
    ("dotnet", "needed for BE build/migrations (https://dotnet.microsoft.com/download)"),
    ("rg", "ripgrep — bounded source search (pacman -S ripgrep / apt install ripgrep)"),
]

_step_no = 0
_todos: list[str] = []


def step(title: str) -> None:
    global _step_no
    _step_no += 1
    print(f"\n=== Step {_step_no}: {title} ===")


def todo(msg: str) -> None:
    _todos.append(msg)


def which(name: str) -> str | None:
    return shutil.which(name)


def run(argv: list[str], *, cwd: Path | None = None, check: bool = False) -> int:
    """Stream a child command; return its exit code (never raises by default)."""
    print(f"  $ {' '.join(argv)}")
    sys.stdout.flush()  # keep parent output ahead of the child's when piped/redirected
    try:
        proc = subprocess.run(argv, cwd=str(cwd) if cwd else None)
        return proc.returncode
    except FileNotFoundError:
        print(f"  ! command not found: {argv[0]}")
        return 127


def capture(argv: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            argv, cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        return proc.returncode, proc.stdout.strip()
    except FileNotFoundError:
        return 127, ""


# --- Steps ----------------------------------------------------------------


def step_prereqs() -> list[str]:
    """Report tool availability. Returns the list of MISSING required tools."""
    step("Prerequisite check")
    # Python is implied (we are running under it) — report which interpreter.
    print(f"  [OK ] python      {sys.executable} ({sys.version.split()[0]})")
    missing_required: list[str] = []
    for name, hint in REQUIRED_TOOLS:
        path = which(name)
        if path:
            print(f"  [OK ] {name:<11} {path}")
        else:
            print(f"  [MISS] {name:<11} REQUIRED — install: {hint}")
            missing_required.append(name)
            todo(f"Install required tool '{name}': {hint}")
    for name, hint in RECOMMENDED_TOOLS:
        path = which(name)
        if path:
            print(f"  [OK ] {name:<11} {path}")
        else:
            print(f"  [warn] {name:<11} recommended — install: {hint}")
    if missing_required:
        print(f"\n  -> {len(missing_required)} required tool(s) missing: {', '.join(missing_required)}")
    else:
        print("\n  -> all required tools present")
    return missing_required


def step_python_deps() -> None:
    step("Python dependencies")
    req = next((f for f in ("requirements.txt", "requirements-dev.txt", "pyproject.toml", "setup.py")
                if (ROOT / f).exists()), None)
    if req:
        print(f"  Found {req}.")
        print(f"  $ python -m pip install -r {req}   # (run if you maintain a project venv)")
        todo(f"Review Python deps in {req} and install into your environment.")
    else:
        print("  No requirements file — harness scripts are stdlib-only. Nothing to install.")
        print("  (worktree.py auto-creates a pymssql venv on demand for DB sync.)")


def step_npm_deps() -> None:
    step("npm dependencies (harness tooling: promptfoo / ast-grep / ctx7)")
    pkg = ROOT / "package.json"
    if not pkg.exists():
        print("  No package.json — skip.")
        return
    if (ROOT / "node_modules").exists():
        print("  node_modules/ present — skip (already installed).")
        return
    if not which("npm"):
        print("  npm not on PATH — skipping auto-install. Run later:")
        print("  $ npm install")
        todo("Run `npm install` once npm is available (installs promptfoo/ast-grep/ctx7).")
        return
    print("  node_modules/ missing — installing devDependencies.")
    code = run(["npm", "install"], cwd=ROOT)
    if code != 0:
        print(f"  ! npm install exited {code}. Re-run manually: npm install")
        todo("`npm install` failed — re-run manually to get harness tooling.")


def discover_repo_url(repo_dir: str, env_var: str, default: str) -> tuple[str | None, str]:
    """Resolve a product-repo clone URL: env override > existing remote > baked default."""
    v = os.environ.get(env_var)
    if v:
        return v, f"env:{env_var}"
    target = ROOT / repo_dir
    if target.exists():
        code, out = capture(["git", "-C", str(target), "remote", "get-url", "origin"])
        if code == 0 and out:
            return out, "existing remote"
    if default:
        return default, "baked default (verify before use)"
    return None, "unknown"


def step_product_repos() -> None:
    step("Product repos (myhospital-fe / myhospital-be)")
    repos = [
        ("myhospital-fe", "MYHOSPITAL_FE_REPO_URL", DEFAULT_FE_REPO_URL, "master"),
        ("myhospital-be", "MYHOSPITAL_BE_REPO_URL", DEFAULT_BE_REPO_URL, "main"),
    ]
    for repo_dir, env_var, default, base in repos:
        target = ROOT / repo_dir
        if target.exists():
            code, out = capture(["git", "-C", str(target), "remote", "get-url", "origin"])
            origin = out if code == 0 else "(no origin)"
            print(f"  [OK ] {repo_dir} present — skip clone. origin={origin}")
            continue
        url, src = discover_repo_url(repo_dir, env_var, default)
        if url:
            print(f"  [need] {repo_dir} absent. Clone (url via {src}; default branch {base}):")
            print(f"    $ git clone {url} {repo_dir}")
            todo(f"Clone {repo_dir}:  git clone {url} {repo_dir}")
        else:
            print(f"  [need] {repo_dir} absent and URL unknown.")
            print(f"    $ git clone TODO_OWNER_FILL_REPO_URL {repo_dir}")
            todo(f"TODO: owner fill repo URL, then: git clone <url> {repo_dir} "
                 f"(or set {env_var})")


def step_worktrees() -> None:
    step("Worktrees (owner/slot-driven — not auto-created)")
    wt = ROOT / "worktrees"
    if not wt.exists() or not any(p.is_dir() and p.name != "_db-backups" for p in wt.iterdir()):
        print("  No active worktrees (expected on a fresh clone — worktrees/ is gitignored).")
    else:
        print("  Existing worktrees:")
        run([sys.executable, "scripts/worktree.py", "list"], cwd=ROOT)
    print("  Create one when you start a task (needs the product repos + docker for the DB slot):")
    print("    $ just wt-create <slug> <slot>            # e.g. just wt-create bed 1")
    print("    $ python scripts/worktree.py create --slug <slug> --slot <slot>")
    print("    $ python scripts/worktree.py init-db-slots --slots 1   # docker SQL slot")


def step_indexes() -> None:
    step("Indexes — machine-specific, REGENERATE locally (never copied)")

    # graphify (optional docs/specs design-intent graph)
    graph = ROOT / "graphify-out" / "graph.json"
    print("  graphify (docs/specs design-intent — optional):")
    if graph.exists():
        print("    graphify-out/graph.json present. Verify trust + refresh if stale:")
    else:
        print("    No graphify-out/graph.json (gitignored). Build only if you need it:")
    print("    $ graphify check-update .                 # is a rebuild needed?")
    print("    $ graphify update .                       # AST-only refresh, no API key")
    print("    $ /graphify .                             # full semantic build in Claude Code (host LLM)")
    print("    (scope is fixed by .graphifyignore; run `python scripts/harness_doctor.py` to check trust.)")

    # CodeGraph (per-package source index; root is never indexed)
    print("  CodeGraph (per-package source index; the harness root is never indexed):")
    if which("codegraph"):
        fe_idx = (ROOT / "myhospital-fe" / ".codegraph").exists()
        be_idx = (ROOT / "myhospital-be" / ".codegraph").exists()
        repos_present = (ROOT / "myhospital-fe").exists() or (ROOT / "myhospital-be").exists()
        if not repos_present:
            print("    Clone the product repos first (Step on product repos), then:")
        elif fe_idx and be_idx:
            print("    Both indexes present. Refresh after a pull if stale:")
            print("    $ just codegraph-sync-main")
        else:
            print("    Build the per-package indexes (one-time):")
        print("    $ just codegraph-init-main                # cd myhospital-{be,fe} && codegraph init")
        print("    $ just codegraph-status                   # verify")
    else:
        print("    codegraph not on PATH — install, then `just codegraph-init-main`:")
        print("    $ curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh")
        todo("Install codegraph CLI, then run `just codegraph-init-main`.")


def step_doctor() -> int:
    step("Harness doctor (read-only health check)")
    doctor = ROOT / "scripts" / "harness_doctor.py"
    if not doctor.exists():
        print("  ! scripts/harness_doctor.py missing — cannot report health.")
        return 1
    return run([sys.executable, str(doctor)], cwd=ROOT)


def print_todos() -> None:
    print("\n=== Action items ===")
    if not _todos:
        print("  None — harness looks ready.")
        return
    for i, t in enumerate(_todos, 1):
        print(f"  {i}. {t}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stand up the MyHospital harness on a fresh machine (idempotent).")
    parser.add_argument("--check", action="store_true",
                        help="Prereqs + doctor only. No mutation (safe validation).")
    args = parser.parse_args(argv)

    print(f"MyHospital harness bootstrap — {ROOT}")
    if args.check:
        print("Mode: --check (read-only: prerequisites + doctor, no changes)")
    else:
        print("Mode: full bootstrap (idempotent; safe ops auto-run, the rest are printed)")

    step_prereqs()

    if args.check:
        step_doctor()
        print_todos()
        print("\nDone (--check): no changes were made.")
        return 0

    step_python_deps()
    step_npm_deps()
    step_product_repos()
    step_worktrees()
    step_indexes()
    step_doctor()
    print_todos()
    print("\nBootstrap pass complete. Re-run any printed command above to finish setup, "
          "then `python scripts/harness_doctor.py` to confirm.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
