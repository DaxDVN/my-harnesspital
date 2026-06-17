#!/usr/bin/env python3
"""supertest — deterministic core for the MiMo-led Super-Test workflow.

Owns: run-init (the run-NNN folder + artifact skeletons), the run-state marker, and validators for the
harvest artifacts MiMo produces. NO orchestration (Topology B: MiMo drives; this is just memory + checks).
Envelopes use the SHARED schema (engine/workflows/_shared/envelope.schema.json + validate-envelope.py) — not
re-implemented here. Pure stdlib. Writes only under engine/workflows/super-test/runs/ (never fe/be/worktrees).

    python lib/supertest.py init-run <module>
    python lib/supertest.py get-state <run-dir>
    python lib/supertest.py set-state <run-dir> HARVESTING
    python lib/supertest.py validate-run <run-dir>
    python lib/supertest.py validate <kind> <file>      # kind: state|bug-catalog|coverage-map|opus-request
    python lib/supertest.py --self-test
"""
from __future__ import annotations

import re
import sys
import os
from datetime import date
from pathlib import Path

SUPERTEST_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = SUPERTEST_DIR / "config.yaml"
RUNS = SUPERTEST_DIR / "runs"
DEFAULT_EXECUTOR_MODEL = "mimo-v2.5"
DEFAULT_EXECUTOR_CLI_MODEL = "xiaomi-token-plan-sgp/mimo-v2.5"
STATES = [
    "INIT", "LOAD_TEST_MAP", "HARVESTING", "CALLING_OPUS", "OPUS_BATCH_RCA", "CODEX_REVIEW",
    "APPROVED_REPAIR_PLAN", "IMPLEMENTING", "TARGETED_RETEST", "MODULE_SWEEP_RETEST",
    "FINAL_REPORT", "DONE", "BLOCKED",
]
_MARKER = re.compile(r"<!--\s*super-test-state:\s*([A-Z_]+).*?-->")


def _config_value(key: str) -> str | None:
    if not CONFIG_PATH.exists():
        return None
    stack: list[tuple[int, str]] = []
    values: dict[str, str] = {}
    for raw in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#") or ":" not in raw:
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        k, v = line.split(":", 1)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        stack.append((indent, k.strip()))
        if v.strip():
            values[".".join(x[1] for x in stack)] = v.strip().split("#", 1)[0].strip().strip('"').strip("'")
    return values.get(key)


def _executor_model() -> str:
    return os.environ.get("SUPERTEST_EXECUTOR_MODEL") or _config_value("super_test.executor.model") or DEFAULT_EXECUTOR_MODEL


def _executor_cli_model() -> str:
    return os.environ.get("SUPERTEST_CLI_MODEL") or os.environ.get("SUPERTEST_EXECUTOR_MODEL") or _config_value("super_test.executor.cli_model") or _config_value("super_test.executor.model") or DEFAULT_EXECUTOR_CLI_MODEL


def _state_file(run_dir: Path) -> Path:
    return run_dir / "00-super-test-state.md"


def _skeletons(module: str, run: str, stamp: str) -> dict[str, str]:
    marker = f"<!-- super-test-state: INIT | run: {run} | at: {stamp} -->"
    executor_model = _executor_model()
    executor_cli_model = _executor_cli_model()
    return {
        "00-super-test-state.md": f"""# Super-Test State

{marker}

## Module
{module}

## Run ID
{run}

## Current Phase
INIT

## Current Flow / Feature
(none yet)

## Stop Condition
none

## Counts
- Planned flows: 0
- Tested flows: 0
- Passed flows: 0
- Buggy flows: 0
- Blocked flows: 0
- Bugs found: 0
- Bypasses used: 0

## Next Action
Fill 01-module-test-map.md, then run the harvest sweep.
""",
        "01-module-test-map.md": f"""# Module Test Map

## Module
{module}

## Preconditions
- (login / data / route)

## Flows to Explore
### FLOW-001 — (name)
- Entry route:
- Goal:
- Main actions:
- Expected success state:

## Features to Probe
- list/search/filter · create · edit · delete/cancel · detail · validation · permission · empty/error state
""",
        "02-coverage-map.md": f"""# Coverage Map

## Module
{module}

## Legend
PASS · BUGGED · BYPASSED · BLOCKED · PARTIAL · NOT_TESTED  (PASS != BYPASSED != PARTIAL; BLOCKED != NOT_TESTED)

## Flows
| Flow ID | Flow Name | Status | Bugs | Bypass | Notes |
|---|---|---|---|---|---|

## Untested Areas
-
""",
        "03-current-frontier.md": "# Current Frontier\n\n(what MiMo is testing right now / what's next)\n",
        "04-bug-catalog.md": f"""# Super-Test Bug Catalog

## Metadata
- Module: {module}
- Run ID: {run}
- Executor model: {executor_model}
- Executor CLI model: {executor_cli_model}
- Browser tool: agent-browser
- Started at: {stamp}
- Stopped at:
- Stop reason:

## Coverage Summary
- Planned flows: 0
- Tested flows: 0
- Passed flows: 0
- Blocked flows: 0
- Total bugs found: 0

---

# Bugs
(append BUG-001, BUG-002 … here — see protocol/harvest-sweep.md for the entry format)
""",
        "05-bypass-log.md": "# Bypass Log\n\n(append BYPASS-001 … — related bug, method, result, what stayed testable)\n",
        "06-blocked-flows.md": "# Blocked Flows\n\n(append BLOCKED-001 … — flow, blocking bug, last good step, why no bypass)\n",
    }


def init_run(module: str) -> Path:
    module = re.sub(r"[^A-Za-z0-9_.-]", "-", module).strip("-") or "module"
    base = RUNS / module
    base.mkdir(parents=True, exist_ok=True)
    n = 1 + max([int(m.group(1)) for p in base.glob("run-*")
                 if (m := re.match(r"run-(\d+)$", p.name))], default=0)
    run = f"run-{n:03d}"
    run_dir = base / run
    (run_dir / "evidence" / "screenshots").mkdir(parents=True, exist_ok=True)
    (run_dir / "evidence" / "snapshots").mkdir(parents=True, exist_ok=True)
    (run_dir / "evidence" / "network").mkdir(parents=True, exist_ok=True)
    (run_dir / "evidence" / "console").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    for name, body in _skeletons(module, run, date.today().isoformat()).items():
        (run_dir / name).write_text(body, encoding="utf-8")
    return run_dir


def get_state(run_dir: Path) -> str:
    p = _state_file(run_dir)
    if not p.exists():
        return "UNSET"
    m = _MARKER.search(p.read_text(encoding="utf-8", errors="ignore"))
    return m.group(1) if m else "UNSET"


def set_state(run_dir: Path, state: str, today: str | None = None) -> None:
    if state not in STATES:
        raise ValueError(f"unknown state {state!r}; valid: {', '.join(STATES)}")
    p = _state_file(run_dir)
    if not p.exists():
        raise FileNotFoundError(f"no state file: {p}")
    body = p.read_text(encoding="utf-8", errors="ignore")
    stamp = today or date.today().isoformat()
    run = ""
    rm = re.search(r"run:\s*(run-\d+)", body)
    if rm:
        run = rm.group(1)
    marker = f"<!-- super-test-state: {state} | run: {run} | at: {stamp} -->"
    body = _MARKER.sub(marker, body, count=1) if _MARKER.search(body) else marker + "\n" + body
    # keep the human "## Current Phase" line in sync
    body = re.sub(r"(## Current Phase\n)[A-Z_]+", rf"\g<1>{state}", body, count=1)
    p.write_text(body, encoding="utf-8")


def _has(text: str, *needles: str) -> list[str]:
    return [n for n in needles if n not in text]


def validate(kind: str, path: Path) -> list[str]:
    """Return a list of problems (empty == valid). Markdown-marker validation (artifacts are .md)."""
    if not path.exists():
        return [f"missing: {path}"]
    t = path.read_text(encoding="utf-8", errors="ignore")
    if kind == "state":
        miss = _has(t, "## Current Phase", "## Stop Condition", "## Counts")
        if not _MARKER.search(t):
            miss.append("super-test-state marker")
        else:
            ph = _MARKER.search(t).group(1)
            if ph not in STATES:
                miss.append(f"invalid phase {ph!r}")
        return [f"state: missing {m}" for m in miss]
    if kind == "bug-catalog":
        return [f"bug-catalog: missing {m}" for m in _has(t, "# Super-Test Bug Catalog", "## Coverage Summary")]
    if kind == "coverage-map":
        miss = _has(t, "# Coverage Map", "| Flow")
        return [f"coverage-map: missing {m}" for m in miss]
    if kind == "opus-request":
        return [f"opus-request: missing {m}" for m in _has(t, "Input Artifacts")]
    if kind == "opus-batch-rca":
        return [f"opus-batch-rca: missing {m}" for m in _has(t, "Bug Cluster", "Repair Batch")]
    if kind == "approved-repair-plan":
        return [f"approved-repair-plan: missing {m}" for m in _has(t, "Approved Repair Plan", "Files Allowed To Modify")]
    if kind == "codex-review":
        miss = _has(t, "Verdict")
        if not re.search(r"APPROVE|REJECT", t):
            miss.append("a verdict value (APPROVE/APPROVE_WITH_CHANGES/REJECT)")
        return [f"codex-review: missing {m}" for m in miss]
    if kind == "implementation-report":
        return [f"implementation-report: missing {m}" for m in _has(t, "Files Changed")]
    if kind in ("targeted-retest", "module-sweep-retest"):
        return [f"{kind}: missing {m}" for m in _has(t, "Retest")]
    if kind == "final-report":
        return [f"final-report: missing {m}" for m in _has(t, "Final Super-Test Report")]
    return [f"unknown kind {kind!r}"]


def validate_run(run_dir: Path) -> list[str]:
    if not run_dir.exists():
        return [f"run dir missing: {run_dir}"]
    problems: list[str] = []
    problems += validate("state", run_dir / "00-super-test-state.md")
    problems += validate("bug-catalog", run_dir / "04-bug-catalog.md")
    problems += validate("coverage-map", run_dir / "02-coverage-map.md")
    return problems


def _self_test() -> int:
    import tempfile
    global RUNS
    orig = RUNS
    with tempfile.TemporaryDirectory() as d:
        RUNS = Path(d) / "runs"
        rd = init_run("demo/module")            # sanitized to demo-module
        assert rd.exists() and rd.name == "run-001", rd
        assert get_state(rd) == "INIT", get_state(rd)
        assert validate_run(rd) == [], validate_run(rd)     # skeleton is valid
        set_state(rd, "HARVESTING")
        assert get_state(rd) == "HARVESTING"
        body = _state_file(rd).read_text(encoding="utf-8")
        assert body.count("super-test-state:") == 1, "marker duplicated"
        assert "## Current Phase\nHARVESTING" in body, "human phase not synced"
        rd2 = init_run("demo/module")
        assert rd2.name == "run-002", rd2          # increments
        try:
            set_state(rd, "NONSENSE"); raise AssertionError("bad state accepted")
        except ValueError:
            pass
        # a stripped catalog is INVALID
        (rd / "04-bug-catalog.md").write_text("# wrong", encoding="utf-8")
        assert any("bug-catalog" in p for p in validate_run(rd)), "bad catalog not caught"
    RUNS = orig
    print("supertest self-test: OK")
    return 0


def extract_allowlist(plan: Path) -> list[str]:
    """Parse the 'Files Allowed To Modify' bullets across an approved-repair-plan (union of all batches)."""
    if not plan.exists():
        return []
    globs, capture = [], False
    for line in plan.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if s.startswith("#"):
            capture = "Files Allowed To Modify" in s
            continue
        if capture:
            m = re.match(r"[-*]\s+`?([^`]+?)`?\s*$", s)
            if m:
                g = m.group(1).strip()
                if g and not g.startswith("("):
                    globs.append(g)
    return globs


def write_final_report(run_dir: Path) -> Path:
    cat = run_dir / "04-bug-catalog.md"
    nbugs = len(re.findall(r"(?m)^##\s+BUG-\d+", cat.read_text(encoding="utf-8", errors="ignore"))) if cat.exists() else 0
    present = ", ".join(p.name for p in sorted(run_dir.glob("[0-9][0-9]-*.md")))
    out = run_dir / "14-final-super-test-report.md"
    out.write_text(
        f"# Final Super-Test Report\n\n## Module / Run\n{run_dir.parent.name} / {run_dir.name} (state: {get_state(run_dir)})\n\n"
        f"## Initial Sweep\n- Bugs catalogued: {nbugs}\n- Artifacts: {present}\n\n"
        "## RCA / Repair\n- See 08-opus-batch-rca.md · 09-codex-review.md · 10-approved-repair-plan.md (if present).\n\n"
        "## Implementation / Retest\n- See 11-implementation-report.md · 12-targeted-retest-report.md · 13-module-sweep-retest-report.md (if present).\n\n"
        "## Recommendation\n- Ready for review workflow: (fill)\n- Needs another Super-Test run: (fill)\n- Needs human/BA decision: (fill)\n",
        encoding="utf-8")
    return out


def main(argv: list[str]) -> int:
    if "--self-test" in argv or (argv and argv[0] == "self-test"):
        return _self_test()
    if not argv:
        print(__doc__)
        return 1
    cmd, rest = argv[0], argv[1:]
    if cmd == "init-run":
        if not rest:
            print("usage: init-run <module>", file=sys.stderr); return 2
        rd = init_run(rest[0])
        print(f"RUN_DIR={rd}")
        print(f"RUN_ID={rd.name}")
        return 0
    if cmd == "get-state":
        if not rest:
            print("usage: get-state <run-dir>", file=sys.stderr); return 2
        print(get_state(Path(rest[0])))
        return 0
    if cmd == "set-state":
        if len(rest) < 2:
            print("usage: set-state <run-dir> <STATE>", file=sys.stderr); return 2
        try:
            set_state(Path(rest[0]), rest[1])
        except (ValueError, FileNotFoundError) as exc:
            print(f"FAIL: {exc}", file=sys.stderr); return 1
        print(f"set {rest[1]}"); return 0
    if cmd == "validate-run":
        if not rest:
            print("usage: validate-run <run-dir>", file=sys.stderr); return 2
        probs = validate_run(Path(rest[0]))
        if probs:
            print("INVALID run:"); [print(f"  - {p}") for p in probs]; return 1
        print("VALID run"); return 0
    if cmd == "validate":
        if len(rest) < 2:
            print("usage: validate <kind> <file>", file=sys.stderr); return 2
        probs = validate(rest[0], Path(rest[1]))
        if probs:
            print("INVALID:"); [print(f"  - {p}") for p in probs]; return 1
        print("VALID"); return 0
    if cmd == "allowlist":
        if not rest:
            print("usage: allowlist <approved-repair-plan.md>", file=sys.stderr); return 2
        print(",".join(extract_allowlist(Path(rest[0])))); return 0
    if cmd == "final-report":
        if not rest:
            print("usage: final-report <run-dir>", file=sys.stderr); return 2
        print(write_final_report(Path(rest[0]))); return 0
    print(f"unknown command {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
