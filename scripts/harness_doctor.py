#!/usr/bin/env python3
"""MyHospital harness doctor — read-only health check for the agent/dev harness.

Verifies the things that silently break this workspace: missing tools, invalid
hook JSON, non-compiling hooks, a stale/cross-OS graphify graph, secret leakage
into the graph, and routing-doc drift. It changes nothing.

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


def _run(argv: list[str], timeout: int = 30, input_text: str | None = None) -> tuple[int, str]:
    try:
        stdin_args = {"input": input_text} if input_text is not None else {"stdin": subprocess.DEVNULL}
        proc = subprocess.run(
            argv, cwd=str(root()),
            **stdin_args,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout,
            env=env_with_dotnet_tools(),
        )
        return proc.returncode, proc.stdout
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def check_tools() -> None:
    required = ["python", "git"]
    recommended = ["docker", "dotnet", "npm", "just", "graphify", "rg"]
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


def check_guard_wired() -> None:
    """Efficacy (not just existence): the guard must be WIRED as a PreToolUse hook — a guard that exists
    but is not wired protects nothing (the self-test passing says nothing about it being active)."""
    settings = root() / ".claude" / "settings.json"
    if not settings.exists():
        add(WARN, "guard-wired", ".claude/settings.json absent — guard not wired as a hook")
        return
    body = settings.read_text(encoding="utf-8", errors="ignore")
    if "myhospital_guard" in body and "PreToolUse" in body:
        add(OK, "guard-wired", "guard wired as a PreToolUse hook in settings.json")
    else:
        add(WARN, "guard-wired", "myhospital_guard NOT wired as PreToolUse in settings.json — the guard is INACTIVE")


def check_codegraph_freshness() -> None:
    """Efficacy: CodeGraph staleness is otherwise invisible — agents are told 'CodeGraph first', so a stale
    index hands back wrong callers/blast-radius that look authoritative. WARN when an index is older than
    the repo's last commit (e.g. after a pull without reindex)."""
    r = root()
    for repo in ("myhospital-be", "myhospital-fe"):
        if not (r / repo / ".codegraph").exists():
            continue  # check_codegraph already reports the missing index
        _, out = _run(["bash", "-lc", f"find {repo}/.codegraph -type f -printf '%T@\\n' 2>/dev/null | sort -rn | head -1"])
        try:
            idx_mtime = float(out.strip())
        except ValueError:
            add(WARN, f"codegraph-fresh:{repo}", ".codegraph present but unreadable mtime")
            continue
        code, cout = _run(["git", "-C", str(r / repo), "log", "-1", "--format=%ct", "HEAD"])
        commit = cout.strip()
        if code != 0 or not commit.isdigit():
            add(INFO, f"codegraph-fresh:{repo}", "cannot read last-commit time (freshness skipped)")
        elif int(commit) > idx_mtime + 60:
            mins = int((int(commit) - idx_mtime) / 60)
            add(WARN, f"codegraph-fresh:{repo}", f"index OLDER than last commit (~{mins}min stale) — rebuild: just codegraph-sync-main")
        else:
            add(OK, f"codegraph-fresh:{repo}", "index newer than last commit (fresh)")


def check_removed_legacy_workflows() -> None:
    """Deprecated autonomous workflow runtimes should stay removed from active harness paths."""
    stale = []
    for rel in (
        "engine/workflows/progressive-test",
        "engine/workflows/super-test",
        "engine/skills/agentflow",
        "engine/skills/super-test",
        "engine/agents/mh-batch-rca.md",
    ):
        if (root() / rel).exists():
            stale.append(rel)
    add(OK if not stale else WARN, "legacy-workflows-removed",
        "progressive-test/super-test runtime removed; robust-test is the replacement"
        if not stale else "stale deprecated runtime paths still present: " + ", ".join(stale))


def check_workflow_shared() -> None:
    """engine/workflows/_shared/ primitives — the gate/envelope/state code workflows depend on. Self-test each."""
    shared = root() / "engine" / "workflows" / "_shared"
    if not shared.exists():
        add(INFO, "workflow-shared", "engine/workflows/_shared/ absent (no shared workflow primitives)")
        return
    schema = shared / "envelope.schema.json"
    if schema.exists():
        try:
            json.loads(schema.read_text(encoding="utf-8"))
            add(OK, "workflow-shared:schema", "envelope.schema.json valid JSON")
        except Exception as exc:  # noqa: BLE001
            add(FAIL, "workflow-shared:schema", f"envelope.schema.json INVALID: {exc}")
    else:
        add(WARN, "workflow-shared:schema", "envelope.schema.json missing")
    runtime_boundary = shared / "runtime-boundary.md"
    add(OK if runtime_boundary.exists() else WARN, "workflow-shared:runtime-boundary",
        "runtime-boundary.md present" if runtime_boundary.exists() else "runtime-boundary.md missing")
    for name in ("validate-envelope", "gate-check", "module-state", "allowlist-check", "run-init"):
        p = shared / f"{name}.py"
        if not p.exists():
            add(WARN, f"workflow-shared:{name}", "missing")
            continue
        code, out = _run([sys.executable, str(p), "--self-test"])
        add(OK if code == 0 else FAIL, f"workflow-shared:{name}",
            out.strip().splitlines()[-1] if out.strip() else f"exit {code}")


def check_learning() -> None:
    """Self-learning intake (H13): the capture/check/list scripts must self-test green; second-brain present."""
    for name in ("learning_capture", "learning_check", "learning_list", "learning_recall"):
        p = root() / "scripts" / f"{name}.py"
        if not p.exists():
            add(WARN, f"learning:{name}", "missing (self-learning MVP)")
            continue
        code, out = _run([sys.executable, str(p), "--self-test"])
        add(OK if code == 0 else FAIL, f"learning:{name}",
            out.strip().splitlines()[-1] if out.strip() else f"exit {code}")
    th = root() / "engine" / "hooks" / "learning_trigger.py"
    if th.exists():
        code, out = _run([sys.executable, str(th), "--self-test"])
        add(OK if code == 0 else FAIL, "learning:trigger-hook",
            out.strip().splitlines()[-1] if out.strip() else f"exit {code}")
        st = root() / ".claude" / "settings.json"
        body = st.read_text(encoding="utf-8", errors="ignore") if st.exists() else ""
        wired = "learning_trigger" in body and "UserPromptSubmit" in body
        add(OK if wired else WARN, "learning:trigger-wired",
            "UserPromptSubmit → learning_trigger (auto-capture nudge)" if wired
            else "learning_trigger NOT wired as UserPromptSubmit in settings.json")
    else:
        add(WARN, "learning:trigger-hook", "engine/hooks/learning_trigger.py missing (auto-capture nudge)")
    sb = root() / "second-brain"
    add(OK if sb.exists() else WARN, "learning:second-brain",
        "second-brain/ present (provisional intake buffer)" if sb.exists() else "second-brain/ missing")
    idx = sb / "INDEX.md"
    if sb.exists() and idx.exists():
        body = idx.read_text(encoding="utf-8", errors="ignore")
        candidates = list(sb.glob("*.md")) + list((sb / "grouped").glob("[0-9][0-9]-*.md"))
        live = [p for p in candidates if p.name not in ("INDEX.md", "README.md")
                and "status: provisional" in p.read_text(encoding="utf-8", errors="ignore")[:400]]
        missing = []
        for p in live:
            rel = p.relative_to(sb).as_posix()
            if rel not in body and p.name not in body:
                missing.append(rel)
        add(OK if not missing else WARN, "learning:map",
            f"INDEX.md maps all {len(live)} live note(s)" if not missing
            else f"INDEX.md stale — missing {missing}; run: python scripts/learning_recall.py --rebuild-map")
        if live and th.exists():
            code, out = _run(
                [sys.executable, str(th)],
                input_text='{"prompt":"fix frontend form bug"}',
            )
            ok = code == 0 and "[learning-recall]" in out
            add(OK if ok else FAIL, "learning:trigger-recall",
                "work prompt emits recall nudge" if ok else "work prompt did not emit recall nudge")


def check_maturity() -> None:
    """Workflow maturity (H12): every workflow manifest should declare a maturity; summarize them."""
    wf = root() / "engine" / "workflows"
    levels: dict[str, str] = {}
    missing: list[str] = []
    for m in sorted(wf.glob("*/manifest.json")):
        try:
            d = json.loads(m.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if d.get("lifecycle_status") == "DEPRECATED":
            continue
        (levels.__setitem__(m.parent.name, d["maturity"]) if d.get("maturity") else missing.append(m.parent.name))
    if missing:
        add(WARN, "maturity", f"workflow(s) with no maturity field: {', '.join(missing)}")
    else:
        add(OK, "maturity", f"{len(levels)} workflows declare maturity ("
            + ", ".join(f"{k}={v}" for k, v in sorted(levels.items())) + ")")
    # H2-07: surface UNPROVEN-e2e workflows separately so a green dashboard doesn't imply they're proven.
    proven = {"smoke-tested", "real-run-proven", "production-default"}
    unproven = sorted(k for k, v in levels.items() if v not in proven)
    if unproven:
        add(INFO, "maturity:unproven",
            f"{len(unproven)} UNPROVEN e2e (scaffolded — owner-invoke only, first real run = gate): {', '.join(unproven)}")


def check_codex_guard_wiring() -> None:
    """H4: the Codex guard must resolve via WALK-UP (works from a worktree cwd), not a bare relative .claude path."""
    h = root() / ".codex" / "hooks.json"
    if not h.exists():
        add(INFO, "codex-guard-wiring", ".codex/hooks.json absent")
        return
    body = h.read_text(encoding="utf-8", errors="ignore")
    if "engine/hooks/myhospital_guard.py" in body and ("dirname" in body or "while" in body):
        add(OK, "codex-guard-wiring", "walk-up to engine/hooks/myhospital_guard.py (fires from a worktree cwd)")
    elif ".claude/hooks/myhospital_guard.py" in body:
        add(WARN, "codex-guard-wiring", "relative .claude path — guard fails OPEN from a worktree cwd")
    else:
        add(WARN, "codex-guard-wiring", "guard not clearly wired in .codex/hooks.json")


def check_router() -> None:
    """P1 router dry-run: present, documented, and self-test green. The router is advisory only."""
    readme = root() / "engine" / "router" / "README.md"
    script = root() / "scripts" / "harness_router.py"
    add(OK if readme.exists() else WARN, "router:readme",
        "engine/router/README.md present" if readme.exists() else "engine/router/README.md missing")
    if not script.exists():
        add(WARN, "router:selftest", "scripts/harness_router.py missing")
        return
    code, out = _run([sys.executable, str(script), "--self-test"])
    add(OK if code == 0 else FAIL, "router:selftest",
        out.strip().splitlines()[-1] if out.strip() else f"exit {code}")
    for label, rel in (
        ("preflight:selftest", "scripts/harness_preflight.py"),
        ("codex-preflight:selftest", "scripts/codex_preflight.py"),
    ):
        p = root() / rel
        if not p.exists():
            add(WARN, label, f"{rel} missing")
            continue
        code, out = _run([sys.executable, str(p), "--self-test"])
        add(OK if code == 0 else FAIL, label,
            out.strip().splitlines()[-1] if out.strip() else f"exit {code}")


def check_rule_cards() -> None:
    """Compact FE/BE rule cards keep daily tasks from loading full convention docs by default."""
    script = root() / "scripts" / "rule_card.py"
    if not script.exists():
        add(WARN, "rule-card:selftest", "scripts/rule_card.py missing")
        return
    code, out = _run([sys.executable, str(script), "--self-test"])
    add(OK if code == 0 else FAIL, "rule-card:selftest",
        out.strip().splitlines()[-1] if out.strip() else f"exit {code}")


def check_eval_ledger() -> None:
    """P4 eval/cost ledger: lightweight evidence for lifecycle promotion and future cost comparison."""
    readme = root() / "docs" / "harness" / "evals" / "README.md"
    template = root() / "docs" / "harness" / "evals" / "_TEMPLATE.yaml"
    script = root() / "scripts" / "harness_eval.py"
    add(OK if readme.exists() else WARN, "eval-ledger:readme",
        "docs/harness/evals/README.md present" if readme.exists() else "docs/harness/evals/README.md missing")
    add(OK if template.exists() else WARN, "eval-ledger:template",
        "docs/harness/evals/_TEMPLATE.yaml present" if template.exists() else "docs/harness/evals/_TEMPLATE.yaml missing")
    if not script.exists():
        add(WARN, "eval-ledger:selftest", "scripts/harness_eval.py missing")
        return
    code, out = _run([sys.executable, str(script), "--self-test"])
    add(OK if code == 0 else WARN, "eval-ledger:selftest",
        out.strip().splitlines()[-1] if out.strip() else f"exit {code}")
    code, out = _run([sys.executable, str(script), "scan"])
    summary = out.strip().splitlines()[-1] if out.strip() else f"exit {code}"
    add(OK if code == 0 else WARN, "eval-ledger:scan", summary)


def check_workflow_governance() -> None:
    """P5 workflow taxonomy/deprecation governance: safe consolidation requires evidence and replacements."""
    policy = root() / "engine" / "workflows" / "LIFECYCLE.md"
    script = root() / "scripts" / "harness_workflow_governance.py"
    add(OK if policy.exists() else WARN, "workflow-governance:policy",
        "engine/workflows/LIFECYCLE.md present" if policy.exists() else "engine/workflows/LIFECYCLE.md missing")
    if not script.exists():
        add(WARN, "workflow-governance:selftest", "scripts/harness_workflow_governance.py missing")
        return
    code, out = _run([sys.executable, str(script), "--self-test"])
    add(OK if code == 0 else WARN, "workflow-governance:selftest",
        out.strip().splitlines()[-1] if out.strip() else f"exit {code}")
    code, out = _run([sys.executable, str(script), "scan"])
    summary = out.strip().splitlines()[-1] if out.strip() else f"exit {code}"
    add(OK if code == 0 else WARN, "workflow-governance:scan", summary)


def check_runtime_contract() -> None:
    """P7 runtime contract scanner: catches prompt-only boundary drift in workflow manifests."""
    script = root() / "scripts" / "harness_runtime_contract.py"
    if not script.exists():
        add(WARN, "runtime-contract:selftest", "scripts/harness_runtime_contract.py missing")
        return
    code, out = _run([sys.executable, str(script), "--self-test"])
    add(OK if code == 0 else WARN, "runtime-contract:selftest",
        out.strip().splitlines()[-1] if out.strip() else f"exit {code}")
    code, out = _run([sys.executable, str(script), "scan"])
    summary = out.strip().splitlines()[-1] if out.strip() else f"exit {code}"
    add(OK if code == 0 else WARN, "runtime-contract:scan", summary)


def check_registry() -> None:
    """engine/REGISTRY.md + per-workflow manifest.json: every referenced agent/skill/rule must resolve to a pool file."""
    r = root(); eng = r / "engine"
    has_reg = (eng / "REGISTRY.md").exists()
    add(OK if has_reg else WARN, "registry",
        "engine/REGISTRY.md present" if has_reg else "engine/REGISTRY.md missing (inventory index)")
    wf = eng / "workflows"
    manifests = sorted(wf.glob("*/manifest.json")) if wf.exists() else []
    if not manifests:
        add(INFO, "registry:manifests", "no engine/workflows/*/manifest.json yet")
        return
    bad: list[str] = []
    governance: list[str] = []
    lifecycle_levels: dict[str, str] = {}
    allowed_kinds = {"workflow", "internal", "advisory"}
    allowed_lifecycle = {"DRAFT", "LAB", "PROVEN", "DEFAULT", "DEPRECATED"}
    for m in manifests:
        try:
            d = json.loads(m.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            bad.append(f"{m.parent.name}: invalid JSON ({exc})"); continue
        for field in ("name", "entry_skill", "agents", "rules"):
            if field not in d: bad.append(f"{m.parent.name}: missing '{field}'")
        for field in ("kind", "public_entry", "auto_route_allowed", "lifecycle_status", "recommended_prompt_file", "budget", "eval_summary"):
            if field not in d:
                governance.append(f"{m.parent.name}: missing '{field}'")
        kind = d.get("kind")
        if kind is not None and kind not in allowed_kinds:
            governance.append(f"{m.parent.name}: unknown kind '{kind}' (expected workflow|internal|advisory)")
        lifecycle = d.get("lifecycle_status")
        if lifecycle:
            lifecycle_levels[m.parent.name] = str(lifecycle)
        if lifecycle is not None and lifecycle not in allowed_lifecycle:
            governance.append(f"{m.parent.name}: unknown lifecycle_status '{lifecycle}'")
        if d.get("auto_route_allowed") is True and lifecycle in {"DRAFT", "LAB"}:
            governance.append(f"{m.parent.name}: auto_route_allowed=true but lifecycle_status={lifecycle}")
        if d.get("public_entry") is True and not d.get("entry_skill"):
            governance.append(f"{m.parent.name}: public_entry=true but entry_skill missing")
        budget = d.get("budget")
        if "budget" in d and not isinstance(budget, dict):
            governance.append(f"{m.parent.name}: budget is not an object")
        eval_summary = d.get("eval_summary")
        if "eval_summary" in d and not isinstance(eval_summary, dict):
            governance.append(f"{m.parent.name}: eval_summary is not an object")
        artifact = eval_summary.get("artifact_path") if isinstance(eval_summary, dict) else ""
        if lifecycle in {"PROVEN", "DEFAULT"} and not artifact:
            governance.append(f"{m.parent.name}: lifecycle_status={lifecycle} but eval_summary.artifact_path is empty")
        if lifecycle in {"PROVEN", "DEFAULT"} and artifact:
            artifact_path = r / artifact
            if not artifact_path.exists():
                governance.append(f"{m.parent.name}: eval_summary.artifact_path does not exist: {artifact}")
            else:
                code, out = _run([sys.executable, "scripts/harness_eval.py", "validate", str(artifact_path)])
                if code != 0:
                    detail = next((line for line in out.splitlines() if line.startswith("FAIL")), f"exit {code}")
                    governance.append(f"{m.parent.name}: eval artifact invalid ({detail})")
        if lifecycle == "DEFAULT" and d.get("auto_route_allowed") is not True:
            governance.append(f"{m.parent.name}: lifecycle_status=DEFAULT but auto_route_allowed is not true")
        prompt_file = d.get("recommended_prompt_file")
        if "recommended_prompt_file" in d:
            if not isinstance(prompt_file, str):
                governance.append(f"{m.parent.name}: recommended_prompt_file is not a string")
            elif prompt_file and not (r / prompt_file).exists():
                governance.append(f"{m.parent.name}: recommended_prompt_file does not exist: {prompt_file}")
        es = d.get("entry_skill")
        if es and not (eng / "skills" / es / "SKILL.md").exists(): bad.append(f"{m.parent.name}: entry_skill '{es}' not in engine/skills/")
        for a in (d.get("agents") or []):
            if not (eng / "agents" / f"{a}.md").exists(): bad.append(f"{m.parent.name}: agent '{a}' not in engine/agents/")
        for ru in (d.get("rules") or []):
            if not (eng / "rules" / f"{ru}.md").exists(): bad.append(f"{m.parent.name}: rule '{ru}' not in engine/rules/")
    add(FAIL if bad else OK, "registry:manifests",
        "; ".join(bad[:6]) if bad else f"{len(manifests)} workflow manifest(s); all entry_skill/agent/rule refs resolve")
    add(WARN if governance else OK, "registry:manifest-governance",
        "; ".join(governance[:8]) if governance else "lifecycle/public/auto-route/prompt metadata present")
    if lifecycle_levels:
        add(OK, "registry:lifecycle",
            ", ".join(f"{k}={v}" for k, v in sorted(lifecycle_levels.items())))


def main() -> int:
    strict = "--strict" in sys.argv[1:]
    print(f"MyHospital harness doctor — {root()}\n")
    for fn in (
        check_tools, check_root_versioning, check_json, check_pycompile,
        check_guard_selftest, check_guard_wired, check_worktree_cli, check_graphify_trust,
        check_graph_secrets, check_just,
        check_routing, check_legacy_isolation, check_codegraph, check_codegraph_freshness,
        check_convention_scan, check_convention_truth, check_opencode_guard,
        check_brains, check_symlinks, check_workflow_shared, check_removed_legacy_workflows,
        check_learning, check_maturity, check_codex_guard_wiring, check_router, check_rule_cards,
        check_eval_ledger, check_workflow_governance, check_runtime_contract, check_registry,
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
