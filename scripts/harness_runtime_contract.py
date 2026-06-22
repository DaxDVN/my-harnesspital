#!/usr/bin/env python3
"""Scan workflow runtime-boundary contracts.

P7 scope: detect prompt-only/runtime-boundary drift before real workflow testing. This script is
read-only; it validates manifest contracts and does not execute any workflow.

Usage:
    python scripts/harness_runtime_contract.py --self-test
    python scripts/harness_runtime_contract.py scan
    python scripts/harness_runtime_contract.py summary --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / "engine" / "workflows"


def load_manifests(base: Path = WORKFLOWS) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    for path in sorted(base.glob("*/manifest.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_path"] = str(path.relative_to(ROOT))
        data["_folder"] = path.parent.name
        manifests.append(data)
    return manifests


def _items(manifest: dict[str, Any], key: str) -> list[str]:
    value = manifest.get(key) or []
    return [str(x) for x in value] if isinstance(value, list) else []


def _has_any(items: list[str], needles: tuple[str, ...]) -> bool:
    haystack = "\n".join(items)
    return any(needle in haystack for needle in needles)


def analyze(manifests: list[dict[str, Any]]) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    summary: dict[str, Any] = {
        "total": len(manifests),
        "external_boundary_checked": [],
        "write_boundary_checked": [],
        "read_only_checked": [],
        "auto_route_checked": [],
    }

    for manifest in manifests:
        name = str(manifest.get("name") or manifest.get("_folder"))
        kind = str(manifest.get("kind") or "")
        lifecycle = str(manifest.get("lifecycle_status") or "")
        external = _items(manifest, "external_agents")
        allowed_writes = _items(manifest, "allowed_writes")
        validators = _items(manifest, "validators")
        uses_shared = _items(manifest, "uses_shared")
        public_entry = manifest.get("public_entry") is True
        auto_route = manifest.get("auto_route_allowed") is True

        if public_entry and not validators:
            errors.append(f"{name}: public_entry=true but validators is empty")

        if external:
            summary["external_boundary_checked"].append(name)
            if "runtime-boundary.md" not in uses_shared:
                errors.append(f"{name}: external_agents present but uses_shared lacks runtime-boundary.md")
            if not validators:
                errors.append(f"{name}: external_agents present but validators is empty")

        writes_worktree = any(path.startswith("worktrees/") or "worktrees/<slug>/" in path for path in allowed_writes)
        if writes_worktree:
            summary["write_boundary_checked"].append(name)
            has_allowlist = _has_any(validators + uses_shared, ("allowlist-check.py", "runtime-boundary.md"))
            if not has_allowlist:
                errors.append(f"{name}: worktree writes declared but no runtime/allowlist boundary is declared")

        if kind == "advisory":
            summary["read_only_checked"].append(name)
            if writes_worktree:
                errors.append(f"{name}: advisory workflow must not allow worktree writes")

        if auto_route:
            summary["auto_route_checked"].append(name)
            eval_summary = manifest.get("eval_summary") or {}
            artifact = eval_summary.get("artifact_path") if isinstance(eval_summary, dict) else ""
            if lifecycle not in {"PROVEN", "DEFAULT"}:
                errors.append(f"{name}: auto_route_allowed=true but lifecycle_status={lifecycle}")
            if not artifact:
                errors.append(f"{name}: auto_route_allowed=true but eval_summary.artifact_path is empty")
            if not validators:
                errors.append(f"{name}: auto_route_allowed=true but validators is empty")

        if lifecycle == "DEPRECATED" and auto_route:
            errors.append(f"{name}: DEPRECATED workflow must not auto-route")

    return errors, warnings, summary


def command_scan() -> int:
    errors, warnings, summary = analyze(load_manifests())
    for error in errors:
        print(f"FAIL: {error}")
    for warning in warnings:
        print(f"WARN: {warning}")
    print(
        "Summary: "
        f"{summary['total']} workflow(s), "
        f"{len(summary['external_boundary_checked'])} external boundary check(s), "
        f"{len(summary['write_boundary_checked'])} write boundary check(s), "
        f"{len(errors)} error(s), {len(warnings)} warning(s)"
    )
    return 1 if errors else 0


def command_summary(json_output: bool) -> int:
    errors, warnings, summary = analyze(load_manifests())
    summary["errors"] = errors
    summary["warnings"] = warnings
    if json_output:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"Total workflows: {summary['total']}")
        print("External boundary checked: " + (", ".join(summary["external_boundary_checked"]) or "none"))
        print("Write boundary checked: " + (", ".join(summary["write_boundary_checked"]) or "none"))
        for warning in warnings:
            print(f"WARN: {warning}")
        for error in errors:
            print(f"FAIL: {error}")
    return 1 if errors else 0


def self_test() -> int:
    good = [
        {
            "name": "robust-test",
            "kind": "workflow",
            "public_entry": True,
            "auto_route_allowed": False,
            "lifecycle_status": "DRAFT",
            "external_agents": [],
            "allowed_writes": ["engine/workflows/robust-test/runs/**"],
            "validators": ["python engine/workflows/_shared/validate-envelope.py <envelope> --payload <payload>"],
            "uses_shared": ["runtime-boundary.md", "validate-envelope.py"],
        },
        {
            "name": "impact-analysis",
            "kind": "advisory",
            "public_entry": True,
            "auto_route_allowed": False,
            "lifecycle_status": "DRAFT",
            "external_agents": ["codegraph"],
            "allowed_writes": ["engine/workflows/impact-analysis/rounds/**"],
            "validators": ["python engine/workflows/_shared/validate-envelope.py <envelope>"],
            "uses_shared": ["runtime-boundary.md", "validate-envelope.py"],
        },
    ]
    errors, warnings, summary = analyze(good)
    assert not errors, errors
    assert not warnings, warnings
    assert summary["external_boundary_checked"] == ["impact-analysis"]
    bad = [{**good[1], "uses_shared": ["validate-envelope.py"]}]
    errors, _, _ = analyze(bad)
    assert errors, "external workflow without runtime-boundary accepted"
    bad_advisory = [{**good[1], "allowed_writes": ["worktrees/<slug>/fe/**"]}]
    errors, _, _ = analyze(bad_advisory)
    assert errors, "advisory workflow with worktree writes accepted"
    print("harness_runtime_contract self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Scan MyHospital workflow runtime contracts")
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("scan")
    summary = sub.add_parser("summary")
    summary.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.command == "scan":
        return command_scan()
    if args.command == "summary":
        return command_summary(args.json)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
