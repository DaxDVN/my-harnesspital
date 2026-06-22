#!/usr/bin/env python3
"""Validate the harness quality suite and router expectations."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "docs" / "harness" / "quality-suite" / "cases.json"


def run_router(prompt: str) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, "scripts/harness_router.py", "--json", prompt],
        cwd=str(ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout)
    return json.loads(proc.stdout)


def load_cases() -> list[dict[str, Any]]:
    data = json.loads(CASES.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("cases.json must be a list")
    return data


def validate_cases(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    required = {"id", "task_class", "prompt", "expected_workflow", "expected_risk_tier", "quality_gates"}
    for idx, case in enumerate(cases, start=1):
        missing = required.difference(case)
        if missing:
            errors.append(f"case {idx}: missing {sorted(missing)}")
        case_id = str(case.get("id", ""))
        if case_id in seen:
            errors.append(f"duplicate id: {case_id}")
        seen.add(case_id)
        if not isinstance(case.get("quality_gates"), list) or not case.get("quality_gates"):
            errors.append(f"{case_id}: quality_gates must be a non-empty list")
    return errors


def command_run() -> int:
    cases = load_cases()
    errors = validate_cases(cases)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    failures = []
    for case in cases:
        decision = run_router(str(case["prompt"]))
        got_workflow = decision.get("candidate_workflow")
        got_tier = decision.get("risk_tier")
        if got_workflow != case["expected_workflow"] or got_tier != case["expected_risk_tier"]:
            failures.append(
                f"{case['id']}: got {got_workflow}/{got_tier}, "
                f"expected {case['expected_workflow']}/{case['expected_risk_tier']}"
            )
        print(f"OK {case['id']}: {got_workflow}/{got_tier} gates={','.join(case['quality_gates'])}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(f"quality suite: {len(cases)} case(s) PASS")
    return 0


def self_test() -> int:
    cases = load_cases()
    errors = validate_cases(cases)
    assert not errors, errors
    print("harness_quality_eval self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run MyHospital harness quality suite")
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("run")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.command == "run":
        return command_run()
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
