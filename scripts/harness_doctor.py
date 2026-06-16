#!/usr/bin/env python3
"""MyHospital harness doctor — read-only health check for the agent/dev harness.

Verifies the things that silently break this workspace: missing tools, invalid
hook JSON, non-compiling hooks, a stale/cross-OS graphify graph, secret leakage
into the graph, missing fish/Zellij helpers, and routing-doc drift. It changes
nothing.

Usage:
    python scripts/harness_doctor.py            # human report, always exits 0
    python scripts/harness_doctor.py --strict   # exit 1 if any check FAILED
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

OK, WARN, FAIL, INFO = "OK", "WARN", "FAIL", "INFO"
_results: list[tuple[str, str, str]] = []


def root() -> Path:
    return Path(__file__).resolve().parent.parent


def add(status: str, name: str, detail: str = "") -> None:
    _results.append((status, name, detail))


def env_with_dotnet_tools() -> dict[str, str]:
    env = os.environ.copy()
    tools_dir = Path.home() / ".dotnet" / "tools"
    if tools_dir.exists():
        current_path = env.get("PATH", "")
        paths = current_path.split(os.pathsep) if current_path else []
        tools_path = str(tools_dir)
        if tools_path not in paths:
            env["PATH"] = os.pathsep.join([current_path, tools_path]) if current_path else tools_path
    return env


def which(name: str) -> str | None:
    return shutil.which(name, path=env_with_dotnet_tools().get("PATH"))


def _run(argv: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            argv, cwd=str(root()), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout,
            env=env_with_dotnet_tools(),
        )
        return proc.returncode, proc.stdout
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def check_tools() -> None:
    required = ["python", "git"]
    recommended = ["docker", "dotnet", "npm", "just", "graphify", "zellij", "fish", "rg"]
    for tool in required:
        if which(tool):
            add(OK, f"tool:{tool}", "on PATH")
        else:
            add(FAIL, f"tool:{tool}", "REQUIRED, not on PATH")
    for tool in recommended:
        add(OK if which(tool) else WARN, f"tool:{tool}",
            "on PATH" if which(tool) else "recommended, not on PATH")

    x_path = which("x")
    add(OK if x_path else WARN, "tool:x", "ServiceStack DTO CLI on PATH" if x_path else "needed for npm run dtos:update")
    code, out = _run(["dotnet", "ef", "--version"], timeout=10)
    add(OK if code == 0 else WARN, "tool:dotnet-ef", out.strip() if code == 0 else "needed for worktree.py sync-db")


def check_root_versioning() -> None:
    r = root()
    if (r / ".git").exists():
        add(OK, "root-vcs", "root is a git repo (harness is version-controlled)")
    else:
        add(WARN, "root-vcs", "root is NOT a git repo — harness has no version history. "
                              "Use `git init` (see docs) or `just harness-backup`.")
    backups = r / ".harness-backups"
    if backups.exists():
        n = sum(1 for p in backups.iterdir() if p.is_dir())
        add(INFO, "harness-backups", f"{n} snapshot(s) in .harness-backups/")
    else:
        add(INFO, "harness-backups", "no snapshots yet (run `just harness-backup`)")


def check_json() -> None:
    for rel in [".claude/settings.json", ".claude/settings.local.json", ".codex/hooks.json"]:
        p = root() / rel
        if not p.exists():
            add(INFO, f"json:{rel}", "absent")
            continue
        try:
            json.loads(p.read_text(encoding="utf-8"))
            add(OK, f"json:{rel}", "valid")
        except Exception as exc:  # noqa: BLE001
            add(FAIL, f"json:{rel}", f"INVALID: {exc}")


def check_pycompile() -> None:
    targets = sorted((root() / ".claude/hooks").glob("*.py")) + sorted((root() / "scripts").glob("*.py"))
    bad = []
    for p in targets:
        code, out = _run([sys.executable, "-m", "py_compile", str(p)])
        if code != 0:
            bad.append(p.name)
    if bad:
        add(FAIL, "py-compile", f"failed: {', '.join(bad)}")
    else:
        add(OK, "py-compile", f"{len(targets)} hook/script file(s) compile")


def check_guard_selftest() -> None:
    guard = root() / ".claude/hooks/myhospital_guard.py"
    if not guard.exists():
        add(FAIL, "guard", "myhospital_guard.py missing")
        return
    code, out = _run([sys.executable, str(guard), "--self-test"])
    add(OK if code == 0 else FAIL, "guard-selftest", out.strip().splitlines()[-1] if out.strip() else f"exit {code}")


def check_worktree_cli() -> None:
    code, _ = _run([sys.executable, "scripts/worktree.py", "--help"])
    add(OK if code == 0 else FAIL, "worktree-cli:help", f"exit {code}")
    code, out = _run([sys.executable, "scripts/worktree.py", "list"])
    add(OK if code == 0 else FAIL, "worktree-cli:list", out.strip() or f"exit {code}")


def check_graphify_trust() -> None:
    out = root() / "graphify-out"
    graph = out / "graph.json"
    if not graph.exists():
        add(INFO, "graphify", "no graph.json (nothing to trust/verify)")
        return
    marker = out / ".graphify_root"
    recorded = marker.read_text(encoding="utf-8", errors="ignore").strip() if marker.exists() else ""
    if not recorded:
        add(WARN, "graphify-trust", "graph.json present but build root unknown — treat as unverified")
    elif "\\" in recorded or (len(recorded) >= 2 and recorded[1] == ":") or recorded.replace("\\", "/").rstrip("/").lower() != str(root()).rstrip("/").lower():
        add(WARN, "graphify-trust", f"STALE/cross-machine: built for {recorded!r}, not {root()}. Rebuild on Linux before trusting graph paths.")
    else:
        add(OK, "graphify-trust", "graph built for this workspace")


def check_graph_secrets() -> None:
    graph = root() / "graphify-out" / "graph.json"
    if graph.exists():
        try:
            text = graph.read_text(encoding="utf-8", errors="ignore").lower()
        except Exception:  # noqa: BLE001
            text = ""
        hits = [k for k in ("session-auth", "cookie", "bearer", ".har") if k in text]
        if hits:
            add(WARN, "graph-secrets", f"graph.json contains {hits} — rebuild after the .graphifyignore fix to purge")
        else:
            add(OK, "graph-secrets", "no obvious auth/cookie/har leakage in graph.json")
    ignore = root() / ".graphifyignore"
    if ignore.exists():
        body = ignore.read_text(encoding="utf-8", errors="ignore")
        needed = ["*.har", "session-auth.json", "scripts/legacy-powershell/"]
        missing = [n for n in needed if n not in body]
        add(OK if not missing else WARN, "graphify-ignore",
            "excludes secrets/legacy" if not missing else f"missing patterns: {missing}")


def check_helpers_and_layouts() -> None:
    fish_helper = root() / "scripts/fish/myhospital-zellij.fish"
    if not fish_helper.exists():
        add(FAIL, "fish-helpers", "scripts/fish/myhospital-zellij.fish missing")
    elif shutil.which("fish"):
        code, out = _run(["fish", "-n", str(fish_helper)])
        add(OK if code == 0 else FAIL, "fish-helpers", "parses" if code == 0 else f"parse error: {out.strip()}")
    else:
        add(INFO, "fish-helpers", "present (fish not installed to parse-check)")
    for name in ["myhospital-orch.kdl", "myhospital-impl.kdl"]:
        p = root() / "scripts/zellij" / name
        add(OK if p.exists() else WARN, f"layout:{name}", "present" if p.exists() else "missing repo template")


def check_just() -> None:
    if not shutil.which("just"):
        add(WARN, "just", "not installed")
        return
    code, out = _run(["just", "--list"])
    add(OK if code == 0 else FAIL, "just", "recipes load" if code == 0 else out.strip())


def check_routing() -> None:
    be_conv = root() / "myhospital-be" / "CONVENTIONS.md"
    add(OK if be_conv.exists() else FAIL, "routing:be", "myhospital-be/CONVENTIONS.md exists"
        if be_conv.exists() else "myhospital-be/CONVENTIONS.md MISSING")
    fe_claude = root() / "myhospital-fe" / "CLAUDE.md"
    add(OK if fe_claude.exists() else WARN, "routing:fe", "myhospital-fe/CLAUDE.md exists"
        if fe_claude.exists() else "myhospital-fe/CLAUDE.md missing")
    # CLAUDE.md must not route BE work to a nonexistent myhospital-be/CLAUDE.md.
    claude = root() / "CLAUDE.md"
    if claude.exists():
        body = claude.read_text(encoding="utf-8", errors="ignore")
        if "obey `myhospital-be/CLAUDE.md`" in body or "obey myhospital-be/CLAUDE.md" in body:
            add(FAIL, "routing:claude-md", "CLAUDE.md still routes BE to missing myhospital-be/CLAUDE.md")
        else:
            add(OK, "routing:claude-md", "BE routing points at CONVENTIONS.md")


def check_legacy_isolation() -> None:
    legacy = root() / "scripts" / "legacy-powershell"
    if legacy.exists():
        add(INFO, "legacy-powershell", "archive present (excluded from graph/audit)")
    # No active .ps1 invocation in justfile/worktree tooling.
    hits = []
    for rel in ["justfile", "scripts/worktree.py", "scripts/harness_backup.py"]:
        p = root() / rel
        if p.exists() and ".ps1" in p.read_text(encoding="utf-8", errors="ignore"):
            hits.append(rel)
    add(OK if not hits else WARN, "legacy-active-refs",
        "no active .ps1 runtime refs" if not hits else f".ps1 referenced in {hits}")


def check_codegraph() -> None:
    """CodeGraph = the source-code knowledge graph (per code repo; root is NOT indexed)."""
    r = root()
    # Binary + version.
    if shutil.which("codegraph"):
        code, out = _run(["codegraph", "--version"], timeout=20)
        ver = out.strip().splitlines()[-1] if out.strip() else f"exit {code}"
        add(OK if code == 0 else WARN, "codegraph:bin",
            f"on PATH ({ver})" if code == 0 else f"on PATH but --version failed: {ver}")
    else:
        add(WARN, "codegraph:bin", "not on PATH — source-code graph unavailable. "
            "Install: curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh")

    # Per-repo indexes. The workspace root must NOT be indexed (root .gitignore excludes FE/BE/worktrees).
    for repo in ("myhospital-be", "myhospital-fe"):
        if (r / repo).exists():
            idx = r / repo / ".codegraph"
            add(OK if idx.exists() else INFO, f"codegraph-index:{repo}",
                "indexed (.codegraph/ present)" if idx.exists() else "no index yet — run `just codegraph-init-main`")
    if (r / ".codegraph").exists():
        add(WARN, "codegraph-root", ".codegraph/ at workspace ROOT — root should not be indexed "
            "(root .gitignore excludes FE/BE/worktrees). Run `codegraph uninit` here.")

    # Discovery policy wired into the harness.
    policy = r / "engine/rules/source-discovery.md"
    add(OK if policy.exists() else WARN, "codegraph-policy",
        "engine/rules/source-discovery.md present" if policy.exists() else "source-discovery.md MISSING")
    for name in ("AGENTS.md", "CLAUDE.md"):
        p = r / name
        if p.exists():
            body = p.read_text(encoding="utf-8", errors="ignore")
            ok = "CodeGraph" in body and "source-discovery.md" in body
            add(OK if ok else WARN, f"codegraph-doc:{name}",
                "references CodeGraph + source-discovery.md" if ok else "missing CodeGraph/source-discovery reference")

    # Anti-pattern: harness must not tell agents to broad-scan with rg as the primary code finder.
    agents = r / "AGENTS.md"
    if agents.exists():
        body = agents.read_text(encoding="utf-8", errors="ignore")
        bad = "Search existing code first with `rg`" in body
        add(WARN if bad else OK, "codegraph-antipattern",
            "AGENTS.md still leads code discovery with rg — should lead with CodeGraph" if bad
            else "no rg-first broad-scan instruction in AGENTS.md")

    # Best-effort: is the CodeGraph MCP server wired into any installed agent's config?
    home = Path.home()
    candidates = [
        home / ".claude.json",
        home / ".codex" / "config.toml",
        home / ".config" / "opencode" / "opencode.jsonc",
        home / ".config" / "opencode" / "opencode.json",
        home / ".config" / "opencode" / "config.json",
    ]
    wired = []
    for c in candidates:
        try:
            if c.exists() and "codegraph" in c.read_text(encoding="utf-8", errors="ignore").lower():
                wired.append(c.name)
        except Exception:  # noqa: BLE001
            pass
    add(OK if wired else INFO, "codegraph-mcp",
        f"MCP wired in: {', '.join(wired)}" if wired
        else "MCP not detected in agent configs — run `codegraph install` (or `just codegraph-install`)")


def check_convention_scan() -> None:
    """mh_scan — the deterministic convention scanner pack (audit bug-classes)."""
    sc = root() / "scripts" / "mh_scan" / "scanners.py"
    if not sc.exists():
        add(WARN, "mh-scan", "scripts/mh_scan/ missing (deterministic convention floor)")
        return
    code, out = _run([sys.executable, "scripts/mh_scan", "--self-test"])
    add(OK if code == 0 else FAIL, "mh-scan:selftest",
        out.strip().splitlines()[-1] if out.strip() else f"exit {code}")


def check_convention_truth() -> None:
    """Canon = engine/rules (authoritative). convention_truth --strict FAILs only if a CANON doc
    drifts from code; the stale project myhospital-be/CONVENTIONS.md is advisory (INFO, canon
    supersedes — decision 2026-06-16), so it never demands a project edit."""
    ct = root() / "scripts" / "convention_truth.py"
    if not ct.exists():
        add(INFO, "convention-truth", "scripts/convention_truth.py absent")
        return
    code, out = _run([sys.executable, "scripts/convention_truth.py", "--strict"])
    summary = next((l for l in out.splitlines() if l.startswith("Summary:")), f"exit {code}")
    add(OK if code == 0 else WARN, "convention-truth",
        "canon=engine/rules authoritative; project CONVENTIONS.md superseded (advisory only)" if code == 0
        else f"CANON doc drift — {summary.strip()} → fix the engine/rules canon (run: python scripts/convention_truth.py)")


def check_opencode_guard() -> None:
    """The opencode guard plugin must be symlinked in to enforce cross-tool (Claude/Codex already wired)."""
    plugin = root() / "scripts" / "opencode" / "myhospital-guard.js"
    if not plugin.exists():
        add(INFO, "opencode-guard", "scripts/opencode/myhospital-guard.js absent")
        return
    dest = Path.home() / ".config" / "opencode" / "plugin"
    installed = False
    if dest.exists():
        for p in dest.iterdir():
            try:
                if "myhospital-guard" in p.name or (p.is_symlink() and "myhospital-guard" in os.readlink(p)):
                    installed = True
                    break
            except Exception:  # noqa: BLE001
                pass
    add(OK if installed else INFO, "opencode-guard",
        "installed in ~/.config/opencode/plugin/" if installed
        else "present but NOT installed — symlink into ~/.config/opencode/plugin/ (see cross-tool-enforcement.md)")


def check_brains() -> None:
    """Self-learning tiers: main-brain (gated SoT), second-brain (open buffer), /promote skill."""
    r = root()
    mb = r / "main-brain"
    if mb.exists() and (mb / "README.md").exists() and (mb / "knowledge.md").exists():
        add(OK, "main-brain", "present (gated source of truth)")
    elif mb.exists():
        add(WARN, "main-brain", "main-brain/ present but README.md/knowledge.md incomplete")
    else:
        add(WARN, "main-brain", "main-brain/ missing (gated source-of-truth tier)")
    sb = r / "second-brain"
    if sb.exists() and (sb / "README.md").exists():
        add(OK, "second-brain", "present (open learning buffer)")
    elif sb.exists():
        add(WARN, "second-brain", "second-brain/ present but README.md missing")
    else:
        add(WARN, "second-brain", "second-brain/ missing (learning buffer tier)")
    promote = r / ".claude" / "skills" / "promote" / "SKILL.md"
    add(OK if promote.exists() else WARN, "promote-skill",
        "/promote present (owner-gated)" if promote.exists() else "/promote skill missing")


def check_symlinks() -> None:
    """Tool dirs must POINT into engine/ (canonical), not hold copies. Catches a broken/forgotten link."""
    r = root()
    for name in ("skills", "agents", "hooks", "workflows"):
        link = r / ".claude" / name
        target = r / "engine" / name
        if not link.exists() and not link.is_symlink():
            add(WARN, f"link:.claude/{name}", f"missing — should be a symlink → engine/{name}")
        elif not link.is_symlink():
            add(WARN, f"link:.claude/{name}", "real dir, not a symlink (assets should be canonical in engine/)")
        elif not target.exists():
            add(FAIL, f"link:.claude/{name}", f"dangling — engine/{name} missing")
        else:
            add(OK, f"link:.claude/{name}", f"→ engine/{name}")


def main() -> int:
    strict = "--strict" in sys.argv[1:]
    print(f"MyHospital harness doctor — {root()}\n")
    for fn in (
        check_tools, check_root_versioning, check_json, check_pycompile,
        check_guard_selftest, check_worktree_cli, check_graphify_trust,
        check_graph_secrets, check_helpers_and_layouts, check_just,
        check_routing, check_legacy_isolation, check_codegraph,
        check_convention_scan, check_convention_truth, check_opencode_guard,
        check_brains, check_symlinks,
    ):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            add(WARN, fn.__name__, f"check crashed: {exc}")

    width = max((len(n) for _, n, _ in _results), default=0)
    counts = {OK: 0, WARN: 0, FAIL: 0, INFO: 0}
    for status, name, detail in _results:
        counts[status] = counts.get(status, 0) + 1
        print(f"  [{status:4}] {name.ljust(width)}  {detail}")
    print(f"\nSummary: {counts[OK]} OK, {counts[WARN]} WARN, {counts[FAIL]} FAIL, {counts[INFO]} INFO")
    if counts[FAIL]:
        print("Action: resolve FAIL items above.")
    return 1 if (strict and counts[FAIL]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
