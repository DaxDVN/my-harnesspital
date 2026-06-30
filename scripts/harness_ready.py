#!/usr/bin/env python3
"""One-shot harness readiness gate before real workflow experiments.

This command is intentionally read-only. It runs the deterministic checks that matter before the owner
starts testing workflows for real.

Usage:
    python scripts/harness_ready.py
    python scripts/harness_ready.py --json
    python scripts/harness_ready.py --self-test
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


CHECKS = [
    ("doctor-strict", [sys.executable, "scripts/harness_doctor.py", "--strict"]),
    ("router-selftest", [sys.executable, "scripts/harness_router.py", "--self-test"]),
    ("preflight-selftest", [sys.executable, "scripts/harness_preflight.py", "--self-test"]),
    ("codex-preflight-selftest", [sys.executable, "scripts/codex_preflight.py", "--self-test"]),
    ("rule-card-selftest", [sys.executable, "scripts/rule_card.py", "--self-test"]),
    ("preflight-trigger-selftest", [sys.executable, "engine/hooks/preflight_trigger.py", "--self-test"]),
    ("context-audit-selftest", [sys.executable, "scripts/harness_context_audit.py", "--self-test"]),
    ("daily-eval-selftest", [sys.executable, "scripts/harness_daily_eval.py", "--self-test"]),
    ("quality-gate-selftest", [sys.executable, "scripts/artifact_gate.py", "--self-test"]),
    ("quality-eval-selftest", [sys.executable, "scripts/harness_quality_eval.py", "--self-test"]),
    ("scanner-promotion-selftest", [sys.executable, "scripts/harness_scanner_promotion.py", "--self-test"]),
    ("promotion-candidates-selftest", [sys.executable, "scripts/main_brain_promotion_candidates.py", "--self-test"]),
    ("eval-scan", [sys.executable, "scripts/harness_eval.py", "scan"]),
    ("scanner-promotion-scan", [sys.executable, "scripts/harness_scanner_promotion.py", "scan"]),
    ("workflow-governance", [sys.executable, "scripts/harness_workflow_governance.py", "scan"]),
    ("runtime-contract", [sys.executable, "scripts/harness_runtime_contract.py", "scan"]),
    ("learning-check", [sys.executable, "scripts/learning_check.py"]),
]


def run_check(name: str, argv: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        argv,
        cwd=str(ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    return {
        "name": name,
        "command": " ".join(argv),
        "returncode": proc.returncode,
        "summary": lines[-1] if lines else f"exit {proc.returncode}",
    }


def run_all() -> dict[str, Any]:
    results = [run_check(name, argv) for name, argv in CHECKS]
    return {
        "ready": all(item["returncode"] == 0 for item in results),
        "checks": results,
    }


def self_test() -> int:
    assert CHECKS, "CHECKS must not be empty"
    names = [name for name, _ in CHECKS]
    assert len(names) == len(set(names)), "check names must be unique"
    required = {
        "doctor-strict",
        "router-selftest",
        "preflight-selftest",
        "codex-preflight-selftest",
        "rule-card-selftest",
        "preflight-trigger-selftest",
        "context-audit-selftest",
        "daily-eval-selftest",
        "quality-gate-selftest",
        "quality-eval-selftest",
        "scanner-promotion-selftest",
        "promotion-candidates-selftest",
        "eval-scan",
        "scanner-promotion-scan",
        "workflow-governance",
        "runtime-contract",
        "learning-check",
    }
    missing = required.difference(names)
    assert not missing, f"missing required readiness checks: {sorted(missing)}"
    print("harness_ready self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run MyHospital harness readiness checks")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    result = run_all()
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Harness readiness: " + ("READY" if result["ready"] else "NOT READY"))
        for item in result["checks"]:
            status = "OK" if item["returncode"] == 0 else "FAIL"
            print(f"[{status}] {item['name']}: {item['summary']}")
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
