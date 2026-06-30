#!/usr/bin/env python3
"""Validate small quality-gate artifacts.

This intentionally validates structure, not correctness. Correctness still needs the reviewer/model.

Usage:
    python scripts/artifact_gate.py --self-test
    python scripts/artifact_gate.py check-main-brain
    python scripts/artifact_gate.py validate-reuse <file>
    python scripts/artifact_gate.py validate-fix-plan <file>
    python scripts/artifact_gate.py validate-regression <file>
    python scripts/artifact_gate.py validate-review <findings.md> [--require-adjudicated]
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def words(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="ignore").split())


def require_text(path: Path, required: list[str]) -> list[str]:
    body = path.read_text(encoding="utf-8", errors="ignore").lower()
    return [item for item in required if item.lower() not in body]


def command_check_main_brain(max_words: int, hard_words: int) -> int:
    path = ROOT / "main-brain" / "knowledge.md"
    count = words(path)
    if count > hard_words:
        print(f"FAIL main-brain words={count} hard_threshold={hard_words}")
        return 1
    if count > max_words:
        print(f"WARN main-brain words={count} target={max_words}")
        return 0
    print(f"OK main-brain words={count} target={max_words}")
    return 0


def command_require(path: Path, required: list[str], label: str) -> int:
    missing = require_text(path, required)
    if missing:
        print(f"FAIL {label}: missing {', '.join(missing)}")
        return 1
    print(f"OK {label}: {path}")
    return 0


def _finding_blocks(text: str) -> list[str]:
    return [block for block in re.split(r"\n###\s+F-\d+\b", text) if "- severity:" in block]


def command_validate_review(path: Path, require_adjudicated: bool) -> int:
    text = path.read_text(encoding="utf-8", errors="ignore")
    failures: list[str] = []
    if "## Coverage ledger" not in text:
        failures.append("missing Coverage ledger")
    blocks = _finding_blocks(text)
    for i, block in enumerate(blocks, start=1):
        sev = re.search(r"- severity:\s*(BLOCK|HIGH|MED|LOW|NIT)", block)
        if not sev:
            failures.append(f"F-{i:03d}: missing severity")
            continue
        if sev.group(1) in {"BLOCK", "HIGH"}:
            if "- review_status:" not in block:
                failures.append(f"F-{i:03d}: BLOCK/HIGH missing review_status")
            if "- evidence:" not in block:
                failures.append(f"F-{i:03d}: BLOCK/HIGH missing evidence")
            for field in ("fix_reasonableness", "regression_risk", "alternative_considered", "why_not_bigger_fix"):
                if f"- {field}:" not in block:
                    failures.append(f"F-{i:03d}: BLOCK/HIGH missing {field}")
            if require_adjudicated and "review_status: CONFIRMED" not in block and "review_status: REJECTED" not in block:
                failures.append(f"F-{i:03d}: BLOCK/HIGH not adjudicated")
    if failures:
        print("FAIL review quality gate")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(f"OK review quality gate: {path}")
    return 0


def self_test() -> int:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        reuse = tmp / "reuse.md"
        reuse.write_text("searched:\n- a.ts:1\n- b.ts:2\ndecision: reuse\nwhy: same pattern\n", encoding="utf-8")
        assert command_require(reuse, ["searched:", "decision:", "why:"], "reuse") == 0

        fix = tmp / "fix.md"
        fix.write_text(
            "\n".join([
                "root_cause:",
                "allowed_files:",
                "forbidden_files:",
                "reuse_evidence:",
                "regression_map:",
                "risk:",
                "validation:",
                "rollback:",
            ]),
            encoding="utf-8",
        )
        assert command_require(fix, ["root_cause:", "allowed_files:", "validation:", "rollback:"], "fix-plan") == 0

        review = tmp / "review.md"
        review.write_text(
            "# Review\n\n## Coverage ledger\n\n## Findings\n\n### F-001\n"
            "- severity: HIGH\n"
            "- evidence: rule-hit:test\n"
            "- fix_reasonableness: minimal local fix\n"
            "- regression_risk: none\n"
            "- alternative_considered: none\n"
            "- why_not_bigger_fix: out of scope\n"
            "- review_status: CONFIRMED\n",
            encoding="utf-8",
        )
        assert command_validate_review(review, require_adjudicated=True) == 0
    print("artifact_gate self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate MyHospital quality-gate artifacts")
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="command")
    mb = sub.add_parser("check-main-brain")
    mb.add_argument("--max-words", type=int, default=1500)
    mb.add_argument("--hard-words", type=int, default=2000)
    for name in ("validate-reuse", "validate-fix-plan", "validate-regression"):
        p = sub.add_parser(name)
        p.add_argument("path")
    review = sub.add_parser("validate-review")
    review.add_argument("path")
    review.add_argument("--require-adjudicated", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.command == "check-main-brain":
        return command_check_main_brain(args.max_words, args.hard_words)
    if args.command == "validate-reuse":
        return command_require(Path(args.path), ["searched:", "decision:", "why:"], "reuse")
    if args.command == "validate-fix-plan":
        return command_require(
            Path(args.path),
            ["root_cause:", "allowed_files:", "forbidden_files:", "reuse_evidence:", "regression_map:", "risk:", "validation:", "rollback:"],
            "fix-plan",
        )
    if args.command == "validate-regression":
        return command_require(Path(args.path), ["changed_surface:", "callers_checked:", "validation:"], "regression-map")
    if args.command == "validate-review":
        return command_validate_review(Path(args.path), args.require_adjudicated)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
