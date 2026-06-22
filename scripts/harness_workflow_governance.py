#!/usr/bin/env python3
"""Scan workflow taxonomy, lifecycle, and deprecation governance.

P5 scope: make consolidation/deprecation decisions explicit and evidence-gated. This script does not
modify manifests or deprecate workflows. It reports governance drift so later cleanup can happen safely.

Usage:
    python scripts/harness_workflow_governance.py --self-test
    python scripts/harness_workflow_governance.py scan
    python scripts/harness_workflow_governance.py summary --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / "engine" / "workflows"
ALLOWED_KIND = {"workflow", "internal", "advisory"}
ALLOWED_LIFECYCLE = {"DRAFT", "LAB", "PROVEN", "DEFAULT", "DEPRECATED"}


def load_manifests(base: Path = WORKFLOWS) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    for path in sorted(base.glob("*/manifest.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_path"] = path
        data["_folder"] = path.parent.name
        manifests.append(data)
    return manifests


def _replacement(manifest: dict[str, Any]) -> str:
    if manifest.get("replacement_workflow"):
        return str(manifest["replacement_workflow"])
    deprecation = manifest.get("deprecation")
    if isinstance(deprecation, dict) and deprecation.get("replacement_workflow"):
        return str(deprecation["replacement_workflow"])
    return ""


def analyze(manifests: list[dict[str, Any]]) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    summary: dict[str, Any] = {
        "total": len(manifests),
        "by_kind": {},
        "by_lifecycle": {},
        "public_entries": [],
        "internal_entries": [],
        "advisory_entries": [],
        "deprecated": [],
        "auto_route_candidates": [],
        "recommended_prompt_files": [],
    }
    names = {str(m.get("name") or m.get("_folder")) for m in manifests}
    entry_skills: dict[str, list[str]] = {}

    for manifest in manifests:
        name = str(manifest.get("name") or manifest.get("_folder"))
        kind = str(manifest.get("kind") or "")
        lifecycle = str(manifest.get("lifecycle_status") or "")
        entry_skill = str(manifest.get("entry_skill") or "")
        summary["by_kind"][kind] = summary["by_kind"].get(kind, 0) + 1
        summary["by_lifecycle"][lifecycle] = summary["by_lifecycle"].get(lifecycle, 0) + 1
        if kind == "workflow":
            summary["public_entries"].append(name)
        elif kind == "internal":
            summary["internal_entries"].append(name)
        elif kind == "advisory":
            summary["advisory_entries"].append(name)
        if lifecycle == "DEPRECATED":
            summary["deprecated"].append(name)
        if manifest.get("auto_route_allowed") is True:
            summary["auto_route_candidates"].append(name)
        prompt_file = manifest.get("recommended_prompt_file")
        if prompt_file:
            summary["recommended_prompt_files"].append(f"{name}:{prompt_file}")
        if entry_skill:
            entry_skills.setdefault(entry_skill, []).append(name)

        if kind not in ALLOWED_KIND:
            errors.append(f"{name}: invalid kind={kind!r}")
        if lifecycle not in ALLOWED_LIFECYCLE:
            errors.append(f"{name}: invalid lifecycle_status={lifecycle!r}")
        if kind == "internal" and manifest.get("public_entry") is True:
            warnings.append(f"{name}: kind=internal but public_entry=true")
        if kind == "advisory" and any("worktrees/<slug>/" in item for item in manifest.get("allowed_writes", [])):
            warnings.append(f"{name}: advisory workflow allows worktree writes")
        if lifecycle in {"DRAFT", "LAB"} and manifest.get("auto_route_allowed") is True:
            errors.append(f"{name}: auto_route_allowed=true below PROVEN")
        if lifecycle == "DEFAULT" and manifest.get("public_entry") is not True:
            warnings.append(f"{name}: DEFAULT workflow is not public_entry=true")
        if "recommended_prompt_file" not in manifest:
            warnings.append(f"{name}: missing recommended_prompt_file")
        elif not isinstance(manifest.get("recommended_prompt_file"), str):
            warnings.append(f"{name}: recommended_prompt_file is not a string")
        elif manifest.get("recommended_prompt_file") and not (ROOT / str(manifest["recommended_prompt_file"])).exists():
            warnings.append(f"{name}: recommended_prompt_file does not exist: {manifest['recommended_prompt_file']}")
        if lifecycle == "DEPRECATED":
            replacement = _replacement(manifest)
            if not replacement:
                errors.append(f"{name}: DEPRECATED without replacement_workflow")
            elif replacement not in names:
                errors.append(f"{name}: replacement_workflow={replacement!r} does not match any workflow")

    for skill, workflows in sorted(entry_skills.items()):
        if len(workflows) > 1:
            warnings.append(f"entry_skill {skill!r} is shared by workflows: {', '.join(workflows)}")

    return errors, warnings, summary


def command_scan() -> int:
    manifests = load_manifests()
    if not manifests:
        print("WARN workflow governance: no workflow manifests found")
        return 0
    errors, warnings, summary = analyze(manifests)
    for error in errors:
        print(f"FAIL: {error}")
    for warning in warnings:
        print(f"WARN: {warning}")
    print(
        "Summary: "
        f"{summary['total']} workflow(s), "
        f"kind={summary['by_kind']}, "
        f"lifecycle={summary['by_lifecycle']}, "
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
        print("Public workflow class: " + ", ".join(sorted(summary["public_entries"])))
        print("Internal workflow class: " + ", ".join(sorted(summary["internal_entries"])))
        print("Advisory workflow class: " + ", ".join(sorted(summary["advisory_entries"])))
        print("Auto-route candidates: " + (", ".join(sorted(summary["auto_route_candidates"])) or "none"))
        print("Recommended prompt files: " + (", ".join(sorted(summary["recommended_prompt_files"])) or "none"))
        print("Deprecated: " + (", ".join(sorted(summary["deprecated"])) or "none"))
        for warning in warnings:
            print(f"WARN: {warning}")
        for error in errors:
            print(f"FAIL: {error}")
    return 1 if errors else 0


def self_test() -> int:
    sample = [
        {
            "name": "robust-test",
            "kind": "workflow",
            "public_entry": True,
            "auto_route_allowed": False,
            "lifecycle_status": "DRAFT",
            "entry_skill": "robust-test",
            "recommended_prompt_file": "engine/prompts/robust-test.md",
            "allowed_writes": ["engine/workflows/robust-test/runs/**"],
        },
        {
            "name": "old-flow",
            "kind": "workflow",
            "public_entry": False,
            "auto_route_allowed": False,
            "lifecycle_status": "DEPRECATED",
            "entry_skill": "old-flow",
            "recommended_prompt_file": "",
            "replacement_workflow": "robust-test",
            "allowed_writes": [],
        },
    ]
    errors, warnings, summary = analyze(sample)
    assert not errors, errors
    assert not warnings, warnings
    assert summary["by_kind"]["workflow"] == 2
    bad = [{**sample[0], "auto_route_allowed": True, "lifecycle_status": "LAB"}]
    errors, _, _ = analyze(bad)
    assert errors, "auto-route below PROVEN accepted"
    bad_deprecated = [{**sample[1], "replacement_workflow": ""}]
    errors, _, _ = analyze(bad_deprecated)
    assert errors, "deprecated workflow without replacement accepted"
    print("harness_workflow_governance self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Scan MyHospital workflow governance")
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
