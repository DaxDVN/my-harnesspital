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
    "[learning-trigger] Durable learning signal. If reusable, capture to second-brain only:\n"
    "  python scripts/learning_capture.py --title \"...\" --source conversation --scope <scope> "
    "--confidence <low|medium|high> --proposed-target <target> --what \"...\" --why \"...\""
)


WORK_TRIGGERS = [
    r"\bfix\b", r"\bsửa\b", r"\bdebug\b", r"\brca\b", r"\bbug\b",
    r"\breview\b", r"\baudit\b", r"\bduyệt\b", r"\brefactor\b",
    r"\bimplement\b", r"\bbuild\b", r"\bscaffold\b", r"\bcode\b",
    r"\blàm\b", r"triển khai", r"\btạo\b",
]
_RE_WORK = re.compile("|".join(WORK_TRIGGERS), re.IGNORECASE)

RECALL_REMINDER = (
    "[learning-recall] Work intent + notes exist. Run: "
    "python scripts/learning_recall.py --context \"<task>\". Open matched notes only."
)


def detect(prompt: str) -> bool:
    return bool(prompt and _RE.search(prompt))


def detect_work(prompt: str) -> bool:
    return bool(prompt and _RE_WORK.search(prompt))


def _live_note_paths(second_brain=None):
    from pathlib import Path
    sb = Path(second_brain) if second_brain else Path(__file__).resolve().parents[2] / "second-brain"
    paths = list(sb.glob("*.md")) + list((sb / "grouped").glob("[0-9][0-9]-*.md"))
    for p in sorted(paths):
        if p.name in ("INDEX.md", "README.md"):
            continue
        yield p


def _has_live_notes(second_brain=None) -> bool:
    try:
        for p in _live_note_paths(second_brain):
            if "status: provisional" in p.read_text(encoding="utf-8", errors="ignore")[:400]:
                return True
    except Exception:
        return False
    return False


def _self_test() -> int:
    import tempfile
    from pathlib import Path

    for p in ("nhớ cái này: luôn dùng BaseService", "from now on never use axios",
              "để ý cái này nhé", "remember this for later", "đừng bao giờ sửa generated file"):
        assert detect(p), f"missed trigger: {p!r}"
    for p in ("fix the login bug please", "the test always passes now", "", "implement the page"):
        assert not detect(p), f"false trigger: {p!r}"
    for p in ("fix the login bug", "implement the page", "review my diff", "sửa bug nội trú"):
        assert detect_work(p), f"missed work: {p!r}"
    for p in ("hello there", "what is this", ""):
        assert not detect_work(p), f"false work: {p!r}"
    with tempfile.TemporaryDirectory() as d:
        sb = Path(d) / "second-brain"
        grouped = sb / "grouped"
        grouped.mkdir(parents=True)
        (grouped / "01-test.md").write_text(
            "---\nstatus: provisional\n---\n# What\nGrouped live note.\n",
            encoding="utf-8",
        )
        assert _has_live_notes(sb), "grouped live notes must trigger recall"
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
