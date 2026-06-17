#!/usr/bin/env python3
"""learning_trigger — UserPromptSubmit hook: reliably NUDGE second-brain capture AND recall.

Two self-learning gaps, both "the agent forgets": (1) capture — when the owner signals a durable learning,
nudge a provisional second-brain write; (2) recall — when the prompt signals relevant WORK and second-brain
has notes, nudge consulting the applicability MAP (so on-demand notes don't rot unread). This hook makes both
deterministic. It **NEVER writes anything** — capture is the agent running
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


WORK_TRIGGERS = [
    r"\bfix\b", r"\bsửa\b", r"\bdebug\b", r"\brca\b", r"\bbug\b",
    r"\breview\b", r"\baudit\b", r"\bduyệt\b", r"\brefactor\b",
    r"\bimplement\b", r"\bbuild\b", r"\bscaffold\b", r"\bcode\b",
    r"\blàm\b", r"triển khai", r"\btạo\b",
]
_RE_WORK = re.compile("|".join(WORK_TRIGGERS), re.IGNORECASE)

RECALL_REMINDER = (
    "[learning-recall] Relevant work + second-brain has notes. BEFORE acting, consult the applicability MAP "
    "(do NOT read the full second-brain):\n"
    "  python scripts/learning_recall.py --context \"<this task in a few words>\"\n"
    "Open ONLY the matched notes — provisional strong-hints: apply if they fit, but verify."
)


def detect(prompt: str) -> bool:
    return bool(prompt and _RE.search(prompt))


def detect_work(prompt: str) -> bool:
    return bool(prompt and _RE_WORK.search(prompt))


def _has_live_notes() -> bool:
    from pathlib import Path
    sb = Path(__file__).resolve().parents[2] / "second-brain"
    try:
        for p in sb.glob("*.md"):
            if p.name in ("INDEX.md", "README.md"):
                continue
            if "status: provisional" in p.read_text(encoding="utf-8", errors="ignore")[:400]:
                return True
    except Exception:
        return False
    return False


def _self_test() -> int:
    for p in ("nhớ cái này: luôn dùng BaseService", "from now on never use axios",
              "để ý cái này nhé", "remember this for later", "đừng bao giờ sửa generated file"):
        assert detect(p), f"missed trigger: {p!r}"
    for p in ("fix the login bug please", "the test always passes now", "", "implement the page"):
        assert not detect(p), f"false trigger: {p!r}"
    for p in ("fix the login bug", "implement the page", "review my diff", "sửa bug nội trú"):
        assert detect_work(p), f"missed work: {p!r}"
    for p in ("hello there", "what is this", ""):
        assert not detect_work(p), f"false work: {p!r}"
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
    elif detect_work(str(prompt)) and _has_live_notes():
        print(RECALL_REMINDER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
