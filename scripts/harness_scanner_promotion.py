#!/usr/bin/env python3
"""Find repeated bug classes that should become deterministic scanners, and emit
a scanner skeleton for one.

Two modes:
  - `scan`            : advisory — scans lightweight markdown artifacts for stable `bug_class:`
                        markers and reports classes seen at least twice (≥3 to promote).
  - `promote`         : emit a copy-paste-ready deterministic scanner skeleton for a bug class
                        (argparse + --self-test + fail-open scan fn + TODO markers). Does NOT
                        auto-wire into scripts/mh_scan/scanners.py (deliberate manual step).
  - `list-candidates` : list bug_class markers with >= MIN_OCCURRENCES occurrences.

Usage:
    python scripts/harness_scanner_promotion.py scan
    python scripts/harness_scanner_promotion.py scan --fail-on-promote
    python scripts/harness_scanner_promotion.py list-candidates
    python scripts/harness_scanner_promotion.py promote <bug_class> [--dry-run] [--yes]
    python scripts/harness_scanner_promotion.py --self-test
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MH_SCAN = ROOT / "scripts" / "mh_scan"
MIN_OCCURRENCES = 3

DEFAULT_GLOBS = [
    "docs/audit/**/*.md",
    "engine/workflows/robust-test/runs/**/*.md",
    "second-brain/**/*.md",
]
BUG_CLASS_RE = re.compile(r"^\s*-?\s*bug[_-]class\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


# --- scan mode ---------------------------------------------------------------
def normalize(value: str) -> str:
    key = re.sub(r"`|\[|\]|\(|\)", "", value.strip().lower())
    key = re.sub(r"[^a-z0-9_.:-]+", "-", key).strip("-")
    return key[:120]


def scan_paths(paths: list[Path]) -> dict[str, list[Path]]:
    hits: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in BUG_CLASS_RE.finditer(text):
            key = normalize(match.group(1))
            if key:
                hits[key].append(path)
    return dict(hits)


def default_paths() -> list[Path]:
    paths: list[Path] = []
    for pattern in DEFAULT_GLOBS:
        paths.extend(ROOT.glob(pattern))
    return sorted(set(paths))


def command_scan(fail_on_promote: bool) -> int:
    hits = scan_paths(default_paths())
    promotable = {key: paths for key, paths in hits.items() if len(paths) >= 2}
    if not promotable:
        print("Scanner promotion: no repeated bug_class markers found")
        return 0
    for key, paths in sorted(promotable.items()):
        print(f"PROMOTE_TO_SCANNER {key} count={len(paths)}")
        for path in paths[:5]:
            print(f"  - {path.relative_to(ROOT)}")
        if len(paths) > 5:
            print(f"  - ... {len(paths) - 5} more")
    return 1 if fail_on_promote else 0


# --- promote mode ------------------------------------------------------------
def _scan_candidates_text() -> str:
    """Run the scan in-process and capture its stdout text (for parse_candidates)."""
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        command_scan(fail_on_promote=False)
    return buf.getvalue()


def parse_candidates(out: str) -> list[tuple[str, int, list[str]]]:
    """Parse `PROMOTE_TO_SCANNER <key> count=N` + indented path lines."""
    candidates: list[tuple[str, int, list[str]]] = []
    key, count, paths = "", 0, []
    for line in out.splitlines():
        m = re.match(r"^PROMOTE_TO_SCANNER\s+(\S+)\s+count=(\d+)", line)
        if m:
            if key:
                candidates.append((key, count, paths))
            key, count, paths = m.group(1), int(m.group(2)), []
            continue
        pm = re.match(r"^\s+-\s+(.+)$", line)
        if pm and key:
            paths.append(pm.group(1).strip())
    if key:
        candidates.append((key, count, paths))
    return candidates


def command_list_candidates() -> int:
    candidates = parse_candidates(_scan_candidates_text())
    eligible = [c for c in candidates if c[1] >= MIN_OCCURRENCES]
    if not eligible:
        print(f"No bug_class markers with >= {MIN_OCCURRENCES} occurrences "
              f"(promotion scan reported {len(candidates)} class(es) with >= 2).")
        return 0
    print(f"Scanner promotion candidates (>= {MIN_OCCURRENCES} occurrences):")
    for key, count, paths in sorted(eligible, key=lambda c: (-c[1], c[0])):
        print(f"  {key}  count={count}")
        for p in paths[:3]:
            print(f"    - {p}")
        if len(paths) > 3:
            print(f"    - ... {len(paths) - 3} more")
    print(f"\nPromote one: python scripts/harness_scanner_promotion.py promote <bug_class> --dry-run")
    return 0


def _module_name(bug_class: str) -> str:
    # hyphens → underscores so the file is importable as a Python module
    return re.sub(r"[^a-z0-9_]+", "_", bug_class.lower()).strip("_")


def skeleton(bug_class: str, occurrences: list[str]) -> str:
    mod = _module_name(bug_class)
    occ_block = "\n".join(f"  - {p}" for p in occurrences[:5]) or "  - (no occurrence paths recorded)"
    today = date.today().isoformat()
    return f'''#!/usr/bin/env python3
"""{mod} — deterministic scanner for the `{bug_class}` bug class.

Skeleton emitted by scripts/harness_scanner_promotion.py on {today}.
Owner: fill the TODO markers below, then wire into scripts/mh_scan/scanners.py.

Source occurrences (from `harness_scanner_promotion.py scan`):
{occ_block}

Design mirrors scripts/mh_scan/scanners.py: rg-backed, pure-stdlib, fail-open.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass

WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# TODO(owner): point at the right repo root — BE default; use myhospital-fe for FE bug classes.
DEFAULT_ROOT = os.path.join(WORKSPACE, "myhospital-be")


@dataclass
class Finding:
    scanner: str
    severity: str
    path: str
    line: int
    title: str
    snippet: str = ""

    def as_dict(self) -> dict:
        return {{"scanner": self.scanner, "severity": self.severity, "path": self.path,
                "line": self.line, "title": self.title, "snippet": self.snippet[:200]}}


# TODO(owner): set the rg pattern that defines this bug class.
PATTERN = r"TODO-REPLACE-WITH-REAL-PATTERN"
# TODO(owner): adjust globs (e.g. ("*.tsx", "*.ts") for FE, ("*.cs",) for BE).
GLOBS = ("*.cs",)
SEVERITY = "WARN"  # TODO(owner): BLOCK | HIGH | WARN | INFO


def _rg(pattern: str, root: str, globs: tuple = GLOBS) -> list[tuple[str, int, str]]:
    cmd = ["rg", "-n", "--no-heading", "--color=never"]
    for g in globs:
        cmd += ["-g", g]
    cmd += ["-g", "!**/bin/**", "-g", "!**/obj/**", "-g", "!**/Migrations/**"]
    cmd += ["-e", pattern, root]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except Exception:
        return []  # fail-open
    out: list[tuple[str, int, str]] = []
    for line in proc.stdout.splitlines():
        m = re.match(r"^(.*?):(\\d+):(.*)$", line)
        if m:
            out.append((m.group(1), int(m.group(2)), m.group(3)))
    return out


# TODO(owner): classify a hit (path, matched text) -> keep? Default keeps everything.
def classify(path: str, text: str) -> bool:
    return True


def scan(root: str = DEFAULT_ROOT) -> list[Finding]:
    out: list[Finding] = []
    for path, line, text in _rg(PATTERN, root):
        try:
            if classify(path, text):
                out.append(Finding("{bug_class}", SEVERITY, path, line,
                                   "TODO(owner): one-line title for {bug_class}", text))
        except Exception:
            pass  # fail-open: a classifier bug must not abort the scan
    return out


def self_test() -> int:
    failures = 0

    def check(cond: bool, msg: str) -> None:
        nonlocal failures
        if not cond:
            failures += 1
            print(f"FAIL: {{msg}}")

    # pattern must compile as a Python regex (catches a typo before owner fills it in)
    try:
        re.compile(PATTERN)
        check(True, "")
    except re.error as e:
        check(False, f"PATTERN does not compile: {{e}}")
    # scan() must fail-open on a missing root (return [], not raise)
    findings = scan("/nonexistent-path-xyz-{{bug_class}}")
    check(isinstance(findings, list), "scan() did not return a list on missing root")
    # classify() must be callable without raising on a sample
    try:
        classify("sample.cs", "sample text")
        check(True, "")
    except Exception as e:
        check(False, f"classify() crashed: {{e}}")
    if failures:
        print(f"{mod} self-test: {{failures}} FAILED")
        return 1
    print(f"{mod} self-test: OK (pattern compiles, scan fail-open)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="{mod}", description="{bug_class} scanner (skeleton)")
    ap.add_argument("--root", default=DEFAULT_ROOT, help="repo root to scan")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    findings = scan(args.root)
    for f in findings:
        print(f"{{f.severity:5}} {{f.path}}:{{f.line}}  {{f.title}}  | {{f.snippet.strip()[:120]}}")
    print(f"\\n{{bug_class}}: {{len(findings)}} finding(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def command_promote(bug_class: str, dry_run: bool, yes: bool) -> int:
    mod = _module_name(bug_class)
    target = MH_SCAN / f"{mod}.py"
    candidates = parse_candidates(_scan_candidates_text())
    occurrences = next((paths for key, _, paths in candidates if key == bug_class), [])

    if target.exists():
        print(f"harness_scanner_promotion: refusing to overwrite {target.relative_to(ROOT)} "
              f"(delete it first to re-generate).", file=sys.stderr)
        return 1

    skel = skeleton(bug_class, occurrences)

    if dry_run:
        print(f"--- would write: {target.relative_to(ROOT)} ---")
        print(skel)
        print("--- end skeleton ---")
        print("\n(dry-run: no file written)")
        print_next_steps(target)
        return 0

    if not yes:
        print(f"About to emit scanner skeleton → {target.relative_to(ROOT)}")
        ans = input("Proceed? [y/N] ").strip().lower()
        if ans not in ("y", "yes"):
            print("aborted.")
            return 1

    MH_SCAN.mkdir(parents=True, exist_ok=True)
    target.write_text(skel, encoding="utf-8")
    print(f"emitted: {target.relative_to(ROOT)}")
    print_next_steps(target)
    return 0


def print_next_steps(target: Path) -> None:
    print("\nNext steps (owner):")
    print(f"  1. Edit {target.relative_to(ROOT)}: replace PATTERN, adjust GLOBS, fill classify() + title.")
    print(f"  2. Run: python {target.relative_to(ROOT)} --self-test")
    print(f"  3. Wire into the pack: there is NO dynamic registry in scripts/mh_scan/__init__.py —")
    print(f"     add an entry to the SCANNERS list in scripts/mh_scan/scanners.py (or import + call")
    print(f"     scan() from a custom block). This is a manual, deliberate step.")
    print(f"  4. Re-run: python scripts/harness_doctor.py  (mh-scan:selftest should stay OK)")


# --- self-test ---------------------------------------------------------------
def self_test() -> int:
    failures = 0

    def check(cond: bool, msg: str) -> None:
        nonlocal failures
        if not cond:
            failures += 1
            print(f"FAIL: {msg}")

    # scan mode
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        a = root / "a.md"
        b = root / "b.md"
        c = root / "c.md"
        a.write_text("- bug_class: fe-raw-fetch\n", encoding="utf-8")
        b.write_text("bug_class: fe raw fetch\n", encoding="utf-8")
        c.write_text("bug_class: be-missing-scope\n", encoding="utf-8")
        hits = scan_paths([a, b, c])
        check(len(hits["fe-raw-fetch"]) == 2, f"scan: fe-raw-fetch expected 2, got {len(hits.get('fe-raw-fetch', []))}")
        check(len(hits["be-missing-scope"]) == 1, "scan: be-missing-scope expected 1")

    # promote mode
    sample = (
        "PROMOTE_TO_SCANNER fe-raw-fetch count=4\n"
        "  - docs/audit/a.md\n"
        "  - docs/audit/b.md\n"
        "PROMOTE_TO_SCANNER be-missing-scope count=2\n"
        "  - second-brain/x.md\n"
    )
    cands = parse_candidates(sample)
    check(len(cands) == 2, f"parse_candidates expected 2, got {len(cands)}")
    check(cands[0][0] == "fe-raw-fetch" and cands[0][1] == 4, "parse_candidates first row wrong")
    check(len(cands[0][2]) == 2, f"parse_candidates paths wrong: {cands[0][2]}")
    check(_module_name("fe-raw-fetch") == "fe_raw_fetch", "module name not sanitized")
    check(_module_name("BE Missing Scope!") == "be_missing_scope", "module name not sanitized (2)")
    skel = skeleton("fe-raw-fetch", ["docs/audit/a.md"])
    check("class Finding" in skel and "--self-test" in skel, "skeleton missing key parts")
    check("TODO-REPLACE-WITH-REAL-PATTERN" in skel, "skeleton missing TODO marker")
    try:
        ast.parse(skel)
        check(True, "")
    except SyntaxError as e:
        check(False, f"skeleton does not parse as Python: {e}")
    check(_module_name("fe-raw-fetch") + ".py" == "fe_raw_fetch.py", "filename not underscore-safe")

    if failures:
        print(f"harness_scanner_promotion self-test: {failures} FAILED")
        return 1
    print("harness_scanner_promotion self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="harness_scanner_promotion",
        description="Report repeated bug classes that should become scanners, and emit scanner skeletons.",
    )
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="command")
    scan_p = sub.add_parser("scan", help="report repeated bug_class markers")
    scan_p.add_argument("--fail-on-promote", action="store_true")
    sub.add_parser("list-candidates", help=f"list bug_class markers with >= {MIN_OCCURRENCES} occurrences")
    prom_p = sub.add_parser("promote", help="emit a scanner skeleton for a bug class")
    prom_p.add_argument("--dry-run", action="store_true", help="print the skeleton, write nothing")
    prom_p.add_argument("--yes", action="store_true", help="skip confirmation prompt")
    prom_p.add_argument("bug_class", help="bug class key to promote (from list-candidates)")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.command == "scan":
        return command_scan(args.fail_on_promote)
    if args.command == "list-candidates":
        return command_list_candidates()
    if args.command == "promote":
        return command_promote(args.bug_class, args.dry_run, args.yes)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
