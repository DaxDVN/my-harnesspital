#!/usr/bin/env python3
"""run-init — create a standard ISOLATED run folder for a workflow (run-memory convention).

Gives the skill-orchestrated workflows (bug-fix, impact-analysis, technical-design, task-slicing,
incremental-impl, ui-spec) the same per-run isolation the browser workflows already have: a UNIQUE
`run-NNN/` folder + `00-run-meta.json` + `logs/`, so any agent that joins the run knows exactly which
files are its run's. Full contract: engine/workflows/_shared/run-memory.md. Writes ONLY under
engine/workflows/<workflow>/rounds/.

    python engine/workflows/_shared/run-init.py <workflow> [--module <m>]
    python engine/workflows/_shared/run-init.py --self-test
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[1]   # engine/workflows


def init_run(workflow: str, module: str = "", base: Path | None = None) -> Path:
    base = base or WORKFLOWS
    rounds = base / workflow / "rounds"
    rounds.mkdir(parents=True, exist_ok=True)
    n = 1 + max([int(m.group(1)) for p in rounds.glob("run-*")
                 if (m := re.match(r"run-(\d+)$", p.name))], default=0)
    run_id = f"run-{n:03d}"
    rd = rounds / run_id
    (rd / "logs").mkdir(parents=True, exist_ok=True)   # class B: per-session logs
    meta = {"workflow": workflow, "run_id": run_id, "module": module or None,
            "created": date.today().isoformat(), "phase": "INIT"}
    (rd / "00-run-meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return rd


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        rd = init_run("demo-wf", base=base)
        assert rd.name == "run-001", rd
        assert (rd / "00-run-meta.json").exists() and (rd / "logs").is_dir(), "missing meta/logs"
        assert init_run("demo-wf", base=base).name == "run-002", "run-id did not increment (collision risk)"
        meta = json.loads((rd / "00-run-meta.json").read_text(encoding="utf-8"))
        assert meta["workflow"] == "demo-wf" and meta["run_id"] == "run-001", meta
    print("run-init self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return _self_test()
    plain = [a for a in argv if not a.startswith("--")]
    if not plain:
        print(__doc__)
        return 1
    module = ""
    if "--module" in argv:
        i = argv.index("--module")
        module = argv[i + 1] if i + 1 < len(argv) else ""
    rd = init_run(plain[0], module)
    print(f"RUN_DIR={rd}")
    print(f"RUN_ID={rd.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
