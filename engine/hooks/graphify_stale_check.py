#!/usr/bin/env python3
"""graphify staleness / trust probe + session marker cleanup (SessionStart hook).

Two jobs at session start:
  1. Check that the knowledge graph in `graphify-out/` can be trusted on THIS machine.
  2. Clean up stale per-session markers so every session starts fresh:
     - .direct-mode   → removed (each session starts in blind-PM mode; the owner
                        activates direct mode in-chat if needed — AGENTS.md §3).
     - .pm-run-active → removed (a leftover from a crashed session would falsely
                        activate the invariants / drift-guard hooks).

Prints a short notice ONLY when markers were cleaned or the graph is stale; stays
silent otherwise so it never blocks session start.

Usage: python graphify_stale_check.py <project_root>
"""

from __future__ import annotations

import sys
from pathlib import Path


def _looks_windows(p: str) -> bool:
    return "\\" in p or (len(p) >= 2 and p[1] == ":")


def _clean_markers(root: Path) -> list[str]:
    """Remove per-session markers so every session starts fresh. Returns the list of cleaned names."""
    cleaned: list[str] = []
    for name in (".direct-mode", ".pm-run-active"):
        marker = root / name
        try:
            if marker.exists():
                marker.unlink()
                cleaned.append(name)
        except OSError:
            pass
    return cleaned


def main() -> int:
    if "--self-test" in sys.argv:
        return _self_test()
    if len(sys.argv) < 2:
        return 0
    root = Path(sys.argv[1]).resolve()

    # Clean stale per-session markers so every session starts fresh (AGENTS.md §3).
    # .direct-mode lives at root; .pm-run-active lives in .claude/.
    cleaned = _clean_markers(root)
    if (root / ".claude").exists():
        cleaned += _clean_markers(root / ".claude")
    if cleaned:
        print(f"[session-start] cleaned stale marker(s): {', '.join(cleaned)} — session starts fresh in blind-PM mode")

    out = root / "graphify-out"
    graph = out / "graph.json"
    root_marker = out / ".graphify_root"

    # No graph at all → nothing to warn about.
    if not graph.exists():
        return 0

    try:
        recorded = root_marker.read_text(encoding="utf-8", errors="ignore").strip() if root_marker.exists() else ""
    except Exception:
        return 0

    if not recorded:
        # Graph exists but provenance unknown — flag gently, do not block.
        print(
            "[graphify] graph.json exists but its build root is unknown "
            "(graphify-out/.graphify_root missing). Treat graph output as unverified; "
            "prefer reading docs/specs directly."
        )
        return 0

    recorded_norm = recorded.replace("\\", "/").rstrip("/").lower()
    actual_norm = str(root).replace("\\", "/").rstrip("/").lower()

    if _looks_windows(recorded) or recorded_norm != actual_norm:
        print(
            f"[graphify] Knowledge graph is STALE / cross-machine: built for root "
            f"'{recorded}', but this workspace is '{root}'. Its src= file citations "
            f"do not resolve here."
        )
        print(
            "[graphify] Do NOT trust graph paths. Use rg/fd/bat for code and read "
            "docs/specs directly; rebuild on Linux with /graphify when a fresh graph "
            "is actually needed."
        )
        return 0

    # Roots match → graph is at least built for this machine. Stay silent.
    return 0


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        # Create stale markers
        (root / ".direct-mode").write_text("", encoding="utf-8")
        (root / ".claude").mkdir()
        (root / ".claude" / ".pm-run-active").write_text("ledger", encoding="utf-8")
        # Clean
        c1 = _clean_markers(root)
        c2 = _clean_markers(root / ".claude")
        all_cleaned = c1 + c2
        assert not (root / ".direct-mode").exists(), ".direct-mode should be cleaned"
        assert not (root / ".claude" / ".pm-run-active").exists(), ".pm-run-active should be cleaned"
        assert ".direct-mode" in all_cleaned and ".pm-run-active" in all_cleaned, "both markers should be reported as cleaned"
    print("graphify_stale_check self-test: OK")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    sys.exit(main())
