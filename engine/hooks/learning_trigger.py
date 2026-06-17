#!/usr/bin/env python3
"""learning_trigger — UserPromptSubmit hook: reliably NUDGE a second-brain capture.

The #1 self-learning gap was that capture depended on the agent *remembering*. This hook makes it
deterministic: when the owner's prompt signals a durable learning, it injects a reminder so the agent
captures before ending the turn. It **NEVER writes anything** — capture is the agent running
`scripts/learning_capture.py`, which lands in **second-brain/ ONLY**. Promotion to main-brain stays
OWNER-gated via `/promote` (the guard blocks agent main-brain writes regardless). Fail-open: any error or a
non-trigger prompt → exit 0 with no output.

    echo '{"prompt":"nhớ cái này: luôn dùng BaseService"}' | python engine/hooks/learning_trigger.py
    python engine/hooks/learning_trigger.py --self-test
"""
from __future__ import annotations

import json
import re
import sys

# Intent phrases only (NOT bare always/never — those are too noisy). VN + EN.
TRIGGERS = [
    r"nhớ cái này", r"ghi nhớ", r"để ý cái này", r"từ giờ", r"từ nay", r"lần sau",
    r"đừng bao giờ", r"luôn nhớ", r"quy tắc", r"\bremember this\b", r"\bmake this a rule\b",
    r"\bfrom now on\b", r"\bgoing forward\b", r"\bdon'?t ever\b", r"\bnever again\b",
    r"\bpromote this later\b", r"\bkeep in mind\b",
]
_RE = re.compile("|".join(TRIGGERS), re.IGNORECASE)

REMINDER = (
    "[learning-trigger] The owner signalled a durable learning. Before ending this turn, capture it as a "
    "PROVISIONAL second-brain entry:\n"
    "  python scripts/learning_capture.py --title \"…\" --source conversation "
    "--scope <workspace|backend|frontend|module:X|workflow:X> --confidence <low|medium|high> "
    "--proposed-target <engine/rules/*|engine/skills/*|deep-review/checklist|main-brain|skill|spec-decision|reject> "
    "--what \"…\" --why \"…\"\n"
    "Rules: writes second-brain/ ONLY — NEVER main-brain/ (owner-gated via /promote). A decision scoped to ONE "
    "module → specs/<m>/06-decision-log.md instead. Purely task-local → skip. Recurrence auto-appends 'Seen again'."
)


def detect(prompt: str) -> bool:
    return bool(prompt and _RE.search(prompt))


def _self_test() -> int:
    for p in ("nhớ cái này: luôn dùng BaseService", "from now on never use axios",
              "để ý cái này nhé", "remember this for later", "đừng bao giờ sửa generated file"):
        assert detect(p), f"missed trigger: {p!r}"
    for p in ("fix the login bug please", "the test always passes now", "", "implement the page"):
        assert not detect(p), f"false trigger: {p!r}"
    print("learning_trigger self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return _self_test()
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        event = json.loads(raw)
        prompt = event.get("prompt") or event.get("user_prompt") or event.get("message") or ""
    except Exception:
        return 0
    if detect(str(prompt)):
        print(REMINDER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
