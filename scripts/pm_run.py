#!/usr/bin/env python3
"""pm_run — deterministic lifecycle for a pm-orchestrator run's active-marker + ledger dir.

WHY: the blind-PM anti-drift machinery gates on a marker file `.claude/.pm-run-active` whose
contents = the active run's ledger path. Previously the PM agent itself created/removed this
marker with a shell `echo` — but the very agent whose drift the marker is meant to catch can
forget to create it or drop it early, silently disabling the invariants + drift-guard hooks
(drift bug D2). This script makes marker lifecycle deterministic and script-backed, and creates
the run ledger dir + state file from the canonical template so the agent does not hand-author it.

Usage:
    python scripts/pm_run.py start <scope> [--recipe <preset>] [--task "<one-line>"] [--worktree <slug>]
    python scripts/pm_run.py end [--stop <DONE|CAP_HIT|BLOCKED|PARKED>] [--note "<reason>"]
    python scripts/pm_run.py status
    python scripts/pm_run.py --self-test

- start: creates runs/<scope>/run-NNN/ (auto-incrementing), writes 00-pm-state.md from the
  template, creates `.claude/.pm-run-active` (contents = ledger path), seeds the heartbeat.
  Refuses if a run is already active unless --force.
- end:   records the stop reason in the ledger (optional), removes the marker.
- status: prints active/not, the ledger path, heartbeat age, and run dir.

Exit codes: 0 ok · 1 usage · 2 preconditions (active run already / no active run).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "engine" / "workflows" / "pm-orchestrator" / "runs"
TEMPLATE = ROOT / "engine" / "workflows" / "pm-orchestrator" / "templates" / "pm-state-template.md"
MARKER = ROOT / ".claude" / ".pm-run-active"
HEARTBEAT = ROOT / ".claude" / ".orchestrator_invariants.heartbeat"
STOP_VALUES = {"DONE", "CAP_HIT", "BLOCKED", "PARKED"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_ledger_path() -> str | None:
    try:
        return MARKER.read_text(encoding="utf-8", errors="ignore").strip() or None
    except Exception:
        return None


def _heartbeat_age_minutes() -> float | None:
    try:
        ts = datetime.fromisoformat(HEARTBEAT.read_text(encoding="utf-8", errors="ignore").strip())
    except Exception:
        return None
    return (datetime.now(timezone.utc) - ts).total_seconds() / 60.0


def _next_run_dir(scope: str) -> Path:
    scope_dir = RUNS / scope
    scope_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(d.name for d in scope_dir.glob("run-*") if d.is_dir())
    n = 0
    for name in existing:
        try:
            n = max(n, int(name.split("-", 1)[1]))
        except ValueError:
            continue
    return scope_dir / f"run-{n + 1:03d}"


def _seed_heartbeat() -> None:
    try:
        HEARTBEAT.write_text(_now_iso(), encoding="utf-8")
    except Exception:
        pass


def cmd_start(args: argparse.Namespace) -> int:
    if MARKER.exists() and not args.force:
        print(f"pm_run: a run is already active — ledger: {_read_ledger_path()}", file=sys.stderr)
        print("        run `pm_run.py end` first, or `pm_run.py start ... --force` to replace.", file=sys.stderr)
        return 2
    run_dir = _next_run_dir(args.scope)
    ledger = run_dir / "00-pm-state.md"
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        body = TEMPLATE.read_text(encoding="utf-8")
    except FileNotFoundError:
        body = "# PM Orchestrator State\n\n(fallback — template not found)\n"
    body = body.replace("<scope>", args.scope)
    body = body.replace("run-NNN", run_dir.name)
    if args.recipe:
        body = body.replace("<preset name: review | espresso | bugfix | feature | custom>", args.recipe)
    if args.task:
        body = body.replace("<one-line scope of this run>", args.task)
    if args.worktree:
        body = body.replace("<slug> (slot <n>)", f"{args.worktree} (slot —)")
    ledger.write_text(body, encoding="utf-8")
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(str(ledger.relative_to(ROOT)), encoding="utf-8")
    _seed_heartbeat()
    print(f"pm_run: STARTED — run_dir: {run_dir.relative_to(ROOT)}")
    print(f"        ledger:   {ledger.relative_to(ROOT)}")
    print(f"        marker:   {MARKER.relative_to(ROOT)} (contents = ledger path)")
    return 0


def cmd_end(args: argparse.Namespace) -> int:
    if not MARKER.exists():
        print("pm_run: no active run to end.", file=sys.stderr)
        return 2
    ledger_path = _read_ledger_path()
    if args.stop:
        if args.stop not in STOP_VALUES:
            print(f"pm_run: invalid --stop {args.stop!r}; one of {sorted(STOP_VALUES)}", file=sys.stderr)
            return 1
        if ledger_path:
            lp = ROOT / ledger_path
            if lp.exists():
                lp.write_text(
                    lp.read_text(encoding="utf-8")
                    .replace("status   : RUNNING", f"status   : {args.stop}"),
                    encoding="utf-8",
                )
    if args.note and ledger_path:
        lp = ROOT / ledger_path
        lp.parent.mkdir(parents=True, exist_ok=True)
        with (lp.parent / "stop-reason.txt").open("a", encoding="utf-8") as fh:
            fh.write(f"{_now_iso()}\t{args.stop or 'ENDED'}\t{args.note}\n")
    MARKER.unlink()
    print(f"pm_run: ENDED — ledger: {ledger_path}  stop: {args.stop or '(none)'}")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    if not MARKER.exists():
        print("pm_run: no active run.")
        return 0
    ledger = _read_ledger_path()
    age = _heartbeat_age_minutes()
    age_txt = "no heartbeat" if age is None else f"{int(age)} min ago"
    print(f"pm_run: ACTIVE — ledger: {ledger}  heartbeat: {age_txt}")
    return 0


def _self_test() -> int:
    import tempfile

    global RUNS, TEMPLATE, MARKER, HEARTBEAT, ROOT
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        ROOT = root
        RUNS = root / "engine" / "workflows" / "pm-orchestrator" / "runs"
        TEMPLATE = root / "engine" / "workflows" / "pm-orchestrator" / "templates" / "pm-state-template.md"
        MARKER = root / ".claude" / ".pm-run-active"
        HEARTBEAT = root / ".claude" / ".orchestrator_invariants.heartbeat"
        RUNS.mkdir(parents=True)
        MARKER.parent.mkdir(parents=True)
        TEMPLATE.parent.mkdir(parents=True)
        TEMPLATE.write_text("# state <scope> run-NNN\nstatus   : RUNNING\n", encoding="utf-8")

        ns_start = argparse.Namespace(scope="demo", recipe="review", task="demo run", worktree="bed", force=False)
        assert cmd_start(ns_start) == 0
        assert MARKER.exists(), "start must create marker"
        assert "demo" in MARKER.read_text() and "run-001" in MARKER.read_text()
        # double-start without --force -> refused
        assert cmd_start(ns_start) == 2
        # --force replaces
        ns_force = argparse.Namespace(scope="demo", recipe="espresso", task="again", worktree=None, force=True)
        assert cmd_start(ns_force) == 0
        assert "run-002" in MARKER.read_text(), "force must advance run number"
        # status
        assert cmd_status(argparse.Namespace()) == 0
        # end
        ns_end = argparse.Namespace(stop="DONE", note="clean")
        assert cmd_end(ns_end) == 0
        assert not MARKER.exists(), "end must remove marker"
        # end without active -> refused
        assert cmd_end(ns_end) == 2
    print("pm_run self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return _self_test()
    p = argparse.ArgumentParser(prog="pm_run", description="pm-orchestrator run lifecycle")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("start", help="start a run — create ledger dir + marker")
    sp.add_argument("scope")
    sp.add_argument("--recipe", default=None)
    sp.add_argument("--task", default=None)
    sp.add_argument("--worktree", default=None)
    sp.add_argument("--force", action="store_true", help="replace an existing active run")
    se = sub.add_parser("end", help="end the active run — remove marker")
    se.add_argument("--stop", default=None)
    se.add_argument("--note", default=None)
    sub.add_parser("status", help="show active run state")
    args = p.parse_args(argv)
    if args.cmd == "start":
        return cmd_start(args)
    if args.cmd == "end":
        return cmd_end(args)
    if args.cmd == "status":
        return cmd_status(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
