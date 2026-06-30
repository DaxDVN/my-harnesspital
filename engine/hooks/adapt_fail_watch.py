#!/usr/bin/env python3
"""adapt_fail_watch — PostToolUse hook: detect a workflow run ledger that just ended badly.

When a Write/Edit lands on a workflow run-state ledger (engine/workflows/*/runs/**/00-*-state.md)
and that ledger's `status` is BLOCKED / CAP_HIT / FAILED with a machinery root-cause hint, queue an
adapt-trigger for the NEXT adapt_detect scan (so the SessionEnd report picks it up). This is the
MID-session detection that complements the SessionEnd full scan — it catches a failure the moment
the coordinator writes the stop status, without waiting for session end.

It NEVER blocks, NEVER edits, NEVER spawns a fixer. It only writes the trigger key into the
adapt_detect dedup store (marking it as NOT-yet-reported so SessionEnd prints it). Fail-open.

    echo '{"tool_name":"Write","tool_input":{"file_path":"..."}}' | python .claude/hooks/adapt_fail_watch.py
    python .claude/hooks/adapt_fail_watch.py --self-test
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

BAD_STATUSES = {"BLOCKED", "CAP_HIT", "FAILED"}
MACHINERY_HINT = re.compile(r"(?i)workflow|harness|manifest|gate|hook|ledger|envelope|registry")
STORE_KEYS = ("reported",)  # we write into the same store adapt_detect uses


def _root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def _direct_mode(root: Path) -> bool:
    """Owner-opened direct-collaboration window: adapt auto-detection stays silent (the owner is
    fixing harness issues directly with Claude, so adapt triggers would be noise). AGENTS.md §3."""
    return (root / ".direct-mode").exists() or os.environ.get("MH_DIRECT") == "1"


def _store_path(root: Path) -> Path:
    return root / ".claude" / ".adapt-triggers.json"


def _is_state_ledger(path: str) -> bool:
    return bool(re.search(r"engine/workflows/[^/]+/runs/.+/00-.*-state\.md$", path))


def _workflow_from_path(path: str) -> str:
    m = re.search(r"engine/workflows/([^/]+)/runs/", path)
    return m.group(1) if m else "unknown"


def _parse_status(text: str) -> str | None:
    m = re.search(r"(?im)^\s*-?\s*status\s*:\s*(\w+)", text)
    return m.group(1).upper() if m else None


def _stop_reason(text: str) -> str:
    m = re.search(r"(?is)##\s*Stop reason.*?(?:##\s|\Z)", text)
    return m.group(0)[:300] if m else ""


def _load_store(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"reported": {}}


def _save_store(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def maybe_queue(file_path: str, file_content: str | None, root: Path) -> str | None:
    """If the written file is a state ledger ending badly with a machinery hint, queue a trigger.

    Returns a short notice string if a trigger was queued, else None.
    Silent when DIRECT-MODE is active (AGENTS.md §3) — the owner is collaborating directly, so
    adapt auto-detection is off; the owner can still invoke `/adapt` manually if needed.
    """
    if _direct_mode(root):
        return None
    if not _is_state_ledger(file_path):
        return None
    # content may come from tool_input (Write) or we read the file (Edit fallback)
    text = file_content
    if text is None:
        try:
            text = (root / file_path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None
    status = _parse_status(text)
    if status not in BAD_STATUSES:
        return None
    stop = _stop_reason(text)
    if not MACHINERY_HINT.search(stop):
        return None  # task failure, not machinery — not adapt-worthy
    wf = _workflow_from_path(file_path)
    sig = f"run:{wf}:{status}:{hashlib.md5(stop.encode()).hexdigest()[:8]}"
    key_raw = f"A|{wf}|{sig}"
    key = hashlib.md5(key_raw.encode()).hexdigest()[:12]
    store = _load_store(_store_path(root))
    # Remove the key from `reported` so the NEXT adapt_detect scan re-emits it as fresh.
    # (adapt_detect records reported keys; deleting ensures it re-surfaces.)
    was_reported = key in store.get("reported", {})
    if was_reported:
        del store["reported"][key]
    # Also stash the signal so adapt_detect's run-ledger scan picks it up even if the file scan
    # misses it (defence in depth). We store it under a "queued" key.
    already_queued = key in store.get("queued", {})
    store.setdefault("queued", {})[key] = {
        "mode": "A", "target": wf, "root_cause_signature": sig,
        "source": f"post-tool-fail-watch:{file_path}", "fail_count": 1,
        "evidence_path": file_path,
    }
    _save_store(_store_path(root), store)
    if was_reported or not already_queued:
        return f"[adapt-fail-watch] queued trigger for {wf} ({status}) — will appear in the next adapt report"
    return None  # already queued and not previously reported — silent (SessionEnd will print it)


def _parse(event: dict) -> tuple[str, dict]:
    tool = str(event.get("tool_name") or event.get("tool") or event.get("name") or "")
    ti = event.get("tool_input")
    if not isinstance(ti, dict):
        for alt in ("params", "arguments", "input"):
            cand = event.get(alt)
            if isinstance(cand, dict):
                ti = cand
                break
    if not isinstance(ti, dict):
        ti = {}
    return tool.lower(), ti


def _self_test() -> int:
    import tempfile

    failures = 0

    def check(cond: bool, msg: str) -> None:
        nonlocal failures
        if not cond:
            failures += 1
            print(f"FAIL: {msg}")

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        ledger = "engine/workflows/bug-fix/runs/demo/run-001/00-bug-fix-state.md"
        # not a state ledger → no-op
        assert maybe_queue("docs/audit/x.md", None, root) is None, "non-ledger must be no-op"
        # state ledger, status DONE → no-op
        assert maybe_queue(ledger, "status : DONE\n", root) is None, "DONE must be no-op"
        # state ledger, BLOCKED but no machinery hint → no-op (task failure)
        assert maybe_queue(ledger, "status : BLOCKED\n## Stop reason\ntask bug in RoomService\n", root) is None, "task failure must be no-op"
        # state ledger, BLOCKED + machinery hint → queue
        notice = maybe_queue(ledger, "status : BLOCKED\n## Stop reason\nworkflow gate mis-fired (manifest drift)\n", root)
        assert notice is not None and "bug-fix" in notice, "machinery BLOCKED must queue"
        store = _load_store(_store_path(root))
        assert "queued" in store and len(store["queued"]) == 1, "queued store must have 1 entry"
        # re-queue same → silent (already queued)
        assert maybe_queue(ledger, "status : BLOCKED\n## Stop reason\nworkflow gate mis-fired (manifest drift)\n", root) is None, "re-queue must be silent"
        # CAP_HIT + machinery → queue
        ledger2 = "engine/workflows/pm-orchestrator/runs/demo/run-002/00-pm-state.md"
        notice2 = maybe_queue(ledger2, "status   : CAP_HIT\n## Stop reason\nharness hook drift\n", root)
        assert notice2 is not None and "pm-orchestrator" in notice2, "CAP_HIT machinery must queue"

        # direct-mode active → silent even for machinery BLOCKED (owner is collaborating directly)
        (root / ".direct-mode").write_text("", encoding="utf-8")
        assert maybe_queue(ledger, "status : BLOCKED\n## Stop reason\nworkflow gate mis-fired\n", root) is None, "direct-mode must silence fail-watch"
        (root / ".direct-mode").unlink()

    # malformed stdin → exit 0
    assert main(["--from-stdin-test"], stdin_text="not json {{{") == 0
    assert main(["--from-stdin-test"], stdin_text="") == 0

    if failures:
        print(f"adapt_fail_watch self-test: {failures} FAILED")
        return 1
    print("adapt_fail_watch self-test: OK")
    return 0


def main(argv: list[str], stdin_text: str | None = None) -> int:
    if "--self-test" in argv:
        return _self_test()
    try:
        raw = stdin_text if stdin_text is not None else sys.stdin.read()
        if not raw.strip():
            return 0
        event = json.loads(raw)
    except Exception:
        return 0
    if not isinstance(event, dict):
        return 0
    tool_lower, ti = _parse(event)
    if tool_lower not in {"write", "edit", "multiedit"}:
        return 0
    file_path = str(ti.get("file_path") or ti.get("path") or "")
    if not file_path:
        return 0
    content = ti.get("content") if tool_lower == "write" else None
    try:
        notice = maybe_queue(file_path.replace("\\", "/"), content, _root())
    except Exception:
        return 0
    if notice:
        print(notice, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
