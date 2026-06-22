#!/usr/bin/env python3
"""Promptfoo exec provider for deterministic harness router evals.

The script receives a rendered prompt as argv[1] and prints a compact,
assertion-friendly summary. It intentionally does not call any LLM.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from harness_router import build_decision  # noqa: E402


def main(argv: list[str]) -> int:
    prompt = argv[0] if argv else ""
    decision = build_decision(prompt)
    fields = {
        "candidate_workflow": decision.get("candidate_workflow", ""),
        "risk_tier": decision.get("risk_tier", ""),
        "entry_skill": decision.get("entry_skill", ""),
        "auto_route_allowed": decision.get("auto_route_allowed", ""),
        "confirmation_required": (decision.get("owner_confirmation") or {}).get("required", ""),
    }
    print(" ".join(f"{key}={value}" for key, value in fields.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
