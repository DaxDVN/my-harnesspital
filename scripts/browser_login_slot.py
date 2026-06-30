#!/usr/bin/env python3
"""Drive agent-browser to log in to a MyHospital slot FE.

Credential is DATA, not code: it is parsed from `engine/rules/session-boot-details.md`
every run (never hardcoded). The script is only a driver: it reads the credential,
resolves the slot FE URL, and issues `agent-browser` subprocess commands to
navigate + fill + submit + verify.

Per session-boot-details.md: the ONLY permitted browser-test credential is
bvtest3 / lynkhanh9822@gmail.com / 12.[s7HXZQ;NfAoF (TenantId=6, HospitalId=7).
Do NOT use the e2e HMU_ADMIN account — it is a different tenant and lacks
bed/inpatient/schedule permissions (produces false no-permission results).

Usage:
    python scripts/browser_login_slot.py <slot> [--url <override>] [--dry-run] [--self-test]

`<slot>` may be a slot number (1-4) or a worktree slug. Slot map:
  1 -> http://localhost:3001, 2 -> 3002, 3 -> 3003, 4 -> 3004.
`--url` overrides the resolved URL. `--dry-run` prints the command plan without
launching agent-browser.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CREDENTIAL_FILE = ROOT / "engine" / "rules" / "session-boot-details.md"
PYTHON = sys.executable

SLOT_FE_PORTS = {1: 3001, 2: 3002, 3: 3003, 4: 3004}

# Login form selectors (signin-page.tsx): input names are code/username/password.
SIGNIN_PATH = "/auth/signin"
SELECTOR_CODE = 'input[name="code"]'
SELECTOR_USERNAME = 'input[name="username"]'
SELECTOR_PASSWORD = 'input[name="password"]'
SELECTOR_SUBMIT = 'button[type="submit"]'


# ---------------------------------------------------------------------------
# Credential parsing (data, not hardcoded)
# ---------------------------------------------------------------------------

def parse_credentials(text: str) -> dict[str, str]:
    """Parse the bvtest3 credential block from session-boot-details.md.

    Expected lines (inside a code block):
        customer code: bvtest3
        username: lynkhanh9822@gmail.com
        password: 12.[s7HXZQ;NfAoF
        tenant: bvtest3 -> TenantId = 6, HospitalId = 7
    """
    creds: dict[str, str] = {}
    # Pull the fenced code block that contains the credential lines.
    m = re.search(r"```text\n(.*?customer code:.*?tenant:.*?)\n```", text, re.S | re.I)
    block = m.group(1) if m else text
    for line in block.splitlines():
        low = line.lower()
        if low.startswith("customer code:"):
            creds["code"] = line.split(":", 1)[1].strip()
        elif low.startswith("username:"):
            creds["username"] = line.split(":", 1)[1].strip()
        elif low.startswith("password:"):
            # password may contain colons — split on first only.
            creds["password"] = line.split(":", 1)[1].strip()
        elif low.startswith("tenant:"):
            creds["tenant"] = line.split(":", 1)[1].strip()
    return creds


def load_credentials() -> dict[str, str]:
    if not CREDENTIAL_FILE.exists():
        raise FileNotFoundError(f"credential file not found: {CREDENTIAL_FILE}")
    creds = parse_credentials(CREDENTIAL_FILE.read_text(encoding="utf-8"))
    missing = [k for k in ("code", "username", "password") if not creds.get(k)]
    if missing:
        raise ValueError(f"credential file missing fields {missing}: {CREDENTIAL_FILE}")
    return creds


# ---------------------------------------------------------------------------
# Slot -> URL resolution
# ---------------------------------------------------------------------------

def resolve_slot_url(slot: str) -> tuple[str, dict[str, Any] | None]:
    """Resolve a slot number or slug to a FE URL.

    Returns (url, info) where info is the parsed worktree.py info row (or None
    for a bare slot number).
    """
    if slot.isdigit() and int(slot) in SLOT_FE_PORTS:
        return f"http://localhost:{SLOT_FE_PORTS[int(slot)]}{SIGNIN_PATH}", None

    # Treat as slug: ask worktree.py info.
    proc = subprocess.run(
        [PYTHON, "scripts/worktree.py", "info", "--slug", slot],
        cwd=str(ROOT), stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20,
    )
    if proc.returncode != 0:
        raise FileNotFoundError(
            f"worktree.py info --slug {slot!r} failed: {(proc.stderr or proc.stdout).strip()}"
        )
    info: dict[str, Any] = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            info[k.strip()] = v.strip()
    fe_url = info.get("fe_url")
    if not fe_url:
        raise ValueError(f"no fe_url in worktree.py info for slug {slot!r}: {info}")
    return f"{fe_url}{SIGNIN_PATH}", info


# ---------------------------------------------------------------------------
# agent-browser driver
# ---------------------------------------------------------------------------

def ab_run(argv: list[str], *, dry_run: bool, timeout: int = 60) -> tuple[int, str, str]:
    """Run an agent-browser command."""
    print(f"> agent-browser {' '.join(argv)}", file=sys.stderr)
    if dry_run:
        return 0, "(dry-run)", ""
    try:
        proc = subprocess.run(
            ["agent-browser", *argv], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    return proc.returncode, proc.stdout, proc.stderr


def drive_login(url: str, creds: dict[str, str], *, dry_run: bool) -> dict[str, Any]:
    """Run the agent-browser login flow. Returns a result dict."""
    result: dict[str, Any] = {"steps": [], "errors": [], "logged_in": False, "final_url": ""}

    # 1. navigate
    rc, out, err = ab_run(["open", url], dry_run=dry_run)
    result["steps"].append(f"open {url} -> rc={rc}")
    if rc != 0:
        result["errors"].append(f"open failed: {(err or out).strip()}")
        return result

    # 2. fill customer code (only visible on fresh/untrusted browser).
    rc, out, err = ab_run(["fill", SELECTOR_CODE, creds["code"]], dry_run=dry_run)
    result["steps"].append(f"fill code -> rc={rc}")
    if rc != 0 and not dry_run:
        # The code field is hidden when the browser is trusted; treat as non-fatal.
        result["steps"].append("  (code field not visible on trusted browser — skipped)")

    # 3. fill username
    rc, out, err = ab_run(["fill", SELECTOR_USERNAME, creds["username"]], dry_run=dry_run)
    result["steps"].append(f"fill username -> rc={rc}")
    if rc != 0:
        result["errors"].append(f"fill username failed: {(err or out).strip()}")
        return result

    # 4. fill password
    rc, out, err = ab_run(["fill", SELECTOR_PASSWORD, creds["password"]], dry_run=dry_run)
    result["steps"].append(f"fill password -> rc={rc}")
    if rc != 0:
        result["errors"].append(f"fill password failed: {(err or out).strip()}")
        return result

    # 5. submit
    rc, out, err = ab_run(["click", SELECTOR_SUBMIT], dry_run=dry_run)
    result["steps"].append(f"click submit -> rc={rc}")
    if rc != 0:
        result["errors"].append(f"click submit failed: {(err or out).strip()}")
        return result

    # 6. wait for navigation away from /auth/
    rc, out, err = ab_run(["wait", "3000"], dry_run=dry_run, timeout=15)
    result["steps"].append(f"wait -> rc={rc}")

    # 7. verify via eval (current pathname should NOT start with /auth/)
    rc, out, err = ab_run(["eval", "location.pathname"], dry_run=dry_run)
    result["steps"].append(f"eval pathname -> rc={rc}")
    if rc == 0 and not dry_run:
        path = out.strip().strip('"').strip("'")
        result["final_url"] = path
        if path and not path.startswith("/auth/"):
            result["logged_in"] = True
        else:
            result["errors"].append(
                f"login verification failed: still on /auth/ (path={path!r}). "
                "Credential may be invalid or the form did not submit."
            )
    elif dry_run:
        result["logged_in"] = None  # unknown

    return result


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render_result(slot: str, url: str, creds: dict[str, str], result: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("=== agent-browser slot login ===")
    lines.append(f"Slot/input: {slot}")
    lines.append(f"URL: {url}")
    lines.append(f"Customer code: {creds.get('code', '?')}")
    lines.append(f"Username: {creds.get('username', '?')}")
    lines.append(f"Tenant: {creds.get('tenant', '?')}")
    lines.append("")
    lines.append("Steps:")
    for s in result.get("steps", []):
        lines.append(f"  {s}")
    lines.append("")
    if result.get("logged_in") is True:
        lines.append(f"RESULT: login OK (final path={result.get('final_url', '?')})")
    elif result.get("logged_in") is None:
        lines.append("RESULT: (dry-run — login not executed)")
    else:
        lines.append("RESULT: login FAILED")
    if result.get("errors"):
        lines.append("")
        lines.append("Errors:")
        for e in result["errors"]:
            lines.append(f"  ! {e}")
        lines.append("")
        lines.append("Hint: if the code field was required but missing, the browser may be")
        lines.append("      trusted from a prior session. Run `agent-browser close --all` and retry.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def self_test() -> int:
    # parse_credentials on the real file
    assert CREDENTIAL_FILE.exists(), CREDENTIAL_FILE
    creds = load_credentials()
    assert creds["code"] == "bvtest3", creds
    assert creds["username"] == "lynkhanh9822@gmail.com", creds
    assert creds["password"] == "12.[s7HXZQ;NfAoF", creds
    assert "TenantId" in creds.get("tenant", ""), creds

    # parse_credentials on a synthetic block
    synthetic = (
        "## Local Agent Browser Smoke Login\n\n"
        "```text\n"
        "customer code: bvtest3\n"
        "username: lynkhanh9822@gmail.com\n"
        "password: 12.[s7HXZQ;NfAoF\n"
        "tenant: bvtest3 -> TenantId = 6, HospitalId = 7\n"
        "```\n"
    )
    c2 = parse_credentials(synthetic)
    assert c2["code"] == "bvtest3" and c2["username"] == "lynkhanh9822@gmail.com", c2
    assert c2["password"] == "12.[s7HXZQ;NfAoF", c2

    # resolve_slot_url: bare slot numbers
    for slot, port in SLOT_FE_PORTS.items():
        url, info = resolve_slot_url(str(slot))
        assert url == f"http://localhost:{port}{SIGNIN_PATH}", (slot, url)
        assert info is None

    # invalid slot number
    try:
        resolve_slot_url("9")
        raise AssertionError("expected error for slot 9")
    except (ValueError, FileNotFoundError):
        pass

    # agent-browser availability check (does not require launching it)
    available = shutil.which("agent-browser") is not None
    print(f"  agent-browser on PATH: {available}")

    # render_result smoke
    out = render_result("3", "http://localhost:3003/auth/signin", creds,
                        {"steps": ["open -> rc=0"], "errors": [], "logged_in": True, "final_url": "/dashboard"})
    assert "login OK" in out and "bvtest3" in out, out

    print("browser_login_slot self-test: OK")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Drive agent-browser to log in to a MyHospital slot FE (credential from session-boot-details.md)."
    )
    parser.add_argument("slot", nargs="?", help="Slot number (1-4) or worktree slug.")
    parser.add_argument("--url", help="Override the resolved signin URL.")
    parser.add_argument("--dry-run", action="store_true", help="Print the agent-browser plan without executing.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    if not args.slot:
        parser.error("provide a slot number (1-4) or worktree slug")

    # Credential (data, parsed fresh each run)
    try:
        creds = load_credentials()
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # URL
    url = args.url
    info: dict[str, Any] | None = None
    if not url:
        try:
            url, info = resolve_slot_url(args.slot)
        except (FileNotFoundError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    elif not url.endswith(SIGNIN_PATH) and SIGNIN_PATH not in url:
        # If the override is a bare origin, append the signin path.
        url = url.rstrip("/") + SIGNIN_PATH

    # agent-browser must be available
    if not args.dry_run and shutil.which("agent-browser") is None:
        print("ERROR: agent-browser not found on PATH.", file=sys.stderr)
        print("Install hint: see the agent-browser CLI docs / your harness setup.", file=sys.stderr)
        return 1

    result = drive_login(url, creds, dry_run=args.dry_run)
    print(render_result(args.slot, url, creds, result))

    if result.get("errors"):
        return 1
    if result.get("logged_in") is False:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
