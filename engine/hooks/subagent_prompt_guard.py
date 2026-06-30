#!/usr/bin/env python3
"""Claude PreToolUse guard — enforce the Anthropic prompt-engineering guideline on
EVERY worker / coding-tool prompt the orchestrator authors.

Reads a Claude hook JSON event on stdin and BLOCKS (exit 2, stderr shown to Claude)
a sub-standard *mutating worker* prompt before it is dispatched, so the next time
Opus generates a prompt for a subagent or an external coding tool it MUST conform to
engine/prompts/subagent-prompt-template.md (which distills docs/anthropic-guideline/).

Two dispatch channels are intercepted:
  - Task tool          -> a Claude subagent. Linted on the `task` channel (full bar).
  - Bash invoking      -> opencode / grok / agy. Linted on the `oc` channel, where
    scripts/agent_exec.py    oc_worker.PREAMBLE is auto-prepended, so the author must
    or  scripts/oc_worker.py supply intent / allowlist / xml / validation.

Read-only / search / review dispatches (Explore, mh-reviewer, --read-only, …) get a
light advisory bar and are NEVER hard-blocked.

Deliberately **fail-open**: malformed input, an unreadable prompt file, or any internal
error returns exit 0 (allow) — a guard bug must never wedge a session. The actual bar
lives in scripts/subagent_prompt_lint.py (regex-only, has its own --self-test).

Run: python engine/hooks/subagent_prompt_guard.py --self-test
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and (Path(env) / "scripts" / "subagent_prompt_lint.py").exists():
        return Path(env)
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "scripts" / "subagent_prompt_lint.py").exists():
            return parent
    return here.parent.parent.parent  # engine/hooks/ -> repo root, best effort


_ROOT = _repo_root()
sys.path.insert(0, str(_ROOT / "scripts"))

try:
    from subagent_prompt_lint import format_block_message, lint_prompt  # noqa: E402
    _LINTER_OK = True
except Exception:  # pragma: no cover - fail-open if the linter can't import
    _LINTER_OK = False


# ---- Tolerant event parsing (mirrors myhospital_guard._parse) -----------------
def _parse(event: dict[str, Any]) -> tuple[str, dict[str, Any]]:
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


# ---- Bash channel: pull the task prompt out of an agent_exec/oc_worker call ----
_CODING_SCRIPT = re.compile(r"(agent_exec|oc_worker)\.py", re.IGNORECASE)


def _flag_value(toks: list[str], names: tuple[str, ...]) -> str | None:
    """Return the value of --name VALUE or --name=VALUE for any name in `names`."""
    for i, t in enumerate(toks):
        for n in names:
            if t == n and i + 1 < len(toks):
                return toks[i + 1]
            if t.startswith(n + "="):
                return t.split("=", 1)[1]
    return None


def _bash_dispatch_prompt(command: str) -> tuple[str | None, bool] | None:
    """If `command` invokes agent_exec.py / oc_worker.py with a real task, return
    (task_text, read_only). Returns None when the command is not a coding-tool
    dispatch (or is a self-test/dry-run, or the prompt cannot be read)."""
    if not _CODING_SCRIPT.search(command or ""):
        return None
    try:
        toks = shlex.split(command)
    except ValueError:
        toks = command.split()
    if any(t in ("--self-test", "--dry-run") for t in toks):
        return None
    read_only = "--read-only" in toks
    inline = _flag_value(toks, ("--prompt",))
    if inline:
        return inline, read_only
    pf = _flag_value(toks, ("--prompt-file",))
    if pf:
        for cand in (Path(pf), _ROOT / pf):
            try:
                return cand.read_text("utf-8"), read_only
            except OSError:
                continue
    return None  # no readable prompt -> fail-open (nothing to lint)


# ---- Decision -----------------------------------------------------------------
def evaluate(event: dict[str, Any]) -> str | None:
    """Return a block message (BLOCKED_RULE body) if the dispatch prompt is a
    sub-standard mutating worker prompt; else None (allow)."""
    if not _LINTER_OK:
        return None
    tool_lower, tool_input = _parse(event)

    if tool_lower == "task":
        prompt = tool_input.get("prompt") or ""
        if not str(prompt).strip():
            return None
        subagent_type = tool_input.get("subagent_type") or tool_input.get("subagentType")
        result = lint_prompt(str(prompt), channel="task", subagent_type=subagent_type)
        if result["profile"] == "worker" and not result["passed"]:
            return format_block_message(result)
        return None

    command = tool_input.get("command") or event.get("command") or ""
    if tool_lower == "bash" or (not tool_lower and command):
        found = _bash_dispatch_prompt(str(command))
        if not found:
            return None
        task, read_only = found
        if not (task or "").strip():
            return None
        result = lint_prompt(task, channel="oc", read_only=read_only)
        if result["profile"] == "worker" and not result["passed"]:
            return format_block_message(result)
    return None


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
        msg = evaluate(event)
    except Exception:
        return 0  # fail-open: a guard bug must never wedge a session
    if msg:
        print(f"BLOCKED_RULE: {msg}", file=sys.stderr)
        return 2
    return 0


# ---- Self-test ----------------------------------------------------------------
_ROOMS_PROMPT = """# TASK: Refactor rooms
Use ripgrep to DISCOVER the code. Do NOT invent paths.
Convert /rooms/new to a Sheet; reuse the existing form (Ponytail), do not rewrite.
REMOVE the add-bed column. Validation: tsc. Report back files changed + reuse evidence.
"""

_GOOD_PROMPT = """You are a SUBAGENT; no human is watching, do not ask. STOP + NEEDS-OWNER-DECISION on ambiguity.
<intent>I'm working on the rooms screen for nurses; they need inline add/edit.</intent>
<scope>allowlist: fe/src/modules/rooms/** ; do_not_touch: generated DTO, migrations</scope>
## Task
Convert the add page to a Sheet. Investigate the sibling Sheet pattern; reuse it (smallest diff),
do not invent paths, cite file:line evidence.
## Validation
Run tsc and the scanner; report real output.
## return_format
Lead with the TLDR, then files changed + reuse evidence.
"""


def _ev_task(prompt: str, subagent_type: str | None = None) -> dict:
    inp: dict[str, Any] = {"prompt": prompt, "description": "x"}
    if subagent_type:
        inp = {**inp, "subagent_type": subagent_type}
    return {"tool_name": "Task", "tool_input": inp}


def _ev_bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def _self_test() -> int:
    checks: list[tuple[bool, str]] = []

    def ck(cond: bool, msg: str) -> None:
        checks.append((bool(cond), msg))
        print(f"  {'PASS' if cond else 'FAIL'}: {msg}")

    ck(_LINTER_OK, "linter imported")

    # Task channel.
    ck(evaluate(_ev_task(_ROOMS_PROMPT)) is not None, "Task: sub-standard worker prompt BLOCKED")
    ck(evaluate(_ev_task(_GOOD_PROMPT)) is None, "Task: conformant worker prompt allowed")
    ck(evaluate(_ev_task("Search for list+Sheet modules; report file:line. Do not invent paths.",
                         subagent_type="Explore")) is None, "Task: Explore (read-only) allowed")

    # Bash channel — coding-tool dispatch.
    pfile = Path(_ROOT) / ".lint_selftest_prompt.md"
    try:
        pfile.write_text(_ROOMS_PROMPT, "utf-8")
        ck(evaluate(_ev_bash(f"python scripts/agent_exec.py --role agentic_primary --scope wt/x "
                             f"--prompt-file {pfile}")) is not None,
           "Bash: agent_exec with sub-standard prompt-file BLOCKED")
        pfile.write_text(_GOOD_PROMPT, "utf-8")
        ck(evaluate(_ev_bash(f"python scripts/oc_worker.py --role agentic_primary "
                             f"--prompt-file {pfile}")) is None,
           "Bash: oc_worker with conformant prompt-file allowed")
        pfile.write_text(_ROOMS_PROMPT, "utf-8")
        ck(evaluate(_ev_bash(f"python scripts/agent_exec.py --role audit --read-only "
                             f"--prompt-file {pfile}")) is None,
           "Bash: --read-only dispatch allowed (readonly profile)")
    finally:
        try:
            pfile.unlink()
        except OSError:
            pass

    ck(evaluate(_ev_bash("cat scripts/agent_exec.py")) is None,
       "Bash: reading the script file (no --prompt) allowed")
    ck(evaluate(_ev_bash("python scripts/agent_exec.py --self-test")) is None,
       "Bash: --self-test allowed")
    ck(evaluate(_ev_bash("ls -la")) is None, "Bash: unrelated command allowed")
    ck(evaluate(_ev_bash("python scripts/agent_exec.py --role agentic_primary "
                         f"--prompt 'Edit the file and make it work.'")) is not None,
       "Bash: agent_exec with terse inline --prompt BLOCKED")

    failed = [m for ok, m in checks if not ok]
    print(f"\nsubagent_prompt_guard self-test: {'OK' if not failed else 'FAIL'} "
          f"({len(checks)} assertions, {len(failed)} failed)")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
