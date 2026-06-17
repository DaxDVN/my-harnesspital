#!/usr/bin/env python3
"""gate-check — deterministic SDD precondition gate for the design/slice/impl workflows.

The "Gate FIRST" line in technical-design / task-slicing / incremental-impl used to be PROSE the
orchestrator was trusted to honor. This makes it a runnable check (B): a workflow runs gate-check
BEFORE doing work and STOPs on a closed gate. Read-only. Fail-CLOSED for the gate (a missing input
is a closed gate), fail-OPEN for the tool (its own crash never fabricates an OPEN gate).

    python engine/workflows/_shared/gate-check.py <module> --require 02-requirements,03-ui
    python engine/workflows/_shared/gate-check.py <module> --require 07-schema,08-api --no-blocking 05-open-questions
    python engine/workflows/_shared/gate-check.py --self-test

--require   : numbered SDD files that must EXIST and be non-placeholder under specs/<module>/.
--no-blocking : a file (usually 05-open-questions) that must contain NO line tagged BLOCKING
               (BLOCKING / BLOCKING_SCHEMA / BLOCKING_API) — an unresolved blocking question closes the gate.
--specs-root : override 'specs' (used by --self-test).

Exit 0 = gate OPEN (proceed) · 2 = gate CLOSED (STOP; reasons printed) · 1 = usage error.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MIN_REAL_CHARS = 80          # below this a file is treated as an empty template stub
_BLOCKING = re.compile(r"\bBLOCKING(?:_SCHEMA|_API)?\b")
_PLACEHOLDER = re.compile(r"<!--\s*template\s*-->|TODO:\s*fill|_TEMPLATE", re.IGNORECASE)


def _find(module_dir: Path, stem: str) -> Path | None:
    """Resolve '02-requirements' to specs/<m>/02-requirements.md (exact, else 02-requirements*.md)."""
    exact = module_dir / f"{stem}.md"
    if exact.exists():
        return exact
    hits = sorted(module_dir.glob(f"{stem}*.md"))
    return hits[0] if hits else None


def _is_real(p: Path) -> bool:
    try:
        body = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return False
    stripped = re.sub(r"\s+", "", body)
    if len(stripped) < MIN_REAL_CHARS:
        return False
    if _PLACEHOLDER.search(body) and len(stripped) < MIN_REAL_CHARS * 4:
        return False
    return True


def check(module: str, require: list[str], no_blocking: list[str],
          specs_root: Path | None = None) -> tuple[bool, list[str]]:
    """Return (gate_open, reasons)."""
    specs_root = specs_root or (ROOT / "specs")
    module_dir = specs_root / module
    reasons: list[str] = []
    if not module_dir.exists():
        return False, [f"specs/{module}/ does not exist — run the discovery phase first"]
    for stem in require:
        p = _find(module_dir, stem)
        if p is None:
            reasons.append(f"required input missing: specs/{module}/{stem}.md")
        elif not _is_real(p):
            reasons.append(f"required input is an empty/template stub: {p.name}")
    for stem in no_blocking:
        p = _find(module_dir, stem)
        if p is None:
            continue  # absent open-questions file == nothing blocking
        body = p.read_text(encoding="utf-8", errors="ignore")
        hits = [ln.strip() for ln in body.splitlines() if _BLOCKING.search(ln)]
        if hits:
            reasons.append(f"{p.name} has {len(hits)} unresolved BLOCKING item(s): {hits[0][:80]}")
    return (not reasons), reasons


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        specs = Path(d) / "specs"
        m = specs / "demo"
        m.mkdir(parents=True)
        body = "# Requirements\n" + ("real content line. " * 12)
        (m / "02-requirements.md").write_text(body, encoding="utf-8")
        (m / "03-ui.md").write_text(body, encoding="utf-8")
        # all present, no blocking -> OPEN
        ok, why = check("demo", ["02-requirements", "03-ui"], ["05-open-questions"], specs)
        assert ok, f"gate should be open: {why}"
        # missing input -> CLOSED
        ok, why = check("demo", ["02-requirements", "07-schema"], [], specs)
        assert not ok and any("07-schema" in r for r in why), why
        # template stub -> CLOSED
        (m / "08-api.md").write_text("# API\n<!-- template -->", encoding="utf-8")
        ok, why = check("demo", ["08-api"], [], specs)
        assert not ok, "stub should close the gate"
        # blocking open-question -> CLOSED
        (m / "05-open-questions.md").write_text(body + "\n- OQ-1 BLOCKING_API which error code?", encoding="utf-8")
        ok, why = check("demo", ["02-requirements"], ["05-open-questions"], specs)
        assert not ok and any("BLOCKING" in r for r in why), why
    print("gate-check self-test: OK")
    return 0


def _csv(argv: list[str], flag: str) -> list[str]:
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            return [s.strip() for s in argv[i + 1].split(",") if s.strip()]
    return []


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return _self_test()
    # first non-flag token is the module (flag VALUES like the --require list are filtered below)
    flag_values = set()
    for flag in ("--require", "--no-blocking", "--specs-root"):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 < len(argv):
                flag_values.add(argv[i + 1])
    plain = [a for a in argv if not a.startswith("--") and a not in flag_values]
    if not plain:
        print(__doc__)
        return 1
    module = plain[0]
    require = _csv(argv, "--require")
    no_blocking = _csv(argv, "--no-blocking")
    specs_root = None
    if "--specs-root" in argv:
        i = argv.index("--specs-root")
        if i + 1 < len(argv):
            specs_root = Path(argv[i + 1])
    open_, reasons = check(module, require, no_blocking, specs_root)
    if open_:
        print(f"GATE OPEN: specs/{module}/ — inputs present, no blocking questions. Proceed.")
        return 0
    print(f"GATE CLOSED: specs/{module}/ — STOP, do not proceed:")
    for r in reasons:
        print(f"  - {r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
