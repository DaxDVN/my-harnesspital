#!/usr/bin/env python3
"""agent_exec.py — agentic coding tool adapter: 3 backends + fallback chain.

One interface `doThisTask(role, task, scope, ...) -> compact JSON blob`, three
backend implementations:

  opencode  — delegate to scripts/oc_worker.py (subprocess). Reuses oc_worker's
              PREAMBLE / build_prompt / build_command / extract_text / summarize /
              run() — NO duplicated logic. oc_worker owns the opencode CLI details
              (agent selection, --format json NDJSON parsing, process-group kill).
  grok      — subprocess `grok` CLI (--single, --output-format json, --model,
              --effort, --allow/--deny permission rules, --disallowed-tools for
              read-only). NDJSON output parsed with oc_worker.extract_text.
  agy       — subprocess `agy` CLI (--print, --model, --add-dir, --sandbox for
              read-only, --dangerously-skip-permissions for mutating). Plain-text
              stdout; summarized with oc_worker.summarize.

Fallback chain: role.backend -> role.fallback[i+1] (unless allow_fallback=false or
--no-fallback). When the primary backend fails with a fallback-able error
(QuotaExhausted / WorkerTimeout / AuthError / BackendUnavailable), agent_exec tries
the next backend in the chain. Real-bug failures (non-zero exit, non-fallback error)
return a failed blob immediately — no fallback (a real bug is not a quota issue).

Owner-locked policy (scripts/tier_policy.json, 2026-06-29):
  - native roles (provider=anthropic: final_review / clinical_floor / danger_refactor /
    adjudicate / design / orchestrator) are REFUSED here — dispatch via the Claude
    Task tool. agent_exec only drives non-Anthropic backends.
  - Review roles (audit) set allow_fallback=false — glm-5.2 review is mandatory.

Exit codes: 0 OK | 1 worker fail (real bug) | 2 config err | 3 native refused |
            4 all backends failed (chain exhausted) | 5 timeout (chain ended on timeout).

Output: ONE compact JSON blob on stdout (the PM reads THIS). Progress/errors -> stderr.

Usage:
  python scripts/agent_exec.py --role <role-key> --scope <dir> --prompt <text|--prompt-file <path>>
      [--backend opencode|grok|agy|native] [--model <id>] [--effort low|medium|high|xhigh|max]
      [--rule-card <path>] [--manifest <path>] [--read-only] [--allow-edit]
      [--out <path>] [--timeout 900] [--no-fallback] [--dry-run] [--self-test]

Env: DB_SERVER/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD are inherited by the worker
     subprocess; AGENT_EXEC_BACKEND overrides the global default backend
     (used only when the role has no explicit `backend` field).
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

# Reuse oc_worker helpers (read-only import — NEVER edit oc_worker.py).
# PREAMBLE / build_prompt / build_command / extract_text / summarize are pure and
# shared across all three backends so the SUBAGENT markers + NDJSON parsing stay DRY.
# resolve_role is NOT reused: oc_worker.resolve_role -> harness_router._resolve_role
# clobbers `backend` to "opencode-cli" and drops `fallback` / `allow_fallback`, which
# does not fit agent_exec's backend keys (opencode|grok|agy|native). We re-resolve from
# tier_policy directly via load_tier_policy (reused from harness_router).
from oc_worker import (  # noqa: E402
    PREAMBLE,
    build_command,
    build_prompt,
    extract_text,
    summarize,
)
from harness_router import load_tier_policy  # noqa: E402

# ---- Exit codes ---------------------------------------------------------------
EX_OK = 0
EX_WORKER_FAIL = 1
EX_CONFIG = 2
EX_NATIVE_REFUSED = 3
EX_ALL_BACKENDS_FAILED = 4
EX_TIMEOUT = 5

# ---- Error classification keywords -------------------------------------------
_QUOTA_KEYWORDS = (
    "quota", "rate limit", "rate-limit", "402", "payment required", "429",
    "credit", "exhausted", "capacity", "spending limit",
)
_AUTH_KEYWORDS = (
    "401", "403", "unauthorized", "forbidden", "api key", "apikey",
    "invalid key", "authentication", "not authenticated", "auth failed",
)


# ---- Fallback-able exceptions -------------------------------------------------
class QuotaExhausted(Exception):
    """Backend quota / rate-limit hit -> fallback."""


class WorkerTimeout(Exception):
    """Backend subprocess timed out -> fallback."""


class AuthError(Exception):
    """Backend authentication failure -> fallback."""


class BackendUnavailable(Exception):
    """Backend binary not found / cannot start -> fallback.

    Not in the spec's explicit fallback list (quota/timeout/auth) but a missing
    CLI is an infra issue, not a worker-logic bug — falling back is obviously
    correct and matches the spec's intent ("real bug, not quota" = no fallback).
    """


# ---- Helpers ------------------------------------------------------------------
def _emit(blob: dict[str, Any]) -> None:
    """Emit the compact JSON blob on stdout (PM reads THIS)."""
    print(json.dumps(blob))


def _err(msg: str) -> None:
    """Progress / errors -> stderr (never stdout, which is reserved for the blob)."""
    print(f"[agent_exec] {msg}", file=sys.stderr)


def _read_file(path: str | None) -> str | None:
    if not path:
        return None
    try:
        return Path(path).read_text("utf-8")
    except OSError:
        return None


def _write_out(out_path: str | None, text: str) -> None:
    if not out_path or not text:
        return
    try:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(text, "utf-8")
    except OSError:
        pass


def _killpg(proc: subprocess.Popen, sig: int) -> None:
    """Signal the whole process group (CLIs may spawn children). Local copy to avoid
    importing a private helper from oc_worker; identical 4-line semantics."""
    try:
        os.killpg(os.getpgid(proc.pid), sig)
    except Exception:
        pass


def _worker_env() -> dict[str, str]:
    """Inherit os.environ (DB_SERVER/DB_PORT/... + AGENT_EXEC_BACKEND pass through)."""
    return dict(os.environ)


def _redact(cmd: list[str], prompt_len: int) -> list[str]:
    """Redact the long prompt argument in a command preview (anything > 200 chars)."""
    return [a if len(a) < 200 else f"<prompt:{prompt_len} chars>" for a in cmd]


# ---- Role resolution ----------------------------------------------------------
def resolve_role(role_key: str) -> dict[str, Any]:
    """Resolve a role key from tier_policy.json, preserving the explicit `backend`,
    `fallback`, `allow_fallback`, and `read_only` fields (oc_worker.resolve_role
    clobbers backend to opencode-cli and drops fallback/allow_fallback — see module
    docstring). Carries the full policy dict for backend_defaults lookups."""
    policy = load_tier_policy()
    roles = policy.get("roles") or {}
    r = dict(roles.get(role_key) or {})
    r["role"] = role_key
    prov = r.get("provider")
    providers = policy.get("providers") or {}
    provider_cfg = providers.get(prov) or {}
    # Backend resolution. Native roles (Opus floors) are NEVER switchable. For non-native
    # roles: opencode is the standing default (role.backend), but a per-session global
    # switch via AGENT_EXEC_BACKEND env OVERRIDES it (so one Claude Code session can run
    # all workers on agy, another on grok, or fall off opencode when its 5h quota is spent).
    # CLI --backend (applied in main()) still has the final say. providers[*].backend uses
    # "*-cli" labels, not agent_exec keys, so it is only a last-resort default, not a source.
    env_be = os.environ.get("AGENT_EXEC_BACKEND")
    role_be = r.get("backend")
    if role_be == "native":
        r["backend"] = "native"
    else:
        r["backend"] = env_be or role_be or "opencode"
    # model_id: prefix opencode-go/ for opencode-provider models (matches oc_worker)
    model = str(r.get("model", ""))
    if prov == "opencode" and model and not model.startswith("opencode"):
        r["model_id"] = f"opencode-go/{model}"
    else:
        r["model_id"] = model
    r.setdefault("fallback", [])
    r.setdefault("allow_fallback", True)
    r.setdefault("read_only", False)
    r["_policy"] = policy
    return r


def backend_default(policy: dict, backend: str, key: str, default: Any = None) -> Any:
    bd = (policy.get("backend_defaults") or {}).get(backend) or {}
    return bd.get(key, default)


# ---- Backend chain ------------------------------------------------------------
def build_backend_chain(role: dict, no_fallback: bool) -> list[str]:
    """[primary] + role.fallback (de-duped, order-preserving) unless allow_fallback
    is False or --no-fallback."""
    primary = role["backend"]
    if no_fallback or not role.get("allow_fallback", True):
        return [primary]
    chain = [primary] + [b for b in (role.get("fallback") or []) if b != primary]
    seen: set[str] = set()
    out: list[str] = []
    for b in chain:
        if b not in seen:
            seen.add(b)
            out.append(b)
    return out


# ---- Error classification -----------------------------------------------------
def _matches(text: str, keywords: tuple[str, ...]) -> bool:
    t = (text or "").lower()
    return any(k in t for k in keywords)


def classify_failure(failure: dict | str) -> type[Exception] | None:
    """Return the fallback-able exception class for a failure, or None (real bug —
    no fallback). Checks timeout first (exit 124 / "timeout" text), then quota,
    then auth."""
    if isinstance(failure, dict):
        err = " ".join(filter(None, [
            str(failure.get("error") or ""),
            str(failure.get("stderr_tail") or ""),
            str(failure.get("stream_errors") or ""),
        ]))
        exit_code = failure.get("exit_code")
    else:
        err = str(failure)
        exit_code = None
    low = err.lower()
    if exit_code == 124 or "timeout" in low or "timed out" in low:
        return WorkerTimeout
    if _matches(err, _QUOTA_KEYWORDS):
        return QuotaExhausted
    if _matches(err, _AUTH_KEYWORDS):
        return AuthError
    return None


# ---- agy model map ------------------------------------------------------------
# agy models are addressed by display-style IDs, not the opencode-go/ names. This map
# bridges role.model -> an agy model id. Best-effort; --model overrides. The fallback
# is backend_defaults.agy.default_model ("claude-sonnet-4-6" per tier_policy).
AGY_MODEL_MAP: dict[str, str] = {
    "deepseek-v4-pro":   "claude-sonnet-4-6",
    "deepseek-v4-flash": "claude-sonnet-4-6",
    "mimo-v2.5":         "gemini-3.5-flash",
    "minimax-m3":        "claude-sonnet-4-6",
    "kimi-k2.7-code":    "claude-sonnet-4-6",
    "glm-5.2":           "gemini-3.5-flash",
}


def map_agy_model(role: dict, override: str | None, policy: dict) -> str:
    if override:
        return override
    # A role may pin its agy model explicitly (effort is model-fixed for agy, e.g.
    # "Gemini 3.5 Flash (Low|Medium|High)") via `agy_model`; that wins. Else map the
    # opencode-go name -> an agy id; else pass a raw value through (may already be a valid
    # agy display id); only fall to the backend default when nothing is set.
    pinned = role.get("agy_model")
    if pinned:
        return str(pinned)
    raw = str(role.get("model", ""))
    return AGY_MODEL_MAP.get(raw) or raw or backend_default(policy, "agy", "default_model")


# ---- grok model map -----------------------------------------------------------
# grok models map role.model to a supported grok CLI model name.
GROK_MODEL_MAP: dict[str, str] = {
    "deepseek-v4-pro":   "grok-composer-2.5-fast",
    "deepseek-v4-flash": "grok-composer-2.5-fast",
    "mimo-v2.5":         "grok-composer-2.5-fast",
    "minimax-m3":        "grok-composer-2.5-fast",
    "kimi-k2.7-code":    "grok-composer-2.5-fast",
    "glm-5.2":           "grok-composer-2.5-fast",
}


def map_grok_model(role: dict, override: str | None, policy: dict) -> str | None:
    if override:
        return override
    raw = str(role.get("model", ""))
    return GROK_MODEL_MAP.get(raw) or backend_default(policy, "grok", "default_model") or None


# ---- Command builders (pure; used by dry-run + dispatch) ---------------------
def _grok_command(role: dict, task: str, scope: str, slug: str | None, args: argparse.Namespace,
                  policy: dict, rule_card_text: str | None) -> list[str]:
    binary = backend_default(policy, "grok", "binary", "grok")
    read_only = bool(role.get("read_only")) or bool(args.read_only)
    prompt = build_prompt(task, rule_card_text, args.manifest,
                          slug=slug, scope=scope, read_only=read_only)
    model = map_grok_model(role, args.model, policy)
    effort = None
    if model != "grok-build":
        effort = (args.effort or role.get("variant") or role.get("effort")
                  or backend_default(policy, "grok", "default_effort"))
    cmd = [binary, "-p", prompt, "--output-format", "json", "--always-approve"]
    if model:
        cmd += ["--model", model]
    if effort:
        cmd += ["--effort", effort]
    cmd += ["--cwd", str(ROOT)]
    if read_only:
        cmd += ["--disallowed-tools", "edit,write"]
    if role.get("grok_agent"):
        cmd += ["--agent", role["grok_agent"]]
    return cmd



def _agy_command(role: dict, task: str, scope: str, slug: str | None, args: argparse.Namespace,
                 policy: dict, rule_card_text: str | None) -> list[str]:
    binary = backend_default(policy, "agy", "binary", "agy")
    read_only = bool(role.get("read_only")) or bool(args.read_only)
    prompt = build_prompt(task, rule_card_text, args.manifest,
                          slug=slug, scope=scope, read_only=read_only)
    model = map_agy_model(role, args.model, policy)
    cmd = [binary, "--print", prompt, "--dangerously-skip-permissions"]
    if model:
        cmd += ["--model", model]
    cmd += ["--add-dir", str(ROOT)]
    if read_only:
        cmd += ["--sandbox"]
    return cmd



def _opencode_command(role: dict, task: str, scope: str, slug: str | None,
                     args: argparse.Namespace) -> list[str]:
    read_only = bool(role.get("read_only")) or bool(args.read_only)
    prompt = build_prompt(task, _read_file(args.rule_card), args.manifest,
                          slug=slug, scope=scope, read_only=read_only)
    return build_command(role, prompt, scope, read_only, args.allow_edit,
                         args.attach, args.pure)


# ---- Backend dispatchers ------------------------------------------------------
def doThisTaskWithOpenCode(role: dict, task: str, scope: str, args: argparse.Namespace,
                           timeout: int, policy: dict) -> dict:
    """Delegate to scripts/oc_worker.py via subprocess. oc_worker re-resolves the role
    from tier_policy by key, builds the prompt (PREAMBLE + rule-card + manifest), runs
    `opencode run --format json`, parses NDJSON, and emits a compact blob on stdout.
    We parse that blob and add agent_exec fields.

    NOTE: oc_worker doesn't expose --model / --effort flags, so those overrides are
    advisory for the opencode backend (documented limitation; owner can extend
    oc_worker separately — agent_exec must not edit it). --backend is resolved here
    before dispatch; --rule-card / --manifest / --read-only / --allow-edit / --out /
    --attach / --pure are forwarded."""
    cmd = [
        sys.executable, str(ROOT / "scripts" / "oc_worker.py"),
        "--role", role["role"],
        "--scope", scope or "",
        "--prompt", task,
        "--timeout", str(timeout),
    ]
    if args.out:
        cmd += ["--out", args.out]
    if args.rule_card:
        cmd += ["--rule-card", args.rule_card]
    if args.manifest:
        cmd += ["--manifest", args.manifest]
    if args.slug:
        cmd += ["--slug", args.slug]
    if args.read_only:
        cmd += ["--read-only"]
    if args.allow_edit:
        cmd += ["--allow-edit"]
    if args.attach:
        cmd += ["--attach", args.attach]
    if args.pure:
        cmd += ["--pure"]
    _err(f"opencode: {' '.join(_redact(cmd, len(task)))}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout + 30, env=_worker_env(),
                              start_new_session=True)
    except FileNotFoundError as e:
        raise BackendUnavailable(f"python / oc_worker.py not found: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise WorkerTimeout(f"oc_worker subprocess timed out after {timeout + 30}s") from e

    # oc_worker emits one JSON blob on stdout (last non-blank { line).
    blob: dict | None = None
    for line in reversed((proc.stdout or "").splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                blob = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    if blob is None:
        # oc_worker crashed before emitting — real failure, no fallback.
        return {
            "ok": False, "backend": "opencode", "backend_used": "opencode",
            "role": role["role"], "model_id": role.get("model_id"),
            "scope": scope, "out": args.out, "exit_code": proc.returncode,
            "summary": "", "error": "oc_worker emitted no JSON blob",
            "stderr_tail": (proc.stderr or "").strip()[-600:],
            "stream_errors": None, "partial": False, "fallback_fired": False,
        }

    blob.setdefault("backend", "opencode")
    blob.setdefault("backend_used", "opencode")
    blob.setdefault("role", role["role"])
    blob.setdefault("model_id", role.get("model_id"))
    blob.setdefault("scope", scope)
    blob.setdefault("out", args.out)
    blob.setdefault("fallback_fired", False)

    if blob.get("ok"):
        return blob
    # Classify failure for fallback decision.
    exc = classify_failure(blob)
    if exc is WorkerTimeout:
        raise WorkerTimeout(blob.get("error") or "opencode timeout")
    if exc is QuotaExhausted:
        raise QuotaExhausted(blob.get("error") or "opencode quota exhausted")
    if exc is AuthError:
        raise AuthError(blob.get("error") or "opencode auth error")
    # Real bug — return failed blob, no fallback.
    return blob


def _run_cli_backend(backend: str, cmd: list[str], role: dict, scope: str,
                     args: argparse.Namespace, timeout: int,
                     parse_mode: str) -> dict:
    """Run a CLI backend (grok/agy) with timeout + process-group kill.
    parse_mode: 'ndjson' (grok --output-format json -> extract_text) or 'text'
    (agy --print -> raw stdout). Returns a blob on success or real-bug failure;
    raises fallback-able exceptions (Quota/Timeout/Auth/Unavailable) otherwise."""
    _err(f"{backend}: {' '.join(_redact(cmd, len(cmd[2]) if len(cmd) > 2 else 0))}")
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True, env=_worker_env())
    except FileNotFoundError as e:
        raise BackendUnavailable(f"{cmd[0]} CLI not found on PATH: {e}") from e
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _killpg(proc, signal.SIGTERM)
        try:
            out, err = proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            _killpg(proc, signal.SIGKILL)
            try:
                out, err = proc.communicate(timeout=10)
            except Exception:
                out, err = "", ""
        raise WorkerTimeout(f"{backend} timed out after {timeout}s")

    if proc.returncode != 0:
        err_text = (err or "").strip()
        exc_class = classify_failure({"error": err_text, "stderr_tail": err_text,
                                      "exit_code": proc.returncode})
        if exc_class is QuotaExhausted:
            raise QuotaExhausted(err_text[-400:] or f"{backend} quota exhausted")
        if exc_class is AuthError:
            raise AuthError(err_text[-400:] or f"{backend} auth error")
        # Real bug — failed blob, no fallback.
        return {
            "ok": False, "backend": backend, "backend_used": backend,
            "role": role["role"], "model_id": role.get("model_id"),
            "scope": scope, "out": args.out, "exit_code": proc.returncode,
            "summary": "", "error": f"{backend} exited {proc.returncode}",
            "stderr_tail": err_text[-600:] or None, "stream_errors": None,
            "partial": False, "fallback_fired": False,
        }

    # Success — parse output.
    if parse_mode == "ndjson":
        text, errors = extract_text(out or "")
    else:
        text, errors = (out or "").strip(), None
    _write_out(args.out, text or out)
    return {
        "ok": True, "backend": backend, "backend_used": backend,
        "role": role["role"], "model_id": role.get("model_id"),
        "scope": scope, "out": args.out, "exit_code": 0,
        "summary": summarize(text), "error": None,
        "stream_errors": (errors[:600] if errors else None),
        "stderr_tail": None, "partial": False, "fallback_fired": False,
    }


def doThisTaskWithGrok(role: dict, task: str, scope: str, args: argparse.Namespace,
                        timeout: int, policy: dict) -> dict:
    rule_card_text = _read_file(args.rule_card)
    cmd = _grok_command(role, task, scope, args.slug or None, args, policy, rule_card_text)
    return _run_cli_backend("grok", cmd, role, scope, args, timeout, parse_mode="ndjson")


def doThisTaskWithAntigravity(role: dict, task: str, scope: str, args: argparse.Namespace,
                               timeout: int, policy: dict) -> dict:
    rule_card_text = _read_file(args.rule_card)
    cmd = _agy_command(role, task, scope, args.slug or None, args, policy, rule_card_text)
    return _run_cli_backend("agy", cmd, role, scope, args, timeout, parse_mode="text")


def dispatch_to_backend(backend: str, role: dict, task: str, args: argparse.Namespace,
                        timeout: int) -> dict:
    policy = role["_policy"]
    scope = args.scope or ""
    if backend == "opencode":
        return doThisTaskWithOpenCode(role, task, scope, args, timeout, policy)
    if backend == "grok":
        return doThisTaskWithGrok(role, task, scope, args, timeout, policy)
    if backend == "agy":
        return doThisTaskWithAntigravity(role, task, scope, args, timeout, policy)
    if backend == "native":
        raise BackendUnavailable("native roles dispatch via Claude Task tool, not agent_exec")
    raise BackendUnavailable(f"unknown backend {backend!r}")


# ---- Orchestrator: doThisTask -------------------------------------------------
def _exit_code_for(blob: dict) -> int:
    if blob.get("ok"):
        return EX_OK
    if blob.get("exit_code") == 124:
        return EX_TIMEOUT
    return EX_WORKER_FAIL


def doThisTask(role: dict, task: str, args: argparse.Namespace, timeout: int) -> tuple[dict, int]:
    """The one interface: try primary backend -> fallback chain. Returns (blob, exit)."""
    chain = build_backend_chain(role, args.no_fallback)
    primary = chain[0]
    _err(f"role={role['role']} primary={primary} chain={chain} "
         f"fallback={'off' if args.no_fallback or not role.get('allow_fallback', True) else 'on'}")
    last_exc: Exception | None = None
    for i, backend in enumerate(chain):
        try:
            blob = dispatch_to_backend(backend, role, task, args, timeout)
            blob["backend"] = primary
            blob["backend_used"] = backend
            blob["fallback_fired"] = i > 0
            _err(f"backend {backend} OK: {(blob.get('summary') or '')[:120]}")
            return blob, _exit_code_for(blob)
        except (QuotaExhausted, WorkerTimeout, AuthError, BackendUnavailable) as e:
            last_exc = e
            if i + 1 < len(chain):
                _err(f"backend {backend} failed ({type(e).__name__}): {e}; trying fallback {chain[i + 1]}...")
            else:
                _err(f"backend {backend} failed ({type(e).__name__}): {e}; chain exhausted.")
            continue
    # All backends failed.
    blob = {
        "ok": False, "role": role["role"], "backend": primary, "backend_used": None,
        "fallback_fired": len(chain) > 1, "model_id": role.get("model_id"),
        "scope": args.scope or "", "out": args.out, "exit_code": None,
        "summary": "", "error": f"all backends failed (chain={chain}); last: {last_exc}",
        "stream_errors": None, "stderr_tail": None, "partial": False,
    }
    if isinstance(last_exc, WorkerTimeout):
        return blob, EX_TIMEOUT
    return blob, EX_ALL_BACKENDS_FAILED


# ---- Dry-run ------------------------------------------------------------------
def dry_run(role: dict, task: str, args: argparse.Namespace, timeout: int) -> int:
    chain = build_backend_chain(role, args.no_fallback)
    policy = role["_policy"]
    scope = args.scope or ""
    slug = args.slug or None
    rule_card_text = _read_file(args.rule_card)
    prompt_len = len(build_prompt(task, rule_card_text, args.manifest, slug=slug, scope=scope))
    commands: dict[str, list[str]] = {}
    for backend in chain:
        if backend == "opencode":
            commands[backend] = _redact(_opencode_command(role, task, scope, slug, args), prompt_len)
        elif backend == "grok":
            commands[backend] = _redact(_grok_command(role, task, scope, slug, args, policy, rule_card_text), prompt_len)
        elif backend == "agy":
            commands[backend] = _redact(_agy_command(role, task, scope, slug, args, policy, rule_card_text), prompt_len)
        elif backend == "native":
            commands[backend] = ["<native: refused — dispatch via Claude Task tool>"]
        else:
            commands[backend] = [f"<unknown backend {backend!r}>"]
    blob = {
        "ok": True, "dry_run": True, "role": role["role"],
        "backend": chain[0], "backend_used": chain[0], "fallback_fired": False,
        "model_id": role.get("model_id"), "scope": scope, "out": args.out,
        "exit_code": 0, "summary": f"dry-run; chain={chain}", "error": None,
        "stream_errors": None, "stderr_tail": None, "partial": False,
        "chain": chain, "commands": commands,
        "prompt_preview": build_prompt(task, rule_card_text, args.manifest, slug=slug, scope=scope)[:240],
    }
    _emit(blob)
    _err(f"dry-run role={role['role']} backend={chain[0]} chain={chain}")
    for b, c in commands.items():
        _err(f"dry-run {b}: {' '.join(c)}")
    return EX_OK


# ---- Self-test ----------------------------------------------------------------
def _fake_args(**kw: Any) -> argparse.Namespace:
    base: dict[str, Any] = dict(
        model=None, effort=None, read_only=False, allow_edit=False,
        rule_card=None, manifest=None, out=None, attach=None, pure=False,
        scope="", slug="", prompt="", prompt_file=None, backend=None, no_fallback=False,
        dry_run=False, timeout=900,
    )
    base.update(kw)
    return argparse.Namespace(**base)


def self_test() -> int:
    checks: list[tuple[bool, str]] = []

    def check(cond: bool, msg: str) -> None:
        checks.append((bool(cond), msg))
        print(f"  {'PASS' if cond else 'FAIL'}: {msg}")

    # 1. Role resolution.
    audit = resolve_role("audit")
    check(audit.get("backend") == "opencode", f"audit backend=opencode (got {audit.get('backend')})")
    check(audit.get("model_id") == "opencode-go/glm-5.2", f"audit model_id (got {audit.get('model_id')})")
    check(audit.get("read_only") is True, "audit read_only=True")
    check(audit.get("allow_fallback") is False, "audit allow_fallback=False")
    check(audit.get("fallback") == [], "audit fallback empty")

    primary = resolve_role("agentic_primary")
    # Owner routing (2026-06-29): opencode is the standing default; agy/grok are alternates
    # (per-session via AGENT_EXEC_BACKEND, or quota fallback). The agentic roles pin an
    # `agy_model` (Gemini 3.5 Flash Low/Med/High) used only when the backend resolves to agy.
    check(primary.get("backend") == "opencode", f"agentic_primary backend=opencode (got {primary.get('backend')})")
    check(primary.get("model_id") == "opencode-go/deepseek-v4-pro",
          f"agentic_primary model_id (got {primary.get('model_id')})")
    check(primary.get("fallback") == ["agy", "grok"], f"agentic_primary fallback (got {primary.get('fallback')})")
    check(primary.get("agy_model") == "Gemini 3.5 Flash (Low)", "agentic_primary pins agy_model Low")
    check(primary.get("allow_fallback") is True, "agentic_primary allow_fallback=True")
    check(primary.get("read_only") is False, "agentic_primary read_only=False")
    # Per-session env switch: AGENT_EXEC_BACKEND overrides non-native backend; native protected.
    _saved = os.environ.get("AGENT_EXEC_BACKEND")
    os.environ["AGENT_EXEC_BACKEND"] = "agy"
    try:
        check(resolve_role("agentic_primary")["backend"] == "agy", "env AGENT_EXEC_BACKEND=agy switches non-native role")
        check(resolve_role("final_review")["backend"] == "native", "env switch never overrides native role")
    finally:
        if _saved is None:
            os.environ.pop("AGENT_EXEC_BACKEND", None)
        else:
            os.environ["AGENT_EXEC_BACKEND"] = _saved
    # Synthetic opencode role for backend-mechanism tests (decoupled from live routing).
    oc_role = {"model": "deepseek-v4-pro", "variant": "high", "backend": "opencode",
               "fallback": ["grok", "agy"], "allow_fallback": True, "read_only": False,
               "_policy": primary["_policy"]}

    fr = resolve_role("final_review")
    check(fr.get("backend") == "native", f"final_review backend=native (got {fr.get('backend')})")
    check(fr.get("provider") == "anthropic", "final_review provider=anthropic")

    # 2. Backend chain building.
    check(build_backend_chain(oc_role, False) == ["opencode", "grok", "agy"],
          f"chain order (got {build_backend_chain(oc_role, False)})")
    check(build_backend_chain(oc_role, True) == ["opencode"],
          f"--no-fallback -> primary only (got {build_backend_chain(oc_role, True)})")
    check(build_backend_chain(primary, False) == ["opencode", "agy", "grok"],
          f"agentic_primary chain opencode->agy->grok (got {build_backend_chain(primary, False)})")
    check(build_backend_chain(audit, False) == ["opencode"],
          f"audit allow_fallback=False -> primary only (got {build_backend_chain(audit, False)})")

    # 3. PREAMBLE import from oc_worker.
    check(PREAMBLE.startswith("SUBAGENT IDENTITY:"), "PREAMBLE imported from oc_worker")
    check("HYDRATION IS MANDATORY" in PREAMBLE, "PREAMBLE has HYDRATION marker")
    check("TLDR:" in PREAMBLE, "PREAMBLE enforces TLDR")

    # 4. Command builders (dry-run shape).
    policy = primary["_policy"]
    args_mut = _fake_args(allow_edit=True)
    gcmd = _grok_command(oc_role, "fix bug", "wt/x/be", "x", args_mut, policy, None)
    check(gcmd[0] == "grok", f"grok binary (got {gcmd[0]})")
    check("-p" in gcmd and "--output-format" in gcmd and "json" in gcmd and "--always-approve" in gcmd, "grok -p --output-format json --always-approve")
    check("--model" in gcmd and "grok-composer-2.5-fast" in gcmd, "grok --model mapped (deepseek-v4-pro -> grok-composer-2.5-fast)")
    check("--effort" in gcmd and "high" in gcmd, "grok --effort from role.variant")
    check("--cwd" in gcmd and any("/roast" in c for c in gcmd), "grok --cwd <ROOT>")

    gcmd_ro = _grok_command(audit, "review", "wt/x/be", "x", _fake_args(read_only=True), policy, None)
    check("--disallowed-tools" in gcmd_ro and "edit,write" in gcmd_ro, "grok read-only -> --disallowed-tools edit,write")
    check("--effort" in gcmd_ro and "max" in gcmd_ro, "grok audit effort=max from variant")

    acmd = _agy_command(oc_role, "fix bug", "wt/x/be", "x", args_mut, policy, None)
    check(acmd[0] == "agy", f"agy binary (got {acmd[0]})")
    check("--print" in acmd, "agy --print")
    check("--model" in acmd and "claude-sonnet-4-6" in acmd, "agy --model mapped (deepseek-v4-pro -> claude-sonnet-4-6)")
    # agentic_primary now carries an agy display id directly -> passes through unchanged.
    acmd_primary = _agy_command(primary, "fix bug", "wt/x/be", "x", args_mut, policy, None)
    check("--model" in acmd_primary and "Gemini 3.5 Flash (Low)" in acmd_primary,
          "agy uses the role's gemini display id directly")
    check("--add-dir" in acmd and any("/roast" in c for c in acmd), "agy --add-dir <ROOT>")

    acmd_ro = _agy_command(audit, "review", "wt/x/be", "x", _fake_args(read_only=True), policy, None)
    check("--sandbox" in acmd_ro, "agy read-only -> --sandbox")
    check("--dangerously-skip-permissions" in acmd_ro, "agy read-only -> has skip-perms")

    check("gemini-3.5-flash" in acmd_ro, "agy audit model mapped (glm-5.2 -> gemini-3.5-flash)")

    ocmd = _opencode_command(audit, "review this file", "wt/ipd-improve-v5/be", "x", _fake_args())
    check(ocmd[0] == "opencode" and "run" in ocmd[:2], f"opencode delegates via build_command (got {ocmd[:3]})")
    check("-m" in ocmd and "opencode-go/glm-5.2" in ocmd, "opencode -m <model_id>")
    check("--agent" in ocmd and "mh-reviewer-oc" in ocmd, "opencode read-only -> mh-reviewer-oc agent")
    check("--format" in ocmd and "json" in ocmd, "opencode --format json")
    check("--variant" in ocmd and "max" in ocmd, "opencode --variant from role")
    check("--dangerously-skip-permissions" not in ocmd, "opencode no blanket skip-perms")
    ocmd_mut = _opencode_command(primary, "fix", "wt/x", None, _fake_args(allow_edit=True))
    check("mh-fixer" in ocmd_mut, "opencode mutating -> mh-fixer agent")

    # 5. Error classification.
    check(classify_failure({"error": "rate limit exceeded", "exit_code": 1}) is QuotaExhausted, "rate limit -> QuotaExhausted")
    check(classify_failure({"error": "402 payment required", "exit_code": 1}) is QuotaExhausted, "402 -> QuotaExhausted")
    check(classify_failure({"error": "429 too many requests", "exit_code": 1}) is QuotaExhausted, "429 -> QuotaExhausted")
    check(classify_failure({"error": "quota exhausted", "exit_code": 1}) is QuotaExhausted, "quota -> QuotaExhausted")
    check(classify_failure({"error": "timeout after 900s", "exit_code": 124}) is WorkerTimeout, "timeout text -> WorkerTimeout")
    check(classify_failure({"error": "x", "exit_code": 124}) is WorkerTimeout, "exit 124 -> WorkerTimeout")
    check(classify_failure({"error": "process timed out", "exit_code": 1}) is WorkerTimeout, "timed out -> WorkerTimeout")
    check(classify_failure({"error": "401 unauthorized", "exit_code": 1}) is AuthError, "401 -> AuthError")
    check(classify_failure({"error": "403 forbidden", "exit_code": 1}) is AuthError, "403 -> AuthError")
    check(classify_failure({"error": "invalid api key", "exit_code": 1}) is AuthError, "api key -> AuthError")
    check(classify_failure({"error": "TypeError: cannot read undefined", "exit_code": 1}) is None, "real bug -> None (no fallback)")
    check(classify_failure({"error": "syntax error in file foo.cs", "exit_code": 1}) is None, "syntax error -> None (no fallback)")
    check(classify_failure({"error": "AssertionError in test", "exit_code": 1}) is None, "test failure -> None (no fallback)")

    # 6. agy model map.
    # Decoupled from live role definitions (those now carry agy display ids).
    check(map_agy_model({"model": "deepseek-v4-pro"}, None, policy) == "claude-sonnet-4-6",
          "agy map deepseek-v4-pro -> claude-sonnet-4-6")
    check(map_agy_model({"model": "glm-5.2"}, None, policy) == "gemini-3.5-flash",
          "agy map glm-5.2 -> gemini-3.5-flash")
    check(map_agy_model({"model": "deepseek-v4-pro"}, "custom-model", policy) == "custom-model",
          "agy --model override wins")
    check(map_agy_model({"model": "deepseek-v4-pro"}, None, policy) != "deepseek-v4-pro",
          "agy map actually transforms opencode name (not raw)")
    check(map_agy_model({"model": "Gemini 3.5 Flash (Low)"}, None, policy) == "Gemini 3.5 Flash (Low)",
          "agy passes a valid agy display id through unchanged")




    # 8. Refuse native backend (resolve + main()-level check simulated).
    check(fr["backend"] == "native", "final_review resolves native (would be refused in main)")
    check(resolve_role("clinical_floor")["backend"] == "native", "clinical_floor resolves native")
    check(resolve_role("danger_refactor")["backend"] == "native", "danger_refactor resolves native")

    # PREAMBLE applied to grok/agy prompt via build_prompt (reused, no duplicate).
    gp = build_prompt("do task", None, None)
    check(gp.startswith(PREAMBLE), "build_prompt prepends PREAMBLE (reused for grok/agy)")
    check("## Task" in gp and "do task" in gp, "build_prompt appends task section")

    # build_prompt with rule-card + manifest.
    gp2 = build_prompt("do task", "RULE-X: do Y", "/path/manifest.md")
    check("## Convention contract" in gp2 and "RULE-X" in gp2, "build_prompt injects rule-card")
    check("## Context manifest" in gp2 and "/path/manifest.md" in gp2, "build_prompt injects manifest path")

    # build_prompt with slug: WORKTREE SETUP prepended before PREAMBLE.
    gp3 = build_prompt("do task", "RULE-X: do Y", None, slug="x", scope="worktrees/x/be")
    check("## WORKTREE SETUP" in gp3 and "x" in gp3 and "## Convention contract" in gp3,
          "build_prompt with slug adds WORKTREE SETUP + rule cards")
    check(not gp3.startswith(PREAMBLE) and "## WORKTREE SETUP" in gp3[:40],
          "build_prompt with slug: WORKTREE SETUP precedes PREAMBLE")

    # build_prompt dev/review: write path has PATTERN HYDRATION, read path has RULES HYDRATION only.
    gp4 = build_prompt("dev", "R", None, slug="x", scope="worktrees/x/be", read_only=False)
    check("PATTERN HYDRATION" in gp4 and "RULES + PATTERN HYDRATION" in gp4,
          "build_prompt dev mode has PATTERN HYDRATION")
    gp5 = build_prompt("review", "R", None, slug="x", scope="worktrees/x/be", read_only=True)
    check("RULES HYDRATION (review task)" in gp5 and "PATTERN HYDRATION" not in gp5,
          "build_prompt review mode has RULES HYDRATION only, no PATTERN HYDRATION")

    failed = [m for ok, m in checks if not ok]
    print(f"\nagent_exec self-test: {'OK' if not failed else 'FAIL'} "
          f"({len(checks)} assertions, {len(failed)} failed)")
    return 0 if not failed else 1


# ---- CLI ----------------------------------------------------------------------
def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Agentic coding tool adapter: 3 backends (opencode/grok/agy) + fallback chain.",
    )
    p.add_argument("--role", help="role key from tier_policy.json roles")
    p.add_argument("--scope", default="", help="working directory passed to the worker (worktree)")
    p.add_argument("--slug", default="", help="worktree slug for join + rule hydration")
    p.add_argument("--prompt", default="", help="inline task text (or use --prompt-file)")
    p.add_argument("--prompt-file", help="path to a file containing the task")
    p.add_argument("--backend", choices=["opencode", "grok", "agy", "native"],
                   help="override role.backend")
    p.add_argument("--model", help="override role.model (grok/agy; opencode delegate doesn't expose --model)")
    p.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"],
                   help="override role.effort/variant (grok; agy effort is model-fixed)")
    p.add_argument("--rule-card", help="path to rule-card injected as the convention contract")
    p.add_argument("--manifest", help="context-manifest path (referenced, not inlined)")
    p.add_argument("--read-only", action="store_true", help="force read-only (no edit/write)")
    p.add_argument("--allow-edit", action="store_true", help="explicit mutating intent (advisory)")
    p.add_argument("--out", help="artifact path to write the worker output")
    p.add_argument("--timeout", type=int, default=900, help="seconds before killing the run + its process group")
    p.add_argument("--no-fallback", action="store_true", help="disable fallback chain (primary backend only)")
    p.add_argument("--attach", help="(opencode) attach to a warm `opencode serve`")
    p.add_argument("--pure", action="store_true", help="(opencode) skip external plugins for speed")
    p.add_argument("--dry-run", action="store_true", help="print resolved command + blob, no exec")
    p.add_argument("--self-test", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.role:
        _err("--role is required (or --self-test)")
        return EX_CONFIG

    # Resolve scope to absolute path to prevent CLI tools (like grok) from failing
    if args.scope:
        args.scope = str(Path(args.scope).resolve())

    # Auto-extract slug from scope path if not explicitly provided.
    # e.g. scope=worktrees/combine-his-pacs/be → slug=combine-his-pacs
    if not args.slug and args.scope:
        p = Path(args.scope)
        parts = p.parts
        try:
            wt_idx = parts.index("worktrees")
            if wt_idx + 1 < len(parts):
                args.slug = parts[wt_idx + 1]
        except ValueError:
            pass

    role = resolve_role(args.role)

    if not role.get("model"):
        _emit({"ok": False, "role": args.role, "error": f"unknown role {args.role!r}"})
        return EX_CONFIG

    # --backend override (highest precedence).
    if args.backend:
        role["backend"] = args.backend

    if role["backend"] == "native":
        _emit({
            "ok": False, "role": args.role, "backend": "native",
            "backend_used": None, "fallback_fired": False,
            "model_id": role.get("model_id"), "scope": args.scope, "out": args.out,
            "exit_code": None, "summary": "", "partial": False,
            "error": "native roles dispatch via Claude Task tool, not agent_exec",
        })
        return EX_NATIVE_REFUSED

    # Read task.
    try:
        task = args.prompt or (Path(args.prompt_file).read_text("utf-8") if args.prompt_file else "")
    except OSError as e:
        _emit({"ok": False, "role": args.role, "error": f"cannot read prompt file: {e}"})
        return EX_CONFIG
    if not task.strip():
        _emit({"ok": False, "role": args.role, "error": "empty task (need --prompt or --prompt-file)"})
        return EX_CONFIG

    # Prompt-keyword backend PROMOTE (only when not explicitly overridden via CLI):
    # an explicit "grok"/"agy" mention in the task forces that backend. Otherwise honor
    # the backend resolved from tier_policy (role.backend) — do NOT hard-default to
    # opencode, which would silently ignore a role's configured backend (e.g. agy).
    if role["backend"] != "native" and not args.backend and not os.environ.get("AGENT_EXEC_BACKEND"):
        task_lower = task.lower()
        if "grok" in task_lower:
            role["backend"] = "grok"
        elif "agy" in task_lower or "antigravity" in task_lower:
            role["backend"] = "agy"


    if args.dry_run:
        return dry_run(role, task, args, args.timeout)

    blob, exit_code = doThisTask(role, task, args, args.timeout)
    _emit(blob)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
