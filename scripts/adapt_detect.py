#!/usr/bin/env python3
"""adapt_detect — scan the harness for adapt-trigger signals and emit a dedup'd trigger report.

This is the DETECTION + PROPOSAL half of the adapt workflow. It is read-only: it never edits
harness machinery, never spawns a fixer, never auto-applies anything. It scans four signal
sources, dedups against a persistent trigger store, and prints a human-readable trigger report
the owner can act on with `/adapt`. The APPLY half stays owner-gated (AGENTS.md §3).

Signal sources:
  1. harness_doctor FAIL/WARN  → Mode A (a workflow machinery defect — registry drift, broken
     ref, governance error, runtime-contract violation).
  2. run-ledger status         → Mode A (a workflow run ended BLOCKED / CAP_HIT / FAILED with a
     machinery root-cause signature, not a task bug).
  3. scanner_promotion         → Mode B (a bug_class seen >=3 times → candidate for a deterministic
     scanner, OR if the pattern is multi-phase, a new workflow).
  4. learning_recall           → Mode B (a note seen >=3 times → candidate for graduation into a
     workflow/skill/rule).

Dedup: each signal is hashed into a stable trigger key (mode + target + root_cause_signature).
A trigger already in the store (.claude/.adapt-triggers.json) is NOT re-reported until the owner
clears it (by running /adapt or `adapt_detect --clear <key>`). This prevents nagging.

Usage:
    python scripts/adapt_detect.py                 # scan + print NEW triggers only
    python scripts/adapt_detect.py --all           # print ALL triggers incl. already-reported
    python scripts/adapt_detect.py --clear <key>   # mark a trigger acted-on (remove from store)
    python scripts/adapt_detect.py --clear-all     # reset the store
    python scripts/adapt_detect.py --json          # machine-readable (for hooks)
    python scripts/adapt_detect.py --self-test
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / ".claude" / ".adapt-triggers.json"
THRESHOLD_MODE_B = 3


# --- signal collection -------------------------------------------------------
def _run(argv: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        p = subprocess.run(
            argv, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=timeout, stdin=subprocess.DEVNULL,
        )
        return p.returncode, p.stdout
    except Exception as exc:  # noqa: BLE001
        return 1, f"<{argv[0]} failed: {exc}>"


def _doctor_signals() -> list[dict]:
    """Mode A signals from harness_doctor FAIL/WARN (excludes pre-known graphify noise)."""
    rc, out = _run([sys.executable, "scripts/harness_doctor.py"])
    signals: list[dict] = []
    for line in out.splitlines():
        m = re.match(r"^\s*\[(FAIL|WARN)\]\s+(\S+)\s+(.*)$", line)
        if not m:
            continue
        level, check, detail = m.group(1), m.group(2), m.group(3).strip()
        if check.startswith("graphify"):  # pre-known cross-machine noise, not adapt-worthy
            continue
        sig = f"doctor:{check}:{detail[:80]}"
        signals.append({
            "mode": "A",
            "target": _workflow_from_check(check),
            "root_cause_signature": sig,
            "source": "harness_doctor",
            "detail": f"[{level}] {check}: {detail}",
            "fail_count": 1,  # doctor is a snapshot; the run-ledger scan supplies repeat counts
        })
    return signals


def _run_ledger_signals() -> list[dict]:
    """Mode A signals from workflow run ledgers that ended badly with a machinery root cause."""
    signals: list[dict] = []
    for state_file in ROOT.glob("engine/workflows/*/runs/**/00-*-state.md"):
        try:
            text = state_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # status line variants: "status : BLOCKED", "- status: CAP_HIT", "status   : FAILED"
        sm = re.search(r"(?im)^\s*-?\s*status\s*:\s*(\w+)", text)
        if not sm:
            continue
        status = sm.group(1).upper()
        if status not in {"BLOCKED", "CAP_HIT", "FAILED"}:
            continue
        wf = state_file.parts[state_file.parts.index("workflows") + 1]
        # look for a machinery root-cause hint (not a task bug): the stop-reason / BLOCKED_RULE
        rm = re.search(r"(?is)##\s*Stop reason.*?(?:##\s|\Z)", text)
        stop = rm.group(0)[:300] if rm else ""
        # only treat as machinery if the stop reason mentions workflow/harness/manifest/gate/hook
        if not re.search(r"(?i)workflow|harness|manifest|gate|hook|ledger|envelope|registry", stop):
            continue
        sig = f"run:{wf}:{status}:{hashlib.md5(stop.encode()).hexdigest()[:8]}"
        signals.append({
            "mode": "A",
            "target": wf,
            "root_cause_signature": sig,
            "source": f"run-ledger:{state_file.relative_to(ROOT)}",
            "detail": f"{wf} run ended {status} with machinery root-cause hint",
            "fail_count": 1,
            "evidence_path": str(state_file.relative_to(ROOT)),
        })
    # aggregate same root_cause_signature across runs → fail_count
    by_sig: dict[str, dict] = {}
    for s in signals:
        key = s["root_cause_signature"]
        if key in by_sig:
            by_sig[key]["fail_count"] += 1
        else:
            by_sig[key] = dict(s)
    return list(by_sig.values())


def _scanner_signals() -> list[dict]:
    """Mode B signals from harness_scanner_promotion (bug_class >= THRESHOLD_MODE_B)."""
    rc, out = _run([sys.executable, "scripts/harness_scanner_promotion.py", "scan"])
    NOISE_KEYS = {"none", "", "na", "n/a"}
    signals: list[dict] = []
    for line in out.splitlines():
        m = re.match(r"^PROMOTE_TO_SCANNER\s+(\S+)\s+count=(\d+)", line)
        if not m:
            continue
        key, count = m.group(1), int(m.group(2))
        if count < THRESHOLD_MODE_B:
            continue
        if key.lower() in NOISE_KEYS or key.lower().startswith("none"):
            continue
        signals.append({
            "mode": "B",
            "target": key,
            "root_cause_signature": f"scanner:{key}",
            "source": "harness_scanner_promotion",
            "detail": f"bug_class `{key}` seen {count} times — candidate for a deterministic scanner or workflow",
            "occurrences": count,
        })
    return signals


def _learning_signals() -> list[dict]:
    """Mode B signals from learning notes seen >= THRESHOLD_MODE_B times (best-effort).

    Coarse: groups notes by a crude stem (first 3 filename tokens) and reports groups >=3. We
    FILTER OUT pure-date stems (e.g. `2026_06_17`) and meaningless stems (`none`, `readme`,
    `index`) — they are not real repetition patterns, just temporal/boilerplate clustering. The
    owner is the final filter; this is a nudge, not a verdict.
    """
    sb = ROOT / "second-brain"
    if not sb.exists():
        return []
    DATE_STEM = re.compile(r"^\d{4}(_\d{2})+$")  # 2026_06_17 etc.
    NOISE_STEMS = {"none", "readme", "index", "template", "trash", "archive", "grouped"}
    stems: dict[str, list[Path]] = {}
    for note in sb.rglob("*.md"):
        if note.parent.name == "_archive" and "_archive" in str(note):
            # archive notes are historical; count them but the stem filter removes date clusters
            pass
        name = note.stem.lower()
        stem = "_".join(re.split(r"[\s\-_]+", name)[:3])
        if DATE_STEM.match(stem) or stem in NOISE_STEMS:
            continue
        stems.setdefault(stem, []).append(note)
    signals: list[dict] = []
    for stem, notes in stems.items():
        if len(notes) < THRESHOLD_MODE_B:
            continue
        signals.append({
            "mode": "B",
            "target": stem,
            "root_cause_signature": f"learning:{stem}",
            "source": "second-brain",
            "detail": f"{len(notes)} notes share stem `{stem}` — candidate for graduation into a skill/rule/workflow",
            "occurrences": len(notes),
            "evidence_paths": [str(n.relative_to(ROOT)) for n in notes[:5]],
        })
    return signals


def collect() -> list[dict]:
    return _doctor_signals() + _run_ledger_signals() + _scanner_signals() + _learning_signals()


# --- dedup store -------------------------------------------------------------
def _load_store() -> dict:
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        return {"reported": {}}


def _save_store(data: dict) -> None:
    try:
        STORE.parent.mkdir(parents=True, exist_ok=True)
        STORE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _trigger_key(s: dict) -> str:
    raw = f"{s['mode']}|{s.get('target','')}|{s['root_cause_signature']}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _threshold_ok(s: dict) -> bool:
    if s["mode"] == "A":
        return s.get("fail_count", 1) >= 2
    return s.get("occurrences", 0) >= THRESHOLD_MODE_B


def _format_trigger(key: str, s: dict) -> str:
    if s["mode"] == "A":
        suggest = (f"/adapt mode=A target={s.get('target','?')} "
                   f"root_cause_signature={s['root_cause_signature']} "
                   f"fail_count={s.get('fail_count',1)}")
    else:
        suggest = (f"/adapt mode=B proposed_workflow_name=<slug> "
                   f"pattern=\"{s.get('target','?')}\" repetition_signal={s['root_cause_signature']}")
    ev = s.get("evidence_path") or s.get("evidence_paths") or s.get("source")
    detail = s.get("detail") or f"{s.get('target','?')} machinery failure — see evidence"
    return (f"ADAPT-TRIGGER (mode={s['mode']}, target={s.get('target','?')}, key={key})\n"
            f"  source: {s.get('source','?')}\n"
            f"  detail: {detail}\n"
            f"  evidence: {ev}\n"
            f"  suggestion: {suggest}")


def report(new_only: bool = True) -> list[dict]:
    collected = collect()
    store = _load_store()
    # Pull any signals queued by the PostToolUse fail-watch hook. These are CONFIRMED machinery
    # failures (the fail-watch already verified status + machinery hint), so they bypass the
    # fail_count>=2 threshold — the post-tool detection IS the second confirmation.
    queued = store.pop("queued", {})
    queued_list: list[dict] = []
    for key, q in queued.items():
        sig = q.get("root_cause_signature", "")
        if any(s.get("root_cause_signature") == sig for s in collected):
            continue
        q["_key"] = key
        q["fail_count"] = max(q.get("fail_count", 1), 2)  # bypass threshold
        queued_list.append(q)
    # threshold-gate the COLLECTED signals (not the queued ones — they are pre-confirmed)
    signals = [s for s in collected if _threshold_ok(s)] + queued_list
    fresh: list[dict] = []
    for s in signals:
        key = s.get("_key") or _trigger_key(s)
        s["_key"] = key
        if new_only and key in store["reported"]:
            continue
        fresh.append(s)
    # record fresh triggers as reported (so they don't nag next scan)
    for s in fresh:
        store["reported"][s["_key"]] = {"mode": s["mode"], "target": s.get("target"),
                                        "sig": s["root_cause_signature"], "first_seen": True}
    if fresh:
        _save_store(store)
    return fresh


def clear(key: str) -> int:
    store = _load_store()
    if key not in store["reported"]:
        print(f"adapt_detect: key {key!r} not in store", file=sys.stderr)
        return 1
    del store["reported"][key]
    _save_store(store)
    print(f"adapt_detect: cleared {key}")
    return 0


def clear_all() -> int:
    _save_store({"reported": {}})
    print("adapt_detect: store reset")
    return 0


# --- self-test ---------------------------------------------------------------
def _self_test() -> int:
    import tempfile

    global STORE, ROOT
    failures = 0

    def check(cond: bool, msg: str) -> None:
        nonlocal failures
        if not cond:
            failures += 1
            print(f"FAIL: {msg}")

    # trigger key is stable
    s = {"mode": "A", "target": "bug-fix", "root_cause_signature": "doctor:registry:x"}
    k1 = _trigger_key(s)
    check(_trigger_key(s) == k1, "trigger key not stable")
    check(_trigger_key({**s, "mode": "B"}) != k1, "trigger key should differ by mode")

    # threshold gate
    check(_threshold_ok({"mode": "A", "fail_count": 2}) is True, "A fail_count=2 should pass")
    check(_threshold_ok({"mode": "A", "fail_count": 1}) is False, "A fail_count=1 should NOT pass")
    check(_threshold_ok({"mode": "B", "occurrences": 3}) is True, "B occ=3 should pass")
    check(_threshold_ok({"mode": "B", "occurrences": 2}) is False, "B occ=2 should NOT pass")

    # store dedup in temp dir
    with tempfile.TemporaryDirectory() as d:
        STORE = Path(d) / ".adapt-triggers.json"
        ROOT = Path(d)
        store = _load_store()
        check(store == {"reported": {}}, "empty store init failed")
        # simulate a fresh signal → reported
        store["reported"]["abc123"] = {"mode": "A"}
        _save_store(store)
        check(_load_store()["reported"]["abc123"]["mode"] == "A", "store round-trip failed")
        # clear
        check(clear("abc123") == 0, "clear failed")
        check("abc123" not in _load_store()["reported"], "clear did not remove key")
        # clear-all
        _save_store({"reported": {"x": 1, "y": 2}})
        check(clear_all() == 0, "clear-all failed")
        check(_load_store() == {"reported": {}}, "clear-all did not reset")

    # _workflow_from_check heuristic
    check(_workflow_from_check("registry:manifests") == "registry", "workflow_from_check registry")
    check(_workflow_from_check("workflow-governance:scan") == "workflow-governance", "workflow_from_check governance")

    if failures:
        print(f"adapt_detect self-test: {failures} FAILED")
        return 1
    print("adapt_detect self-test: OK")
    return 0


def _workflow_from_check(check: str) -> str:
    """Heuristic: map a doctor check name to a workflow/target slug."""
    if "registry" in check or "manifest" in check:
        return "registry"
    if "workflow-governance" in check:
        return "workflow-governance"
    if "runtime-contract" in check:
        return "runtime-contract"
    if "legacy" in check:
        return "legacy"
    return check.split(":")[0]


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return _self_test()
    p = argparse.ArgumentParser(prog="adapt_detect", description="scan for adapt-trigger signals")
    p.add_argument("--all", action="store_true", help="print ALL triggers incl. already-reported")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--clear", metavar="KEY", help="mark a trigger acted-on (remove from store)")
    p.add_argument("--clear-all", action="store_true", help="reset the trigger store")
    args = p.parse_args(argv)
    if args.clear_all:
        return clear_all()
    if args.clear:
        return clear(args.clear)
    fresh = report(new_only=not args.all)
    if args.json:
        print(json.dumps(fresh, indent=2, ensure_ascii=False))
        return 0
    if not fresh:
        return 0  # silent when nothing new (hook-friendly)
    for s in fresh:
        print(_format_trigger(s["_key"], s))
        print()
    print(f"({len(fresh)} new trigger(s). Act with /adapt, or clear with: "
          f"python scripts/adapt_detect.py --clear <key>)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
