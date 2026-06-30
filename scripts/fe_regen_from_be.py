#!/usr/bin/env python3
"""Regenerate FE DTOs + API client after a BE contract change.

Pipeline:
  1. Detect FE/BE paths (worktrees/<slug>/{fe,be} or myhospital-{fe,be}).
  2. Read `myhospital-fe/package.json` scripts to find the REAL command names
     for DTO update + client generation + typecheck (never assume).
  3. Snapshot `git status --short` in the FE path (before).
  4. Run `npm run <dtos-cmd>` then `npm run <client-cmd>` in the FE path.
  5. Snapshot `git status --short` again; the diff = regenerated files.
  6. Validate via the typecheck command (warn, not fail, on typecheck failure).

Usage:
    python scripts/fe_regen_from_be.py --be-path worktrees/ipd-v5/be [--fe-path worktrees/ipd-v5/fe] \
        [--dry-run] [--skip-validate] [--self-test]

The script does NOT edit source itself; it only invokes the project's own
codegen scripts via `npm run`. Generated files (DTOs/Constants/client) are
ignored by the harness review discipline and are not reported as violations.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Path detection
# ---------------------------------------------------------------------------

def detect_paths(be_path: str | None, fe_path: str | None) -> tuple[Path, Path]:
    if be_path:
        be = Path(be_path).resolve()
    else:
        be = (ROOT / "myhospital-be").resolve()
    if fe_path:
        fe = Path(fe_path).resolve()
    else:
        # Default to sibling `fe` under the same worktree task root, else main FE.
        if be.name == "be" and be.parent.name != "":
            sibling_fe = be.parent / "fe"
            fe = sibling_fe.resolve() if sibling_fe.exists() else (ROOT / "myhospital-fe").resolve()
        else:
            fe = (ROOT / "myhospital-fe").resolve()
    if not fe.exists():
        raise FileNotFoundError(f"FE path not found: {fe}")
    if not be.exists():
        raise FileNotFoundError(f"BE path not found: {be}")
    return fe, be


# ---------------------------------------------------------------------------
# package.json script discovery (never assume names)
# ---------------------------------------------------------------------------

DTO_CANDIDATES = ["dtos:update", "dtos:sync", "dtos:pull", "update:dtos", "generate:dtos", "dtos:generate"]
CLIENT_CANDIDATES = ["client:generate", "generate:client", "client:gen", "openapi:generate", "api:generate", "generate:api"]
TYPECHECK_CANDIDATES = ["typecheck", "type-check", "tsc", "typecheck:watch", "check-types"]


def load_package_scripts(fe_path: Path) -> dict[str, str]:
    pkg = fe_path / "package.json"
    if not pkg.exists():
        raise FileNotFoundError(f"package.json not found in FE path: {pkg}")
    data = json.loads(pkg.read_text(encoding="utf-8"))
    scripts = data.get("scripts", {})
    if not isinstance(scripts, dict):
        raise ValueError(f"package.json `scripts` is not an object in {pkg}")
    return {str(k): str(v) for k, v in scripts.items()}


def pick_script(scripts: dict[str, str], candidates: list[str], label: str) -> str:
    for name in candidates:
        if name in scripts:
            return name
    raise KeyError(
        f"no {label} script found in package.json. Tried: {', '.join(candidates)}. "
        f"Available scripts: {', '.join(sorted(scripts))}"
    )


def find_typecheck_script(scripts: dict[str, str]) -> str | None:
    for name in TYPECHECK_CANDIDATES:
        if name in scripts:
            return name
    return None


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

def _run(argv: list[str], *, cwd: Path, dry_run: bool, timeout: int = 300) -> tuple[int, str, str]:
    marker = "(dry-run)" if dry_run else ""
    print(f"> {' '.join(argv)}  (cwd={cwd}) {marker}".rstrip(), file=sys.stderr)
    if dry_run:
        return 0, "(dry-run)", ""
    try:
        proc = subprocess.run(
            argv, cwd=str(cwd), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    return proc.returncode, proc.stdout, proc.stderr


def git_status_short(fe_path: Path) -> set[str]:
    """Return the set of `git status --short` entries (first 2 cols + path)."""
    proc = subprocess.run(
        ["git", "-C", str(fe_path), "status", "--short"],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    )
    return {line.rstrip() for line in proc.stdout.splitlines() if line.strip()}


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    *, be_path: str | None, fe_path: str | None, dry_run: bool, skip_validate: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {"errors": [], "warnings": [], "regenerated_files": [], "dry_run": dry_run}

    fe, be = detect_paths(be_path, fe_path)
    result["fe_path"] = str(fe)
    result["be_path"] = str(be)

    scripts: dict[str, str] = {}
    try:
        scripts = load_package_scripts(fe)
    except (FileNotFoundError, ValueError) as exc:
        result["errors"].append(str(exc))
        return result

    # Discover command names.
    try:
        dtos_cmd = pick_script(scripts, DTO_CANDIDATES, "DTO update")
    except KeyError as exc:
        result["errors"].append(str(exc))
        return result
    try:
        client_cmd = pick_script(scripts, CLIENT_CANDIDATES, "client generate")
    except KeyError as exc:
        result["errors"].append(str(exc))
        return result
    typecheck_cmd = find_typecheck_script(scripts)
    result["dtos_command"] = dtos_cmd
    result["client_command"] = client_cmd
    result["typecheck_command"] = typecheck_cmd or "(none found)"

    # Snapshot before
    before = git_status_short(fe) if not dry_run else set()

    # 1. dtos:update
    rc, out, err = _run(["npm", "run", dtos_cmd], cwd=fe, dry_run=dry_run)
    if rc != 0:
        result["errors"].append(f"`npm run {dtos_cmd}` failed (rc={rc}): {(err or out).strip()}")
        # Still try client gen? No — client depends on DTOs. Stop.
        return result
    result["dtos_ok"] = True

    # 2. client:generate
    rc, out, err = _run(["npm", "run", client_cmd], cwd=fe, dry_run=dry_run)
    if rc != 0:
        result["errors"].append(f"`npm run {client_cmd}` failed (rc={rc}): {(err or out).strip()}")
        return result
    result["client_ok"] = True

    # 3. diff
    after = git_status_short(fe) if not dry_run else set()
    diff = sorted(after - before)
    result["regenerated_files"] = diff

    # 4. validate (typecheck)
    if skip_validate:
        result["typecheck"] = "skipped"
    elif dry_run:
        result["typecheck"] = "(dry-run — not executed)"
    elif typecheck_cmd:
        rc, out, err = _run(["npm", "run", typecheck_cmd], cwd=fe, dry_run=dry_run, timeout=420)
        if rc == 0:
            result["typecheck"] = "pass"
        else:
            result["typecheck"] = "fail"
            result["warnings"].append(
                f"`npm run {typecheck_cmd}` failed (rc={rc}). "
                f"DTOs/client regenerated but typecheck reported errors — inspect manually."
            )
    else:
        # Fall back to `npx tsc --noEmit` if typescript is available.
        rc, out, err = _run(["npx", "--no-install", "tsc", "--noEmit"], cwd=fe, dry_run=dry_run, timeout=420)
        if rc == 0:
            result["typecheck"] = "pass (tsc --noEmit)"
        elif rc == 124:
            result["typecheck"] = "timeout (tsc --noEmit)"
            result["warnings"].append("tsc --noEmit timed out; validation inconclusive.")
        else:
            result["typecheck"] = "fail (tsc --noEmit)"
            result["warnings"].append(
                "No typecheck script in package.json and `npx tsc --noEmit` failed. "
                "Regen completed but FE type validation is inconclusive."
            )

    return result


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render_summary(result: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("=== FE regen from BE ===")
    lines.append(f"FE: {result.get('fe_path', '?')}")
    lines.append(f"BE: {result.get('be_path', '?')}")
    if result.get("dtos_command"):
        lines.append(f"DTO command:  npm run {result['dtos_command']}")
        lines.append(f"Client command: npm run {result['client_command']}")
        lines.append(f"Typecheck:    {result.get('typecheck', '?')}")
    lines.append("")
    regen = result.get("regenerated_files") or []
    if regen:
        lines.append(f"Regenerated/changed files ({len(regen)}):")
        for f in regen:
            lines.append(f"  {f}")
    elif result.get("dtos_ok") and result.get("client_ok"):
        lines.append("Regenerated files: (no git-visible changes — DTOs already up to date)")
    lines.append("")
    if result.get("errors"):
        lines.append("ERRORS:")
        for e in result["errors"]:
            lines.append(f"  ! {e}")
    if result.get("warnings"):
        lines.append("WARNINGS:")
        for w in result["warnings"]:
            lines.append(f"  - {w}")
    if not result.get("errors"):
        if result.get("dry_run"):
            lines.append("Plan complete (dry-run — nothing was actually regenerated).")
        else:
            lines.append("Done: DTOs updated + client regenerated.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def self_test() -> int:
    # detect_paths: real main FE/BE exist
    fe, be = detect_paths(None, None)
    assert fe.name == "myhospital-fe" and be.name == "myhospital-be", (fe, be)

    # detect_paths with explicit be -> sibling fe
    # (use the real combine-his-pacs worktree if present, else skip that branch)
    wt_be = ROOT / "worktrees" / "combine-his-pacs" / "be"
    if wt_be.exists():
        fe2, be2 = detect_paths(str(wt_be), None)
        assert fe2.name == "fe" and be2.name == "be", (fe2, be2)

    # load_package_scripts + pick_script on the real FE
    scripts = load_package_scripts(ROOT / "myhospital-fe")
    assert "dtos:update" in scripts and "client:generate" in scripts, sorted(scripts)
    assert pick_script(scripts, DTO_CANDIDATES, "dto") == "dtos:update"
    assert pick_script(scripts, CLIENT_CANDIDATES, "client") == "client:generate"
    # this repo has no `typecheck` script -> find_typecheck_script returns None
    assert find_typecheck_script(scripts) is None

    # pick_script raises on missing
    try:
        pick_script({"a": "x"}, ["b"], "missing")
        raise AssertionError("expected KeyError")
    except KeyError:
        pass

    print("fe_regen_from_be self-test: OK")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate FE DTOs + API client after a BE contract change."
    )
    parser.add_argument("--be-path", help="BE checkout path (default: myhospital-be or sibling of --fe-path).")
    parser.add_argument("--fe-path", help="FE checkout path (default: sibling fe/ or myhospital-fe).")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
    parser.add_argument("--skip-validate", action="store_true", help="Skip the typecheck validation step.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    result = run_pipeline(
        be_path=args.be_path, fe_path=args.fe_path,
        dry_run=args.dry_run, skip_validate=args.skip_validate,
    )
    print(render_summary(result))
    if result.get("errors"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
