#!/usr/bin/env python3
"""graphify staleness / trust probe (SessionStart hook).

Robust, dependency-free check that the knowledge graph in `graphify-out/` can be
trusted on THIS machine. The previous version imported `graphify.detect`, which is
not importable from the system Python (graphify ships as a standalone binary), so it
silently did nothing. This version instead compares the recorded build root against
the actual workspace root — which directly catches the real failure mode: a graph
built on another machine/OS (e.g. Windows `D:\\arabica\\roast`) whose file citations
do not exist here.

Prints a short `[graphify] …` directive to stdout ONLY when the graph is
untrustworthy or its provenance cannot be confirmed; stays silent and exits 0
otherwise so it never blocks or slows session start.

Usage: python graphify_stale_check.py <project_root>
"""

from __future__ import annotations

import sys
from pathlib import Path


def _looks_windows(p: str) -> bool:
    return "\\" in p or (len(p) >= 2 and p[1] == ":")


def main() -> int:
    if len(sys.argv) < 2:
        return 0
    root = Path(sys.argv[1]).resolve()
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


if __name__ == "__main__":
    sys.exit(main())
