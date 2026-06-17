#!/usr/bin/env python3
"""learning_recall.py — the second-brain APPLICABILITY MAP + query ("which note applies NOW?").

second-brain is on-demand (NOT auto-loaded like main-brain, to save tokens). The failure mode: notes get
written then never read, because the agent doesn't know WHEN they apply. This tool is the notebook's table
of contents: every note declares `applies_when` (tasks / globs / keywords); you query the MAP with your
current task and get back ONLY the matching notes. You never read the full second-brain — you read the MAP
(second-brain/INDEX.md) or you query here, then open just the matches.

  python scripts/learning_recall.py --context "fix listing hospital-scope in BE"
  python scripts/learning_recall.py --scope backend --task fix --keywords listing,hospital-scope
  python scripts/learning_recall.py --touch myhospital-be/Services/RoomService.cs
  python scripts/learning_recall.py --all            # print the whole map (cheap)
  python scripts/learning_recall.py --rebuild-map    # regenerate INDEX.md from entry frontmatter
  python scripts/learning_recall.py --self-test

A match is a CANDIDATE, not a command: it MAY apply (or not, or several may) — apply if it fits, but
verify, because second-brain is provisional.
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SECOND_BRAIN = WORKSPACE_ROOT / "second-brain"
INDEX_FILE = SECOND_BRAIN / "INDEX.md"
SKIP_FILES = {"INDEX.md", "README.md"}
CONF_W = {"high": 3, "medium": 2, "low": 1}

# task verbs (VN/EN) → canonical task, for --context parsing
TASK_HINTS = {
    "fix": "fix", "sửa": "fix", "bug": "fix", "rca": "fix",
    "review": "review", "audit": "review", "duyệt": "review",
    "implement": "implement", "làm": "implement", "build": "implement",
    "triển": "implement", "code": "implement",
    "design": "design", "thiết kế": "design", "spec": "design",
    "scaffold": "scaffold", "tạo": "scaffold",
    "test": "test", "kiểm thử": "test",
}
SCOPE_HINTS = {"backend": "backend", "be": "backend", "frontend": "frontend", "fe": "frontend"}
_STOP = {"the", "a", "an", "and", "or", "to", "in", "of", "for", "on", "is", "this", "that",
         "please", "with", "into", "from", "do", "my", "it", "be", "fe"}


# ---------------------------------------------------------------------------
# Parse one entry's frontmatter + signals
# ---------------------------------------------------------------------------

def _list(fm: dict, key: str) -> list[str]:
    raw = fm.get(key, "").strip().strip("[]")
    return [x.strip().strip('"').lower() for x in raw.split(",") if x.strip()]


def slug_of(p: Path) -> str:
    return re.sub(r"^\d{4}-\d\d-\d\d-", "", p.stem)


def parse_entry(p: Path) -> dict | None:
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
    m = re.match(r"^---\s*\n(.*?)\n---", txt, re.S)
    if not m:
        return None
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    if "provisional" not in fm.get("status", ""):
        return None  # tombstones / promoted entries are not live candidates
    wm = re.search(r"#\s*What\s*\n+(.+)", txt)
    one = (wm.group(1).strip() if wm else fm.get("title", "")).strip().strip('"')
    return {
        "path": p,
        "slug": slug_of(p),
        "title": fm.get("title", "").strip().strip('"'),
        "scope": (fm.get("scope") or "workspace").lower(),
        "conf": (fm.get("confidence") or "medium").lower(),
        "target": fm.get("proposed_target", ""),
        "tasks": _list(fm, "applies_tasks"),
        "globs": _list(fm, "applies_globs"),
        "keywords": _list(fm, "applies_keywords") + _list(fm, "tags"),
        "recurrence": txt.count("## Seen again"),
        "one_line": one[:140],
    }


def load_entries() -> list[dict]:
    out = []
    for p in sorted(SECOND_BRAIN.glob("*.md")):
        if p.name in SKIP_FILES:
            continue
        e = parse_entry(p)
        if e:
            out.append(e)
    return out


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def score(e: dict, scope: str | None, task: str | None,
          keywords: list[str], paths: list[str]) -> tuple[int, list[str]] | None:
    """Return (score, reasons) if e is a candidate for this context, else None.
    workspace-scoped notes are broad (always a candidate); a scoped note only matches its scope."""
    if scope and e["scope"] != "workspace" and e["scope"] != scope:
        return None
    if task and e["tasks"] and "any" not in e["tasks"] and task not in e["tasks"]:
        return None
    s = CONF_W.get(e["conf"], 2) + e["recurrence"]
    why: list[str] = []
    hay = (" " + e["title"] + " " + " ".join(e["keywords"]) + " ").lower()
    kh = [k for k in keywords if k and (" " + k + " " in hay or k in e["keywords"])]
    if kh:
        s += 5 * len(kh)
        why.append("kw:" + ",".join(sorted(set(kh))[:4]))
    gh = sorted({g for g in e["globs"] for pth in paths if fnmatch.fnmatch(pth.lower(), g)})
    if gh:
        s += 5 * len(gh)
        why.append("path:" + ",".join(gh[:3]))
    if scope and e["scope"] == scope and scope != "workspace":
        s += 2
        why.append("scope:" + scope)
    elif e["scope"] == "workspace":
        why.append("broad")
    if not why:
        why.append("scope-compatible")
    return s, why


def recall(scope=None, task=None, keywords=None, paths=None, limit=8):
    keywords = [k.lower() for k in (keywords or []) if k]
    paths = paths or []
    scored = []
    for e in load_entries():
        r = score(e, scope, task, keywords, paths)
        if r is not None:
            scored.append((r[0], r[1], e))
    # keyword/glob hits first, then by score
    scored.sort(key=lambda t: (any(w.startswith(("kw:", "path:")) for w in t[1]), t[0]), reverse=True)
    return scored[:limit]


def parse_context(text: str) -> tuple[str | None, str | None, list[str]]:
    low = " " + text.lower() + " "
    task = next((v for k, v in TASK_HINTS.items() if k in low), None)
    scope = next((v for k, v in SCOPE_HINTS.items() if " " + k + " " in low), None)
    toks = re.findall(r"[a-zA-Z][\w-]{2,}", text.lower())
    kws = [t for t in toks if t not in _STOP and t not in TASK_HINTS and t not in SCOPE_HINTS]
    return scope, task, kws


# ---------------------------------------------------------------------------
# Map (INDEX.md) — regenerate from entry frontmatter (canonical, no drift)
# ---------------------------------------------------------------------------

MAP_HEADER = (
    "# second-brain index — the APPLICABILITY MAP\n\n"
    "Read THIS file to know what second-brain holds + WHEN each note may apply. Do **NOT** read the full\n"
    "second-brain. To pull only the notes that fit your task:\n"
    "`python scripts/learning_recall.py --context \"<your task>\"`. A match MAY apply (or not, or several) —\n"
    "apply if it fits, but **verify** (second-brain is provisional). Promote a proven note with `/promote`.\n\n"
    "| slug | scope | applies when (tasks · keywords) | conf | → target |\n"
    "|---|---|---|---|---|\n"
)


def rebuild_map() -> int:
    entries = load_entries()
    tombstones = []
    if INDEX_FILE.exists():
        for line in INDEX_FILE.read_text(encoding="utf-8").splitlines():
            if re.match(r"^\s*[-|]\s*~~", line):   # a real tombstone row, not prose mentioning ~~slug~~
                tombstones.append(line.rstrip())
    rows = []
    for e in entries:
        when = (",".join(e["tasks"]) or "any") + " · " + (",".join(e["keywords"][:5]) or "—")
        rows.append(f"| [{e['slug']}]({e['path'].name}) | {e['scope']} | {when} | {e['conf']} | {e['target']} |")
    body = MAP_HEADER + ("\n".join(rows) if rows else "| _(none yet)_ | | | | |") + "\n"
    if tombstones:
        body += "\n## Tombstones (never re-learn)\n" + "\n".join(tombstones) + "\n"
    SECOND_BRAIN.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(body, encoding="utf-8")
    print(f"[learning_recall] map rebuilt: {len(entries)} note(s) → {INDEX_FILE.relative_to(WORKSPACE_ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# Print
# ---------------------------------------------------------------------------

def print_matches(scored) -> None:
    if not scored:
        print("[learning_recall] no matching second-brain notes — nothing to apply.")
        return
    print(f"[learning_recall] {len(scored)} candidate note(s) — open ONLY these; provisional, VERIFY before acting:\n")
    for s, why, e in scored:
        print(f"  [{s:>3}] {e['slug']}  ({'; '.join(why)})")
        print(f"        {e['one_line']}")
        print(f"        → {e['path'].relative_to(WORKSPACE_ROOT)}")


def print_map() -> None:
    if INDEX_FILE.exists():
        print(INDEX_FILE.read_text(encoding="utf-8"))
    else:
        print("[learning_recall] no INDEX.md yet — run --rebuild-map (or capture a note).")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> int:
    import tempfile
    global SECOND_BRAIN, INDEX_FILE, WORKSPACE_ROOT
    orig = (SECOND_BRAIN, INDEX_FILE, WORKSPACE_ROOT)
    with tempfile.TemporaryDirectory() as d:
        sb = Path(d) / "second-brain"
        sb.mkdir()
        SECOND_BRAIN, INDEX_FILE, WORKSPACE_ROOT = sb, sb / "INDEX.md", Path(d)
        try:
            (sb / "2026-06-17-be-listing-rule.md").write_text(
                "---\ntitle: \"BE listing hospital-scope\"\nstatus: provisional\nscope: backend\n"
                "confidence: high\nproposed_target: engine/rules/backend\n"
                "applies_tasks: [fix, review]\napplies_globs: [myhospital-be/**]\n"
                "applies_keywords: [listing, hospital-scope]\ntags: [security]\n---\n# What\nFilter by hospital.\n",
                encoding="utf-8")
            (sb / "2026-06-17-broad-note.md").write_text(
                "---\ntitle: \"Broad note\"\nstatus: provisional\nscope: workspace\nconfidence: low\n"
                "proposed_target: reject\napplies_tasks: [any]\napplies_keywords: [orchestration]\n---\n# What\nx.\n",
                encoding="utf-8")
            (sb / "2026-06-17-tombstone.md").write_text(  # promoted → not a candidate
                "---\ntitle: \"Gone\"\nstatus: promoted\nscope: backend\n---\n# What\ny.\n", encoding="utf-8")

            ents = load_entries()
            assert len(ents) == 2, f"expected 2 live entries, got {len(ents)}"

            # scope+keyword query → backend note ranks first via kw hit
            r = recall(scope="backend", task="fix", keywords=["listing"])
            assert r and r[0][2]["slug"] == "be-listing-rule", f"backend note not top: {r}"
            assert any(w.startswith("kw:") for w in r[0][1]), "keyword reason missing"

            # frontend scope → backend note filtered OUT, broad note stays
            r2 = recall(scope="frontend", task="fix")
            slugs = {e["slug"] for _, _, e in r2}
            assert "be-listing-rule" not in slugs and "broad-note" in slugs, f"scope filter wrong: {slugs}"

            # glob query
            r3 = recall(paths=["myhospital-be/Services/RoomService.cs"])
            assert any(e["slug"] == "be-listing-rule" for _, _, e in r3), "glob match failed"

            # context parse
            sc, tk, kw = parse_context("fix listing hospital-scope in BE")
            assert sc == "backend" and tk == "fix" and "listing" in kw, (sc, tk, kw)

            # rebuild map
            rebuild_map()
            idx = INDEX_FILE.read_text(encoding="utf-8")
            assert "be-listing-rule" in idx and "broad-note" in idx and "APPLICABILITY MAP" in idx, "map missing rows"
            assert "tombstone" not in idx, "tombstone leaked into live rows"
        finally:
            SECOND_BRAIN, INDEX_FILE, WORKSPACE_ROOT = orig
    print("learning_recall self-test: OK")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Query the second-brain applicability map.")
    ap.add_argument("--context", help="free-text task; scope/task/keywords are derived from it")
    ap.add_argument("--scope", help="workspace | backend | frontend | module:<n> | workflow:<n>")
    ap.add_argument("--task", help="fix | review | implement | design | scaffold | test")
    ap.add_argument("--keywords", help="comma-separated keywords")
    ap.add_argument("--touch", help="comma-separated file paths/globs you will change")
    ap.add_argument("--all", action="store_true", help="print the whole map (INDEX.md)")
    ap.add_argument("--rebuild-map", action="store_true", help="regenerate INDEX.md from entry frontmatter")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)

    if a.self_test:
        return _self_test()
    if a.rebuild_map:
        return rebuild_map()
    if a.all or not (a.context or a.scope or a.task or a.keywords or a.touch):
        print_map()
        return 0

    scope, task = a.scope, a.task
    keywords = [k.strip() for k in (a.keywords or "").split(",") if k.strip()]
    paths = [p.strip() for p in (a.touch or "").split(",") if p.strip()]
    if a.context:
        cs, ct, ck = parse_context(a.context)
        scope = scope or cs
        task = task or ct
        keywords = keywords or ck
    print_matches(recall(scope, task, keywords, paths, a.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
