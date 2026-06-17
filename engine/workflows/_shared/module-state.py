#!/usr/bin/env python3
"""module-state — read/advance the per-module SDLC state on specs/<module>/00-module-state.md (C9).

GPT's workflow set carried an implicit DOC_INTAKE -> ... -> RELEASE state model. We map it onto the
SDD file every session already reads first (00-module-state.md) instead of inventing a parallel store,
so the state IS the deterministic re-entry point. This helper owns ONE machine-readable marker line:

    <!-- workflow-state: DESIGN | by: technical-design | at: 2026-06-16 -->

The rest of 00-module-state.md stays human-authored. Only specs/ is ever written (never fe/be/worktrees).

    python engine/workflows/_shared/module-state.py <module> --get
    python engine/workflows/_shared/module-state.py <module> --set DESIGN --by technical-design
    python engine/workflows/_shared/module-state.py --self-test

States (canonical SDLC lifecycle; map GPT's onto these):
    DISCOVERY  (DOC_INTAKE/DISCOVERY) -> DESIGN -> DESIGN_REVIEW -> SLICED -> IMPLEMENTING
    -> VERIFYING -> DONE     side: BLOCKED_BA, BLOCKED_DESIGN, BLOCKED_PLAN
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATES = [
    "DISCOVERY", "DESIGN", "DESIGN_REVIEW", "SLICED", "IMPLEMENTING",
    "VERIFYING", "DONE", "BLOCKED_BA", "BLOCKED_DESIGN", "BLOCKED_PLAN",
]
_MARKER = re.compile(r"<!--\s*workflow-state:\s*([A-Z_]+).*?-->")
STATE_FILE = "00-module-state.md"


def _path(module: str, specs_root: Path | None = None) -> Path:
    return (specs_root or (ROOT / "specs")) / module / STATE_FILE


def get_state(module: str, specs_root: Path | None = None) -> str:
    p = _path(module, specs_root)
    if not p.exists():
        return "UNSET"
    m = _MARKER.search(p.read_text(encoding="utf-8", errors="ignore"))
    return m.group(1) if m else "UNSET"


def set_state(module: str, state: str, by: str = "workflow",
              specs_root: Path | None = None, today: str | None = None) -> Path:
    if state not in STATES:
        raise ValueError(f"unknown state {state!r}; valid: {', '.join(STATES)}")
    p = _path(module, specs_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    stamp = today or date.today().isoformat()
    marker = f"<!-- workflow-state: {state} | by: {by} | at: {stamp} -->"
    if p.exists():
        body = p.read_text(encoding="utf-8", errors="ignore")
        if _MARKER.search(body):
            body = _MARKER.sub(marker, body, count=1)
        else:
            body = marker + "\n" + body
    else:
        body = f"# {module} — module state\n\n{marker}\n"
    p.write_text(body, encoding="utf-8")
    return p


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        specs = Path(d) / "specs"
        assert get_state("demo", specs) == "UNSET", "missing file should be UNSET"
        set_state("demo", "DESIGN", by="technical-design", specs_root=specs, today="2026-06-16")
        assert get_state("demo", specs) == "DESIGN", "set/get round-trip failed"
        # advancing replaces the single marker (no duplicate markers)
        set_state("demo", "SLICED", by="task-slicing", specs_root=specs, today="2026-06-16")
        body = _path("demo", specs).read_text(encoding="utf-8")
        assert body.count("workflow-state:") == 1, "marker duplicated"
        assert get_state("demo", specs) == "SLICED"
        # invalid state rejected
        try:
            set_state("demo", "NONSENSE", specs_root=specs)
            raise AssertionError("invalid state accepted")
        except ValueError:
            pass
    print("module-state self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return _self_test()
    plain = [a for a in argv if not a.startswith("--")]
    # strip flag values
    for flag in ("--set", "--by", "--specs-root"):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 < len(argv) and argv[i + 1] in plain:
                plain.remove(argv[i + 1])
    if not plain:
        print(__doc__)
        return 1
    module = plain[0]
    specs_root = None
    if "--specs-root" in argv:
        i = argv.index("--specs-root")
        if i + 1 < len(argv):
            specs_root = Path(argv[i + 1])
    if "--set" in argv:
        i = argv.index("--set")
        state = argv[i + 1] if i + 1 < len(argv) else ""
        by = "workflow"
        if "--by" in argv:
            j = argv.index("--by")
            by = argv[j + 1] if j + 1 < len(argv) else by
        try:
            p = set_state(module, state, by=by, specs_root=specs_root)
        except ValueError as exc:
            print(f"FAIL: {exc}")
            return 1
        print(f"set {module} -> {state} ({p})")
        return 0
    # default / --get
    print(get_state(module, specs_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
