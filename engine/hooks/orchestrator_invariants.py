#!/usr/bin/env python3
"""orchestrator_invariants — UserPromptSubmit hook: RE-INJECT PM-orchestrator invariants every turn.

Anti-forget contract (Phase 4 of the Fugu orchestrator upgrade). A long-running PM coordinator drifts: across
many turns it forgets that it must stay BLIND (route paths, never read worker output md), re-derive state from
the ledger, and gate-by-risk. A UserPromptSubmit hook re-injects a TINY invariants block on every turn — but
ONLY while a PM run is active, so normal turns pay zero tokens.

Active-run gate: a marker file at <project_root>/.claude/.pm-run-active. The PM creates it at run start and
removes it at run end; its contents = the active run's ledger path. Absent marker → print NOTHING, exit 0.

Fail-open: any error or malformed stdin → exit 0 with no output (never block a turn). On every successful run a
tiny timestamp is written to <project_root>/.claude/.orchestrator_invariants.heartbeat so silent fail-open death
is detectable.

    echo '{}' | python .claude/hooks/orchestrator_invariants.py        # no marker → silent
    python .claude/hooks/orchestrator_invariants.py --self-test
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def _marker_path(root: Path) -> Path:
    return root / ".claude" / ".pm-run-active"


def _direct_mode(root: Path) -> bool:
    """Owner-opened direct-collaboration window: Claude is a collaborator, NOT a blind PM, so the
    invariants re-injection stays silent. Marker-based, gitignored — same pattern as
    myhospital_guard._direct_mode (AGENTS.md §3)."""
    return (root / ".direct-mode").exists() or os.environ.get("MH_DIRECT") == "1"


def _heartbeat_path(root: Path) -> Path:
    return root / ".claude" / ".orchestrator_invariants.heartbeat"


def _read_ledger_path(marker: Path) -> str:
    try:
        txt = marker.read_text(encoding="utf-8", errors="ignore").strip()
    except Exception:
        return "<ledger path unset — see PM run dir>"
    return txt or "<ledger path unset — see PM run dir>"


def render_block(ledger_path: str) -> str:
    return (
        "[pm-orchestrator] ACTIVE RUN — invariants (re-injected, do not forget):\n"
        "- Blind coordinator: route PATHS + compact blobs; NEVER read worker output md / source / rules.\n"
        f"- Re-derive state from the ledger each tick: {ledger_path}. Author it from blobs only.\n"
        "- Transfer memory to subagents BY REFERENCE (rule_card + recommended_prompt + recalled notes), "
        "with verify-live.\n"
        "- Fan out ONLY from the main loop / Workflow tool; never delegate fan-out into a worker.\n"
        "- Gate-by-risk: auto-dispatch T0/T1 reversible; HARD owner-confirm for T2/T3 with "
        "clinical/billing/permission/migration/irreversible.\n"
        "- Autonomy (Opus 4.8): minor choices -> decide + note, don't ask; hard-confirm ONLY "
        "destructive/scope-change/clinical-billing-permission per gate-by-risk.\n"
        "- `promote` is never dispatchable; business ambiguity -> provisional-or-park, never silent invention."
    )


def _write_heartbeat(root: Path) -> None:
    try:
        _heartbeat_path(root).write_text(
            datetime.now(timezone.utc).isoformat(timespec="seconds"), encoding="utf-8"
        )
    except Exception:
        # heartbeat is best-effort; never block the turn on it
        pass


def emit(root: Path) -> str | None:
    """Return the invariants block when a run is active, else None. Writes heartbeat on every successful call.

    Silent (returns None) when DIRECT-MODE is active — the owner has opened a direct-collaboration
    window where Claude is a collaborator, not a blind PM (AGENTS.md §3). The blind-PM invariants
    would not apply in that mode.
    """
    if _direct_mode(root):
        return None
    marker = _marker_path(root)
    out: str | None = None
    if marker.exists():
        out = render_block(_read_ledger_path(marker))
    _write_heartbeat(root)
    return out


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / ".claude").mkdir()

        # 1. marker absent -> no output, heartbeat written
        assert emit(root) is None, "no marker must produce no block"
        assert _heartbeat_path(root).exists(), "heartbeat must be written even with no marker"

        # 1b. direct-mode active + marker present -> silent (owner opened direct-collaboration window)
        _marker_path(root).write_text("ledger", encoding="utf-8")
        (root / ".direct-mode").write_text("", encoding="utf-8")
        assert emit(root) is None, "direct-mode must silence invariants even with marker active"
        (root / ".direct-mode").unlink()

        # 2. marker present -> block printed with the ledger path from the marker file
        ledger = "engine/workflows/pm-orchestrator/runs/demo/run-001/00-pm-state.md"
        _marker_path(root).write_text(ledger, encoding="utf-8")
        block = emit(root)
        assert block is not None, "marker present must produce a block"
        assert ledger in block, "block must embed the ledger path from the marker"
        assert "Blind coordinator" in block and "promote" in block, "block must carry the full invariants"

        # 3. empty marker -> still prints, with a safe placeholder
        _marker_path(root).write_text("", encoding="utf-8")
        block2 = emit(root)
        assert block2 is not None and "ledger path unset" in block2, "empty marker must use placeholder"

        # 4. malformed stdin -> main() exits 0, no crash
        rc = main(["--from-stdin-test"], stdin_text="not json at all {{{")
        assert rc == 0, "malformed stdin must exit 0"

        # 5. empty stdin -> exit 0
        rc = main(["--from-stdin-test"], stdin_text="")
        assert rc == 0, "empty stdin must exit 0"

    print("orchestrator_invariants self-test: OK")
    return 0


def main(argv: list[str], stdin_text: str | None = None) -> int:
    if "--self-test" in argv:
        return _self_test()
    # consume stdin (event JSON) but tolerate empty/garbage — content is not needed; the marker gates output
    try:
        raw = stdin_text if stdin_text is not None else sys.stdin.read()
        if raw and raw.strip():
            try:
                json.loads(raw)
            except Exception:
                pass  # garbage stdin is fine; we still gate on the marker
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
