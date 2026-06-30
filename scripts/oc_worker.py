#!/usr/bin/env python3
"""oc_worker.py — dispatch ONE bounded OpenCode (non-Anthropic) worker and return a
compact blob, so the blind PM orchestrator can fan out to OpenCode Go models the same
way it fans out Claude subagents: route a PATH + a compact status, never the body.

Owner-locked policy (scripts/tier_policy.json, 2026-06-26):
  - Orchestrator stays Opus 4.8 low; this adapter only drives OPENCODE roles
    (audit / mechanical_fix / agentic_*). Anthropic roles (clinical_floor / danger /
    final_review / adjudicate) run as NATIVE Claude agents and are REFUSED here.
  - Audit roles run read-only via OpenCode's `plan` agent (no mutations).
  - Every code-mutating workflow still owes a mandatory Opus 4.8 xhigh final review —
    that is the orchestrator's job, NOT this adapter's.

`opencode run --format json` contract (verified v1.17.x):
  - NDJSON: one JSON object per line; top-level `type` in {step_start,text,tool_use,step_finish,error}.
  - Final assistant answer = `part.text` of `type=="text"` events AFTER the last `tool_use`
    event (drops inter-tool narration + tool/file-read content). Do NOT rely on step_finish.
  - There is NO `-q/--quiet` flag.

Usage:
  python scripts/oc_worker.py --role audit --scope worktrees/<slug>/be \
      --prompt-file p.md --out artifact.md [--rule-card rc.md] [--attach URL] [--pure] [--dry-run]
  python scripts/oc_worker.py --self-test

Output: a one-line compact JSON blob on stdout (the PM reads THIS, not --out).
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

try:
    from harness_router import load_tier_policy, _resolve_role, TIER_POLICY_FALLBACK
except Exception:  # pragma: no cover - fail-safe if router import breaks
    TIER_POLICY_FALLBACK = {"roles": {}}

    def load_tier_policy() -> dict[str, Any]:
        try:
            data = json.loads((ROOT / "scripts" / "tier_policy.json").read_text("utf-8"))
            return data if isinstance(data, dict) and data.get("roles") else TIER_POLICY_FALLBACK
        except Exception:
            return TIER_POLICY_FALLBACK

    def _resolve_role(roles: dict[str, Any], role_key: str) -> dict[str, Any]:
        r = dict(roles.get(role_key) or {})
        r["role"] = role_key
        prov = r.get("provider")
        r["backend"] = "native" if prov == "anthropic" else "opencode-cli"
        model = str(r.get("model", ""))
        r["model_id"] = f"opencode-go/{model}" if prov == "opencode" and model and not model.startswith("opencode") else model
        return r


PREAMBLE = (
    "SUBAGENT IDENTITY: You are a SUBAGENT dispatched by the PM orchestrator (Opus 4.8 low) via oc_worker.py. "
    "You are NOT the main interactive agent. The owner is NOT watching this turn. Do NOT ask the parent agent "
    "or any human for clarification, worktree choice, or scope expansion — there is no human to answer you. "
    "If you hit genuine ambiguity (business/clinical/billing/permission rule unclear, schema unclear, scope "
    "ambiguous): STOP, report it as a `NEEDS-OWNER-DECISION` finding with the exact question + options + your "
    "recommended default, and end the turn. Do NOT invent an answer, do NOT guess. For everything else "
    "(reversible actions, tool choices, file reads/writes within --dir scope, validation commands): proceed "
    "autonomously.\n\n"
    "OUTPUT LANGUAGE (BLOCK if violated): All your findings, analysis, code, replies, and output MUST be in "
    "ENGLISH. Never emit Vietnamese, Chinese, or any other language — English only. Code identifiers and file "
    "paths stay as-is.\n\n"
    "HYDRATION IS MANDATORY (BLOCK if skipped): Before any review/write/test/scaffold action, you MUST read the "
    "injected convention rule-card (inlined below) and any in-context manifest. Skipping convention hydration is "
    "a BLOCK, not a shortcut — you WILL violate conventions and produce rework. The convention canon is at "
    "engine/rules/{backend,frontend}.md and is accessible from the harness root (your cwd). Read the rule-card "
    "IN FULL before acting; for dev/implement tasks also load engine/rules/{backend,frontend}.md and "
    "engine/rules/ponytail.md.\n\n"
    "You are a bounded MyHospital worker. Do ONLY the task below. "
    "Follow the injected conventions exactly; reuse existing patterns (Ponytail): search the worktree for "
    "similar Services/APIs/DTOs/Components before creating new ones. "
    "Do NOT touch generated DTO/client/Constants.ts or EF migrations. "
    "End with a single line starting `TLDR:` summarizing what you did/found + files touched + how you validated. "
    "Your output IS the return value; ground every claim in files you actually read.\n"
)


def _emit(blob: dict[str, Any]) -> None:
    print(json.dumps(blob))


def resolve_role(role_key: str) -> dict[str, Any]:
    policy = load_tier_policy()
    roles = policy.get("roles") or TIER_POLICY_FALLBACK.get("roles") or {}
    return _resolve_role(roles, role_key)


def build_prompt(task: str, rule_card: str | None, manifest_path: str | None,
                 slug: str | None = None, scope: str | None = None,
                 read_only: bool = True) -> str:
    parts: list[str] = []
    if slug and scope:
        parts.append(
            "## WORKTREE SETUP (mandatory — BLOCK if skipped)\n"
            f"Your task targets worktree `{slug}` at path `{scope}`. "
            "You start at the harness root — all paths are relative from here.\n"
            f"1. Run: python scripts/worktree.py set-current --slug {slug}\n"
            f"2. Worktree files are at: {scope}\n"
            "3. Navigate into the worktree as needed: cd <scope>\n"
            + ("4. RULES HYDRATION (review task): before reading/analyzing, load "
               "engine/rules/backend.md, engine/rules/frontend.md, engine/rules/ponytail.md, "
               "AND the inlined rule-card below.\n" if read_only else
               "4. RULES + PATTERN HYDRATION (dev/implement task): BEFORE any code edit, load:\n"
               "   - engine/rules/backend.md + engine/rules/frontend.md + engine/rules/ponytail.md\n"
               "   - engine/rules/backend/*.md + engine/rules/frontend/*.md (all topic cards)\n"
               "   - The inlined rule-card below\n"
               "   - Then SEARCH the worktree for existing Services/APIs/DTOs/Components matching\n"
               "     your task shape. Reuse them; never invent a new pattern when one exists.\n"
               "5. The CLI you are using MUST follow its built-in Anthropic skill/prompt conventions\n"
               "   for generating subagent prompts (see engine/prompts/subagent-prompt-template.md).\n")
            + "\n"
        )
    parts.append(PREAMBLE)
    if rule_card:
        parts.append("## Convention contract (rule cards)\n" + rule_card.strip() + "\n")
    if manifest_path:
        parts.append(f"## Context manifest (read for hydrate-by-reference)\n{manifest_path}\n")
    parts.append("## Task\n" + task.strip() + "\n")
    return "\n".join(parts)


def build_command(role: dict[str, Any], prompt: str, scope: str, read_only: bool,
                  allow_edit: bool, attach: str | None = None, pure: bool = False) -> list[str]:
    cmd = ["opencode", "run", prompt, "-m", role["model_id"]]
    if role.get("variant"):
        cmd += ["--variant", role["variant"]]
    if read_only:
        cmd += ["--agent", "mh-reviewer-oc"]
    else:
        cmd += ["--agent", "mh-fixer"]
    cmd += ["--dir", str(ROOT)]
    attach_url = attach if attach is not None else "http://127.0.0.1:4096"
    if attach_url:
        cmd += ["--attach", attach_url]
    if pure:
        cmd += ["--pure"]
    cmd += ["--format", "json"]
    return cmd


def extract_text(stdout: str) -> tuple[str, str]:
    """Parse OpenCode `--format json` NDJSON.
    Returns (final_text, error_text). The final assistant answer is the `part.text` of
    `type=="text"` events emitted AFTER the last `type=="tool_use"` event — this drops
    inter-tool narration AND tool/file-read content. Falls back to ALL text parts (then
    raw stdout) if the after-tool slice is empty."""
    events: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line or line[0] != "{":
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if isinstance(ev, dict):
            events.append(ev)

    last_tool = -1
    for i, ev in enumerate(events):
        if ev.get("type") == "tool_use":
            last_tool = i

    def _text(ev: dict[str, Any]) -> str:
        part = ev.get("part") or {}
        t = part.get("text")
        return t if isinstance(t, str) and t.strip() else ""

    after = [_text(ev) for i, ev in enumerate(events) if ev.get("type") == "text" and i > last_tool]
    after_text = "".join(t for t in after if t).strip()
    errors = [json.dumps(ev.get("part") or ev)[:500] for ev in events if ev.get("type") == "error"]

    if after_text:
        return after_text, "\n".join(errors)
    all_text = "".join(t for t in (_text(ev) for ev in events if ev.get("type") == "text") if t).strip()
    return (all_text or stdout.strip()), "\n".join(errors)


def summarize(text: str) -> str:
    """Compact summary for the blob = the TLDR line (worker is told to end with one),
    else the LAST non-blank line. NEVER the first line (that is a heading/intro)."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return ""
    for i in range(len(lines) - 1, -1, -1):
        if "tldr" in lines[i].lower():
            # prefer text on the TLDR line after the marker, else the next line,
            # else the previous non-blank line — NEVER the bare marker itself.
            after_marker = lines[i].split(":", 1)[1].strip() if ":" in lines[i] else ""
            if after_marker:
                return after_marker[:200]
            tail = lines[i + 1:]
            if tail:
                return tail[0][:200]
            prev = lines[:i]
            return (prev[-1][:200] if prev else "")
    return lines[-1][:200]


def _killpg(proc: subprocess.Popen, sig: int) -> None:
    """Send one signal to the whole process group. Does NOT wait/drain — the caller's
    communicate() drains the pipes (avoids the wait()-with-PIPE deadlock)."""
    try:
        os.killpg(os.getpgid(proc.pid), sig)
    except Exception:
        pass


def run(args: argparse.Namespace) -> int:
    role = resolve_role(args.role)
    blob: dict[str, Any] = {
        "ok": False, "role": args.role, "provider": role.get("provider"),
        "scope": args.scope, "out": args.out,
    }
    if not role.get("model"):
        blob["error"] = f"unknown role {args.role!r}"
        _emit(blob)
        return 2
    if role.get("provider") != "opencode":
        blob["error"] = f"role {args.role!r} is {role.get('provider')}/native — dispatch via a Claude Agent, not oc_worker"
        _emit(blob)
        return 3

    read_only = bool(role.get("read_only")) or bool(args.read_only)
    try:
        task = args.prompt or (Path(args.prompt_file).read_text("utf-8") if args.prompt_file else "")
        rule_card = Path(args.rule_card).read_text("utf-8") if args.rule_card else None
    except OSError as e:
        blob["error"] = f"cannot read input file: {e}"
        _emit(blob)
        return 2
    if not task.strip():
        blob["error"] = "empty task (need --prompt or --prompt-file)"
        _emit(blob)
        return 2

    prompt = build_prompt(task, rule_card, args.manifest,
                          slug=args.slug or None, scope=args.scope or None,
                          read_only=read_only)
    cmd = build_command(role, prompt, args.scope, read_only, args.allow_edit, args.attach, args.pure)
    blob.update(model_id=role["model_id"], variant=role.get("variant"),
                read_only=read_only, dry_run=bool(args.dry_run), ok=True)

    if args.dry_run:
        blob["command"] = cmd[:2] + ["<prompt:%d chars>" % len(prompt)] + cmd[3:]
        blob["prompt_preview"] = prompt[:240]
        _emit(blob)
        return 0

    # Force the harness WORKER config so the mh-reviewer-oc / mh-fixer agents (and their
    # system prompts) load even though --dir points at a worktree (opencode does NOT walk up to
    # the harness root for config). worker.json deliberately omits AGENTS.md (the blind-PM
    # bootloader) so a worker isn't told to "route, don't do". Fail-open if the file is missing.
    env = dict(os.environ)
    worker_cfg = ROOT / ".opencode" / "worker.json"
    if worker_cfg.is_file():
        env["OPENCODE_CONFIG"] = str(worker_cfg)
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True, env=env)
    except FileNotFoundError:
        blob.update(ok=False, error="opencode CLI not found on PATH")
        _emit(blob)
        return 4
    try:
        out, err = proc.communicate(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        # SIGTERM the group, let communicate() drain (graceful grace period); escalate to
        # SIGKILL if it still hasn't exited; preserve any partial output for the artifact.
        _killpg(proc, signal.SIGTERM)
        try:
            out, err = proc.communicate(timeout=15)
        except subprocess.TimeoutExpired as e2:
            _killpg(proc, signal.SIGKILL)
            try:
                out, err = proc.communicate(timeout=10)
            except Exception:
                out, err = (e2.output or ""), (e2.stderr or "")
        text, _errors = extract_text(out or "")
        if args.out and text:
            try:
                Path(args.out).parent.mkdir(parents=True, exist_ok=True)
                Path(args.out).write_text(text, "utf-8")
            except OSError:
                pass
        blob.update(ok=False, error=f"timeout after {args.timeout}s (killed process group)",
                    exit_code=124, summary=summarize(text), partial=bool(text))
        _emit(blob)
        return 5

    text, errors = extract_text(out)
    if args.out:
        try:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(text or out, "utf-8")
        except OSError as e:
            blob["out_write_error"] = str(e)
    blob["exit_code"] = proc.returncode
    blob["ok"] = proc.returncode == 0
    blob["summary"] = summarize(text)
    if errors:
        blob["stream_errors"] = errors[:600]
    if proc.returncode != 0:
        blob["stderr_tail"] = (err or "").strip()[-300:]
    _emit(blob)
    return 0 if proc.returncode == 0 else 1


def self_test() -> int:
    audit = resolve_role("audit")
    assert audit.get("model") == "glm-5.2", audit
    assert audit["model_id"] == "opencode-go/glm-5.2", audit
    assert audit.get("read_only") is True, audit
    cmd = build_command(audit, "hello", "worktrees/x/be", read_only=True, allow_edit=False)
    assert "--agent" in cmd and "mh-reviewer-oc" in cmd, cmd
    assert "--variant" in cmd and "max" in cmd, cmd
    assert "--format" in cmd and "json" in cmd, cmd
    assert "--attach" in cmd and "http://127.0.0.1:4096" in cmd, cmd
    assert "--dir" in cmd and str(ROOT) in cmd, cmd
    assert "--dangerously-skip-permissions" not in cmd and "-q" not in cmd, cmd
    fix = resolve_role("agentic_primary")
    assert fix["model_id"] == "opencode-go/deepseek-v4-pro", fix
    cmd2 = build_command(fix, "x", "wt", read_only=False, allow_edit=True, attach="http://127.0.0.1:4096", pure=True)
    assert "--agent" in cmd2 and "mh-fixer" in cmd2, cmd2
    assert "--dangerously-skip-permissions" not in cmd2, cmd2
    assert "--attach" in cmd2 and "--pure" in cmd2, cmd2
    assert "--dir" in cmd2 and str(ROOT) in cmd2, cmd2
    assert resolve_role("clinical_floor").get("provider") == "anthropic"
    # build_prompt with slug: worktree setup must be prepended
    p = build_prompt("do X", "card content", None, slug="x", scope="worktrees/x/be", read_only=True)
    assert "WORKTREE SETUP" in p, p
    assert "x" in p, p
    assert "RULES HYDRATION" in p, p
    p2 = build_prompt("do Y", "card content", None, slug="x", scope="worktrees/x/be", read_only=False)
    assert "PATTERN HYDRATION" in p2, p2
    # NDJSON parsing: final answer = text after last tool_use; tool/file content dropped
    stream = "\n".join([
        json.dumps({"type": "step_start"}),
        json.dumps({"type": "tool_use", "part": {"type": "tool", "text": "SECRET FILE CONTENT should be dropped"}}),
        json.dumps({"type": "text", "part": {"type": "text", "text": "FINDINGS: bug at line 10."}}),
        json.dumps({"type": "text", "part": {"type": "text", "text": "\nTLDR: 1 bug found."}}),
        json.dumps({"type": "step_finish", "reason": "stop"}),
    ])
    text, errors = extract_text(stream)
    assert "SECRET FILE CONTENT" not in text, text
    assert "FINDINGS: bug at line 10." in text, text
    assert summarize(text) == "1 bug found.", summarize(text)
    # bare-TLDR must never return the literal marker
    assert summarize("intro line\nTLDR:") == "intro line", summarize("intro line\nTLDR:")
    assert summarize("# Heading\nLine A\nLast line") == "Last line", summarize("# Heading\nLine A\nLast line")
    print("oc_worker self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Dispatch one bounded OpenCode worker.")
    p.add_argument("--role", help="role key from tier_policy.json roles (opencode roles only)")
    p.add_argument("--scope", default="", help="--dir working directory (worktree)")
    p.add_argument("--slug", default="", help="worktree slug for join + rule hydration")
    p.add_argument("--prompt", default="", help="inline task (or use --prompt-file)")
    p.add_argument("--prompt-file", help="path to a file containing the task")
    p.add_argument("--out", help="artifact path to write the worker output")
    p.add_argument("--rule-card", help="path to rule-card text to inject as the convention contract")
    p.add_argument("--manifest", help="context-manifest path (referenced, not inlined)")
    p.add_argument("--attach", help="attach to a warm `opencode serve` (e.g. http://127.0.0.1:4096)")
    p.add_argument("--pure", action="store_true", help="skip external plugins for speed")
    p.add_argument("--read-only", action="store_true", help="force read-only (plan agent)")
    p.add_argument("--allow-edit", action="store_true", help="explicit intent to mutate (mutating roles run via the guarded mh-fixer agent; advisory)")
    p.add_argument("--timeout", type=int, default=900, help="seconds before killing the run + its process group")
    p.add_argument("--dry-run", action="store_true", help="print resolved command + blob, do not run opencode")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.role:
        p.error("--role is required (or --self-test)")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
