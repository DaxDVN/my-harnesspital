#!/usr/bin/env python3
"""Natural-language preflight for MyHospital harness routing.

This is a read-only confirmation helper. It predicts the workflow/skill/agent/rule set for a natural-language
prompt and renders a compact owner-facing confirmation card. It never executes workflows, launches agents, edits
files, or validates source code.

Usage:
    python scripts/harness_preflight.py "<user prompt>"
    python scripts/harness_preflight.py --json "<user prompt>"
    python scripts/harness_preflight.py --self-test
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from harness_router import build_decision  # noqa: E402
from rule_card import select_cards  # noqa: E402


FE_TERMS = {
    "fe", "frontend", "ui", "tsx", "component", "form", "sheet", "page", "browser", "css", "layout",
    "giao dien", "man hinh", "nut", "bang", "modal", "input", "filter", "table", "grid",
}

BE_TERMS = {
    "be", "backend", "api", "service", "dto", "migration", "db", "sql", "permission", "auth", "tenant",
    "hospital", "controller", "endpoint", "schema", "logic", "business", "nghiep vu", "phan quyen",
    "database", "ef", "migrate",
}

WORKTREE_GENERIC_TOKENS = {"fix", "bug", "wt", "worktree", "ipd", "v1", "v2", "v3", "v4", "feature"}


def _csv(items: list[str]) -> str:
    return ", ".join(items) if items else "(none)"


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _norm(text: str) -> str:
    deaccent = "".join(
        ch for ch in unicodedata.normalize("NFKD", text.lower())
        if not unicodedata.combining(ch)
    )
    return re.sub(r"[^a-z0-9]+", " ", deaccent).strip()


def detect_package_scope(prompt: str) -> dict[str, Any]:
    text = f" {_norm(prompt)} "
    compact = text.replace(" ", "")
    fe_hits = sorted(
        term for term in FE_TERMS
        if f" {term} " in text or (term in {"ui", "tsx", "css"} and term in compact)
    )
    be_hits = sorted(
        term for term in BE_TERMS
        if f" {term} " in text or (term in {"api", "dto", "sql", "db"} and term in compact)
    )
    if fe_hits and be_hits:
        scope = "FE+BE"
        files = ["myhospital-fe/CLAUDE.md"] + select_cards("fe", prompt) + select_cards("be", prompt)
        sequence = "BE contract first -> regenerate FE DTO/client -> FE validation"
    elif fe_hits:
        scope = "FE"
        files = ["myhospital-fe/CLAUDE.md"] + select_cards("fe", prompt)
        sequence = "FE rule cards -> CodeGraph FE -> targeted FE validation"
    elif be_hits:
        scope = "BE"
        files = select_cards("be", prompt)
        sequence = "BE rule cards -> CodeGraph BE -> targeted BE validation"
    else:
        scope = "UNKNOWN"
        files = []
        sequence = "ask/confirm package scope if source edits are needed"
    return {
        "scope": scope,
        "fe_hits": fe_hits,
        "be_hits": be_hits,
        "files_to_load": files,
        "sequence": sequence,
    }


def _load_worktrees() -> list[dict[str, str]]:
    proc = subprocess.run(
        [sys.executable, "scripts/worktree.py", "list"],
        cwd=str(ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    )
    if proc.returncode != 0:
        return []
    rows: list[dict[str, str]] = []
    for line in proc.stdout.splitlines()[1:]:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 6:
            continue
        rows.append({
            "slug": parts[0],
            "slot": parts[1],
            "fe_url": parts[2],
            "be_url": parts[3],
            "sql": parts[4],
            "status": parts[-1],
        })
    return rows


def _worktree_match_reason(prompt_norm: str, slug: str) -> str:
    slug_norm = _norm(slug)
    if f" {slug_norm} " in f" {prompt_norm} ":
        return "slug"
    tokens = [tok for tok in slug_norm.split() if tok not in WORKTREE_GENERIC_TOKENS]
    if tokens and all(f" {tok} " in f" {prompt_norm} " for tok in tokens):
        return "slug-token"
    if len(tokens) >= 2:
        for i in range(len(tokens) - 1):
            phrase = " ".join(tokens[i:i + 2])
            if f" {phrase} " in f" {prompt_norm} ":
                return "slug-phrase"
    return ""


def detect_worktrees(prompt: str) -> dict[str, Any]:
    prompt_norm = _norm(prompt)
    matches = []
    for wt in _load_worktrees():
        reason = _worktree_match_reason(prompt_norm, wt["slug"])
        if reason:
            item = dict(wt)
            item["match"] = reason
            matches.append(item)
    return {
        "matches": matches,
        "selected": matches[0] if len(matches) == 1 else None,
        "ambiguous": len(matches) > 1,
    }


def route_needs_worktree(decision: dict[str, Any], prompt: str) -> bool:
    prompt_norm = _norm(prompt)
    allowed_writes = decision.get("allowed_writes", [])
    required_inputs = decision.get("required_inputs", [])
    if "worktree" in prompt_norm:
        return True
    if any(str(path).startswith("worktrees/") for path in allowed_writes):
        return True
    return any("worktree" in str(item).lower() for item in required_inputs)


def build_preflight(prompt: str) -> dict[str, Any]:
    decision = build_decision(prompt)
    package_scope = detect_package_scope(prompt)
    worktree = detect_worktrees(prompt)
    if not route_needs_worktree(decision, prompt):
        worktree = dict(worktree)
        worktree["selected"] = None
        worktree["ambiguous"] = False
    confirmation = decision.get("owner_confirmation") or {}
    candidate = decision.get("candidate_workflow") or ""
    action = confirmation.get("action") or "ASK_CLARIFICATION"
    needs_confirmation = bool(confirmation.get("required"))
    if not candidate:
        status = "CLARIFY"
    elif needs_confirmation:
        status = "WAIT_OWNER_CONFIRMATION"
    else:
        status = "READY_AFTER_ROUTER"
    return {
        "status": status,
        "prompt": prompt,
        "predicted_workflow": candidate,
        "risk_tier": decision.get("risk_tier"),
        "tier_policy": decision.get("tier_policy", {}),
        "worker_routing": decision.get("worker_routing", {}),
        "recipe_selection": decision.get("recipe_selection", {}),
        "confidence": decision.get("confidence"),
        "action": action,
        "needs_owner_confirmation": needs_confirmation,
        "confirmation_reason": confirmation.get("reason", ""),
        "entry_skill": decision.get("entry_skill", ""),
        "skills_to_apply": decision.get("skills_to_apply", []),
        "candidate_agents": decision.get("candidate_agents", []),
        "external_agents": decision.get("external_agents", []),
        "rules_to_apply": decision.get("rules_to_apply", []),
        "required_gates": decision.get("required_gates", []),
        "required_inputs": decision.get("required_inputs", []),
        "files_to_load": _unique(list(decision.get("files_to_load", [])) + package_scope["files_to_load"]),
        "package_scope": package_scope,
        "worktree": worktree,
        "allowed_writes": decision.get("allowed_writes", []),
        "validators": decision.get("validators", []),
        "blocked_until_confirmed": [
            "workflow execution",
            "agent/subagent launch",
            "browser/E2E sweep",
            "source edits",
            "external executor call",
        ] if needs_confirmation else [],
        "decision": decision,
    }


def render_card(preflight: dict[str, Any]) -> str:
    wr = preflight.get("worker_routing", {}) or {}
    _disp = wr.get("model_id") or wr.get("model") or "?"
    _eff = wr.get("variant") or wr.get("effort") or "?"
    _ro = " · read-only" if wr.get("read_only") else ""
    worker_line = f"- → Worker dispatch: {_disp} ({_eff}) [{wr.get('backend', '?')}] role={wr.get('role', '?')}{_ro}"
    mfr = wr.get("mandatory_final_review")
    review_line = (
        f"- ⚠ BẮT BUỘC review cuối: {mfr.get('model', '?')}/{mfr.get('effort', '?')} (Opus xhigh; model TQ review KHÔNG thay thế)"
        if mfr else "- (read-only / non-mutating — không cần review cuối)"
    )
    lines = [
        "NL Preflight — chờ xác nhận" if preflight["needs_owner_confirmation"] else "NL Preflight",
        "",
        f"- Dự đoán workflow: {preflight['predicted_workflow'] or '(chưa rõ)'}",
        f"- Risk tier: {preflight['risk_tier']} · confidence: {preflight['confidence']}",
        worker_line,
        review_line,
        f"- Floor (Anthropic-equiv baseline): {preflight['tier_policy'].get('model', '?')}/{preflight['tier_policy'].get('effort', '?')}",
        f"- recipe: {preflight['recipe_selection'].get('recipe', '?')} ({preflight['recipe_selection'].get('why', '')})",
        f"- Skill: {preflight['entry_skill'] or '(none)'}",
        f"- Skills áp dụng: {_csv(preflight['skills_to_apply'])}",
        f"- Agents dự kiến: {_csv(preflight['candidate_agents'])}",
        f"- External agents: {_csv(preflight['external_agents'])}",
        f"- Rules áp dụng: {_csv(preflight['rules_to_apply'])}",
        f"- Package scope: {preflight['package_scope']['scope']} ({preflight['package_scope']['sequence']})",
        f"- Worktree match: {preflight['worktree']['selected']['slug'] if preflight['worktree']['selected'] else ('AMBIGUOUS' if preflight['worktree']['ambiguous'] else '(none)')}",
        f"- Gates: {_csv(preflight['required_gates'])}",
        f"- Files sẽ load: {_csv(preflight['files_to_load'])}",
        f"- Writes cho phép: {_csv(preflight['allowed_writes'])}",
    ]
    if preflight["required_inputs"]:
        lines.append(f"- Input còn cần: {_csv(preflight['required_inputs'])}")
    if preflight["validators"]:
        lines.append(f"- Validator dự kiến: {_csv(preflight['validators'])}")
    lines.extend([
        "",
        f"Lý do: {preflight['confirmation_reason'] or 'read-only preflight'}",
    ])
    if preflight["status"] == "CLARIFY":
        lines.append("Cần bạn làm rõ intent/worktree/scope trước khi chọn workflow.")
    elif preflight["needs_owner_confirmation"]:
        lines.append("Xác nhận bằng: `đồng ý route này` hoặc sửa lại workflow/scope bạn muốn.")
        lines.append("Trước khi xác nhận, agent không được execute workflow, launch agent, chạy browser sweep, hoặc sửa source.")
    else:
        lines.append("Không cần owner confirmation theo policy hiện tại; agent vẫn phải giữ đúng gates/validation.")
    return "\n".join(lines)


def self_test() -> int:
    global _load_worktrees
    original_loader = _load_worktrees

    def fake_worktrees() -> list[dict[str, str]]:
        return [
            {
                "slug": "fix-bug-noi-tru",
                "slot": "2",
                "fe_url": "http://localhost:3002",
                "be_url": "http://localhost:5002",
                "sql": "localhost,1435/MyHospital",
                "status": "OK",
            },
            {
                "slug": "vital-signs",
                "slot": "3",
                "fe_url": "http://localhost:3003",
                "be_url": "http://localhost:5003",
                "sql": "localhost,1436/MyHospital",
                "status": "OK",
            },
        ]

    _load_worktrees = fake_worktrees
    try:
        cases = [
            ("fix visible inpatient form sheet bug with existing component reuse", "WAIT_OWNER_CONFIRMATION", "mh-fix"),
            ("sửa bug sheet nội trú trong worktree fix-bug-noi-tru", "WAIT_OWNER_CONFIRMATION", "mh-fix"),
            ("run deep review before merge", "WAIT_OWNER_CONFIRMATION", "deep-review"),
            ("super-test inpatient module", "WAIT_OWNER_CONFIRMATION", "robust-test"),
            ("tối ưu harness hiện tại để giảm đốt token nhưng quality không giảm", "WAIT_OWNER_CONFIRMATION", "harness-maintenance"),
            ("refactor the patient service", "WAIT_OWNER_CONFIRMATION", "mh-implement"),
            ("thiết kế lại màn hình nhập viện", "WAIT_OWNER_CONFIRMATION", "clinical-ui-design"),
            ("nói chuyện bình thường", "CLARIFY", ""),
        ]
        for prompt, want_status, want_workflow in cases:
            preflight = build_preflight(prompt)
            if preflight["status"] != want_status:
                print(f"FAIL {prompt!r}: status {preflight['status']!r} != {want_status!r}")
                return 1
            if preflight["predicted_workflow"] != want_workflow:
                print(f"FAIL {prompt!r}: workflow {preflight['predicted_workflow']!r} != {want_workflow!r}")
                return 1
            if want_status == "WAIT_OWNER_CONFIRMATION" and not preflight["needs_owner_confirmation"]:
                print(f"FAIL {prompt!r}: expected owner confirmation")
                return 1
        sheet = build_preflight("sửa bug sheet nội trú trong worktree fix-bug-noi-tru")
        if sheet["package_scope"]["scope"] != "FE":
            print(f"FAIL package scope: {sheet['package_scope']['scope']!r} != 'FE'")
            return 1
        if not sheet["worktree"]["selected"] or sheet["worktree"]["selected"]["slug"] != "fix-bug-noi-tru":
            print("FAIL worktree detection for fix-bug-noi-tru")
            return 1
        # tier_policy passthrough assertions (additive). Derived from risk_tier.
        tier_policy_cases = [
            # trivial T0 (minimal/ponytail advisory) -> haiku/low baseline
            ("minimal yagni tweak, đơn giản thôi", "haiku", "low"),
            # clinical/billing -> opus/xhigh (owner-locked floor 2026-06-26)
            ("change invoice billing calculation for clinical order", "opus", "xhigh"),
        ]
        for prompt, want_model, want_effort in tier_policy_cases:
            pf = build_preflight(prompt)
            tp = pf.get("tier_policy") or {}
            if tp.get("model") != want_model or tp.get("effort") != want_effort:
                print(f"FAIL {prompt!r}: tier_policy {tp.get('model')!r}/{tp.get('effort')!r} != {want_model!r}/{want_effort!r}")
                return 1
        # worker_routing passthrough (owner-locked): card surfaces the real worker.
        wr_pf = build_preflight("fix these 5 bugs from the list")
        wr = wr_pf.get("worker_routing") or {}
        if wr.get("model") != "deepseek-v4-pro" or "mandatory_final_review" not in wr:
            print(f"FAIL worker_routing passthrough: {wr.get('model')!r} / mfr={'mandatory_final_review' in wr}")
            return 1
        # recipe_selection passthrough assertions (additive). Shallowest-safe.
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
            pf = build_preflight(prompt)
            rs = pf.get("recipe_selection") or {}
            if rs.get("recipe") not in want_recipes:
                print(f"FAIL {prompt!r}: recipe {rs.get('recipe')!r} not in {sorted(want_recipes)!r}")
                return 1
    finally:
        _load_worktrees = original_loader
    print("harness_preflight self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Render a natural-language harness preflight confirmation card")
    parser.add_argument("prompt", nargs="*", help="User prompt / intent to classify")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    prompt = " ".join(args.prompt).strip()
    if not prompt:
        parser.error("provide a prompt to classify, or --self-test")
    preflight = build_preflight(prompt)
    if args.json:
        print(json.dumps(preflight, indent=2, ensure_ascii=False))
    else:
        print(render_card(preflight))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
