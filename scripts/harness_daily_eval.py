#!/usr/bin/env python3
"""Daily harness optimization eval.

Read-only by default. It exercises the cheap signals that should stay stable after
context/workflow optimizations: router decisions, natural-language preflight, quality gates, context footprint,
and readiness.

Usage:
    python scripts/harness_daily_eval.py run
    python scripts/harness_daily_eval.py run --record
    python scripts/harness_daily_eval.py --self-test
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

ROUTER_CASES = [
    ("fix trivial label typo local", "mh-fix", "T1"),
    ("implement admission API DTO change", "mh-implement", "T2"),
    ("run deep review before merge", "deep-review", "T3"),
    ("super-test inpatient module", "robust-test", "T3"),
]

PREFLIGHT_CASES = [
    {
        "prompt": "fix visible inpatient form sheet bug with existing component reuse",
        "status": "WAIT_OWNER_CONFIRMATION",
        "workflow": "mh-fix",
        "package_scope": "FE",
        "worktree": "",
    },
    {
        "prompt": "sửa bug sheet nội trú visible form",
        "status": "WAIT_OWNER_CONFIRMATION",
        "workflow": "mh-fix",
        "package_scope": "FE",
        "worktree": "",
    },
    {
        "prompt": "sửa lỗi api phân quyền admission service",
        "status": "WAIT_OWNER_CONFIRMATION",
        "workflow": "mh-fix",
        "package_scope": "BE",
        "worktree": "",
    },
    {
        "prompt": "run deep review before merge",
        "status": "WAIT_OWNER_CONFIRMATION",
        "workflow": "deep-review",
        "package_scope": "UNKNOWN",
        "worktree": "",
    },
    {
        "prompt": "super-test inpatient module",
        "status": "WAIT_OWNER_CONFIRMATION",
        "workflow": "robust-test",
        "package_scope": "UNKNOWN",
        "worktree": "",
    },
    {
        "prompt": "thiết kế api contract nhập viện",
        "status": "WAIT_OWNER_CONFIRMATION",
        "workflow": "technical-design",
        "package_scope": "BE",
        "worktree": "",
    },
    {
        "prompt": "tạo ui spec từ docx mockup nội trú",
        "status": "WAIT_OWNER_CONFIRMATION",
        "workflow": "ui-spec",
        "package_scope": "FE",
        "worktree": "",
    },
    {
        "prompt": "what breaks if change PatientDto",
        "status": "WAIT_OWNER_CONFIRMATION",
        "workflow": "impact-analysis",
        "package_scope": "BE",
        "worktree": "",
    },
]


def run(argv: list[str], *, timeout: int = 120) -> tuple[int, str]:
    proc = subprocess.run(
        argv,
        cwd=str(ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout


def router_decision(prompt: str) -> dict[str, Any]:
    code, out = run([sys.executable, "scripts/harness_router.py", "--json", prompt])
    if code != 0:
        return {"prompt": prompt, "ok": False, "error": out.strip()}
    data = json.loads(out)
    return {
        "prompt": prompt,
        "ok": True,
        "candidate_workflow": data.get("candidate_workflow"),
        "risk_tier": data.get("risk_tier"),
        "files_to_load": data.get("files_to_load", []),
    }


def preflight_decision(prompt: str) -> dict[str, Any]:
    code, out = run([sys.executable, "scripts/harness_preflight.py", "--json", prompt])
    if code != 0:
        return {"prompt": prompt, "ok": False, "error": out.strip()}
    data = json.loads(out)
    return {
        "prompt": prompt,
        "ok": True,
        "status": data.get("status"),
        "predicted_workflow": data.get("predicted_workflow"),
        "needs_owner_confirmation": data.get("needs_owner_confirmation"),
        "package_scope": (data.get("package_scope") or {}).get("scope"),
        "selected_worktree": ((data.get("worktree") or {}).get("selected") or {}).get("slug", ""),
    }


def collect() -> dict[str, Any]:
    started = time.monotonic()
    decisions = [router_decision(prompt) for prompt, _, _ in ROUTER_CASES]
    router_ok = True
    for decision, (_, want_workflow, want_tier) in zip(decisions, ROUTER_CASES):
        router_ok = router_ok and decision.get("ok")
        router_ok = router_ok and decision.get("candidate_workflow") == want_workflow
        router_ok = router_ok and decision.get("risk_tier") == want_tier

    preflights = [preflight_decision(case["prompt"]) for case in PREFLIGHT_CASES]
    preflight_ok = True
    for decision, case in zip(preflights, PREFLIGHT_CASES):
        preflight_ok = preflight_ok and decision.get("ok")
        preflight_ok = preflight_ok and decision.get("status") == case["status"]
        preflight_ok = preflight_ok and decision.get("predicted_workflow") == case["workflow"]
        preflight_ok = preflight_ok and decision.get("package_scope") == case["package_scope"]
        preflight_ok = preflight_ok and decision.get("selected_worktree") == case["worktree"]
        preflight_ok = preflight_ok and decision.get("needs_owner_confirmation") is True

    context_code, context_out = run([sys.executable, "scripts/harness_context_audit.py", "scan", "--json"])
    context = json.loads(context_out) if context_code == 0 else {"error": context_out.strip()}

    quality_code, quality_out = run([sys.executable, "scripts/harness_quality_eval.py", "run"])

    ready_code, ready_out = run([sys.executable, "scripts/harness_ready.py"], timeout=180)

    return {
        "router_ok": router_ok,
        "router_decisions": decisions,
        "preflight_ok": preflight_ok,
        "preflight_decisions": preflights,
        "quality_ok": quality_code == 0,
        "quality_summary": [line for line in quality_out.splitlines() if line.strip()],
        "context_ok": context_code == 0,
        "context": context,
        "ready_ok": ready_code == 0,
        "ready_summary": [line for line in ready_out.splitlines() if line.strip()],
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def _yaml_list(items: list[str]) -> str:
    if not items:
        return " []\n"
    return "\n" + "".join(f"  - {item}\n" for item in items)


def write_eval(result: dict[str, Any]) -> Path:
    today = date.today().isoformat()
    out_dir = ROOT / "docs" / "harness" / "evals" / today
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "harness-daily-optimization.yaml"
    context = result.get("context", {})
    entry_words = context.get("entry", {}).get("total_words", "")
    skill_words = context.get("skill_stubs", {}).get("total_words", "")
    trap_words = context.get("context_traps", {}).get("total_words", "")
    estimated_tokens = ""
    if isinstance(entry_words, int) and isinstance(skill_words, int):
        # Rough, stable phase-comparison estimate; not provider billing truth.
        estimated_tokens = int((entry_words + skill_words) * 1.35)
    validations = [
        "python scripts/harness_router.py --json <sample>",
        "python scripts/harness_preflight.py --json <sample>",
        "python scripts/harness_quality_eval.py run",
        "python scripts/harness_context_audit.py scan --json",
        "python scripts/harness_ready.py",
    ]
    lessons = [
        f"entry_words={entry_words}",
        f"skill_stub_words={skill_words}",
        f"context_trap_words={trap_words}",
    ]
    residual = []
    if not result["router_ok"]:
        residual.append("router sample mismatch")
    if not result["preflight_ok"]:
        residual.append("preflight sample mismatch")
    if not result["quality_ok"]:
        residual.append("quality suite mismatch")
    if not result["ready_ok"]:
        residual.append("harness readiness failed")
    if trap_words:
        residual.append("context traps still present; load only router-selected files")
    body = (
        "workflow: harness-daily-optimization\n"
        "risk_tier: T2\n"
        "model: n/a\n"
        "executor: local-scripts\n"
        "input_artifacts: []\n"
        f"output_artifacts:\n  - {path.relative_to(ROOT)}\n"
        f"validations_run:{_yaml_list(validations)}"
        f"tool_calls: {len(ROUTER_CASES) + len(PREFLIGHT_CASES) + 3}\n"
        f"estimated_tokens: {estimated_tokens}\n"
        f"elapsed: {result.get('elapsed_seconds', '')}s\n"
        "bugs_found: 0\n"
        "bugs_verified: 0\n"
        "false_positives: 0\n"
        "reopened_bugs: 0\n"
        "rounds: 1\n"
        "human_interventions: 0\n"
        f"verdict: {'PASS' if result['router_ok'] and result['preflight_ok'] and result['quality_ok'] and result['context_ok'] and result['ready_ok'] else 'FAIL'}\n"
        "cost_of_pass:\n"
        f"lessons:{_yaml_list(lessons)}"
        f"residual_risks:{_yaml_list(residual)}"
    )
    path.write_text(body, encoding="utf-8")
    return path


def command_run(record: bool, json_output: bool) -> int:
    result = collect()
    path = write_eval(result) if record else None
    ok = result["router_ok"] and result["preflight_ok"] and result["quality_ok"] and result["context_ok"] and result["ready_ok"]
    if json_output:
        if path:
            result["eval_path"] = str(path.relative_to(ROOT))
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Harness daily eval: " + ("PASS" if ok else "FAIL"))
        context = result.get("context", {})
        if context:
            print(f"entry_words: {context.get('entry', {}).get('total_words')}")
            print(f"skill_stub_words: {context.get('skill_stubs', {}).get('total_words')}")
            print(f"context_trap_words: {context.get('context_traps', {}).get('total_words')}")
        for decision in result["router_decisions"]:
            status = "OK" if decision.get("ok") else "FAIL"
            print(f"[{status}] {decision.get('prompt')}: {decision.get('candidate_workflow')} {decision.get('risk_tier')}")
        for decision in result["preflight_decisions"]:
            status = "OK" if decision.get("ok") else "FAIL"
            print(
                f"[{status}] preflight {decision.get('prompt')}: "
                f"{decision.get('status')} {decision.get('predicted_workflow')} "
                f"pkg={decision.get('package_scope')} wt={decision.get('selected_worktree') or '-'}"
            )
        print("quality suite: " + ("OK" if result["quality_ok"] else "FAIL"))
        print("readiness: " + ("OK" if result["ready_ok"] else "FAIL"))
        if path:
            print(f"eval: {path.relative_to(ROOT)}")
    return 0 if ok else 1


def self_test() -> int:
    assert ROUTER_CASES, "router cases required"
    assert PREFLIGHT_CASES, "preflight cases required"
    prompts = [case[0] for case in ROUTER_CASES]
    assert len(prompts) == len(set(prompts)), "router cases must be unique"
    preflight_prompts = [case["prompt"] for case in PREFLIGHT_CASES]
    assert len(preflight_prompts) == len(set(preflight_prompts)), "preflight cases must be unique"
    print("harness_daily_eval self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run daily harness optimization eval")
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="command")
    run_cmd = sub.add_parser("run")
    run_cmd.add_argument("--record", action="store_true")
    run_cmd.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.command == "run":
        return command_run(args.record, args.json)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
