#!/usr/bin/env python3
"""Validate and summarize MyHospital harness workflow eval ledgers.

P4 scope: lightweight evidence, not a new framework. The eval files are simple YAML ledgers under
docs/harness/evals/. This script deliberately supports only the small top-level YAML subset used by
the template: scalar keys, inline empty lists, and block lists.

Usage:
    python scripts/harness_eval.py --self-test
    python scripts/harness_eval.py validate docs/harness/evals/<run>.yaml
    python scripts/harness_eval.py scan
    python scripts/harness_eval.py summarize
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = ROOT / "docs" / "harness" / "evals"
TEMPLATE = EVAL_DIR / "_TEMPLATE.yaml"

REQUIRED_FIELDS = [
    "workflow",
    "risk_tier",
    "model",
    "executor",
    "input_artifacts",
    "output_artifacts",
    "validations_run",
    "tool_calls",
    "estimated_tokens",
    "elapsed",
    "bugs_found",
    "bugs_verified",
    "false_positives",
    "reopened_bugs",
    "rounds",
    "human_interventions",
    "verdict",
    "cost_of_pass",
    "lessons",
    "residual_risks",
]

LIST_FIELDS = {"input_artifacts", "output_artifacts", "validations_run", "lessons", "residual_risks"}
RISK_TIERS = {"T0", "T1", "T2", "T3", "UNKNOWN", ""}
VERDICTS = {"PASS", "PARTIAL", "FAIL", "UNKNOWN", ""}


def _strip_comment(line: str) -> str:
    in_quote = False
    quote_char = ""
    for i, ch in enumerate(line):
        if ch in {"'", '"'} and (i == 0 or line[i - 1] != "\\"):
            if in_quote and ch == quote_char:
                in_quote = False
                quote_char = ""
            elif not in_quote:
                in_quote = True
                quote_char = ch
        if ch == "#" and not in_quote:
            return line[:i]
    return line


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value == "":
        return ""
    if value == "[]":
        return []
    if value in {"true", "false"}:
        return value == "true"
    if value in {"null", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value


def parse_eval_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list: str | None = None
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = _strip_comment(raw).rstrip()
        if not line.strip():
            continue
        if line.startswith("  ") and current_list and line.strip().startswith("- "):
            data[current_list].append(_parse_scalar(line.strip()[2:]))
            continue
        if line.startswith(" "):
            raise ValueError(f"line {line_no}: nested YAML is not supported by harness_eval")
        if ":" not in line:
            raise ValueError(f"line {line_no}: expected key: value")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"line {line_no}: empty key")
        value = _parse_scalar(raw_value)
        if value == "":
            # Treat an empty value followed by indented "- ..." lines as a block list only for known list fields.
            value = [] if key in LIST_FIELDS else ""
        data[key] = value
        current_list = key if isinstance(value, list) else None
    return data


def validate_data(data: dict[str, Any], *, template_ok: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"missing required field '{field}'")
    for field in LIST_FIELDS:
        if field in data and not isinstance(data[field], list):
            errors.append(f"field '{field}' must be a list")
    if str(data.get("risk_tier", "")) not in RISK_TIERS:
        errors.append(f"risk_tier must be one of {sorted(RISK_TIERS)}")
    if str(data.get("verdict", "")) not in VERDICTS:
        errors.append(f"verdict must be one of {sorted(VERDICTS)}")

    if not template_ok:
        if not data.get("workflow"):
            errors.append("workflow must be set for real eval ledgers")
        if data.get("verdict") in {"PASS", "PARTIAL", "FAIL"} and not data.get("output_artifacts"):
            warnings.append("verdict is terminal but output_artifacts is empty")
        if data.get("verdict") == "PASS" and not data.get("validations_run"):
            warnings.append("PASS eval has no validations_run evidence")
    return errors, warnings


def validate_file(path: Path, *, template_ok: bool = False) -> tuple[dict[str, Any], list[str], list[str]]:
    data = parse_eval_yaml(path)
    errors, warnings = validate_data(data, template_ok=template_ok)
    return data, errors, warnings


def iter_eval_files() -> list[Path]:
    if not EVAL_DIR.exists():
        return []
    return sorted(p for p in EVAL_DIR.rglob("*.yaml") if p.name != "_TEMPLATE.yaml")


def command_validate(paths: list[str]) -> int:
    if not paths:
        paths = [str(TEMPLATE)]
        template_ok = True
    else:
        template_ok = False
    ok = True
    for raw in paths:
        path = Path(raw)
        try:
            _, errors, warnings = validate_file(path, template_ok=template_ok and path.name == "_TEMPLATE.yaml")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {path}: {exc}")
            ok = False
            continue
        status = "OK" if not errors else "FAIL"
        print(f"{status} {path}")
        for warning in warnings:
            print(f"  WARN: {warning}")
        for error in errors:
            print(f"  ERROR: {error}")
        ok = ok and not errors
    return 0 if ok else 1


def command_scan() -> int:
    if not TEMPLATE.exists():
        print(f"FAIL template missing: {TEMPLATE}")
        return 1
    _, template_errors, _ = validate_file(TEMPLATE, template_ok=True)
    if template_errors:
        print(f"FAIL template invalid: {TEMPLATE}")
        for error in template_errors:
            print(f"  ERROR: {error}")
        return 1
    files = iter_eval_files()
    if not files:
        print("OK eval ledger: template valid; no real eval files yet")
        return 0
    failures = 0
    warnings = 0
    for path in files:
        _, errors, warns = validate_file(path)
        if errors:
            failures += 1
            print(f"FAIL {path.relative_to(ROOT)}")
            for error in errors:
                print(f"  ERROR: {error}")
        else:
            print(f"OK {path.relative_to(ROOT)}")
        for warning in warns:
            warnings += 1
            print(f"  WARN: {warning}")
    print(f"Summary: {len(files)} eval file(s), {failures} failure(s), {warnings} warning(s)")
    return 1 if failures else 0


def command_summarize(json_output: bool) -> int:
    summary: dict[str, Any] = {
        "eval_files": 0,
        "by_workflow": {},
        "by_verdict": {},
        "warnings": [],
    }
    for path in iter_eval_files():
        data, errors, warnings = validate_file(path)
        if errors:
            summary["warnings"].append(f"{path.relative_to(ROOT)} invalid: {errors[0]}")
            continue
        summary["eval_files"] += 1
        workflow = str(data.get("workflow") or "<unknown>")
        verdict = str(data.get("verdict") or "UNKNOWN")
        summary["by_workflow"][workflow] = summary["by_workflow"].get(workflow, 0) + 1
        summary["by_verdict"][verdict] = summary["by_verdict"].get(verdict, 0) + 1
        for warning in warnings:
            summary["warnings"].append(f"{path.relative_to(ROOT)}: {warning}")
    if json_output:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"Eval files: {summary['eval_files']}")
        print("By workflow: " + (", ".join(f"{k}={v}" for k, v in sorted(summary["by_workflow"].items())) or "none"))
        print("By verdict: " + (", ".join(f"{k}={v}" for k, v in sorted(summary["by_verdict"].items())) or "none"))
        for warning in summary["warnings"]:
            print(f"WARN: {warning}")
    return 0


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "eval.yaml"
        path.write_text(
            "\n".join([
                "workflow: bug-fix",
                "risk_tier: T1",
                "model: gpt-test",
                "executor: codex",
                "input_artifacts: []",
                "output_artifacts:",
                "  - docs/harness/evals/example-output.md",
                "validations_run:",
                "  - python scripts/harness_doctor.py",
                "tool_calls: 1",
                "estimated_tokens: 1000",
                "elapsed: 1m",
                "bugs_found: 1",
                "bugs_verified: 1",
                "false_positives: 0",
                "reopened_bugs: 0",
                "rounds: 1",
                "human_interventions: 0",
                "verdict: PASS",
                "cost_of_pass: unknown",
                "lessons: []",
                "residual_risks: []",
                "",
            ]),
            encoding="utf-8",
        )
        _, errors, warnings = validate_file(path)
        assert not errors, errors
        assert not warnings, warnings
        bad = Path(tmpdir) / "bad.yaml"
        bad.write_text("workflow: bug-fix\nverdict: GREAT\n", encoding="utf-8")
        _, errors, _ = validate_file(bad)
        assert errors, "invalid eval accepted"
    print("harness_eval self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate/summarize MyHospital harness eval ledgers")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true", help="JSON output for summarize")
    sub = parser.add_subparsers(dest="command")
    validate = sub.add_parser("validate")
    validate.add_argument("paths", nargs="*")
    sub.add_parser("scan")
    summarize = sub.add_parser("summarize")
    summarize.add_argument("--json", dest="summary_json", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.command == "validate":
        return command_validate(args.paths)
    if args.command == "scan":
        return command_scan()
    if args.command == "summarize":
        return command_summarize(args.json or getattr(args, "summary_json", False))
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
