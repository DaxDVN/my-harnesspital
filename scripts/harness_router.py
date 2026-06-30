#!/usr/bin/env python3
"""Read-only MyHospital harness router dry-run.

P1 scope: classify intent, risk, and files-to-load. This script never
executes workflows, edits files, enforces fast-path, or changes runtime state.
"""

from __future__ import annotations

import argparse
import json
import re
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
    "espresso-test",
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
    "espresso-test",
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
        "required_inputs": ["feature description", "target worktree for source edits"],
        "allowed_writes": ["worktrees/<slug>/fe/**", "worktrees/<slug>/be/**"],
        "validators": ["targeted build/test/typecheck", "python scripts/harness_doctor.py"],
        "budget": {"max_context_files": 0, "max_payload_inline_chars": 0},
    },
    "mh-fix": {
        "name": "mh-fix",
        "kind": "workflow",
        "entry_skill": "mh-fix",
        "recommended_prompt_file": "engine/prompts/mh-fix-approved-finding.md",
        "public_entry": True,
        "auto_route_allowed": False,
        "required_inputs": ["bug description or finding path", "target worktree for source edits"],
        "allowed_writes": ["worktrees/<slug>/fe/**", "worktrees/<slug>/be/**"],
        "validators": ["targeted regression validation", "python scripts/harness_doctor.py"],
        "budget": {"max_context_files": 0, "max_payload_inline_chars": 0},
    },
    "mh-scaffold": {
        "name": "mh-scaffold",
        "kind": "workflow",
        "entry_skill": "mh-scaffold",
        "recommended_prompt_file": "",
        "public_entry": True,
        "auto_route_allowed": False,
        "required_inputs": ["scaffold target and scope"],
        "allowed_writes": ["worktrees/<slug>/fe/**", "worktrees/<slug>/be/**"],
        "validators": ["targeted build/test/typecheck"],
        "budget": {"max_context_files": 0, "max_payload_inline_chars": 0},
    },
    "clinical-ui-design": {
        "name": "clinical-ui-design",
        "kind": "workflow",
        "entry_skill": "clinical-ui-design",
        "recommended_prompt_file": "",
        "public_entry": True,
        "auto_route_allowed": False,
        "manual_only": True,
        "owner_invocation_required": True,
        "required_inputs": ["target screen URL or module", "design intent / constraints"],
        "allowed_writes": ["docs/ui-mocks/**"],
        "validators": ["preview-only standalone HTML mocks (no source edits)"],
        "budget": {"max_context_files": 0, "max_payload_inline_chars": 0},
    },
    "ponytail": {
        "name": "ponytail",
        "kind": "advisory",
        "entry_skill": "ponytail",
        "recommended_prompt_file": "",
        "public_entry": True,
        "auto_route_allowed": False,
        "required_inputs": ["source edit, fix, implementation, scaffold, or diff review scope"],
        "allowed_writes": [],
        "validators": ["same scoped validation the task would require without Ponytail"],
        "budget": {"max_context_files": 1, "max_payload_inline_chars": 0},
    },
    "harness-maintenance": {
        "name": "harness-maintenance",
        "kind": "advisory",
        "entry_skill": "",
        "recommended_prompt_file": "",
        "public_entry": True,
        "auto_route_allowed": False,
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
    },
}


INTENT_RULES: list[tuple[str, tuple[str, ...], str, str]] = [
    ("harness-maintenance", ("harness", "harness maintenance", "harness optimize", "optimize harness", "workflow eval", "workflow routing", "router eval", "promptfoo", "context7", "codegraph maintenance", "source index", "graphify", "scanner promotion", "memory promotion", "main brain", "main-brain", "doctor", "readiness", "readiness check", "tối ưu harness", "đánh giá harness", "nâng cấp harness", "cài tooling", "tooling harness", "đốt token", "token tiêu hao", "quality không giảm"), "T2", "harness maintenance/optimization intent"),
    ("dev-from-handoff", ("dev-from-handoff", "dev from handoff", "implement from handoff", "build from handoff", "owner handoff", "handoff docs", "handoff document", "dev từ handoff", "từ tài liệu handoff", "tài liệu handoff", "tài liệu bàn giao", "triển khai từ handoff", "triển khai từ tài liệu bàn giao", "bắt đầu dev từ tài liệu", "bàn giao dev"), "T2", "owner-supplied handoff development intent"),
    ("robust-test", ("robust-test", "super-test", "progressive-test", "agentflow", "harvest", "bug harvest", "e2e harvest", "e2e test", "kiểm thử module", "test chắc", "sweep bugs"), "T3", "owner-gated robust targeted/sweep test intent"),
    ("espresso-test", ("espresso-test", "espresso test", "review-fix loop", "review fix loop", "lặp review fix", "tự fix tới sạch", "review tới sạch", "loop review fix"), "T3", "owner-gated review→fix→re-review convergence loop intent"),
    ("deep-review", ("mh-review", "deep-review", "review", "audit", "kiểm toán", "đánh giá code"), "T3", "explicit review/audit intent"),
    ("ui-spec", ("ui spec", "ui-spec", "03-ui", "mockup", "docx", "reuse audit"), "T2", "UI spec/design-source intent"),
    ("technical-design", ("technical-design", "api contract", "design api", "design the api", "08-api", "thiết kế api"), "T2", "API contract design intent"),
    ("clinical-ui-design", ("thiết kế màn hình", "thiết kế lại màn hình", "redesign screen", "his ui", "clinical ui", "màn hình lâm sàng"), "T2", "clinical/HIS UI design intent"),
    ("task-slicing", ("task-slicing", "slice tasks", "10-plan", "implementation plan", "chia task"), "T2", "task slicing/planning intent"),
    ("mh-implement", ("migration", "migrate data", "đổi schema", "backfill"), "T3", "data/schema migration intent (owner-gated, T3)"),
    ("impact-analysis", ("impact-analysis", "impact", "blast radius", "what breaks", "ảnh hưởng"), "T2", "blast-radius/preflight intent"),
    ("bug-fix", ("bug-fix", "investigate bug", "rca", "root cause"), "T1", "bug investigation workflow intent"),
    ("mh-fix", ("fix", "sửa bug", "sửa lỗi", "finding"), "T1", "direct bug fix intent"),
    ("mh-implement", ("refactor", "simplify", "cleanup", "dọn code", "tái cấu trúc"), "T1", "refactor/simplify/cleanup intent"),
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
    # Builtin routes: dynamically resolve manifest_path by checking
    # engine/workflows/<name>/manifest.json. If a manifest exists for a
    # builtin route that was NOT overridden by the glob above (e.g. it was
    # created after this code was written), pick it up automatically.
    for name, route in routes.items():
        if not route.get("manifest_path"):
            candidate = WORKFLOWS / name / "manifest.json"
            if candidate.exists():
                route["manifest_path"] = str(candidate.relative_to(ROOT))
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
    # Drop self-matches: several intents intentionally map to the same workflow
    # (e.g. refactor/migration -> mh-implement), so a later rule for the SAME
    # workflow is not a genuine ambiguity.
    ambiguity = _unique([m[0] for m in matches[1:] if m[0] != workflow])
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


# Fail-safe fallback mirroring scripts/tier_policy.json. A missing or corrupt
# tier_policy.json must NEVER crash the router; this hardcoded copy is used instead.
# Owner-locked 2026-06-26: clinical floor = opus/xhigh; coordinator = opus/low;
# non-Anthropic dispatch via `roles`/`agentic_ladder`; Opus xhigh final review mandatory
# on every code-mutating recipe. `tiers` here is the Anthropic-equivalent baseline only.
TIER_POLICY_FALLBACK: dict[str, Any] = {
    "orchestrator": {"provider": "anthropic", "model": "opus", "effort": "low"},
    "tiers": {
        "T0": {"model": "haiku", "effort": "low"},
        "T1": {"model": "sonnet", "effort": "medium"},
        "T2": {"model": "sonnet", "effort": "high"},
        "T3": {"model": "opus", "effort": "high"},
    },
    "coordinator": {"model": "opus", "effort": "low"},
    "verifier": {
        "find": {"provider": "opencode", "model": "glm-5.2", "variant": "max", "read_only": True},
        "adjudicate_block_high": {"provider": "anthropic", "model": "opus", "effort": "xhigh"},
    },
    "escalation_ladder": [
        ["sonnet", "medium"],
        ["sonnet", "high"],
        ["opus", "high"],
        ["opus", "xhigh"],
    ],
    "risk_class_floor": {
        "classes": ["clinical", "billing", "permission", "migration"],
        "floor": {"provider": "anthropic", "model": "opus", "effort": "xhigh"},
    },
    "roles": {
        "orchestrator":      {"provider": "anthropic", "model": "opus", "effort": "low"},
        "audit":             {"provider": "opencode", "model": "glm-5.2", "variant": "max", "read_only": True},
        "audit_second_lens": {"provider": "opencode", "model": "deepseek-v4-pro", "variant": "high", "read_only": True},
        "adjudicate":        {"provider": "anthropic", "model": "opus", "effort": "xhigh"},
        "final_review":      {"provider": "anthropic", "model": "opus", "effort": "xhigh"},
        "trivial":           {"provider": "opencode", "model": "mimo-v2.5", "variant": "high"},
        "mechanical_fix":    {"provider": "opencode", "model": "deepseek-v4-flash", "variant": "high"},
        "agentic_primary":   {"provider": "opencode", "model": "deepseek-v4-pro", "variant": "high"},
        "agentic_harder":    {"provider": "opencode", "model": "minimax-m3", "variant": "high"},
        "agentic_complex":   {"provider": "opencode", "model": "kimi-k2.7-code", "variant": "high"},
        "design":            {"provider": "anthropic", "model": "opus", "effort": "xhigh"},
        "clinical_floor":    {"provider": "anthropic", "model": "opus", "effort": "xhigh"},
        "danger_refactor":   {"provider": "anthropic", "model": "opus", "effort": "max"},
    },
    "agentic_ladder": ["agentic_primary", "agentic_harder", "agentic_complex", "clinical_floor", "danger_refactor"],
    "mandatory_final_review": {
        "role": "final_review",
        "skippable": False,
        "applies_to": ["single-skill", "implement+review", "bugfix", "batch-bugfix", "espresso", "full-SDD", "refactor", "scaffold"],
        "rule": "Every code-mutating workflow MUST end with an Opus 4.8 xhigh review of the produced diff, ALWAYS — even if a non-Anthropic model already reviewed. Additive, never a substitute.",
    },
}

TIER_POLICY_PATH = ROOT / "scripts" / "tier_policy.json"


def load_tier_policy() -> dict[str, Any]:
    """Load tier_policy.json; fall back to the hardcoded copy on any error."""
    try:
        data = json.loads(TIER_POLICY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return TIER_POLICY_FALLBACK
    if not isinstance(data, dict) or "tiers" not in data:
        return TIER_POLICY_FALLBACK
    return data


# Effort precedence used when applying the risk_class floor: a floor never lowers
# an already-stronger effort.
_EFFORT_RANK = {"low": 0, "medium": 1, "high": 2, "xhigh": 3}
_MODEL_RANK = {"haiku": 0, "sonnet": 1, "opus": 2}


def select_model_effort(
    risk_tier: str,
    confidence: str | None = None,
    route: dict[str, Any] | None = None,
    risk_class: str | None = None,
) -> dict[str, Any]:
    """Map an already-computed risk_tier (+confidence/risk_class) to a worker
    (model, effort) tier plus the escalation ladder. Derives only; never recomputes
    or mutates risk_tier. Fail-safe: a missing/corrupt policy file uses the fallback.
    """
    policy = load_tier_policy()
    tiers = policy.get("tiers") or TIER_POLICY_FALLBACK["tiers"]
    ladder = policy.get("escalation_ladder") or TIER_POLICY_FALLBACK["escalation_ladder"]
    floor_cfg = policy.get("risk_class_floor") or {}

    tier_default = tiers.get(risk_tier) or tiers.get("T3") or TIER_POLICY_FALLBACK["tiers"]["T3"]
    model = tier_default.get("model", "sonnet")
    effort = tier_default.get("effort", "high")
    basis = f"risk_tier={risk_tier}"

    floor_classes = floor_cfg.get("classes") or []
    floor = floor_cfg.get("floor") or {}
    if risk_class and risk_class in floor_classes and floor:
        f_model = floor.get("model", model)
        f_effort = floor.get("effort", effort)
        if _MODEL_RANK.get(f_model, 0) > _MODEL_RANK.get(model, 0):
            model = f_model
        if _EFFORT_RANK.get(f_effort, 0) > _EFFORT_RANK.get(effort, 0):
            effort = f_effort
        basis += f" + risk_class={risk_class} floor"

    return {
        "model": model,
        "effort": effort,
        "escalation_ladder": ladder,
        "basis": basis,
    }


# Cheap keyword signals for worker routing (danger / trivial / mechanical). Advisory
# only — the orchestrator makes the final per-unit call. English + Vietnamese.
# NOTE: matched on PATH-STRIPPED text with word boundaries so a path like
# "docs/audit/x.md" does NOT trigger the 'doc' trivial signal.
# Always-danger (-> opus max). A bare "refactor <one thing>" is NOT here — it only
# becomes danger when paired with a wide-scope qualifier (see _WIDE_SCOPE_TERMS).
_DANGER_TERMS = ("rewrite", "viết lại", "irreversible", "không thể hoàn", "migration", "schema")
_REFACTOR_TERMS = ("refactor", "tái cấu trúc")
_WIDE_SCOPE_TERMS = ("module", "whole", "entire", "toàn bộ", "nguyên", "all")
_TRIVIAL_TERMS = ("label", "copy", "typo", "comment", "rename", "đổi tên", "doc", "docs", "tài liệu", "docstring", "viết test", "unit test", "write test", "add test", "chú thích", "lặt vặt")
_MECHANICAL_TERMS = ("layout", "css", "style", "spacing", "padding", "margin", "alignment", "căn lề", "simple fix", "sửa nhỏ")
_READ_ONLY_RECIPES = {"review", "triage-only", "design-only"}
# Recipes shallow enough that a trivial/mechanical signal should downgrade the whole
# task. Multi-unit recipes (batch-bugfix/feature/espresso) default to agentic and
# tier per-unit at dispatch instead.
_SHALLOW_RECIPES = {"none", "single-skill"}


def _strip_paths(prompt: str) -> str:
    """Drop path-/filename-like tokens so they don't trigger keyword signals."""
    toks = [
        t for t in re.split(r"\s+", prompt or "")
        if "/" not in t and not re.search(r"\.[A-Za-z0-9]{1,5}$", t)
    ]
    return " ".join(toks).lower()


def _has_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", text) for t in terms)


def _resolve_role(roles: dict[str, Any], role_key: str) -> dict[str, Any]:
    """Resolve a role name to a concrete dispatch dict with backend + full model id."""
    r = dict(roles.get(role_key) or {})
    r["role"] = role_key
    prov = r.get("provider")
    r["backend"] = "native" if prov == "anthropic" else "opencode-cli"
    model = str(r.get("model", ""))
    if prov == "opencode" and model and not model.startswith("opencode"):
        r["model_id"] = f"opencode-go/{model}"
    else:
        r["model_id"] = model
    return r


def select_worker_routing(
    risk_tier: str,
    risk_class: str | None,
    route: dict[str, Any] | None,
    recipe: dict[str, Any] | None,
    prompt: str = "",
) -> dict[str, Any]:
    """Owner-locked 2026-06-26: pick the ACTUAL worker (provider-aware) for a task.
    Orchestrator is always Opus low and is NOT returned here. Non-Anthropic models do
    most generation/fix; Opus only at the floor (clinical xhigh) / danger (max) / the
    mandatory final review. Advisory: the orchestrator may still escalate per unit.
    """
    policy = load_tier_policy()
    roles = policy.get("roles") or TIER_POLICY_FALLBACK["roles"]
    ladder_names = policy.get("agentic_ladder") or TIER_POLICY_FALLBACK["agentic_ladder"]
    mfr = policy.get("mandatory_final_review") or TIER_POLICY_FALLBACK["mandatory_final_review"]
    floor_classes = (policy.get("risk_class_floor") or {}).get("classes") or []

    recipe_name = (recipe or {}).get("recipe") or ""
    text = _strip_paths(prompt)
    has_refactor = _has_term(text, _REFACTOR_TERMS)
    wide_scope = _has_term(text, _WIDE_SCOPE_TERMS)
    has_danger = _has_term(text, _DANGER_TERMS) or (has_refactor and wide_scope)
    has_trivial = _has_term(text, _TRIVIAL_TERMS)
    has_mechanical = _has_term(text, _MECHANICAL_TERMS)
    mutating = recipe_name not in _READ_ONLY_RECIPES

    if recipe_name in {"review", "triage-only"}:
        role_key = "audit"
    elif recipe_name == "design-only":
        role_key = "design"
    elif risk_class in floor_classes:
        # clinical/billing/permission/migration generation OR fix -> Opus floor
        role_key = "clinical_floor"
    elif has_danger:
        # whole-module / rewrite / migration / irreversible -> Opus max
        role_key = "danger_refactor"
    elif recipe_name in _SHALLOW_RECIPES and has_trivial and not has_mechanical:
        role_key = "trivial"
    elif recipe_name in _SHALLOW_RECIPES and has_mechanical:
        role_key = "mechanical_fix"
    elif recipe_name == "none":
        role_key = "trivial"
    else:
        # default mutating worker; multi-unit recipes tier per-unit at dispatch
        role_key = "agentic_primary"

    chosen = _resolve_role(roles, role_key)
    result = dict(chosen)
    result["agentic_ladder"] = [_resolve_role(roles, n) for n in ladder_names]
    result["read_only"] = bool(chosen.get("read_only"))
    result["mutating"] = bool(mutating)
    if mutating:
        result["mandatory_final_review"] = _resolve_role(roles, mfr.get("role", "final_review"))
        result["mandatory_final_review_skippable"] = bool(mfr.get("skippable", False))
    result["basis"] = f"recipe={recipe_name or '-'} risk_class={risk_class or '-'} role={role_key}"
    return result


# Fail-safe fallback for the recipe-depth ladder. Mirrors the `recipe_depth`
# block in scripts/tier_policy.json. A missing/corrupt policy file must NEVER
# crash recipe selection; this hardcoded copy is used instead. The ladder is the
# LOCKED shallowest-safe situation->recipe map; the selection logic lives in
# select_recipe() and only reads depth/metadata from here.
RECIPE_DEPTH_FALLBACK: dict[str, Any] = {
    "none": {
        "depth": 0,
        "situation": "T0 / trivial (label/copy/test/doc/local-guard, 1 file)",
        "recipe_workflow": "oc_worker:trivial",
        "phases": ["ONE mimo-v2.5 worker (role=trivial) via oc_worker + harness gate — the PM still DISPATCHES; it never reads/edits source itself"],
    },
    "single-skill": {
        "depth": 1,
        "situation": "T1 / small (few files, one component or one bug)",
        "recipe_workflow": "mh-implement|mh-fix",
        "phases": ["implement-or-fix + own self-review"],
    },
    "implement+review": {
        "depth": 2,
        "situation": "T2 (shared/API/DTO/permission/cross-file)",
        "recipe_workflow": "implement+deep-review",
        "phases": ["implement", "deep-review"],
    },
    "bugfix": {
        "depth": 2,
        "situation": "a BUG with a known repro (any tier)",
        "recipe_workflow": "bug-fix",
        "phases": ["mh-rca", "mh-fix", "review"],
    },
    "review": {
        "depth": 1,
        "situation": "read-only audit intent",
        "recipe_workflow": "deep-review",
        "phases": ["deep-review"],
    },
    "triage-only": {
        "depth": 1,
        "situation": "verify a finding/bug list real-vs-false-positive, no fix",
        "recipe_workflow": "triage-only",
        "phases": ["adjudicate", "report"],
    },
    "batch-bugfix": {
        "depth": 3,
        "situation": "a LIST of bugs to fix (batched by dependency phase)",
        "recipe_workflow": "batch-bugfix",
        "phases": ["rca-dedupe", "adjudicate", "fix", "review"],
    },
    "design-only": {
        "depth": 2,
        "situation": "design only (distill + spec), stop before implement",
        "recipe_workflow": "design-only",
        "phases": ["distill", "spec", "STOP"],
    },
    "espresso": {
        "depth": 3,
        "situation": "drive to 0 BLOCK/HIGH / review-fix-converge intent",
        "recipe_workflow": "espresso-test",
        "phases": ["review", "fix", "re-review-loop"],
    },
    "full-SDD": {
        "depth": 4,
        "situation": "T3 OR module/feature-set OR a BA-doc/spec-file input",
        "recipe_workflow": "feature",
        "phases": ["distill", "spec", "slice", "implement", "converge"],
    },
}


def load_recipe_ladder() -> dict[str, Any]:
    """Load the recipe_depth ladder from tier_policy.json; fall back to the
    hardcoded copy on any error or if the block is missing/corrupt."""
    policy = load_tier_policy()
    ladder = policy.get("recipe_depth")
    if not isinstance(ladder, dict) or not ladder:
        return RECIPE_DEPTH_FALLBACK
    return ladder


def select_recipe(
    risk_tier: str,
    route: dict[str, Any] | None = None,
    prompt_signals: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Pick the SHALLOWEST recipe that safely covers the task (Ponytail for
    orchestration). Extends (model, effort) tiering from "which model" to "which
    recipe depth". Derives ONLY from the already-computed risk_tier + predicted
    route + cheap prompt signals; it never recomputes or mutates risk_tier.
    Fail-safe: a missing/corrupt policy file uses the hardcoded ladder.
    """
    ladder = load_recipe_ladder()
    route = route or {}
    signals = prompt_signals or {}
    workflow = route.get("name") or ""

    is_bug = bool(signals.get("is_bug"))
    has_repro = bool(signals.get("has_repro"))
    is_review = bool(signals.get("is_review"))
    drive_to_clean = bool(signals.get("drive_to_clean"))
    spec_file = bool(signals.get("spec_file"))
    module_scale = bool(signals.get("module_scale"))
    trivial = bool(signals.get("trivial"))
    triage_only = bool(signals.get("triage_only"))
    batch_bugfix = bool(signals.get("batch_bugfix"))
    design_only = bool(signals.get("design_only"))

    # Intent-locked recipes win first (a read-only review or a drive-to-clean
    # loop must not be inflated into full SDD just because a module is named),
    # then tier-driven shallowest-safe depth. Order = safety, not text order.
    if triage_only:
        recipe = "triage-only"
        why = "verify finding/bug list real-vs-false-positive, no fix (read-only)"
    elif batch_bugfix:
        recipe = "batch-bugfix"
        why = "a LIST of bugs -> rca/dedupe -> adjudicate -> batched fix -> review"
    elif design_only:
        recipe = "design-only"
        why = "design only (distill + spec) -> STOP before implement"
    elif drive_to_clean or workflow == "espresso-test":
        recipe = "espresso"
        why = "drive-to-clean / review<->fix convergence intent"
    elif is_review or workflow == "deep-review":
        recipe = "review"
        why = "read-only audit/review intent"
    elif is_bug and (has_repro or workflow == "bug-fix"):
        recipe = "bugfix"
        why = "bug with a known repro -> rca -> fix -> review"
    elif risk_tier == "T3" or module_scale or spec_file:
        trig = "T3" if risk_tier == "T3" else (
            "module/feature-set scope" if module_scale else "BA-doc/spec-file input"
        )
        recipe = "full-SDD"
        why = f"full feature SDD ({trig})"
    elif risk_tier == "T2":
        recipe = "implement+review"
        why = "T2 shared/contract/cross-file -> implement then deep-review"
    elif risk_tier == "T0" or (trivial and risk_tier in {"T0", "T1"}):
        recipe = "none"
        why = "T0/trivial local change -> direct edit, no workflow"
    elif risk_tier == "T1":
        recipe = "single-skill"
        why = "T1 small scope -> one skill + its own self-review"
    else:
        recipe = "single-skill"
        why = "default minimal actionable recipe (intent unclear)"

    meta = ladder.get(recipe) or RECIPE_DEPTH_FALLBACK.get(recipe) or {}
    return {"recipe": recipe, "depth": meta.get("depth"), "why": why}


# Cheap prompt-signal vocab for recipe selection. Substring matching on the
# lowercased prompt; intentionally broad/forgiving (recipe depth derives from
# these, never replaces risk_tier).
RECIPE_BUG_TERMS = {
    "bug", "bugs", "lỗi", "sửa lỗi", "fix bug", "defect", "regression", "crash",
    "investigate bug", "rca", "root cause", "finding", "stack trace", "exception",
}
RECIPE_REPRO_TERMS = {
    "repro", "reproduce", "reproduction", "steps to reproduce", "tái hiện",
    "stack trace", "error log", "when i click", "khi bấm", "known repro",
    "consistently", "every time", "luôn xảy ra",
}
RECIPE_REVIEW_TERMS = {
    "review", "audit", "kiểm toán", "đánh giá code", "rà soát", "soát lỗi",
    "code review", "mh-review", "deep-review",
}
RECIPE_DRIVE_CLEAN_TERMS = {
    "0 block", "block/high", "drive to clean", "to 0 block", "tới sạch",
    "review fix loop", "review-fix loop", "lặp review fix", "tự fix tới sạch",
    "converge", "hội tụ", "espresso", "to done", "drive to done",
}
RECIPE_SPEC_FILE_TERMS = {
    ".md", ".docx", ".doc", "specs/", "spec file", "ba doc", "ba-doc",
    "tài liệu", "business doc", "requirements doc", "handoff doc",
}
RECIPE_BUILD_VERBS = {
    "build", "implement", "develop", "scaffold", "triển khai", "xây",
    "làm feature", "tạo module", "xây dựng",
}
RECIPE_MODULE_PHRASES = {
    "feature set", "feature-set", "whole module", "entire module",
    "toàn module", "cả module", "new module", "module mới", "subsystem",
}
# verify-first (triage-only): confirm a finding/bug list is real vs false-positive
# WITHOUT fixing.
RECIPE_VERIFY_TERMS = {
    "verify", "adjudicate", "triage", "real or false", "real vs false",
    "false positive", "false-positive", "xác minh", "kiểm chứng", "thẩm định",
}
RECIPE_NO_FIX_TERMS = {
    "don't fix", "dont fix", "do not fix", "not fix", "no fix", "without fix",
    "without fixing", "no fixing", "đừng fix", "không fix", "chưa fix",
    "không sửa", "chưa sửa", "đừng sửa", "no edit", "without editing",
}
RECIPE_FINDING_LIST_TERMS = {
    "finding", "findings", "finding list", "list of findings", "bug list",
    "danh sách lỗi", "danh sách finding", "these findings", "this finding",
}
# multi-bug fix list (batch-bugfix): a LIST of bugs to fix together.
RECIPE_BUG_LIST_TERMS = {
    "list", "these", "those", "multiple", "batch", "several", "from the list",
    "a list of", "bunch of", "danh sách", "nhiều bug", "các bug", "các lỗi",
    "những bug", "những lỗi",
}
RECIPE_FIX_VERBS = {
    "fix", "sửa", "patch", "resolve", "khắc phục", "xử lý",
}
# design-only: the front of `feature` (distill + spec) without implement.
RECIPE_DESIGN_VERBS = {
    "design", "redesign", "thiết kế", "api contract", "thiết kế api",
}
RECIPE_DESIGN_ONLY_TERMS = {
    "only", "don't implement", "dont implement", "do not implement",
    "no implement", "not implement", "without implement", "without implementing",
    "design only", "spec only", "just design", "just the design",
    "chỉ thiết kế", "chỉ design", "không implement", "đừng implement",
    "chưa implement", "không code", "đừng code", "chưa code",
}


def recipe_signals(prompt: str) -> dict[str, bool]:
    """Compute cheap, forgiving prompt signals used by select_recipe."""
    text = prompt.lower()
    module_scale = (
        (("module" in text or "feature set" in text or "feature-set" in text)
         and any(v in text for v in RECIPE_BUILD_VERBS))
        or any(p in text for p in RECIPE_MODULE_PHRASES)
    )
    is_bug = any(t in text for t in RECIPE_BUG_TERMS)
    verify = any(t in text for t in RECIPE_VERIFY_TERMS)
    no_fix = any(t in text for t in RECIPE_NO_FIX_TERMS)
    finding_list = any(t in text for t in RECIPE_FINDING_LIST_TERMS)
    triage_only = verify and (no_fix or finding_list)
    bug_list = any(t in text for t in RECIPE_BUG_LIST_TERMS)
    fix_verb = any(t in text for t in RECIPE_FIX_VERBS)
    batch_bugfix = is_bug and bug_list and fix_verb and not triage_only
    design_verb = any(t in text for t in RECIPE_DESIGN_VERBS)
    design_only = (
        design_verb
        and any(t in text for t in RECIPE_DESIGN_ONLY_TERMS)
        and not triage_only
        and not batch_bugfix
    )
    return {
        "is_bug": is_bug,
        "has_repro": any(t in text for t in RECIPE_REPRO_TERMS),
        "is_review": any(t in text for t in RECIPE_REVIEW_TERMS),
        "drive_to_clean": any(t in text for t in RECIPE_DRIVE_CLEAN_TERMS),
        "spec_file": any(t in text for t in RECIPE_SPEC_FILE_TERMS),
        "module_scale": bool(module_scale),
        "trivial": bool(contains_any(text, TRIVIAL_TERMS)),
        "triage_only": triage_only,
        "batch_bugfix": batch_bugfix,
        "design_only": design_only,
    }


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
            "reason": "Auto-route is disabled (auto_route_allowed is false).",
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
        "reason": "Low-risk route with no uncertainty.",
    }


def build_decision(prompt: str) -> dict[str, Any]:
    routes = load_manifests()
    workflow, base_tier, match_reason, ambiguity = detect_route(prompt, routes)
    ponytail_modifier = bool(workflow != "ponytail" and "ponytail" in ambiguity)
    if ponytail_modifier:
        ambiguity = [item for item in ambiguity if item != "ponytail"]
    risk_tier, risk_hits = escalate_tier(base_tier, prompt)
    route = routes.get(workflow or "", {})
    manifest_auto = bool(route.get("auto_route_allowed"))
    effective_auto = manifest_auto
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
    DEV_SIGNALS = {
        "fix", "implement", "sửa", "thêm", "tạo", "refactor", "scaffold", "dev", "code",
        "review", "audit", "điều tra", "khảo sát", "component", "module", "page", "api",
        "endpoint", "dto", "form", "hook", "adapter", "ui", "view", "controller", "service",
        "fe", "be", "frontend", "backend", "test", "kiểm thử", "lỗi", "bug", "hàm", "class",
        "function", "database", "db", "sql", "migration", "màn"
    }
    prompt_lower = prompt.lower()
    has_dev_signal = (
        (workflow and workflow != "harness-maintenance")
        or any(re.search(r"\b" + re.escape(sig) + r"\b", prompt_lower) for sig in DEV_SIGNALS)
    )
    if has_dev_signal:
        files_to_load.extend([
            "engine/rules/frontend.md",
            "engine/rules/backend.md",
        ])

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

    required_gates = ["learning_recall before fix/review/implement/design"]
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

    # Derive a risk_class (for the tier_policy floor) from the risk terms already hit.
    # Maps Vietnamese/English risk terms onto the floored classes; first match wins.
    _RISK_CLASS_TERMS = {
        "clinical": {"clinical", "admission", "discharge", "lâm sàng", "nhập viện", "xuất viện"},
        "billing": {"billing", "invoice", "payment", "insurance", "financial", "bhyt", "bhtm",
                    "viện phí", "thanh toán", "bảo hiểm"},
        "permission": {"permission", "auth", "authorization", "role", "tenant",
                       "quyền", "phân quyền"},
        "migration": {"migration", "schema"},
    }
    risk_hits_set = set(risk_hits)
    risk_class = None
    for cls, terms in _RISK_CLASS_TERMS.items():
        if risk_hits_set & terms:
            risk_class = cls
            break
    tier_policy = select_model_effort(risk_tier, confidence, route, risk_class)

    # Recipe-depth selection (Ponytail-for-orchestration): pick the shallowest
    # recipe that safely covers the task. Derives from risk_tier + route + cheap
    # signals; never replaces risk_tier.
    recipe_selection = select_recipe(risk_tier, route, recipe_signals(prompt))

    # Owner-locked worker routing (provider-aware): which model ACTUALLY runs the work.
    # Derives from recipe + risk_class + cheap signals; orchestrator stays Opus low.
    worker_routing = select_worker_routing(risk_tier, risk_class, route, recipe_selection, prompt)

    reason = match_reason
    if not effective_auto:
        reason += " Auto-route is disabled because manifest auto_route_allowed is false."
    unique_uncertainty = sorted(set(uncertainty))
    rules_to_apply = route_rules(route, workflow, ponytail_modifier)
    skills_to_apply = route_skills(route, entry_skill)

    return {
        "intent": workflow or "",
        "risk_tier": risk_tier,
        "tier_policy": tier_policy,
        "worker_routing": worker_routing,
        "recipe_selection": recipe_selection,
        "candidate_workflow": workflow or "",
        "entry_skill": entry_skill,
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
        ("refactor the patient service", "mh-implement", "T1"),
        ("thiết kế lại màn hình nhập viện", "clinical-ui-design", "T2"),
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

    # tier_policy assertions (additive). Derived from risk_tier; never replaces it.
    # This is the Anthropic-equivalent safety BASELINE, not the actual worker.
    tier_policy_cases = [
        # trivial T0 (minimal/ponytail advisory) -> haiku/low baseline
        ("minimal yagni tweak, đơn giản thôi", "haiku", "low"),
        # clinical/billing -> opus/xhigh (owner-locked floor 2026-06-26)
        ("run deep review of clinical billing invoice module before merge", "opus", "xhigh"),
    ]
    for prompt, want_model, want_effort in tier_policy_cases:
        decision = build_decision(prompt)
        tp = decision.get("tier_policy") or {}
        if tp.get("model") != want_model or tp.get("effort") != want_effort:
            print(f"FAIL {prompt!r}: tier_policy {tp.get('model')!r}/{tp.get('effort')!r} != {want_model!r}/{want_effort!r}")
            return 1

    # worker_routing assertions (owner-locked 2026-06-26). The ACTUAL provider-aware
    # worker: cheap models implement/audit, Opus only at floor/danger/final-review.
    worker_cases = [
        # read-only review -> glm-5.2 auditor, read_only, no final-review (non-mutating)
        ("review module Y for bugs", "audit", "glm-5.2", True, False),
        # batch fix -> deepseek-v4-pro agentic, mutating, mandatory opus final review
        ("fix these 5 bugs from the list", "agentic_primary", "deepseek-v4-pro", False, True),
        # clinical fix -> opus floor (xhigh), mutating, final review present
        ("fix the billing invoice clinical calculation bug", "clinical_floor", "opus", False, True),
    ]
    for prompt, want_role, want_model, want_ro, want_mfr in worker_cases:
        decision = build_decision(prompt)
        wr = decision.get("worker_routing") or {}
        if wr.get("role") != want_role or wr.get("model") != want_model:
            print(f"FAIL {prompt!r}: worker_routing {wr.get('role')!r}/{wr.get('model')!r} != {want_role!r}/{want_model!r}")
            return 1
        if bool(wr.get("read_only")) != want_ro:
            print(f"FAIL {prompt!r}: worker_routing read_only {wr.get('read_only')!r} != {want_ro!r}")
            return 1
        if (("mandatory_final_review" in wr)) != want_mfr:
            print(f"FAIL {prompt!r}: worker_routing mandatory_final_review present={('mandatory_final_review' in wr)} != {want_mfr!r}")
            return 1
        if want_mfr:
            mfrr = wr.get("mandatory_final_review") or {}
            if mfrr.get("model") != "opus" or mfrr.get("effort") != "xhigh":
                print(f"FAIL {prompt!r}: final review {mfrr.get('model')!r}/{mfrr.get('effort')!r} != opus/xhigh")
                return 1

    # recipe_selection assertions (additive). Shallowest-safe; derives from
    # risk_tier + intent, never replaces risk_tier.
    recipe_cases = [
        ("fix a typo in a button label", {"none", "single-skill"}),
        ("build the inpatient module from specs/Tài liệu Nội trú.md", {"full-SDD"}),
        ("review module Y for bugs", {"review"}),
        ("drive module X to 0 BLOCK/HIGH", {"espresso"}),
        ("verify these findings, don't fix", {"triage-only"}),
        ("fix these 5 bugs from the list", {"batch-bugfix"}),
        ("design the api for billing only", {"design-only"}),
    ]
    for prompt, want_recipes in recipe_cases:
        decision = build_decision(prompt)
        rs = decision.get("recipe_selection") or {}
        if rs.get("recipe") not in want_recipes:
            print(f"FAIL {prompt!r}: recipe {rs.get('recipe')!r} not in {sorted(want_recipes)!r}")
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
