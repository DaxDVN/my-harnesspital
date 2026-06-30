#!/usr/bin/env python3
"""conventions_sync — apply the staged CONVENTIONS.md drift fix and demote the
project doc to a thin pointer to the canon (`engine/rules/backend.md`).

The BE audit (`velvet/notes/myhospital-be-conventions-audit-2026-06-15.md`)
found `myhospital-be/CONVENTIONS.md` factually wrong in 5–6 spots (D1–D6) while
`engine/rules/backend.md` (the canon) was largely correct. A corrected version is
staged at `docs/harness/pending/CONVENTIONS.fixed.md`. The fix is NOT to copy the
fixed version into the project — it is to RETIRE the project doc: demote
`CONVENTIONS.md` to a thin pointer to the canon, killing the drift permanently
(two sources of truth → one). The staged fixed file is archived as an audit
trail. See `engine/rules/README.md` "Known drift" section.

This script never auto-applies. The owner runs `apply` when ready. `status` and
`--self-test` are read-only.

Usage:
    python scripts/conventions_sync.py status            # report drift (delegate convention_truth.py)
    python scripts/conventions_sync.py apply [--dry-run] [--yes]
    python scripts/conventions_sync.py --self-test
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONV = ROOT / "myhospital-be" / "CONVENTIONS.md"
FIXED = ROOT / "docs" / "harness" / "pending" / "CONVENTIONS.fixed.md"
PENDING = ROOT / "docs" / "harness" / "pending"
CANON = ROOT / "engine" / "rules" / "backend.md"
CONVENTION_TRUTH = ROOT / "scripts" / "convention_truth.py"
THIN_POINTER_MARKER = "thin pointer"


def _ts() -> str:
    return datetime.now().strftime("%Y%m%dT%H%M%S")


def _backup_name() -> str:
    return f"CONVENTIONS.old-backup-{_ts()}.md"


def _applied_name() -> str:
    return f"CONVENTIONS.fixed.applied-{_ts()}.md"


def thin_pointer_content() -> str:
    return (
        "# CONVENTIONS.md — pointer to canon\n"
        "\n"
        "This file is now a thin pointer. The BE convention canon lives at:\n"
        f"**`engine/rules/backend.md`** (and topic cards in `engine/rules/backend/`).\n"
        "\n"
        "Read that instead. This file is kept only for backwards-compatible references.\n"
        "\n"
        f"Drift fixes applied {date.today().isoformat()}: see "
        f"`docs/harness/pending/CONVENTIONS.old-backup-{_ts()}.md`.\n"
    )


def _read(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


def _is_thin_pointer(text: str | None) -> bool:
    return bool(text) and THIN_POINTER_MARKER in text  # type: ignore[arg-type]


def _run_convention_truth(strict: bool) -> tuple[int, str]:
    cmd = [sys.executable, str(CONVENTION_TRUTH)]
    if strict:
        cmd.append("--strict")
    try:
        proc = subprocess.run(
            cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=60,
        )
        return proc.returncode, proc.stdout
    except Exception as exc:  # noqa: BLE001
        return 1, f"convention_truth.py failed to run: {exc}"


def command_status() -> int:
    if not CONVENTION_TRUTH.exists():
        print("conventions_sync status: scripts/convention_truth.py missing", file=sys.stderr)
        return 1
    code, out = _run_convention_truth(strict=False)
    print(out, end="")
    current = _read(CONV)
    if _is_thin_pointer(current):
        print("conventions_sync: myhospital-be/CONVENTIONS.md is ALREADY a thin pointer "
              "(drift killed). Re-applying is a no-op.")
    elif current is not None:
        print("conventions_sync: myhospital-be/CONVENTIONS.md still holds content (drift source). "
              "Run `apply` to demote it to a thin pointer.")
    return code


def _print_plan(current: str | None, fixed: str | None) -> None:
    print("Plan (apply):")
    print(f"  1. Read staged fix:    {FIXED.relative_to(ROOT)}")
    print(f"  2. Read current doc:   {CONV.relative_to(ROOT)}")
    print(f"  3. Backup current →    {PENDING.relative_to(ROOT)}/{_backup_name()}")
    print(f"  4. Write {CONV.relative_to(ROOT)} = thin pointer → engine/rules/backend.md")
    print(f"  5. Archive staged fix → {PENDING.relative_to(ROOT)}/{_applied_name()} (audit trail)")
    print(f"  6. Verify: python scripts/convention_truth.py --strict  (rollback on FAIL)")
    print()
    print("--- thin pointer that would be written ---")
    print(thin_pointer_content())
    print("--- end thin pointer ---")
    if current:
        head = current.splitlines()[:6]
        print("--- current CONVENTIONS.md (first 6 lines) ---")
        print("\n".join(head))
        print("--- end current head ---")


def command_apply(dry_run: bool, yes: bool) -> int:
    fixed = _read(FIXED)
    if fixed is None:
        print(f"conventions_sync apply: staged fix not found: {FIXED}", file=sys.stderr)
        return 1
    current = _read(CONV)
    if current is None:
        print(f"conventions_sync apply: current doc not found: {CONV}", file=sys.stderr)
        return 1
    if not CANON.exists():
        print(f"conventions_sync apply: canon missing: {CANON} — fix engine/rules first.", file=sys.stderr)
        return 1
    if _is_thin_pointer(current):
        print("conventions_sync apply: CONVENTIONS.md is already a thin pointer — nothing to do.")
        return 0

    if dry_run:
        _print_plan(current, fixed)
        print("\n(dry-run: no files written)")
        return 0

    if not yes:
        print(f"About to demote {CONV.relative_to(ROOT)} to a thin pointer and archive the staged fix.")
        ans = input("Proceed? [y/N] ").strip().lower()
        if ans not in ("y", "yes"):
            print("aborted.")
            return 1

    PENDING.mkdir(parents=True, exist_ok=True)
    backup_path = PENDING / _backup_name()
    applied_path = PENDING / _applied_name()

    print(f"  backup: {backup_path.relative_to(ROOT)}")
    shutil.copy2(CONV, backup_path)
    print(f"  write thin pointer: {CONV.relative_to(ROOT)}")
    CONV.write_text(thin_pointer_content(), encoding="utf-8")
    print(f"  archive staged fix: {applied_path.relative_to(ROOT)}")
    shutil.copy2(FIXED, applied_path)

    print("  verify: python scripts/convention_truth.py --strict")
    code, out = _run_convention_truth(strict=True)
    summary = next((l for l in out.splitlines() if l.startswith("Summary:")), out.strip().splitlines()[-1] if out.strip() else f"exit {code}")
    if code != 0:
        print(f"  VERIFY FAILED — {summary}", file=sys.stderr)
        print("  rolling back: restore CONVENTIONS.md from backup, remove applied snapshot.", file=sys.stderr)
        shutil.copy2(backup_path, CONV)
        try:
            applied_path.unlink()
        except Exception:
            pass
        print(out, end="", file=sys.stderr)
        return 1
    print(f"  VERIFY OK — {summary}")
    print("\nDone. CONVENTIONS.md is now a thin pointer to engine/rules/backend.md. "
          "Staged fix archived as audit trail.")
    return 0


def self_test() -> int:
    failures = 0

    def check(cond: bool, msg: str) -> None:
        nonlocal failures
        if not cond:
            failures += 1
            print(f"FAIL: {msg}")

    check(CONVENTION_TRUTH.exists(), f"convention_truth.py missing at {CONVENTION_TRUTH}")
    check(FIXED.exists(), f"staged fix missing at {FIXED}")
    check(CONV.exists(), f"CONVENTIONS.md missing at {CONV}")
    # convention_truth.py must be importable (syntax) — quick ast parse
    import ast
    try:
        ast.parse(CONVENTION_TRUTH.read_text(encoding="utf-8"))
        check(True, "")
    except SyntaxError as e:
        check(False, f"convention_truth.py has a syntax error: {e}")
    # thin pointer content must reference the canon path
    check("engine/rules/backend.md" in thin_pointer_content(),
          "thin pointer content does not reference engine/rules/backend.md")
    # dry-run must not write (run it against current state; harmless)
    if CONV.exists() and FIXED.exists():
        before = CONV.read_text(encoding="utf-8", errors="ignore")
        rc = command_apply(dry_run=True, yes=True)
        after = CONV.read_text(encoding="utf-8", errors="ignore")
        check(rc == 0, "dry-run returned non-zero")
        check(before == after, "dry-run modified CONVENTIONS.md (must not write)")
    if failures:
        print(f"conventions_sync self-test: {failures} FAILED")
        return 1
    print("conventions_sync self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="conventions_sync",
        description="Apply the staged CONVENTIONS.md drift fix; demote the project doc to a canon pointer.",
    )
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="command")
    sub.add_parser("status", help="report drift (delegates convention_truth.py)")
    apply_p = sub.add_parser("apply", help="demote CONVENTIONS.md to a thin pointer + archive the staged fix")
    apply_p.add_argument("--dry-run", action="store_true", help="print plan only, write nothing")
    apply_p.add_argument("--yes", action="store_true", help="skip confirmation prompt")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.command == "status":
        return command_status()
    if args.command == "apply":
        return command_apply(args.dry_run, args.yes)
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
