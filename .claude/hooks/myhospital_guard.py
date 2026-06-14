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

Run `python myhospital_guard.py --self-test` to validate the rules.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from typing import Any

# Path fragments. FE/BE match the main repo OR a worktree copy.
FE = r"(?:myhospital-fe|worktrees/[^/]+/fe)"
BE = r"(?:myhospital-be|worktrees/[^/]+/be)"
FE_MAIN = r"myhospital-fe"
BE_MAIN = r"myhospital-be"

_DEP_CMDS = {"npm", "pnpm", "yarn", "bun"}
_DEP_SUBS = {"install", "i", "add"}


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
        if name == "git":
            sub, rest = _git_sub(toks)
            if sub in ("push", "commit"):
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


def evaluate(event: dict[str, Any]) -> str | None:
    tool = str(event.get("tool_name") or "")
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return None
    if tool == "Bash":
        return bash_rule(str(tool_input.get("command") or ""))
    if tool in {"Write", "Edit", "MultiEdit"}:
        file_path = ""
        for name in ("file_path", "path"):
            if tool_input.get(name) is not None:
                file_path = _norm(tool_input[name])
                break
        return edit_rule(file_path, edit_text(tool_input))
    return None


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
def _self_test() -> int:
    def bash(cmd: str) -> dict[str, Any]:
        return {"tool_name": "Bash", "tool_input": {"command": cmd}}

    def edit(path: str, new: str = "") -> dict[str, Any]:
        return {"tool_name": "Edit", "tool_input": {"file_path": path, "new_string": new}}

    blocked = [
        bash("git push"),
        bash("git -C myhospital-fe push origin master"),
        bash("cd x && git commit -m 'y'"),
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
        edit("worktrees/bed/fe/src/lib/dtos/generated-dtos.ts", "x"),
        edit("myhospital-be/MyHospital.ServiceInterface/Migrations/2026_X.cs", "x"),
        edit("worktrees/bed/be/MyHospital.ServiceInterface/Migrations/Y.cs", "x"),
        edit("myhospital-fe/src/components/X.tsx", "const r = await fetch('/api')"),
        edit("myhospital-be/Services/XService.cs", "return null;"),
    ]
    allowed = [
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
        bash("dotnet build"),
        bash("python scripts/worktree.py list"),
        edit("worktrees/bed/be/Services/XService.cs", "return null;"),  # heuristic main-only
        edit("worktrees/bed/fe/src/components/X.tsx", "await fetch('/api')"),  # heuristic main-only
        edit("docs/notes.md", "anything"),
        edit("scripts/foo.py", "import os"),
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
    total = len(blocked) + len(allowed)
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
