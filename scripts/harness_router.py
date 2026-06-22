#!/usr/bin/env python3
"""Read-only MyHospital harness router dry-run.

P1 scope: classify intent, risk, lifecycle, and files-to-load. This script never
executes workflows, edits files, enforces fast-path, or changes runtime state.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / "engine" / "workflows"

RISK_TERMS = {
    "api", "dto", "schema", "security", "permission", "auth", "business",
    "billing", "insurance", "bhyt", "bhtm", "state-machine", "migration",
    "multi-module", "admission", "discharge", "clinical", "financial",
    "contract", "tenant", "role", "invoice", "payment", "authorization",
    "quyền", "bảo hiểm", "viện phí", "thanh toán", "nghiệp vụ", "phân quyền",
    "nhập viện", "xuất viện", "lâm sàng", "hợp đồng", "đa module",
}

T3_TERMS = {
    "merge", "release", "audit", "review", "robust-test", "super-test", "harvest", "module",
    "large", "security", "financial", "clinical", "e2e", "pre-merge",
    "kiểm thử", "kiểm toán", "toàn module", "trước merge",
}

PONYTAIL_DEFAULT_WORKFLOWS = {
    "mh-fix",
    "mh-implement",
    "mh-scaffold",
    "harness-maintenance",
    "bug-fix",
    "deep-review",
    "robust-test",
    "technical-design",
    "task-slicing",
    "ui-spec",
    "incremental-impl",
    "dev-from-handoff",
}

QUALITY_GATE_DEFAULT_WORKFLOWS = {
    "mh-fix",
    "mh-implement",
    "mh-scaffold",
    "harness-maintenance",
    "bug-fix",
    "deep-review",
    "robust-test",
    "technical-design",
    "task-slicing",
    "ui-spec",
    "incremental-impl",
    "dev-from-handoff",
}

TRIVIAL_TERMS = {
    "typo", "copy", "label", "null guard", "small", "trivial", "local",
    "css", "style", "text", "đổi nhãn", "sửa chữ", "nhỏ", "cục bộ",
}


BUILTIN_ROUTES: dict[str, dict[str, Any]] = {
    "mh-implement": {
        "name": "mh-implement",
        "kind": "workflow",
        "entry_skill": "mh-implement",
        "recommended_prompt_file": "engine/prompts/mh-implement-feature.md",
        "public_entry": True,
        "auto_route_allowed": False,
        "lifecycle_status": "DRAFT",
        "required_inputs": ["feature description", "target worktree for source edits"],
        "allowed_writes": ["worktrees/<slug>/fe/**", "worktrees/<slug>/be/**"],
        "validators": ["targeted build/test/typecheck", "python scripts/harness_doctor.py"],
        "budget": {"max_context_files": 0, "max_payload_inline_chars": 0},
        "manifest_path": "",
    },
    "mh-fix": {
        "name": "mh-fix",
        "kind": "workflow",
        "entry_skill": "mh-fix",
        "recommended_prompt_file": "engine/prompts/mh-fix-approved-finding.md",
        "public_entry": True,
        "auto_route_allowed": False,
        "lifecycle_status": "DRAFT",
        "required_inputs": ["bug description or finding path", "target worktree for source edits"],
        "allowed_writes": ["worktrees/<slug>/fe/**", "worktrees/<slug>/be/**"],
        "validators": ["targeted regression validation", "python scripts/harness_doctor.py"],
        "budget": {"max_context_files": 0, "max_payload_inline_chars": 0},
        "manifest_path": "",
    },
    "mh-scaffold": {
        "name": "mh-scaffold",
        "kind": "workflow",
        "entry_skill": "mh-scaffold",
        "recommended_prompt_file": "",
        "public_entry": True,
        "auto_route_allowed": False,
        "lifecycle_status": "DRAFT",
        "required_inputs": ["scaffold target and scope"],
        "allowed_writes": ["worktrees/<slug>/fe/**", "worktrees/<slug>/be/**"],
        "validators": ["targeted build/test/typecheck"],
        "budget": {"max_context_files": 0, "max_payload_inline_chars": 0},
        "manifest_path": "",
    },
    "ponytail": {
        "name": "ponytail",
        "kind": "advisory",
        "entry_skill": "ponytail",
        "recommended_prompt_file": "",
        "public_entry": True,
        "auto_route_allowed": False,
        "lifecycle_status": "DRAFT",
        "required_inputs": ["source edit, fix, implementation, scaffold, or diff review scope"],
        "allowed_writes": [],
        "validators": ["same scoped validation the task would require without Ponytail"],
        "budget": {"max_context_files": 1, "max_payload_inline_chars": 0},
        "manifest_path": "",
    },
    "harness-maintenance": {
        "name": "harness-maintenance",
        "kind": "advisory",
        "entry_skill": "",
        "recommended_prompt_file": "",
        "public_entry": True,
        "auto_route_allowed": False,
        "lifecycle_status": "DRAFT",
        "required_inputs": [
            "maintenance objective",
            "explicit owner approval before non-trivial harness edits or installs",
        ],
        "allowed_writes": [
            "AGENTS.md",
            "CLAUDE.md",
            ".claude/**",
            ".codex/**",
            "engine/**",
            "scripts/**",
            "docs/harness/**",
            ".gitignore",
            ".graphifyignore",
            "package.json",
            "package-lock.json",
        ],
        "validators": [
            "python scripts/harness_doctor.py --strict",
            "python scripts/harness_router.py --self-test",
            "python scripts/harness_preflight.py --self-test",
            "python scripts/harness_quality_eval.py run",
            "npm run promptfoo:router",
            "python scripts/harness_workflow_governance.py scan",
            "python scripts/harness_runtime_contract.py scan",
        ],
        "rules": ["artifact-policy", "preflight-confirmation", "source-discovery"],
        "budget": {"max_context_files": 8, "max_payload_inline_chars": 0},
        "manifest_path": "",
    },
}


INTENT_RULES: list[tuple[str, tuple[str, ...], str, str]] = [
    ("harness-maintenance", ("harness", "harness maintenance", "harness optimize", "optimize harness", "workflow eval", "workflow routing", "router eval", "promptfoo", "context7", "codegraph maintenance", "source index", "graphify", "scanner promotion", "memory promotion", "main brain", "main-brain", "doctor", "readiness", "readiness check", "tối ưu harness", "đánh giá harness", "nâng cấp harness", "cài tooling", "tooling harness", "đốt token", "token tiêu hao", "quality không giảm"), "T2", "harness maintenance/optimization intent"),
    ("dev-from-handoff", ("dev-from-handoff", "dev from handoff", "implement from handoff", "build from handoff", "owner handoff", "handoff docs", "handoff document", "dev từ handoff", "từ tài liệu handoff", "tài liệu handoff", "tài liệu bàn giao", "triển khai từ handoff", "triển khai từ tài liệu bàn giao", "bắt đầu dev từ tài liệu", "bàn giao dev"), "T2", "owner-supplied handoff development intent"),
    ("robust-test", ("robust-test", "super-test", "progressive-test", "agentflow", "harvest", "bug harvest", "e2e harvest", "e2e test", "kiểm thử module", "test chắc", "sweep bugs"), "T3", "owner-gated robust targeted/sweep test intent"),
    ("deep-review", ("mh-review", "deep-review", "review", "audit", "kiểm toán", "đánh giá code"), "T3", "explicit review/audit intent"),
    ("ui-spec", ("ui spec", "ui-spec", "03-ui", "mockup", "docx", "reuse audit"), "T2", "UI spec/design-source intent"),
    ("technical-design", ("technical-design", "api contract", "design api", "08-api", "thiết kế api"), "T2", "API contract design intent"),
    ("task-slicing", ("task-slicing", "slice tasks", "10-plan", "implementation plan", "chia task"), "T2", "task slicing/planning intent"),
    ("impact-analysis", ("impact-analysis", "impact", "blast radius", "what breaks", "ảnh hưởng"), "T2", "blast-radius/preflight intent"),
    ("bug-fix", ("bug-fix", "investigate bug", "rca", "root cause"), "T1", "bug investigation workflow intent"),
    ("mh-fix", ("fix", "sửa bug", "sửa lỗi", "finding"), "T1", "direct bug fix intent"),
    ("mh-scaffold", ("scaffold", "tạo endpoint", "tạo service", "tạo page", "tạo form"), "T1", "scaffold intent"),
    ("mh-implement", ("implement", "build feature", "làm feature", "triển khai", "build page"), "T1", "feature implementation intent"),
    ("ponytail", ("ponytail", "yagni", "minimal", "simplest", "đơn giản", "làm ít", "đừng over-engineer", "over-engineer"), "T0", "minimal-correct-diff advisory intent"),
]


def load_manifests() -> dict[str, dict[str, Any]]:
    routes = {k: dict(v) for k, v in BUILTIN_ROUTES.items()}
    for manifest in sorted(WORKFLOWS.glob("*/manifest.json")):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["manifest_path"] = str(manifest.relative_to(ROOT))
        routes[data["name"]] = data
    return routes


def contains_any(text: str, needles: set[str] | tuple[str, ...]) -> list[str]:
    return [needle for needle in needles if needle in text]


def detect_route(prompt: str, routes: dict[str, dict[str, Any]]) -> tuple[str | None, str, str, list[str]]:
    text = prompt.lower()
    matches: list[tuple[str, str, str]] = []
    for workflow, terms, base_tier, reason in INTENT_RULES:
        if workflow in routes and any(term in text for term in terms):
            matches.append((workflow, base_tier, reason))
    if not matches:
        return None, "UNKNOWN", "No deterministic route matched.", []
    # Prefer the first rule in INTENT_RULES; ordering is explicit specificity.
    workflow, tier, reason = matches[0]
    ambiguity = [m[0] for m in matches[1:]]
    return workflow, tier, reason, ambiguity


def escalate_tier(base_tier: str, prompt: str) -> tuple[str, list[str]]:
    text = prompt.lower()
    risk_hits = contains_any(text, RISK_TERMS)
    t3_hits = contains_any(text, T3_TERMS)
    if t3_hits and base_tier in {"T0", "T1", "T2", "UNKNOWN"}:
        return "T3", sorted(set(t3_hits))
    if risk_hits and base_tier in {"T0", "T1", "UNKNOWN"}:
        return "T2", sorted(set(risk_hits))
    return base_tier, sorted(set(risk_hits))


def fast_path(prompt: str, workflow: str | None, risk_tier: str, uncertainty: list[str]) -> dict[str, Any]:
    text = prompt.lower()
    trivial_hits = contains_any(text, TRIVIAL_TERMS)
    allowed_workflows = {"mh-fix", "mh-implement"}
    allowed = bool(workflow in allowed_workflows and risk_tier in {"T0", "T1"} and trivial_hits and not uncertainty)
    if allowed:
        reason = "Trivial/local language found and no risk uncertainty detected. Dry-run only; not enforced."
    elif workflow not in allowed_workflows:
        reason = "Fast-path only applies to direct mh-fix/mh-implement candidates."
    elif uncertainty:
        reason = "Denied because risk uncertainty exists: " + ", ".join(uncertainty)
    elif not trivial_hits:
        reason = "Denied because prompt is not clearly trivial/local."
    else:
        reason = f"Denied because risk_tier={risk_tier}."
    return {"allowed": allowed, "reason": reason}


def skill_path(entry_skill: str | None) -> str:
    if not entry_skill:
        return ""
    p = ROOT / "engine" / "skills" / entry_skill / "SKILL.md"
    return str(p.relative_to(ROOT)) if p.exists() else ""


def workflow_readme(workflow: str | None) -> str:
    if not workflow:
        return ""
    p = WORKFLOWS / workflow / "README.md"
    return str(p.relative_to(ROOT)) if p.exists() else ""


def lifecycle_evidence_ok(route: dict[str, Any]) -> tuple[bool, str]:
    lifecycle = route.get("lifecycle_status", "")
    if lifecycle not in {"PROVEN", "DEFAULT"}:
        return False, "lifecycle below PROVEN; eval evidence cannot enable auto-route"
    eval_summary = route.get("eval_summary") or {}
    artifact = eval_summary.get("artifact_path") if isinstance(eval_summary, dict) else ""
    if not artifact:
        return False, "missing eval_summary.artifact_path for PROVEN/DEFAULT lifecycle"
    if not (ROOT / artifact).exists():
        return False, f"eval_summary.artifact_path does not exist: {artifact}"
    return True, f"eval evidence present: {artifact}"


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def route_rules(route: dict[str, Any], workflow: str | None, ponytail_modifier: bool) -> list[str]:
    rules = list(route.get("rules") or [])
    if workflow == "ponytail" or ponytail_modifier or workflow in PONYTAIL_DEFAULT_WORKFLOWS:
        rules.append("ponytail")
    if workflow in QUALITY_GATE_DEFAULT_WORKFLOWS:
        rules.append("quality-gates")
    return _unique(rules)


def route_skills(route: dict[str, Any], entry_skill: str) -> list[str]:
    return _unique(([entry_skill] if entry_skill else []) + list(route.get("skills_used") or []))


def confirmation_policy(
    workflow: str | None,
    route: dict[str, Any],
    risk_tier: str,
    effective_auto: bool,
    uncertainty: list[str],
) -> dict[str, Any]:
    if not workflow:
        return {
            "required": False,
            "action": "ASK_CLARIFICATION",
            "reason": "No deterministic route matched; clarify intent before selecting workflow/skill/rule.",
        }
    if uncertainty:
        return {
            "required": True,
            "action": "ASK_CONFIRMATION",
            "reason": "Route has uncertainty; owner must confirm before execution.",
        }
    if route.get("manual_only") or route.get("owner_invocation_required"):
        return {
            "required": True,
            "action": "ASK_CONFIRMATION",
            "reason": "Workflow is owner-gated/manual-only.",
        }
    if route.get("allowed_writes") or route.get("agents") or route.get("external_agents"):
        return {
            "required": True,
            "action": "ASK_CONFIRMATION",
            "reason": "Route may write files or invoke agents/external boundaries.",
        }
    if not effective_auto:
        return {
            "required": True,
            "action": "ASK_CONFIRMATION",
            "reason": "Auto-route is disabled by lifecycle/eval evidence.",
        }
    if risk_tier in {"T2", "T3"}:
        return {
            "required": True,
            "action": "ASK_CONFIRMATION",
            "reason": f"Risk tier {risk_tier} requires owner confirmation.",
        }
    return {
        "required": False,
        "action": "MAY_PROCEED",
        "reason": "Low-risk proven/default route with no uncertainty.",
    }


def build_decision(prompt: str) -> dict[str, Any]:
    routes = load_manifests()
    workflow, base_tier, match_reason, ambiguity = detect_route(prompt, routes)
    ponytail_modifier = bool(workflow != "ponytail" and "ponytail" in ambiguity)
    if ponytail_modifier:
        ambiguity = [item for item in ambiguity if item != "ponytail"]
    risk_tier, risk_hits = escalate_tier(base_tier, prompt)
    route = routes.get(workflow or "", {})
    lifecycle = route.get("lifecycle_status", "")
    manifest_auto = bool(route.get("auto_route_allowed"))
    evidence_ok, evidence_reason = lifecycle_evidence_ok(route)
    effective_auto = bool(manifest_auto and lifecycle in {"PROVEN", "DEFAULT"} and evidence_ok)
    uncertainty = []
    if risk_tier == "UNKNOWN":
        uncertainty.append("intent")
    uncertainty.extend(risk_hits)
    if ambiguity:
        uncertainty.append("ambiguous:" + ",".join(ambiguity))

    entry_skill = route.get("entry_skill", "")
    prompt_file = str(route.get("recommended_prompt_file") or "")
    files_to_load = [
        "AGENTS.md",
        "engine/router/README.md",
    ]
    manifest_path = route.get("manifest_path")
    if manifest_path:
        files_to_load.append(manifest_path)
    sp = skill_path(entry_skill)
    if sp:
        files_to_load.append(sp)
    wr = workflow_readme(workflow)
    if wr:
        files_to_load.append(wr)
    if workflow == "ponytail" or ponytail_modifier or workflow in PONYTAIL_DEFAULT_WORKFLOWS:
        files_to_load.append("engine/rules/ponytail.md")
    if workflow in QUALITY_GATE_DEFAULT_WORKFLOWS:
        files_to_load.append("engine/rules/quality-gates.md")
    if workflow == "harness-maintenance":
        files_to_load.extend([
            "engine/rules/artifact-policy.md",
            "engine/rules/preflight-confirmation.md",
            "engine/rules/source-discovery.md",
        ])

    required_gates = ["learning_recall before fix/review/implement/design", "lifecycle gate"]
    if workflow in QUALITY_GATE_DEFAULT_WORKFLOWS:
        required_gates.append("quality gates: reuse evidence, fix plan, regression map, validation as applicable")
    if risk_tier in {"T1", "T2", "T3"}:
        required_gates.append("CodeGraph-first source discovery for source work")
    allowed_writes = route.get("allowed_writes", [])
    if any(str(path).startswith("worktrees/") for path in allowed_writes):
        required_gates.append("worktree selected before source edits")
    elif allowed_writes:
        required_gates.append("write boundary confirmed")
    if risk_tier in {"T2", "T3"}:
        required_gates.append("deny fast-path; run impact/design/review gates as applicable")

    confidence = "low" if risk_tier == "UNKNOWN" else ("medium" if ambiguity else "high")
    reason = match_reason
    if not effective_auto:
        reason += " Auto-route is disabled because lifecycle/eval evidence is insufficient or manifest auto_route_allowed is false."
    unique_uncertainty = sorted(set(uncertainty))
    rules_to_apply = route_rules(route, workflow, ponytail_modifier)
    skills_to_apply = route_skills(route, entry_skill)

    return {
        "intent": workflow or "",
        "risk_tier": risk_tier,
        "candidate_workflow": workflow or "",
        "entry_skill": entry_skill,
        "lifecycle_status": lifecycle,
        "lifecycle_evidence": {
            "ok": evidence_ok,
            "reason": evidence_reason,
        },
        "auto_route_allowed": effective_auto,
        "confidence": confidence,
        "uncertainty": unique_uncertainty,
        "skills_to_apply": skills_to_apply,
        "candidate_agents": route.get("agents", []),
        "external_agents": route.get("external_agents", []),
        "rules_to_apply": rules_to_apply,
        "required_inputs": route.get("required_inputs", []),
        "required_gates": required_gates,
        "owner_confirmation": confirmation_policy(workflow, route, risk_tier, effective_auto, unique_uncertainty),
        "prompt_file_recommended": prompt_file,
        "prompt_file_required": False,
        "prompt_file_policy": (
            "Advisory only. Do not auto-load this file for normal daily work; use it as a "
            "session/external-agent runbook when the owner asks or when a wrapper explicitly "
            "selects a prompt_file."
        ),
        "files_to_load": files_to_load,
        "do_not_load": [
            "other workflow docs unless router decision changes",
            "engine/workflows/**/rounds/** unless an envelope points there",
            "engine/workflows/**/logs/** unless debugging that workflow",
            "second-brain/*.md wholesale; use learning_recall only",
            "payload artifacts inline unless under max_payload_inline_chars",
        ],
        "allowed_writes": route.get("allowed_writes", []),
        "validators": route.get("validators", []),
        "budget": route.get("budget", {"max_context_files": 0, "max_payload_inline_chars": 0}),
        "fast_path": fast_path(prompt, workflow, risk_tier, unique_uncertainty),
        "reason": reason,
    }


def yaml_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return ""
    if any(ch in text for ch in [":", "#", "{", "}", "[", "]", ","]) or text.lower() in {"true", "false", "null"}:
        return json.dumps(text, ensure_ascii=False)
    return text


def emit_yaml(obj: Any, indent: int = 0) -> list[str]:
    pad = " " * indent
    lines: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if value == []:
                lines.append(f"{pad}{key}: []")
                continue
            if value == {}:
                lines.append(f"{pad}{key}: {{}}")
                continue
            if isinstance(value, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.extend(emit_yaml(value, indent + 2))
            else:
                lines.append(f"{pad}{key}: {yaml_scalar(value)}")
    elif isinstance(obj, list):
        if not obj:
            lines.append(f"{pad}[]")
        for item in obj:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.extend(emit_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}- {yaml_scalar(item)}")
    else:
        lines.append(f"{pad}{yaml_scalar(obj)}")
    return lines


def self_test() -> int:
    cases = [
        ("fix trivial label typo local", "mh-fix", "T1"),
        ("implement admission API DTO change", "mh-implement", "T2"),
        ("run deep review before merge", "deep-review", "T3"),
        ("super-test inpatient module", "robust-test", "T3"),
        ("agentflow targeted e2e", "robust-test", "T3"),
        ("ui spec from DOCX and mockup", "ui-spec", "T2"),
        ("tối ưu harness hiện tại để giảm đốt token nhưng quality không giảm", "harness-maintenance", "T2"),
        ("dev from handoff owner docs for admission module", "dev-from-handoff", "T3"),
        ("bắt đầu dev từ tài liệu handoff module nội trú", "dev-from-handoff", "T3"),
        ("what breaks if we change PatientDto", "impact-analysis", "T2"),
    ]
    for prompt, workflow, tier in cases:
        decision = build_decision(prompt)
        if decision["candidate_workflow"] != workflow:
            print(f"FAIL {prompt!r}: workflow {decision['candidate_workflow']!r} != {workflow!r}")
            return 1
        if decision["risk_tier"] != tier:
            print(f"FAIL {prompt!r}: tier {decision['risk_tier']!r} != {tier!r}")
            return 1
        if decision["auto_route_allowed"] is not False:
            print(f"FAIL {prompt!r}: P1 dry-run must not auto-route")
            return 1
        if workflow in {"deep-review", "robust-test", "impact-analysis", "ui-spec"} and not decision["prompt_file_recommended"]:
            print(f"FAIL {prompt!r}: missing prompt_file_recommended")
            return 1
    print("harness_router self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Read-only MyHospital harness router dry-run")
    parser.add_argument("prompt", nargs="*", help="User prompt / intent to classify")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of YAML")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()
    prompt = " ".join(args.prompt).strip()
    if not prompt:
        parser.error("provide a prompt to classify, or --self-test")
    decision = build_decision(prompt)
    if args.json:
        print(json.dumps(decision, ensure_ascii=False, indent=2))
    else:
        print("\n".join(emit_yaml(decision)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
