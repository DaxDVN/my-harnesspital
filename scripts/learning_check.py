#!/usr/bin/env python3
"""
learning_check.py — doctor-style health checks for the self-learning system.

Exit 0  = all checks pass (OK / WARN only).
Exit 1  = at least one FAIL.

Checks:
  1. Every second-brain/*.md (except README/INDEX) has valid frontmatter with required keys.
  2. Every INDEX.md entry points to an existing file.
  3. No status:provisional entry is cited as canon by main-brain/knowledge.md.
  4. main-brain/knowledge.md stays below a size budget.
  5. No agent-created main-brain/.promote-unlock.
"""

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

WORKSPACE_ROOT      = Path(__file__).resolve().parent.parent
SECOND_BRAIN        = WORKSPACE_ROOT / "second-brain"
MAIN_BRAIN          = WORKSPACE_ROOT / "main-brain"
MAIN_BRAIN_KNOWLEDGE = MAIN_BRAIN / "knowledge.md"
PROMOTE_UNLOCK      = MAIN_BRAIN / ".promote-unlock"

REQUIRED_KEYS = {
    "title", "date", "status", "source", "scope",
    "confidence", "owner_confirmed", "proposed_target",
}

MAIN_BRAIN_SIZE_BUDGET = 8000  # characters — warn if over
INDEX_ENTRY_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAIL_COUNT = 0
WARN_COUNT = 0


def ok(msg: str)   -> None: print(f"  [OK]   {msg}")
def warn(msg: str) -> None:
    global WARN_COUNT
    WARN_COUNT += 1
    print(f"  [WARN] {msg}")

_SELFTEST = False


def fail(msg: str) -> None:
    global FAIL_COUNT
    FAIL_COUNT += 1
    prefix = "[EXPECTED_FAIL]" if _SELFTEST else "[FAIL]"
    print(f"  {prefix} {msg}", file=sys.stderr)


def parse_frontmatter(text: str) -> dict | None:
    """Return dict of frontmatter keys, or None if no valid YAML front-matter block."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].strip()
    result = {}
    for line in block.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_frontmatter_schema() -> None:
    print("\n--- Check 1: second-brain frontmatter schema ---")
    skip = {"README.md", "INDEX.md"}
    files = sorted([p for p in SECOND_BRAIN.glob("*.md") if p.name not in skip] +
                   list((SECOND_BRAIN / "grouped").glob("[0-9][0-9]-*.md")))
    checked = 0
    for md in files:
        text = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm is None:
            fail(f"{md.relative_to(SECOND_BRAIN)}: missing or malformed frontmatter")
            continue
        missing = REQUIRED_KEYS - set(fm.keys())
        if missing:
            fail(f"{md.relative_to(SECOND_BRAIN)}: missing frontmatter keys: {', '.join(sorted(missing))}")
        else:
            ok(f"{md.relative_to(SECOND_BRAIN)}: frontmatter OK")
        checked += 1
    if checked == 0:
        ok("second-brain/ has no learning entries yet")


def check_index_entries() -> None:
    print("\n--- Check 2: INDEX.md links ---")
    index = SECOND_BRAIN / "INDEX.md"
    if not index.exists():
        warn("second-brain/INDEX.md does not exist yet (will be created on first capture)")
        return
    text = index.read_text(encoding="utf-8")

    # Strip inline code spans (backtick) and fenced code blocks before scanning for links
    # so that legend/example text like `[slug](slug.md)` is not treated as a real link.
    stripped = re.sub(r"`[^`]+`", "", text)          # inline code spans
    stripped = re.sub(r"```[\s\S]*?```", "", stripped)  # fenced blocks

    matches = INDEX_ENTRY_RE.findall(stripped)
    if not matches:
        ok("INDEX.md exists; no entry links to validate")
        return
    for _label, href in matches:
        target = SECOND_BRAIN / href
        if target.exists():
            ok(f"INDEX -> {href} exists")
        else:
            fail(f"INDEX -> {href} is a dead link (file not found)")


def check_no_provisional_as_canon() -> None:
    print("\n--- Check 3: no provisional entry cited as canon in main-brain ---")
    if not MAIN_BRAIN_KNOWLEDGE.exists():
        ok("main-brain/knowledge.md not present — nothing to check")
        return
    mb_text = MAIN_BRAIN_KNOWLEDGE.read_text(encoding="utf-8")

    skip = {"README.md", "INDEX.md"}
    files = sorted([p for p in SECOND_BRAIN.glob("*.md") if p.name not in skip] +
                   list((SECOND_BRAIN / "grouped").glob("[0-9][0-9]-*.md")))
    for md in files:
        text = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm is None:
            continue
        if fm.get("status", "").strip() != "provisional":
            continue
        slug = md.stem
        # Check if any fragment of the slug or the filename appears as a link in main-brain
        if slug in mb_text or md.name in mb_text:
            fail(
                f"{md.name} is status:provisional but appears to be cited in "
                f"main-brain/knowledge.md — promote properly via /promote"
            )
        else:
            ok(f"{md.name}: not cited as canon")


def check_main_brain_size() -> None:
    print("\n--- Check 4: main-brain/knowledge.md size budget ---")
    if not MAIN_BRAIN_KNOWLEDGE.exists():
        ok("main-brain/knowledge.md does not exist — size OK (0 chars)")
        return
    size = len(MAIN_BRAIN_KNOWLEDGE.read_text(encoding="utf-8"))
    if size > MAIN_BRAIN_SIZE_BUDGET:
        warn(
            f"main-brain/knowledge.md is {size} chars "
            f"(budget {MAIN_BRAIN_SIZE_BUDGET}) — consider pruning or linking down to engine/"
        )
    else:
        ok(f"main-brain/knowledge.md size: {size} chars (within {MAIN_BRAIN_SIZE_BUDGET})")


def check_expiry() -> None:
    """V1: surface expired provisional learnings — they need revalidation, promotion, or deletion."""
    print("\n--- Check 6: expired provisional learnings (revalidate) ---")
    from datetime import date as _date
    skip = {"README.md", "INDEX.md"}
    found = 0
    for md in sorted(SECOND_BRAIN.glob("*.md")):
        if md.name in skip:
            continue
        fm = parse_frontmatter(md.read_text(encoding="utf-8"))
        if not fm or fm.get("status", "").strip() != "provisional":
            continue
        exp = fm.get("expires", "").strip().strip('"').strip("'")
        if not exp:
            continue
        try:
            if _date.today() >= _date.fromisoformat(exp[:10]):
                warn(f"{md.name}: expired ({exp}) — revalidate, /promote, or delete")
                found += 1
        except ValueError:
            pass
    if found == 0:
        ok("no expired provisional learnings")


def check_no_promote_unlock() -> None:
    print("\n--- Check 5: no agent-created .promote-unlock ---")
    if PROMOTE_UNLOCK.exists():
        fail(
            "main-brain/.promote-unlock exists — it must be created and removed by the owner "
            "manually, not left behind by an agent. Delete it after promote is complete."
        )
    else:
        ok("main-brain/.promote-unlock absent")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def self_test() -> None:
    import tempfile

    print("=== learning_check self-test ===")
    errors = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path  = Path(tmp)
        sb        = tmp_path / "second-brain"
        mb        = tmp_path / "main-brain"
        sb.mkdir(); mb.mkdir()

        # Patch globals
        global SECOND_BRAIN, MAIN_BRAIN, MAIN_BRAIN_KNOWLEDGE, PROMOTE_UNLOCK
        orig_sb, orig_mb   = SECOND_BRAIN, MAIN_BRAIN
        orig_mbk, orig_pu  = MAIN_BRAIN_KNOWLEDGE, PROMOTE_UNLOCK
        SECOND_BRAIN       = sb
        MAIN_BRAIN         = mb
        MAIN_BRAIN_KNOWLEDGE = mb / "knowledge.md"
        PROMOTE_UNLOCK     = mb / ".promote-unlock"

        # Reset counters
        global FAIL_COUNT, WARN_COUNT, _SELFTEST
        orig_fc, orig_wc, orig_st = FAIL_COUNT, WARN_COUNT, _SELFTEST
        _SELFTEST = True  # negative cases below print [EXPECTED_FAIL], not [FAIL]

        try:
            # --- good entry ---
            good = sb / "2026-06-17-test.md"
            good.write_text(
                "---\ntitle: \"t\"\ndate: \"2026-06-17\"\nstatus: provisional\n"
                "source: conversation\nscope: workspace\nconfidence: low\n"
                "owner_confirmed: false\nproposed_target: reject\ntags: []\nexpires: \"\"\n---\n\n# What\nx\n",
                encoding="utf-8",
            )

            # --- INDEX pointing to good entry ---
            idx = sb / "INDEX.md"
            idx.write_text("# index\n- [test](2026-06-17-test.md) — reject | low | conversation\n", encoding="utf-8")

            # --- small knowledge.md ---
            MAIN_BRAIN_KNOWLEDGE.write_text("# knowledge\n_(empty)_\n", encoding="utf-8")

            FAIL_COUNT = 0; WARN_COUNT = 0
            check_frontmatter_schema()
            assert FAIL_COUNT == 0, "unexpected failures on valid entry"
            print("  [PASS] valid frontmatter accepted")

            check_index_entries()
            assert FAIL_COUNT == 0, "unexpected failures on valid index"
            print("  [PASS] valid INDEX accepted")

            check_main_brain_size()
            assert FAIL_COUNT == 0, "unexpected size failure"
            print("  [PASS] size check passes for small knowledge.md")

            # --- dead index link ---
            idx.write_text("# index\n- [missing](nonexistent.md)\n", encoding="utf-8")
            FAIL_COUNT = 0
            check_index_entries()
            assert FAIL_COUNT == 1, "dead link not caught"
            print("  [PASS] dead INDEX link caught")

            # --- missing frontmatter key ---
            bad = sb / "2026-06-17-bad.md"
            bad.write_text(
                "---\ntitle: \"bad\"\nstatus: provisional\n---\n\n# What\nx\n",
                encoding="utf-8",
            )
            FAIL_COUNT = 0
            check_frontmatter_schema()
            assert FAIL_COUNT >= 1, "missing key not caught"
            print("  [PASS] missing frontmatter key caught")
            bad.unlink()

            # --- promote-unlock guard ---
            PROMOTE_UNLOCK.touch()
            FAIL_COUNT = 0
            check_no_promote_unlock()
            assert FAIL_COUNT == 1, ".promote-unlock not caught"
            PROMOTE_UNLOCK.unlink()
            print("  [PASS] stale .promote-unlock caught")

            # --- expired provisional learning warns ---
            exp = sb / "2020-01-01-expired.md"
            exp.write_text(
                '---\ntitle: "e"\ndate: "2020-01-01"\nstatus: provisional\nsource: conversation\n'
                'scope: workspace\nconfidence: low\nowner_confirmed: false\nproposed_target: reject\n'
                'expires: "2020-01-02"\n---\n# What\nx\n', encoding="utf-8")
            WARN_COUNT = 0
            check_expiry()
            assert WARN_COUNT == 1, "expired entry not warned"
            exp.unlink()
            print("  [PASS] expired learning warned")

        finally:
            SECOND_BRAIN        = orig_sb
            MAIN_BRAIN          = orig_mb
            MAIN_BRAIN_KNOWLEDGE = orig_mbk
            PROMOTE_UNLOCK      = orig_pu
            FAIL_COUNT          = orig_fc
            WARN_COUNT          = orig_wc
            _SELFTEST           = orig_st

    print("=== All tests passed ===")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Doctor-style health checks for the learning system.")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()

    if args.self_test:
        self_test()
        return

    print("=== learning_check ===")
    check_frontmatter_schema()
    check_index_entries()
    check_no_provisional_as_canon()
    check_main_brain_size()
    check_no_promote_unlock()
    check_expiry()

    print(f"\nResult: {FAIL_COUNT} failure(s), {WARN_COUNT} warning(s)")
    if FAIL_COUNT:
        sys.exit(1)


if __name__ == "__main__":
    main()
