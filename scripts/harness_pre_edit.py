#!/usr/bin/env python3
"""Pre-edit risk classifier for a file about to be edited.

Classifies the risk of editing a file into T0/T1/T2/T3 by path heuristics. For
T2+ it suggests running the harness router for a full route card, auto-invokes
the router (unless --dry-run) to print a blast-radius hint, and reminds the
owner to apply rule_card fe+be before editing. Stdlib only.

Usage:
    python scripts/harness_pre_edit.py <file> [--dry-run] [--self-test]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Harness-critical scripts: changing these affects every agent/tool.
HARNESS_CRITICAL = {
    "harness_router.py",
    "harness_preflight.py",
    "rule_card.py",
    "tier_policy.json",
    "worktree.py",
    "oc_worker.py",
    "harness_runtime_contract.py",
    "harness_workflow_governance.py",
    "artifact_gate.py",
}

# BE path segments that mark clinical/billing/permission/migration surface.
T3_SEGMENTS = {
    "clinical", "billing", "permission", "permissions", "auth",
    "invoice", "invoices", "payment", "payments", "bhyt", "bhtm",
    "admission", "admissions", "discharge", "migrations",
}

# BE shared/contract markers (T2).
T2_BE_SEGMENTS = {"serviceinterface", "shared", "common", "constants"}
T2_BE_FILE_HINTS = ("dto.cs", "dtos.cs")

# FE shared/contract markers (T2).
T2_FE_SEGMENTS = {"shared", "lib", "types", "dto", "dtos", "client"}
T2_FE_FILE_HINTS = ("constants.ts",)


class ToolError(RuntimeError):
    pass


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _segments(low: str) -> list[str]:
    return [seg for seg in low.split("/") if seg]


def classify(rel_path: str) -> tuple[str, str]:
    """Return (tier, reason) for a repo-relative posix path."""
    low = rel_path.lower()
    segs = _segments(low)
    base = segs[-1] if segs else low

    # T0: docs / README / comment-only.
    if low.startswith("docs/") or base == "readme.md" or low.startswith("readme"):
        return "T0", "docs/README"

    # Harness bootloader/canon files — touch every agent.
    if base in {"agents.md", "claude.md"}:
        return "T2", "harness bootloader/canon file"

    if base.endswith((".md", ".txt")) and not low.startswith(("myhospital-", "engine/")):
        return "T0", "documentation/comment-only"

    # Backend.
    if low.startswith("myhospital-be/"):
        if "migrations/" in low or any(any(m in seg for m in T3_SEGMENTS) for seg in segs):
            return "T3", "BE clinical/billing/permission/migration"
        if any(any(m in seg for m in T2_BE_SEGMENTS) for seg in segs) or any(base.endswith(h) for h in T2_BE_FILE_HINTS):
            return "T2", "BE contract/DTO/shared util"
        return "T1", "BE single component"

    # Frontend.
    if low.startswith("myhospital-fe/"):
        if any(seg in T2_FE_SEGMENTS for seg in segs) or any(base.endswith(h) for h in T2_FE_FILE_HINTS):
            return "T2", "FE shared/contract/types"
        return "T1", "FE single component"

    # Engine canon (rules/workflows) — shared by every agent.
    if low.startswith("engine/"):
        return "T2", "harness rules/workflows (shared canon)"

    # Scripts.
    if low.startswith("scripts/"):
        if base in HARNESS_CRITICAL:
            return "T2", "harness-critical script"
        return "T1", "script (non-harness)"

    # Worktree source.
    if low.startswith("worktrees/"):
        return "T1", "worktree source"

    return "T0", "unclassified (treat as low)"


def invoke_router(file_rel: str) -> str:
    script = ROOT / "scripts" / "harness_router.py"
    if not script.exists():
        return "(harness_router.py not found)"
    proc = subprocess.run(
        [sys.executable, str(script), f"change {file_rel}"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return (proc.stdout or "").strip()


def pre_edit(args: argparse.Namespace) -> int:
    src = Path(args.file)
    if not src.exists():
        raise ToolError(f"File not found: {src}")
    file_rel = rel(src)
    tier, reason = classify(file_rel)

    print(f"File:     {file_rel}")
    print(f"Tier:     {tier}")
    print(f"Reason:   {reason}")
    print()

    if tier in {"T0", "T1"}:
        print("Low risk. Proceed with normal scoped validation.")
        return 0

    # T2+ gates.
    print("Suggested gates (T2+):")
    print(f"  - Run: python scripts/harness_router.py 'change {file_rel}'")
    print("  - Apply rule_card fe+be before editing:")
    print('      python scripts/rule_card.py fe "<task>"')
    print('      python scripts/rule_card.py be "<task>"')
    print("  - For T3 (clinical/billing/permission/migration): owner-confirm gate is REQUIRED.")
    print()

    if args.dry_run:
        print("[dry-run] would auto-invoke harness_router.py for blast-radius hint.")
        return 0

    print("== harness_router.py blast-radius hint ==")
    out = invoke_router(file_rel)
    if out:
        print(out)
    else:
        print("(router produced no output)")
    return 0


def self_test() -> int:
    cases = [
        ("docs/audit/x.md", "T0"),
        ("README.md", "T0"),
        ("scripts/learning_list.py", "T1"),
        ("scripts/harness_router.py", "T2"),
        ("engine/rules/backend.md", "T2"),
        ("myhospital-be/MyHospital.ServiceInterface/Services/PatientService.cs", "T2"),
        ("myhospital-be/MyHospital/Dto/PatientDto.cs", "T2"),
        ("myhospital-be/MyHospital.ServiceInterface/Migrations/20260101000000_Initial.cs", "T3"),
        ("myhospital-be/MyHospital.ServiceInterface/Services/BillingService.cs", "T3"),
        ("myhospital-be/MyHospital.ServiceInterface/Services/AdmissionService.cs", "T3"),
        ("myhospital-be/MyHospital.ServiceInterface/Services/BedService.cs", "T2"),
        ("myhospital-fe/src/features/patient/PatientList.tsx", "T1"),
        ("myhospital-fe/src/shared/utils/format.ts", "T2"),
        ("myhospital-fe/src/types/Constants.ts", "T2"),
        ("worktrees/slug/be/MyHospital/Services/X.cs", "T1"),
        ("AGENTS.md", "T2"),
    ]
    for path, want in cases:
        tier, _ = classify(path.lower())
        assert tier == want, f"classify({path!r}) = {tier!r}, want {want!r}"
    print("harness_pre_edit self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Pre-edit risk classifier; suggests impact-analysis for T2+",
    )
    parser.add_argument("file", nargs="?", help="file to classify (absolute or repo-relative)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print classification, do not invoke harness_router")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.file:
        parser.error("provide a file path")
    try:
        return pre_edit(args)
    except ToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
