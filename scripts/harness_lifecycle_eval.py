#!/usr/bin/env python3
"""Lifecycle evidence report for harness workflows.

This script does not promote workflows. It reports whether each active workflow has real eval evidence and can
create a correctly-shaped eval template for a future real run.

Usage:
    python scripts/harness_lifecycle_eval.py scan
    python scripts/harness_lifecycle_eval.py new-template <workflow> <short-scope>
    python scripts/harness_lifecycle_eval.py --self-test
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from harness_eval import iter_eval_files, validate_file  # noqa: E402

WORKFLOWS = ROOT / "engine" / "workflows"
EVALS = ROOT / "docs" / "harness" / "evals"


def active_workflows() -> dict[str, dict[str, Any]]:
    data: dict[str, dict[str, Any]] = {}
    for manifest in sorted(WORKFLOWS.glob("*/manifest.json")):
        raw = json.loads(manifest.read_text(encoding="utf-8"))
        data[raw["name"]] = raw
    return data


def evals_by_workflow() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for path in iter_eval_files():
        data, errors, warnings = validate_file(path)
        if errors:
            continue
        workflow = str(data.get("workflow") or "")
        if not workflow:
            continue
        item = dict(data)
        item["_path"] = str(path.relative_to(ROOT))
        item["_warnings"] = warnings
        grouped.setdefault(workflow, []).append(item)
    return grouped


def strong_eval(item: dict[str, Any]) -> bool:
    return (
        item.get("verdict") in {"PASS", "PARTIAL"}
        and item.get("risk_tier") != "UNKNOWN"
        and bool(item.get("output_artifacts"))
        and bool(item.get("validations_run"))
    )


def command_scan(json_output: bool) -> int:
    workflows = active_workflows()
    grouped = evals_by_workflow()
    rows = []
    for name, manifest in workflows.items():
        items = grouped.get(name, [])
        strong = [item for item in items if strong_eval(item)]
        status = manifest.get("lifecycle_status", "")
        recommendation = "needs-real-eval"
        if status in {"PROVEN", "DEFAULT"} and not strong:
            recommendation = "demote-or-add-evidence"
        elif strong and status in {"DRAFT", "LAB"}:
            recommendation = "candidate-for-review"
        elif strong:
            recommendation = "evidence-present"
        rows.append({
            "workflow": name,
            "lifecycle_status": status,
            "eval_count": len(items),
            "strong_eval_count": len(strong),
            "recommendation": recommendation,
            "latest_eval": items[-1].get("_path") if items else "",
        })
    if json_output:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        for row in rows:
            print(
                f"{row['workflow']}: status={row['lifecycle_status']} "
                f"evals={row['eval_count']} strong={row['strong_eval_count']} "
                f"recommendation={row['recommendation']} latest={row['latest_eval'] or '-'}"
            )
    return 0


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip().lower()).strip("-")
    return value or "run"


def command_new_template(workflow: str, short_scope: str) -> int:
    workflows = active_workflows()
    if workflow not in workflows:
        print(f"FAIL unknown workflow: {workflow}")
        return 1
    out_dir = EVALS / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{workflow}-{_slug(short_scope)}.yaml"
    if path.exists():
        print(f"FAIL eval already exists: {path.relative_to(ROOT)}")
        return 1
    manifest = workflows[workflow]
    body = "\n".join([
        f"workflow: {workflow}",
        f"lifecycle_status: {manifest.get('lifecycle_status', 'DRAFT')}",
        "risk_tier: UNKNOWN",
        "model:",
        "executor:",
        "input_artifacts: []",
        "output_artifacts: []",
        "validations_run: []",
        "tool_calls:",
        "estimated_tokens:",
        "elapsed:",
        "bugs_found: 0",
        "bugs_verified: 0",
        "false_positives: 0",
        "reopened_bugs: 0",
        "rounds: 1",
        "human_interventions:",
        "verdict: UNKNOWN",
        "cost_of_pass:",
        "lessons: []",
        "residual_risks: []",
        "",
    ])
    path.write_text(body, encoding="utf-8")
    print(path.relative_to(ROOT))
    return 0


def self_test() -> int:
    workflows = active_workflows()
    assert workflows, "active workflows required"
    grouped = evals_by_workflow()
    assert isinstance(grouped, dict)
    print("harness_lifecycle_eval self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Report harness workflow lifecycle eval evidence")
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="command")
    scan = sub.add_parser("scan")
    scan.add_argument("--json", action="store_true")
    new = sub.add_parser("new-template")
    new.add_argument("workflow")
    new.add_argument("short_scope")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.command == "scan":
        return command_scan(args.json)
    if args.command == "new-template":
        return command_new_template(args.workflow, args.short_scope)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
