#!/usr/bin/env python3
"""oc_budget.py — budget guard for the OpenCode Go subscription (one dollar-capped seat:
$12 per 5-hour window, $30 per week, $60 per month). Keeps usage inside those caps and
recommends cost-aware model choices, so the blind PM orchestrator never blows the seat.

Model routing source of truth is scripts/tier_policy.json (its `roles` block maps
role -> {provider, model, variant}); this guard prices the bare model ids it uses.

Design notes (verified `opencode stats` v1.17.x):
  - `opencode stats [--days N]` prints a box table with a `Total Cost ... $X.XX` line.
    `--days` is integer-day only (no sub-day granularity), so the 5h window always comes
    from the local tally; the 7d/30d windows prefer the authoritative `opencode stats`
    spend and fall back to the tally when `opencode` is absent/unparseable.

Local tally: scripts append per-call usage to ROOT/.claude/.oc_budget.json (a JSON list of
{ts_iso, model, in, out, cached, usd}). This is a normal script (NOT a Workflow sandbox),
so wall-clock time is allowed. Fail-open everywhere: a budget guard must never crash a caller.

Usage:
  python scripts/oc_budget.py record --model glm-5.2 --in 12000 --out 3000 [--cached 8000]
  python scripts/oc_budget.py status
  python scripts/oc_budget.py can-spend --est-usd 0.40
  python scripts/oc_budget.py recommend --role audit
  python scripts/oc_budget.py --self-test
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TIER_POLICY_PATH = ROOT / "scripts" / "tier_policy.json"
TALLY_PATH = ROOT / ".claude" / ".oc_budget.json"

# OpenCode Go caps for the single dollar-capped seat (USD).
CAPS: dict[str, float] = {"5h": 12.0, "7d": 30.0, "30d": 60.0}
WINDOW_SECONDS: dict[str, int] = {"5h": 5 * 3600, "7d": 7 * 86400, "30d": 30 * 86400}
WINDOW_DAYS: dict[str, int | None] = {"5h": None, "7d": 7, "30d": 30}  # None => tally only

# Prices per 1M tokens: (input, output, cached_read). Keyed by the bare model id in roles.
PRICES: dict[str, tuple[float, float, float]] = {
    "glm-5.2": (1.40, 4.40, 0.26),
    "glm-5.1": (1.40, 4.40, 0.26),
    "deepseek-v4-pro": (1.74, 3.48, 0.0145),
    "deepseek-v4-flash": (0.14, 0.28, 0.0028),
    "kimi-k2.7-code": (0.95, 4.00, 0.19),
    "kimi-k2.6": (0.95, 4.00, 0.16),
    "minimax-m3": (0.30, 1.20, 0.06),
    "minimax-m2.7": (0.30, 1.20, 0.06),
    "mimo-v2.5": (0.14, 0.28, 0.0028),
    "mimo-v2.5-pro": (1.74, 3.48, 0.0145),
    "qwen3.7-max": (2.50, 7.50, 0.50),
    "qwen3.7-plus": (0.40, 1.60, 0.04),
    "qwen3.6-plus": (0.50, 3.00, 0.05),
}

# Cost-aware one-liner per opencode role (Ponytail: reserve premium models, bulk the cheap).
NOTES: dict[str, str] = {
    "audit": "reserve glm-5.2 (premium 1.40/4.40) for read-only audit; never for bulk edits.",
    "audit_second_lens": "deepseek-v4-pro as a confirm second lens; cheaper output than glm.",
    "trivial": "mimo-v2.5 is the cheapest tier (0.14/0.28); use for label/copy/trivial edits.",
    "mechanical_fix": "deepseek-v4-flash (0.14/0.28) for bulk mechanical fixes; cheap and fast.",
    "agentic_primary": "deepseek-v4-pro default agentic worker; mid output cost (3.48).",
    "agentic_harder": "minimax-m3 for harder agentic tasks; low cost (0.30/1.20).",
    "agentic_complex": "kimi-k2.7-code for complex multi-file work; pricey output (4.00) so scope it.",
}
DEFAULT_MODEL = "deepseek-v4-flash"


def _emit(blob: dict[str, Any]) -> None:
    print(json.dumps(blob))


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def load_tier_policy() -> dict[str, Any]:
    """Load tier_policy.json; fail-open to an empty roles map on any error."""
    try:
        data = json.loads(TIER_POLICY_PATH.read_text("utf-8"))
        if isinstance(data, dict) and data.get("roles"):
            return data
    except Exception:
        pass
    return {"roles": {}}


def cost_usd(model: str, tin: int, tout: int, cached: int = 0) -> float:
    """USD = (in*price_in + out*price_out + cached*price_cached) / 1e6. Unknown model -> 0.0."""
    price = PRICES.get(model)
    if not price:
        return 0.0
    pin, pout, pc = price
    return (tin * pin + tout * pout + cached * pc) / 1e6


def load_tally() -> list[dict[str, Any]]:
    try:
        data = json.loads(TALLY_PATH.read_text("utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def append_record(rec: dict[str, Any]) -> bool:
    """Append one usage record; create dir/file if missing. Fail-open (return False) if unwritable."""
    try:
        records = load_tally()
        records.append(rec)
        TALLY_PATH.parent.mkdir(parents=True, exist_ok=True)
        TALLY_PATH.write_text(json.dumps(records, indent=2), "utf-8")
        return True
    except Exception:
        return False


def tally_spend(window: str) -> float:
    """Sum tally USD over the trailing window. Naive/bad timestamps are skipped (fail-open)."""
    cutoff = _now() - datetime.timedelta(seconds=WINDOW_SECONDS[window])
    total = 0.0
    for rec in load_tally():
        try:
            ts = datetime.datetime.fromisoformat(str(rec.get("ts_iso", "")))
            if ts.tzinfo is not None and ts >= cutoff:
                total += float(rec.get("usd", 0) or 0)
        except Exception:
            continue
    return total


def opencode_cost(days: int) -> float | None:
    """Authoritative spend over the last N days from `opencode stats`. None if unavailable."""
    try:
        proc = subprocess.run(
            ["opencode", "stats", "--days", str(days), "--pure"],
            capture_output=True, text=True, timeout=30,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    m = re.search(r"Total Cost\D+([0-9][0-9,]*\.?[0-9]*)", proc.stdout or "")
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except Exception:
        return None


def window_spend(window: str) -> tuple[float, str]:
    """(spent_usd, source) for a window: prefer opencode stats for day-aligned windows."""
    days = WINDOW_DAYS[window]
    if days is not None:
        oc = opencode_cost(days)
        if oc is not None:
            return oc, "opencode"
    return tally_spend(window), "tally"


def can_spend_decision(est_usd: float, spend: dict[str, float]) -> tuple[bool, list[str]]:
    """Pure: est fits only if it stays under ALL three caps. Returns (ok, blocking_windows)."""
    blockers = [w for w in ("5h", "7d", "30d") if spend.get(w, 0.0) + est_usd > CAPS[w]]
    return (not blockers, blockers)


def resolve_recommend(role: str) -> dict[str, Any]:
    """Resolve a role -> recommended model + price + cost note. Fail-open to a cheap default."""
    r = (load_tier_policy().get("roles") or {}).get(role)
    if not isinstance(r, dict) or not r.get("model"):
        return {"role": role, "provider": "opencode", "model": DEFAULT_MODEL, "fallback": True,
                "price": PRICES[DEFAULT_MODEL], "note": "unknown role; " + NOTES["mechanical_fix"]}
    model = str(r.get("model"))
    provider = str(r.get("provider", "opencode"))
    price = PRICES.get(model)
    if provider != "opencode" or price is None:
        note = "Anthropic/native role — billed on Claude quota, NOT the OpenCode Go seat."
    else:
        note = NOTES.get(role, "OpenCode Go model; mind output price before bulk use.")
    return {"role": role, "provider": provider, "model": model, "variant": r.get("variant"),
            "price": price, "note": note, "fallback": False}


def cmd_record(model: str, tin: int, tout: int, cached: int) -> int:
    usd = round(cost_usd(model, tin, tout, cached), 6)
    rec = {"ts_iso": _now().isoformat(), "model": model, "in": tin, "out": tout,
           "cached": cached, "usd": usd}
    written = append_record(rec)
    _emit({"model": model, "in": tin, "out": tout, "cached": cached, "usd": usd, "recorded": written})
    return 0


def cmd_status() -> int:
    print("window |    spent |      cap | remaining | %used | source")
    print("-------+----------+----------+-----------+-------+-------")
    for w in ("5h", "7d", "30d"):
        spent, src = window_spend(w)
        cap = CAPS[w]
        rem = cap - spent
        pct = (spent / cap * 100.0) if cap else 0.0
        print(f"{w:>6} | {spent:8.2f} | {cap:8.2f} | {rem:9.2f} | {pct:5.1f} | {src}")
    return 0


def cmd_can_spend(est_usd: float) -> int:
    spend = {w: window_spend(w)[0] for w in ("5h", "7d", "30d")}
    ok, blockers = can_spend_decision(est_usd, spend)
    blob = {"est_usd": est_usd, "ok": ok, "spend": {w: round(v, 4) for w, v in spend.items()},
            "caps": CAPS}
    if not ok:
        blob["blocked_by"] = [{"window": w, "cap": CAPS[w], "spent": round(spend[w], 4)} for w in blockers]
    _emit(blob)
    return 0 if ok else 1


def cmd_recommend(role: str) -> int:
    info = resolve_recommend(role)
    price = info.get("price")
    price_str = f"in {price[0]}/out {price[1]}/cached {price[2]} per 1M" if price else "n/a (not on OpenCode seat)"
    print(f"role      : {info['role']}{' (fallback)' if info.get('fallback') else ''}")
    print(f"model     : {info['model']} ({info['provider']})")
    print(f"price     : {price_str}")
    print(f"note      : {info['note']}")
    return 0


def self_test() -> int:
    # cost math: 1M in + 1M out for glm-5.2 == 1.40 + 4.40 == 5.80
    assert abs(cost_usd("glm-5.2", 1_000_000, 1_000_000) - 5.80) < 1e-9, cost_usd("glm-5.2", 10**6, 10**6)
    assert abs(cost_usd("deepseek-v4-flash", 1_000_000, 0, 1_000_000) - (0.14 + 0.0028)) < 1e-9
    assert cost_usd("no-such-model", 10**6, 10**6) == 0.0  # unknown model fails open to 0
    # the 3 cap windows exist and agree across the maps
    assert set(CAPS) == {"5h", "7d", "30d"} == set(WINDOW_SECONDS) == set(WINDOW_DAYS), CAPS
    # can-spend logic: fits under all caps, else names the blocking window
    near = {"5h": 11.5, "7d": 0.0, "30d": 0.0}
    assert can_spend_decision(0.40, near) == (True, []), near
    ok, blockers = can_spend_decision(1.00, near)
    assert ok is False and blockers == ["5h"], (ok, blockers)
    assert can_spend_decision(40.0, {"5h": 0.0, "7d": 0.0, "30d": 0.0})[1] == ["5h", "7d"]
    # recommend resolves at least audit + mechanical_fix from tier_policy roles
    assert resolve_recommend("audit")["model"] == "glm-5.2", resolve_recommend("audit")
    assert resolve_recommend("mechanical_fix")["model"] == "deepseek-v4-flash"
    assert resolve_recommend("__nope__")["fallback"] is True
    print("oc_budget self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Budget guard for the OpenCode Go seat.")
    p.add_argument("--self-test", action="store_true")
    sub = p.add_subparsers(dest="cmd")

    rec = sub.add_parser("record", help="price + append one usage record")
    rec.add_argument("--model", required=True)
    rec.add_argument("--in", dest="tin", type=int, required=True, help="input tokens")
    rec.add_argument("--out", dest="tout", type=int, required=True, help="output tokens")
    rec.add_argument("--cached", type=int, default=0, help="cached-read tokens")

    sub.add_parser("status", help="spend vs cap across 5h/7d/30d windows")

    cs = sub.add_parser("can-spend", help="exit 0 if est fits all caps, else 1")
    cs.add_argument("--est-usd", dest="est_usd", type=float, required=True)

    rc = sub.add_parser("recommend", help="cost-aware model for a tier_policy role")
    rc.add_argument("--role", required=True)

    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    try:
        if args.cmd == "record":
            return cmd_record(args.model, args.tin, args.tout, args.cached)
        if args.cmd == "status":
            return cmd_status()
        if args.cmd == "can-spend":
            return cmd_can_spend(args.est_usd)
        if args.cmd == "recommend":
            return cmd_recommend(args.role)
    except Exception as e:  # fail-open: never crash a caller
        _emit({"ok": False, "error": str(e)})
        return 0
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
