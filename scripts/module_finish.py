#!/usr/bin/env python3
"""Orchestrate the 5-step cleanup when a dev-specs module is finished.

Read-only/suggest by default. With --dry-run it only prints the plan. It NEVER
runs git or worktree cleanup itself; it only suggests the command for owner
confirmation. Archive moves specs/dev-specs/<module>/ -> _archive/<module>-<date>/.
Stdlib only.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS = ROOT / "specs" / "dev-specs"
ARCHIVE = SPECS / "_archive"


class ToolError(RuntimeError):
    pass


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def read_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" not in line or line.strip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def edit_frontmatter(text: str, updates: dict[str, str]) -> str:
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    header = text[3:end]
    body = text[end + 4:]
    out: list[str] = []
    seen: set[str] = set()
    for line in header.splitlines():
        if ":" in line and not line.strip().startswith("#"):
            key = line.split(":", 1)[0].strip()
            if key in updates:
                out.append(f"{key}: {updates[key]}")
                seen.add(key)
            else:
                out.append(line)
        else:
            out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}: {value}")
    return "---\n" + "\n".join(out) + "\n---" + body


def finalize_state(path: Path, today: str, *, dry_run: bool) -> None:
    text = path.read_text(encoding="utf-8")
    updated = edit_frontmatter(text, {
        "state": "DONE",
        "status": "done",
        "finished": today,
        "last_updated": today,
    })
    action = "would write" if dry_run else "write"
    print(f"> {action} {rel(path)} (state: DONE, finished: {today})")
    if not dry_run:
        path.write_text(updated, encoding="utf-8")


def archive_module(module: str, today: str, *, dry_run: bool) -> Path:
    src = SPECS / module
    dst = ARCHIVE / f"{module}-{today}"
    if dst.exists():
        raise ToolError(f"Archive target already exists: {rel(dst)}")
    print(f"> move {rel(src)} -> {rel(dst)}")
    if not dry_run:
        ARCHIVE.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    return dst


def run_promotion_scan(module: str) -> str:
    script = ROOT / "scripts" / "main_brain_promotion_candidates.py"
    if not script.exists():
        return "(promotion-candidates script not found)"
    proc = subprocess.run(
        [sys.executable, str(script), "scan"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    out = proc.stdout or ""
    related = [ln for ln in out.splitlines() if module in ln]
    if not related:
        return "(no promotion candidates matched this module)"
    return "\n  ".join(related)


def finish(args: argparse.Namespace) -> int:
    module = args.module
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", module):
        raise ToolError(f"Bad module slug {module!r}.")
    state_path = SPECS / module / "00-module-state.md"
    if not state_path.exists():
        raise ToolError(f"Module state not found: {rel(state_path)}")
    state = read_frontmatter(state_path)
    today = date.today().isoformat()

    steps: list[tuple[str, str]] = []

    print("== Step 1: verify module state ==")
    cur_state = state.get("state") or state.get("status") or "(none)"
    if cur_state.upper() in {"DONE", "READY", "IMPLEMENTATION-READY", "DONE"}:
        print(f"  state={cur_state} OK")
        steps.append(("verify-state", f"OK (state={cur_state})"))
    else:
        print(f"  WARN: state={cur_state} (expected DONE). Will finalize below.")
        steps.append(("verify-state", f"WARN (state={cur_state})"))

    print("== Step 2: worktree cleanup ==")
    if args.worktree:
        cmd = f"python scripts/worktree.py cleanup --slug {args.worktree}"
        print(f"  SUGGEST (owner confirm, NOT auto-run): {cmd}")
        steps.append(("worktree-cleanup", f"suggested: {cmd}"))
    else:
        print("  --worktree not given; skipping worktree cleanup suggestion.")
        steps.append(("worktree-cleanup", "skipped (no --worktree)"))

    print("== Step 4: promotion candidates ==")
    if args.skip_promote_check:
        print("  skipped (--skip-promote-check).")
        steps.append(("promotion-check", "skipped"))
    else:
        cands = run_promotion_scan(module)
        print(f"  {cands}")
        steps.append(("promotion-check", "scanned"))

    print("== Step 5: finalize state ==")
    finalize_state(state_path, today, dry_run=args.dry_run)
    steps.append(("finalize-state", f"state=DONE, finished={today}"))

    print("== Step 3: archive specs ==")
    if args.skip_archive:
        print("  skipped (--skip-archive).")
        steps.append(("archive", "skipped"))
    else:
        dst = archive_module(module, today, dry_run=args.dry_run)
        action = "would move" if args.dry_run else "moved"
        steps.append(("archive", f"{action} -> {rel(dst)}"))

    print()
    print("== Receipt ==")
    for name in ("verify-state", "worktree-cleanup", "archive", "promotion-check", "finalize-state"):
        status = next((s for n, s in steps if n == name), "skipped")
        print(f"  - {name}: {status}")
    print()
    print("Suggested next (owner):")
    if not args.skip_archive:
        print(f"  - git add specs/dev-specs/_archive/{module}-{today}/ && git commit")
    print("  - Open/merge PR if a worktree branch exists.")
    print("  - Review promotion candidates; run /promote for any ready note.")
    return 0


def self_test() -> int:
    assert ARCHIVE.parent == SPECS
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("---\nmodule: x\nstate: IN-PROGRESS\nlast_updated: 2026-01-01\n---\n# X\n")
        tmp = Path(f.name)
    try:
        s = read_frontmatter(tmp)
        assert s.get("module") == "x"
        assert s.get("state") == "IN-PROGRESS"
        updated = edit_frontmatter(tmp.read_text(encoding="utf-8"),
                                   {"state": "DONE", "finished": "2026-06-29"})
        assert "state: DONE" in updated
        assert "finished: 2026-06-29" in updated
        assert "state: IN-PROGRESS" not in updated
    finally:
        tmp.unlink()
    print("module_finish self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Finish a dev-specs module: 5-step cleanup receipt",
    )
    parser.add_argument("module", nargs="?", help="module slug to finish")
    parser.add_argument("--worktree", help="worktree slug to suggest cleanup for")
    parser.add_argument("--dry-run", action="store_true", help="print plan, do not move/write")
    parser.add_argument("--skip-archive", action="store_true",
                        help="do not move specs into _archive")
    parser.add_argument("--skip-promote-check", action="store_true",
                        help="skip promotion-candidate scan")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.module:
        parser.error("provide a module slug")
    try:
        return finish(args)
    except ToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
