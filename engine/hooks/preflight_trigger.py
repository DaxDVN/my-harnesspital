#!/usr/bin/env python3
"""Claude UserPromptSubmit hook: nudge natural-language preflight.

This hook is intentionally small and read-only. It does not print the full card on every prompt; it only tells
the agent to run `scripts/harness_preflight.py` and wait for owner confirmation when the router predicts an
actionable route that requires confirmation.
"""
from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from harness_preflight import build_preflight  # noqa: E402


def _prompt_from_stdin() -> str:
    raw = sys.stdin.read()
    if not raw.strip():
        return ""
    try:
        event = json.loads(raw)
    except Exception:
        return ""
    return str(event.get("prompt") or event.get("user_prompt") or event.get("message") or "")


def _self_test() -> int:
    preflight = build_preflight("fix visible inpatient form sheet bug with existing component reuse")
    assert preflight["status"] == "WAIT_OWNER_CONFIRMATION"
    assert preflight["predicted_workflow"] == "mh-fix"
    casual = build_preflight("nói chuyện bình thường")
    assert casual["status"] == "CLARIFY"
    print("preflight_trigger self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return _self_test()
    prompt = _prompt_from_stdin()
    if not prompt:
        return 0
    try:
        preflight = build_preflight(prompt)
    except Exception:
        return 0
    if preflight["status"] != "WAIT_OWNER_CONFIRMATION":
        return 0
    quoted = shlex.quote(prompt)
    print(
        "[preflight-confirmation] "
        f"predicted={preflight['predicted_workflow']} risk={preflight['risk_tier']} "
        "requires owner confirmation. Before executing workflows/agents/browser/source edits, show card:\n"
        f"  python scripts/harness_preflight.py {quoted}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
