#!/usr/bin/env python3
"""Claude PreToolUse guard for MyHospital — a cooperative tripwire, NOT a sandbox.

Reads a Claude hook JSON event on stdin and blocks a small set of clearly
dangerous tool patterns (exit 2 = block, stderr shown to Claude). It is
deliberately **fail-open**: malformed input or any internal error returns exit 0
(allow), so a guard bug can never wedge a session.

What it blocks
--------------
Bash (per command segment, after shlex tokenization so `git -C <path> push`,
`A=b git commit`, and `cmd1 && rm -rf x` are all caught):
  - git history mutation: commit, push, reset --hard, checkout discard (`--`/`-f`),
    clean -f
  - recursive rm (rm -r / -rf / -fr / --recursive)
  - new dependency installs: npm/pnpm/yarn/bun install|add <pkg>, dotnet add package
It does NOT block killing/restarting dev servers (kill/pkill/dotnet/npm run) —
implementers need that.

Write/Edit/MultiEdit:
  - editing generated FE artifacts or BE migrations — blocked in the MAIN repos
    AND inside `worktrees/<slug>/(fe|be)/...` (unambiguous, ~zero false positives)
  - heuristic FE/BE convention patterns — MAIN repos only (which are off-limits
    anyway), so legitimate worktree edits are never falsely blocked
  - while a PM-orchestrator run is active (.claude/.pm-run-active marker), the
    blind coordinator is also blocked from editing ANY product source (main repos
    + worktrees) — it must dispatch a worker. The owner opens `.direct-mode` to
    override. Closes the write-side drift door (the read/diff/browser sides are
    already enforced).

Run `python myhospital_guard.py --self-test` to validate the rules.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
import tempfile
from pathlib import Path
from typing import Any

# Path fragments. FE/BE match the main repo OR a worktree copy.
FE = r"(?:myhospital-fe|worktrees/[^/]+/fe)"
BE = r"(?:myhospital-be|worktrees/[^/]+/be)"
FE_MAIN = r"myhospital-fe"
BE_MAIN = r"myhospital-be"
WT_FE = r"worktrees/[^/]+/fe"
WT_BE = r"worktrees/[^/]+/be"

_DEP_CMDS = {"npm", "pnpm", "yarn", "bun"}
_DEP_SUBS = {"install", "i", "add"}

# main-brain = owner-gated source of truth. Agents may NOT write it; only the owner-invoked
# /promote skill, after the owner authorizes with `! touch main-brain/.promote-unlock`. The guard
# does not see the owner's own shell, so only the owner can create the unlock marker.
MAIN_BRAIN = r"(?:^|/)main-brain/"
_MB_WRITERS = {"mv", "cp", "tee", "dd", "truncate", "touch", "ln", "install", "rm"}


def _main_brain_unlocked() -> bool:
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return os.path.exists(os.path.join(root, "main-brain", ".promote-unlock"))


# --- Blind-PM boundary -------------------------------------------------------
# The main interactive session IS the pm-orchestrator: a BLIND coordinator that
# routes PATHs, never content (AGENTS.md §0). It must not read source/diff/worker
# output or drive the browser itself — it dispatches a worker. This is enforced
# ONLY for the main session (the hook payload's `agent_id` is empty); Claude
# subagents (mh-reviewer/mh-rca/Explore/robust-test) carry a non-null `agent_id`
# and read freely, and external agent_exec workers (grok/agy/opencode) run as
# separate processes that never reach this hook at all. The owner opens an
# explicit direct-work window (AGENTS.md §3) with a `.direct-mode` marker at the
# repo root (same pattern as main-brain/.promote-unlock) or MH_DIRECT=1.
SRC_TREE = r"(?:myhospital-fe|myhospital-be|worktrees/[^/]+/(?:fe|be))(?:/|$)"
WORKER_OUT = r"(?:^|/)docs/audit/"
_DIFF_PATH_SAFE = ("--stat", "--name-only", "--name-status", "--numstat", "--shortstat")


def _direct_mode() -> bool:
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return os.path.exists(os.path.join(root, ".direct-mode")) or os.environ.get("MH_DIRECT") == "1"


def _pm_run_active() -> bool:
    """True while a pm-orchestrator run is in progress (marker created by scripts/pm_run.py)."""
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return os.path.exists(os.path.join(root, ".claude", ".pm-run-active"))


def _is_subagent(event: dict[str, Any]) -> bool:
    return bool(event.get("agent_id") or event.get("agent_type"))


def blind_pm_rule(event: dict[str, Any], tool_lower: str, tool_input: dict[str, Any]) -> str | None:
    # Only the blind PM (main session) is constrained; subagents/workers are exempt.
    if _is_subagent(event) or _direct_mode():
        return None
    if tool_lower.startswith("mcp__agent-browser__"):
        return "blind-PM-no-browser (dispatch a smoke/robust-test worker; PM must not drive the browser)"
    # Write-side drift door: while a PM run is active, the blind coordinator must NOT edit
    # product source itself — it dispatches a worker (mh-implementer/mh-fix). The owner can
    # still open a direct-work window with .direct-mode (checked above) to override.
    if tool_lower in {"write", "edit", "multiedit"} and _pm_run_active():
        target = _norm(_file_path(tool_input))
        if target and _imatch(target, SRC_TREE):
            return ("blind-PM-no-source-write (dispatch a worker; PM must not edit product "
                    "source while a run is active — use .direct-mode to override)")
    if tool_lower in {"read", "grep", "glob"}:
        target = _norm(tool_input.get("file_path") or tool_input.get("path") or "")
        if target and (_imatch(target, SRC_TREE) or _imatch(target, WORKER_OUT)):
            return "blind-PM-no-source-read (dispatch a worker; PM receives PATHs, not content)"
    if tool_lower == "bash":
        for seg in _segments(str(tool_input.get("command") or "")):
            toks = _tokens(seg)
            if _cmd0(toks) != "git":
                continue
            sub, rest = _git_sub(toks)
            content_dump = sub in ("diff", "show") or (sub == "log" and "-p" in rest)
            if content_dump and not any(a in _DIFF_PATH_SAFE for a in rest):
                return "blind-PM-no-source-diff (dispatch a worker to read the diff; --stat/--name-only OK)"
    return None


def deny(rule: str) -> None:
    print(f"BLOCKED_RULE: {rule}", file=sys.stderr)
    raise SystemExit(2)


def _norm(value: object) -> str:
    return "" if value is None else str(value).replace("\\", "/")


def _imatch(text: str, pattern: str) -> bool:
    return bool(text and re.search(pattern, text, re.IGNORECASE))


def _segments(command: str) -> list[str]:
    parts = re.split(r"&&|\|\||[;\n|]", command)
    return [p.strip() for p in parts if p.strip()]


def _tokens(segment: str) -> list[str]:
    try:
        toks = shlex.split(segment)
    except ValueError:
        toks = segment.split()
    i = 0
    while i < len(toks) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[i]):
        i += 1  # strip leading VAR=value env assignments
    return toks[i:]


def _cmd0(toks: list[str]) -> str:
    return os.path.basename(toks[0]) if toks else ""


def _git_sub(toks: list[str]) -> tuple[str, list[str]]:
    """Subcommand + rest, after skipping git global options (-C path, -c kv, …)."""
    i = 1
    while i < len(toks):
        t = toks[i]
        if t in ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"):
            i += 2
            continue
        if t.startswith("-"):
            i += 1
            continue
        break
    return (toks[i] if i < len(toks) else ""), toks[i + 1:]


def bash_rule(command: str) -> str | None:
    for seg in _segments(command):
        toks = _tokens(seg)
        if not toks:
            continue
        name = _cmd0(toks)
        if not _main_brain_unlocked():
            seg_norm = seg.replace("\\", "/")
            if ((name in _MB_WRITERS and any("main-brain/" in t.replace("\\", "/") for t in toks[1:]))
                    or re.search(r">>?\s*\S*main-brain/", seg_norm)
                    or (name == "sed" and "-i" in toks and any("main-brain/" in t for t in toks))):
                return "main-brain-protected (source of truth — owner-gated; use /promote)"
        if name == "git":
            sub, rest = _git_sub(toks)
            # git commit is owner-gated by behavior (AGENTS.md §4): allowed only when the
            # owner explicitly asks; never self-initiated. Not hook-blocked. push stays blocked.
            if sub == "push":
                return f"git-history-operation (git {sub})"
            if sub == "reset" and "--hard" in rest:
                return "git-history-operation (git reset --hard)"
            if sub == "checkout" and ("--" in rest or "-f" in rest or "--force" in rest):
                return "git-history-operation (git checkout discard)"
            if sub == "clean" and any(a.startswith("-") and "f" in a for a in rest):
                return "git-history-operation (git clean -f)"
        elif name == "rm":
            for a in toks[1:]:
                if a == "--recursive" or (a.startswith("-") and not a.startswith("--") and "r" in a.lower()):
                    return "destructive-delete (recursive rm)"
        elif name == "find":
            if "-delete" in toks:
                return "destructive-delete (find -delete)"
        elif name == "rimraf" or (name == "npx" and "rimraf" in toks[1:]):
            return "destructive-delete (rimraf)"
        elif name == "xargs":
            if "rm" in toks[1:] and any(
                a == "--recursive" or (a.startswith("-") and not a.startswith("--") and "r" in a.lower())
                for a in toks
            ):
                return "destructive-delete (xargs rm -r)"
        elif name in ("pip", "pip3", "pipx"):
            if "install" in toks and "-r" not in toks and "--requirement" not in toks:
                after = toks[toks.index("install") + 1:]
                if any(not a.startswith("-") for a in after):
                    return "dependency-change (pip install)"
        elif name in _DEP_CMDS:
            if len(toks) >= 3 and toks[1] in _DEP_SUBS and any(not a.startswith("-") for a in toks[2:]):
                return "dependency-change (new package)"
        elif name == "dotnet":
            if len(toks) >= 3 and toks[1] == "add" and "package" in toks[2:]:
                return "dependency-change (dotnet add package)"
    if _imatch(command, r"Remove-Item\b.*-Recurse"):
        return "destructive-delete (Remove-Item -Recurse)"
    return None


def edit_text(tool_input: dict[str, Any]) -> str:
    parts: list[str] = []
    for name in ("content", "new_string"):
        value = tool_input.get(name)
        if value is not None:
            parts.append(str(value))
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict) and edit.get("new_string") is not None:
                parts.append(str(edit["new_string"]))
    return "\n".join(parts)


def edit_rule(file_path: str, text: str) -> str | None:
    # main-brain = owner-gated source of truth — only /promote (owner-authorized) writes here.
    if _imatch(file_path, MAIN_BRAIN) and not _main_brain_unlocked():
        return "main-brain-protected (source of truth — owner-gated; use /promote)"
    # Structural blocks — main repos AND worktrees.
    if _imatch(file_path, rf"{FE}/src/lib/(dtos|server)/(generated-dtos|generated-api-client|Constants)\.ts$"):
        return "generated-fe-file (regenerate, do not hand-edit)"
    if _imatch(file_path, rf"{BE}/MyHospital\.ServiceInterface/Migrations/.*\.cs$"):
        return "migration-hand-edit (change the model + add a migration)"
    # Heuristic convention blocks — MAIN repos only (off-limits anyway).
    if _imatch(file_path, rf"{FE_MAIN}/src/.*\.(ts|tsx)$") and _imatch(
        text,
        r"\bfetch\s*\(|from\s+['\"]axios['\"]|\baxios\.|Authorization\s*:\s*['\"]Bearer|['\"]use client['\"]|from\s+['\"](zustand|jotai|redux|mobx|react-icons|react-modal)['\"]",
    ):
        return "fe-forbidden-pattern (main repo)"
    if _imatch(file_path, rf"{BE_MAIN}/.*\.cs$") and _imatch(
        text,
        r"BeginTransactionAsync|IDbContextTransaction|IProcessLockService|Db\.Remove\s*\(|\.SaveChangesAsync\s*\(|throw\s+new\s+Exception|return\s+null\s*;|AllowAnonymous|JObject|Dictionary\s*<\s*string\s*,\s*object\s*>|dynamic\s+",
    ):
        return "be-forbidden-pattern (main repo)"
    return None


def _parse(event: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Extract (tool_lower, tool_input) tolerantly across agent tools.
    Claude: {tool_name, tool_input:{...}}. Others: {tool|name, params|arguments|input:{...}}."""
    tool = str(event.get("tool_name") or event.get("tool") or event.get("name") or "")
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        for alt in ("params", "arguments", "input"):
            cand = event.get(alt)
            if isinstance(cand, dict):
                tool_input = cand
                break
    if not isinstance(tool_input, dict):
        tool_input = {}
    return tool.lower(), tool_input


def _file_path(tool_input: dict[str, Any]) -> str:
    for name in ("file_path", "path"):
        if tool_input.get(name) is not None:
            return _norm(tool_input[name])
    return ""


def evaluate(event: dict[str, Any]) -> str | None:
    tool_lower, tool_input = _parse(event)
    blind = blind_pm_rule(event, tool_lower, tool_input)
    if blind:
        return blind
    command = tool_input.get("command") or event.get("command") or ""
    if tool_lower == "bash" or (not tool_lower and command):
        return bash_rule(str(command))
    if tool_lower in {"write", "edit", "multiedit"}:
        return edit_rule(_file_path(tool_input), edit_text(tool_input))
    return None


# --- Advisory (WARN, NEVER blocks) -----------------------------------------
# Shift-left nudge for edits INSIDE a worktree, where real dev happens (the
# block-level convention heuristics above are main-repo-only, so they never fire
# there). Maps to BE-audit bug-classes (velvet/notes/...-2026-06-15.md, V-ids).
# Advisory only: printed to stderr, exit 0 — must never wedge a session.
def advise_edit(file_path: str, text: str) -> str | None:
    if _imatch(file_path, rf"{WT_BE}/.*\.cs$"):
        hits: list[str] = []
        if _imatch(text, r"throw\s+new\s+Exception\b"):
            hits.append("raw Exception -> BusinessException+ErrorCodes (V12)")
        if _imatch(text, r'new\s+BusinessException\(\s*"'):
            hits.append("string-literal error code -> ErrorCodes.* (V3)")
        if _imatch(text, r"BeginTransactionAsync|TransactionScope"):
            hits.append("new DB transaction -> no-transaction rule, legacy-only (V6)")
        if _imatch(text, r"\bParse(String|Boolean|Numeric)Equality\b|\bParseContains\b|\bParseInOperator\b"):
            hits.append("legacy listing parse -> [FilterField]+ParseAllFilters (V4)")
        if _imatch(text, r"Dictionary\s*<\s*string\s*,\s*object"):
            hits.append("Dictionary<string,object> at contract -> typed DTO (V13)")
        if hits:
            return "BE convention (worktree): " + "; ".join(hits)
    if _imatch(file_path, rf"{WT_FE}/.*\.(ts|tsx)$"):
        hits: list[str] = []
        if _imatch(text, r"from\s+['\"]@/lib/dtos/dtos['\"]"):
            hits.append("dead import '@/lib/dtos/dtos' -> '@/lib/dtos/generated-dtos' (build-breaking, FE-V1)")
        if _imatch(text, r"\bfetch\s*\(|from\s+['\"]axios['\"]|\baxios\."):
            hits.append("network in UI -> RQ adapter + useMasterData (FE-V2)")
        if _imatch(text, r"from\s+['\"](zustand|jotai|redux|mobx|react-icons|react-modal)['\"]"):
            hits.append("banned lib -> approved stack only (no new global-state/icon/modal libs)")
        if hits:
            return "FE convention (worktree): " + "; ".join(hits)
    return None


def evaluate_advisory(event: dict[str, Any]) -> str | None:
    tool_lower, tool_input = _parse(event)
    if tool_lower in {"write", "edit", "multiedit"}:
        return advise_edit(_file_path(tool_input), edit_text(tool_input))
    return None


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
def _self_test() -> int:
    def bash(cmd: str) -> dict[str, Any]:
        return {"tool_name": "Bash", "tool_input": {"command": cmd}}

    def edit(path: str, new: str = "") -> dict[str, Any]:
        return {"tool_name": "Edit", "tool_input": {"file_path": path, "new_string": new}}

    def read(path: str) -> dict[str, Any]:
        return {"tool_name": "Read", "tool_input": {"file_path": path}}

    def grep(path: str) -> dict[str, Any]:
        return {"tool_name": "Grep", "tool_input": {"pattern": "x", "path": path}}

    def mcpb(name: str) -> dict[str, Any]:
        return {"tool_name": f"mcp__agent-browser__{name}", "tool_input": {}}

    def sub(ev: dict[str, Any]) -> dict[str, Any]:
        return {**ev, "agent_id": "sa_123", "agent_type": "mh-reviewer"}

    blocked = [
        bash("git push"),
        bash("git -C myhospital-fe push origin master"),
        bash("git reset --hard HEAD"),
        bash("git clean -fdx"),
        bash("FOO=bar git push origin main"),
        bash("git checkout -- file.ts"),
        bash("rm -rf /tmp/x"),
        bash("rm -fr build"),
        bash("echo hi; rm -r node_modules"),
        bash("npm install lodash"),
        bash("yarn add react-modal"),
        bash("dotnet add package Newtonsoft.Json"),
        bash("find . -name '*.tmp' -delete"),
        bash("ls build | xargs rm -rf"),
        bash("npx rimraf dist"),
        bash("rimraf node_modules"),
        bash("pip install requests"),
        bash("pipx install black"),
        edit("worktrees/bed/fe/src/lib/dtos/generated-dtos.ts", "x"),
        edit("myhospital-be/MyHospital.ServiceInterface/Migrations/2026_X.cs", "x"),
        edit("worktrees/bed/be/MyHospital.ServiceInterface/Migrations/Y.cs", "x"),
        edit("myhospital-fe/src/components/X.tsx", "const r = await fetch('/api')"),
        edit("myhospital-be/Services/XService.cs", "return null;"),
        edit("main-brain/knowledge.md", "promoted truth"),
        bash("cp note.md main-brain/knowledge.md"),
        bash("touch main-brain/.promote-unlock"),
        bash("echo hi > main-brain/knowledge.md"),
        # blind-PM boundary — main session (no agent_id) must not read source / diff / browser
        read("worktrees/bed/fe/src/modules/bed-management/pages/rooms/room-list-page.tsx"),
        read("myhospital-be/Services/RoomService.cs"),
        grep("worktrees/bed/fe/src/modules/bed-management"),
        read("docs/audit/2026-06-29/grok-rooms-refactor.md"),
        mcpb("agent_browser_open"),
        mcpb("agent_browser_snapshot"),
        bash("git -C worktrees/bed/fe diff src/modules/bed-management/x.tsx"),
        bash("git show HEAD -- worktrees/bed/be/Services/RoomService.cs"),
    ]
    allowed = [
        bash("cd x && git commit -m 'y'"),              # commit owner-gated by behavior, not hook-blocked
        # blind-PM boundary — exemptions: subagent reads, marker/path-list reads
        sub(read("worktrees/bed/fe/src/modules/bed-management/pages/rooms/room-list-page.tsx")),
        sub(grep("worktrees/bed/fe/src")),
        sub(mcpb("agent_browser_open")),
        read("engine/rules/frontend/quick.md"),       # rules are not source — PM may read
        read("AGENTS.md"),                              # harness docs — PM may read
        grep("engine/workflows"),                       # ledger/engine — PM may read
        bash("git diff --stat worktrees/bed/fe"),      # path list only — PM may see paths
        bash("git -C worktrees/bed/fe diff --name-only"),
        bash("git status --short"),
        bash("git -C myhospital-be status --short"),
        bash("git add -A"),
        bash("git pull origin main"),
        bash("git worktree remove --force worktrees/bed/fe"),
        bash("git branch -D feature/bed"),
        bash("git checkout main"),
        bash("npm install"),
        bash("npm install --no-audit --fund=false"),
        bash("npm run dev"),
        bash("pkill -f 'dotnet run'"),
        bash("kill 12345"),
        bash("rm file.txt"),
        bash("rm -f stale.log"),
        bash("pip install -r requirements.txt"),
        bash("find . -name '*.ts'"),
        bash("ls | xargs grep foo"),
        bash("dotnet build"),
        bash("python scripts/worktree.py list"),
        edit("worktrees/bed/be/Services/XService.cs", "return null;"),  # heuristic main-only
        edit("worktrees/bed/fe/src/components/X.tsx", "await fetch('/api')"),  # heuristic main-only
        edit("docs/notes.md", "anything"),
        edit("scripts/foo.py", "import os"),
        bash("cat main-brain/knowledge.md"),  # read main-brain is fine
        bash("rg foo main-brain/"),  # read main-brain is fine
        edit("second-brain/learning-x.md", "free-form learning"),  # second-brain is OPEN
    ]
    # advisory cases: must NOT block (evaluate None) but SHOULD emit an advisory note
    advised = [
        (edit("worktrees/bed/be/Services/XService.cs", 'throw new Exception("x");'), "BE convention"),
        (edit("worktrees/bed/be/Apis/XApi.cs", 'throw new BusinessException("LIT", "m");'), "error code"),
        (edit("worktrees/bed/be/Services/YService.cs", "using var tx = await Db.Database.BeginTransactionAsync();"), "transaction"),
        (edit("worktrees/bed/fe/src/components/X.tsx", "const r = await fetch('/api')"), "FE convention"),
        (edit("worktrees/bed/fe/src/x.tsx", "import { HelloResponse } from '@/lib/dtos/dtos';"), "FE-V1"),
    ]
    failures = 0
    for ev in blocked:
        if evaluate(ev) is None:
            failures += 1
            print(f"FAIL expected BLOCK: {ev['tool_input']}")
    for ev in allowed:
        rule = evaluate(ev)
        if rule is not None:
            failures += 1
            print(f"FAIL expected ALLOW: {ev['tool_input']} -> {rule}")
    for ev, want in advised:
        if evaluate(ev) is not None:
            failures += 1
            print(f"FAIL advisory case must NOT block: {ev['tool_input']}")
        note = evaluate_advisory(ev)
        if not note or want not in note:
            failures += 1
            print(f"FAIL expected ADVISORY containing {want!r}: got {note!r}")
    total = len(blocked) + len(allowed) + 2 * len(advised)
    # PM-active drift door: main session must not edit SRC_TREE while .pm-run-active exists.
    # Run in an isolated temp root (env-patched) so the real session is untouched.
    old_env = os.environ.get("CLAUDE_PROJECT_DIR")
    with tempfile.TemporaryDirectory() as td:
        os.environ["CLAUDE_PROJECT_DIR"] = td
        (Path(td) / ".claude").mkdir()
        (Path(td) / ".claude" / ".pm-run-active").write_text("ledger", encoding="utf-8")
        pm_blocked = [
            edit("worktrees/bed/be/Services/XService.cs", "x"),
            edit("myhospital-fe/src/components/X.tsx", "x"),
            edit("worktrees/ipd/fe/src/x.tsx", "x"),
            edit("myhospital-be/Services/RoomService.cs", "x"),
        ]
        pm_allowed = [
            edit("engine/workflows/pm-orchestrator/runs/x/00-pm-state.md", "blob"),  # ledger OK
            edit("docs/audit/2026-06-30/y.md", "findings"),  # not SRC_TREE
            edit("scripts/foo.py", "x"),  # harness, not product source
            sub(edit("worktrees/bed/be/Services/XService.cs", "x")),  # subagent exempt
        ]
        for ev in pm_blocked:
            if evaluate(ev) is None:
                failures += 1
                print(f"FAIL pm-active expected BLOCK: {ev['tool_input']}")
        for ev in pm_allowed:
            rule = evaluate(ev)
            if rule is not None:
                failures += 1
                print(f"FAIL pm-active expected ALLOW: {ev['tool_input']} -> {rule}")
        total += len(pm_blocked) + len(pm_allowed)
    if old_env is None:
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
    else:
        os.environ["CLAUDE_PROJECT_DIR"] = old_env
    if failures:
        print(f"self-test: {failures}/{total} FAILED")
        return 1
    print(f"self-test: all {total} cases passed ({len(blocked)} block, {len(allowed)} allow)")
    return 0


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return _self_test()
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        event = json.loads(raw)
    except Exception:
        return 0
    if not isinstance(event, dict):
        return 0
    try:
        rule = evaluate(event)
    except Exception:
        return 0  # fail open: a guard bug must never wedge a session
    if rule:
        deny(rule)
    try:
        note = evaluate_advisory(event)
    except Exception:
        note = None
    if note:
        print(f"ADVISORY: {note} — verify: python scripts/mh_scan --scope <file> --format summary",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
