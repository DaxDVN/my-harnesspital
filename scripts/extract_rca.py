#!/usr/bin/env python3
"""One-off: turn the noitru RCA workflow output into a persistent findings doc + compact digest."""
import json, sys

SRC = sys.argv[1]
MD = "/home/dax/Documents/arabica/roast/docs/audit/noitru-rca-findings-2026-06-17.md"
RAW = "/home/dax/Documents/arabica/roast/docs/audit/noitru-rca-findings-2026-06-17.json"

j = json.loads(open(SRC, encoding="utf-8").read())
res = j.get("result", {})
bugs = res.get("bugs", [])

# stable sort: status priority, then id
order = {"STILL_BROKEN": 0, "PARTIAL": 1, "ALREADY_FIXED": 2, "CANT_REPRODUCE": 3}
bugs.sort(key=lambda b: (order.get(b.get("repro_status", ""), 9), b.get("id", "")))

json.dump(bugs, open(RAW, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def g(b, k):
    return (b.get(k) or "").strip()

# ---- markdown doc (full detail) ----
out = ["# Nội-trú bug batch — RCA findings (2026-06-17)\n",
       f"Source: RCA workflow `wvxl31fjz` (8 investigators, read-only, vs current uncommitted worktree state).",
       f"Counts: {res.get('byStatus', {})}. Total {len(bugs)}.\n",
       "Pairs with `noitru-bugfix-batch-catalog-2026-06-17.md` (symptoms) and is the fix playbook. "
       "`blocked_on` = owner/BA decision needed before fixing.\n"]
cur = None
for b in bugs:
    st = b.get("repro_status", "?")
    if st != cur:
        cur = st
        out.append(f"\n---\n## {st}\n")
    out.append(f"### {b.get('id')} — {b.get('layer','?')}/{b.get('complexity','?')}")
    if g(b, "blocked_on"):
        out.append(f"- **BLOCKED_ON:** {g(b,'blocked_on')}")
    out.append(f"- **Root cause:** {g(b,'root_cause')}")
    ev = g(b, "evidence") or g(b, "root_cause_evidence")
    if ev:
        out.append(f"- **Evidence:** {ev}")
    out.append(f"- **Proposed fix:** {g(b,'proposed_fix')}")
    if g(b, "risk"):
        out.append(f"- **Risk:** {g(b,'risk')}")
    out.append("")
open(MD, "w", encoding="utf-8").write("\n".join(out))

# ---- compact digest (stdout -> my context) ----
print(f"=== {len(bugs)} bugs | {res.get('byStatus',{})} ===")
print(f"doc: {MD}")
print(f"{'ID':<9} {'STATUS':<14} {'L':<4} {'CX':<2} BLOCKED_ON / root (short)")
for b in bugs:
    bl = g(b, "blocked_on")
    tag = f"[BLOCK:{bl[:60]}]" if bl else g(b, "root_cause")[:70]
    print(f"{b.get('id',''):<9} {b.get('repro_status',''):<14} {b.get('layer',''):<4} {b.get('complexity',''):<2} {tag}")

print("\n=== BLOCKED_ON (owner decisions needed) ===")
seen = False
for b in bugs:
    if g(b, "blocked_on"):
        seen = True
        print(f"- {b.get('id')}: {g(b,'blocked_on')}")
if not seen:
    print("(none)")
