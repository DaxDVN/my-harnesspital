#!/usr/bin/env python3
"""adapt_trigger — SessionEnd hook: run adapt_detect and print any NEW adapt-trigger report.

At session end, scan the harness for adapt-trigger signals (workflow machinery failures, repeated
bug classes, repeated learning notes) and print a human-readable trigger report for any NEW signal
the owner has not already seen. This is the auto-detect + PROPOSAL half of the adapt workflow — it
NEVER edits, NEVER spawns a fixer, NEVER auto-applies. The owner acts on a trigger with `/adapt`
(the apply half stays owner-gated per AGENTS.md §3).

Dedup: adapt_detect keeps a persistent store (.claude/.adapt-triggers.json); a trigger already
reported in a prior session is NOT re-printed. The owner clears a trigger by running /adapt (which
clears it) or `python scripts/adapt_detect.py --clear <key>`.

Fail-open: any error → exit 0, no output. The session must always be able to end.

    echo '{}' | python .claude/hooks/adapt_trigger.py
    python .claude/hooks/adapt_trigger.py --self-test
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def _direct_mode(root: Path) -> bool:
    """Owner-opened direct-collaboration window: adapt auto-detection stays silent (the owner is
    collaborating directly, so the SessionEnd adapt report would be noise). AGENTS.md §3."""
    return (root / ".direct-mode").exists() or os.environ.get("MH_DIRECT") == "1"


def emit(root: Path) -> str | None:
    """Run adapt_detect and return its stdout if it printed any NEW trigger, else None.

    Silent (returns None) when DIRECT-MODE is active — the owner has opened a direct-collaboration
    window where adapt auto-detection is off (AGENTS.md §3). The owner can still run
    `python scripts/adapt_detect.py` manually if needed.
    """
    if _direct_mode(root):
        return None
    script = root / "scripts" / "adapt_detect.py"
    if not script.exists():
        return None
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=90, stdin=subprocess.DEVNULL,
        )
    except Exception:
        return None  # fail-open: never block session end
    out = proc.stdout.strip()
    return out or None


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "adapt_detect.py").write_text(
            "import sys; print('ADAPT-TRIGGER (mode=A, target=demo, key=abc)\\n  suggestion: /adapt')\n",
            encoding="utf-8",
        )
        out = emit(root)
        assert out is not None and "ADAPT-TRIGGER" in out, "emit must return the script stdout"
        # direct-mode active → silent
        (root / ".direct-mode").write_text("", encoding="utf-8")
        assert emit(root) is None, "direct-mode must silence adapt_trigger"
        (root / ".direct-mode").unlink()
        # missing script → None
        (root / "scripts" / "adapt_detect.py").unlink()
        assert emit(root) is None, "missing script must return None"
    # malformed stdin → main exits 0
    assert main(["--from-stdin-test"], stdin_text="not json {{{") == 0
    assert main(["--from-stdin-test"], stdin_text="") == 0
    print("adapt_trigger self-test: OK")
    return 0


def main(argv: list[str], stdin_text: str | None = None) -> int:
    if "--self-test" in argv:
        return _self_test()
    try:
        raw = stdin_text if stdin_text is not None else sys.stdin.read()
        if raw and raw.strip():
            try:
                json.loads(raw)
            except Exception:
                pass
    except Exception:
        return 0
    try:
        block = emit(_root())
    except Exception:
        return 0
    if block:
        print(block)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
