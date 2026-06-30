#!/usr/bin/env python3
"""orchestrator_drift_guard — PreToolUse hook: re-inject PM invariants EVERY tool call while a run is active.

Anti-drift contract (closes D1 + D4 of the long-session drift bug). The sibling
`orchestrator_invariants.py` only fires on UserPromptSubmit (once per user turn), so during a
multi-tool autonomous turn the PM identity fades and the agent starts DOING work instead of
ROUTING. This hook fires on every PreToolUse so the blind-PM invariant is refreshed mid-turn.

It also closes D5: the invariants hook writes a heartbeat on each UserPromptSubmit call; if that
heartbeat is stale or missing (hook failed-open silently, or a long autonomous turn has had no
user input for a long time), this hook emits a staleness warning so silent fail-open is detectable.

It NEVER blocks — blocking is myhospital_guard.py's job (incl. the write-side drift door). This
hook only re-injects + warns. Fail-open: any error → exit 0, no output.

Active-run gate: marker file at <project_root>/.claude/.pm-run-active. Absent → silent, exit 0.

    echo '{}' | python .claude/hooks/orchestrator_drift_guard.py
    python .claude/hooks/orchestrator_drift_guard.py --self-test
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# A heartbeat older than this (or missing) while a run is active suggests the UserPromptSubmit
# invariants hook has gone silent (fail-open death) or the turn has run autonomous for a long time.
STALE_AFTER_MINUTES = 45


def _root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def _marker_path(root: Path) -> Path:
    return root / ".claude" / ".pm-run-active"


def _direct_mode(root: Path) -> bool:
    """Owner-opened direct-collaboration window: Claude is a collaborator, NOT a blind PM, so the
    drift guard stays silent (no re-injection, no staleness warning). Marker-based, gitignored —
    same pattern as myhospital_guard._direct_mode (AGENTS.md §3)."""
    return (root / ".direct-mode").exists() or os.environ.get("MH_DIRECT") == "1"


def _heartbeat_path(root: Path) -> Path:
    return root / ".claude" / ".orchestrator_invariants.heartbeat"


def _read_ledger_path(marker: Path) -> str:
    try:
        txt = marker.read_text(encoding="utf-8", errors="ignore").strip()
    except Exception:
        return "<ledger path unset>"
    return txt or "<ledger path unset>"


def render_compact(ledger_path: str) -> str:
    """A SHORTER block than orchestrator_invariants.render_block — fires every tool call."""
    return (
        "[pm-orchestrator] ACTIVE RUN — you are the BLIND coordinator. ROUTE, don't DO.\n"
        "- Dispatch a worker (Task/Workflow) for any source read/write/review; you receive PATHs + blobs only.\n"
        "- Re-derive state from the ledger each tick: "
        f"{ledger_path}\n"
        "- Gate-by-risk: auto T0/T1 reversible; HARD owner-confirm T2/T3 clinical/billing/permission/migration."
    )


def _heartbeat_age_minutes(root: Path) -> float | None:
    """Minutes since the invariants hook last wrote its heartbeat, or None if no heartbeat file."""
    hb = _heartbeat_path(root)
    try:
        txt = hb.read_text(encoding="utf-8", errors="ignore").strip()
        ts = datetime.fromisoformat(txt)
    except Exception:
        return None
    delta = datetime.now(timezone.utc) - ts
    return delta.total_seconds() / 60.0


def emit(root: Path) -> str | None:
    """Return the compact invariants block when a run is active, else None. May prepend a staleness warning.

    Silent (returns None) when DIRECT-MODE is active — the owner has opened a direct-collaboration
    window where Claude is a collaborator, not a blind PM (AGENTS.md §3). The drift guard would
    only spam "BLIND coordinator" reminders that do not apply in that mode.
    """
    if _direct_mode(root):
        return None
    marker = _marker_path(root)
    if not marker.exists():
        return None
    block = render_compact(_read_ledger_path(marker))
    age = _heartbeat_age_minutes(root)
    if age is None or age > STALE_AFTER_MINUTES:
        stale_note = (
            f"[pm-orchestrator] WARN: invariants heartbeat is "
            + ("MISSING" if age is None else f"{int(age)} min old")
            + " — the UserPromptSubmit invariants hook may have failed-open silently, or this autonomous "
            "turn has run long without owner input. Re-assert blind-coordinator discipline; if state is "
            "uncertain, re-read the ledger before dispatching."
        )
        return stale_note + "\n" + block
    return block


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / ".claude").mkdir()

        # 1. no marker -> no output
        assert emit(root) is None, "no marker must produce no block"

        # 1b. direct-mode active + marker present -> silent (owner opened direct-collaboration window)
        _marker_path(root).write_text("ledger", encoding="utf-8")
        (root / ".direct-mode").write_text("", encoding="utf-8")
        assert emit(root) is None, "direct-mode must silence the drift guard even with marker active"
        (root / ".direct-mode").unlink()

        # 2. marker present, no heartbeat -> stale warning + block
        _marker_path(root).write_text("engine/workflows/pm-orchestrator/runs/demo/run-001/00-pm-state.md", encoding="utf-8")
        block = emit(root)
        assert block is not None, "marker present must produce a block"
        assert "MISSING" in block, "missing heartbeat must trigger stale warning"
        assert "BLIND coordinator" in block, "block must carry the invariants"
        assert "demo/run-001" in block, "block must embed the ledger path"

        # 3. marker present, fresh heartbeat -> block only (no stale warning)
        _heartbeat_path(root).write_text(datetime.now(timezone.utc).isoformat(timespec="seconds"), encoding="utf-8")
        block2 = emit(root)
        assert block2 is not None and "WARN" not in block2, "fresh heartbeat must not warn"
        assert "BLIND coordinator" in block2

        # 4. marker present, stale heartbeat -> warning + block
        old_ts = "2020-01-01T00:00:00+00:00"
        _heartbeat_path(root).write_text(old_ts, encoding="utf-8")
        block3 = emit(root)
        assert block3 is not None and "WARN" in block3 and "min old" in block3, "stale heartbeat must warn with age"

        # 5. malformed stdin -> main() exits 0
        assert main(["--from-stdin-test"], stdin_text="not json {{{") == 0
        assert main(["--from-stdin-test"], stdin_text="") == 0

    print("orchestrator_drift_guard self-test: OK")
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
