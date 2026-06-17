#!/usr/bin/env python3
"""
learning_capture.py — provisional learning intake for the second-brain.

Usage:
  python scripts/learning_capture.py \
    --title "..." --source conversation --scope workspace \
    --confidence high --proposed-target engine/rules/backend \
    --what "..." --why "..."

Stdin: optional extra body text piped in (appended to # How To Apply).
--self-test: run internal tests and exit.
"""

import argparse
import re
import sys
import os
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SECOND_BRAIN   = WORKSPACE_ROOT / "second-brain"
MAIN_BRAIN     = WORKSPACE_ROOT / "main-brain"
INDEX_FILE     = SECOND_BRAIN / "INDEX.md"

VALID_SOURCES  = {
    "conversation", "review-closeout", "bug-fix",
    "user-correction", "implementation-discovery", "harness-review",
}
VALID_SCOPES   = {
    "workspace", "backend", "frontend",
}  # also module:<name> and workflow:<name> accepted dynamically

VALID_CONFS    = {"low", "medium", "high"}

FRONTMATTER_KEYS = [
    "title", "date", "status", "source", "scope",
    "confidence", "owner_confirmed", "proposed_target", "tags", "expires",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:60].rstrip("-")


def build_frontmatter(args, today: str) -> str:
    tags_raw = args.tags or []
    tags_yaml = "[" + ", ".join(tags_raw) + "]" if tags_raw else "[]"
    expires   = args.expires or '""'
    lines = [
        "---",
        f'title: "{args.title}"',
        f'date: "{today}"',
        "status: provisional",
        f"source: {args.source}",
        f"scope: {args.scope}",
        f"confidence: {args.confidence}",
        "owner_confirmed: false",
        f"proposed_target: {args.proposed_target}",
        f"tags: {tags_yaml}",
        f"expires: {expires}",
        "---",
    ]
    return "\n".join(lines)


def build_body(args, extra_stdin: str) -> str:
    boundaries = args.boundaries or "_No specific boundaries noted._"
    how_to_apply = extra_stdin.strip() if extra_stdin.strip() else "_See # What above._"
    evidence_raw = args.evidence or "_No specific evidence cited._"

    return f"""
# What

{args.what}

# Evidence

- {evidence_raw}

# Why It Matters

{args.why}

# How To Apply

{how_to_apply}

# Boundaries

{boundaries}

# Promotion Recommendation

Promote to: {args.proposed_target}
Reason: (fill in before promoting)
"""


def build_seen_again_section(today: str, args) -> str:
    return f"""

## Seen again ({today})

- source: {args.source}
- what: {args.what}
- why: {args.why}
- confidence: {args.confidence}
"""


def ensure_index(index_path: Path) -> None:
    """Create INDEX.md with header if it does not exist."""
    if not index_path.exists():
        index_path.write_text(
            "# second-brain index\n\n"
            "One line per learning: `- [slug](slug.md) — hook`. "
            "Promoted/graduated entries stay as **tombstones**\n"
            "(`- ~~slug~~ → promoted to main-brain` or `→ graduated to skill <x>`) "
            "so we never re-learn them.\n\n"
            "_(empty — no learnings captured yet.)_\n",
            encoding="utf-8",
        )


def append_index_line(index_path: Path, slug: str, filename: str, args) -> None:
    content = index_path.read_text(encoding="utf-8")
    # Remove the "(empty)" placeholder if present
    content = content.replace("_(empty — no learnings captured yet.)_\n", "").rstrip()
    new_line = f"\n- [{slug}]({filename}) — {args.proposed_target} | {args.confidence} | {args.source}"
    index_path.write_text(content + new_line + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------

def refuse_main_brain(proposed_target: str) -> None:
    """Hard guard: proposed-target must not be a path inside main-brain/."""
    if proposed_target.lower().startswith("main-brain/") or proposed_target.lower().startswith("main-brain\\"):
        print(
            "ERROR: proposed-target cannot be a path inside main-brain/.\n"
            "  Use proposed_target: main-brain  (the tier label) to signal\n"
            "  that this should be promoted — the /promote skill writes main-brain/.",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main capture
# ---------------------------------------------------------------------------

def capture(args, stdin_text: str = "") -> Path:
    today     = date.today().isoformat()
    slug      = slugify(args.title)
    filename  = f"{today}-{slug}.md"
    dest      = SECOND_BRAIN / filename

    refuse_main_brain(args.proposed_target)

    if dest.exists():
        # Append a "seen again" section instead of duplicating
        seen = build_seen_again_section(today, args)
        existing = dest.read_text(encoding="utf-8")
        dest.write_text(existing + seen, encoding="utf-8")
        print(f"[learning_capture] Updated existing entry: {dest.relative_to(WORKSPACE_ROOT)}")
        return dest

    content = build_frontmatter(args, today) + "\n" + build_body(args, stdin_text)
    SECOND_BRAIN.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    print(f"[learning_capture] Created: {dest.relative_to(WORKSPACE_ROOT)}")

    ensure_index(INDEX_FILE)
    append_index_line(INDEX_FILE, slug, filename, args)
    print(f"[learning_capture] Index updated: {INDEX_FILE.relative_to(WORKSPACE_ROOT)}")
    return dest


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def self_test() -> None:
    import tempfile
    import shutil

    print("=== learning_capture self-test ===")
    errors = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        sb = tmp_path / "second-brain"
        sb.mkdir()
        mb = tmp_path / "main-brain"
        mb.mkdir()

        # Patch module globals temporarily
        global SECOND_BRAIN, MAIN_BRAIN, INDEX_FILE, WORKSPACE_ROOT
        orig_sb, orig_mb, orig_idx, orig_root = SECOND_BRAIN, MAIN_BRAIN, INDEX_FILE, WORKSPACE_ROOT
        SECOND_BRAIN  = sb
        MAIN_BRAIN    = mb
        INDEX_FILE    = sb / "INDEX.md"
        WORKSPACE_ROOT = tmp_path

        try:
            # --- test 1: normal capture creates file + index line ---
            class FakeArgs:
                title          = "Test learning entry"
                source         = "conversation"
                scope          = "workspace"
                confidence     = "low"
                proposed_target = "reject"
                what           = "x"
                why            = "y"
                evidence       = None
                boundaries     = None
                tags           = []
                expires        = None

            dest = capture(FakeArgs())
            assert dest.exists(), "file not created"
            text = dest.read_text()
            assert "status: provisional" in text, "frontmatter missing status"
            assert "proposed_target: reject" in text, "frontmatter missing proposed_target"
            assert "# What" in text, "body missing # What"
            print("  [PASS] file created with correct frontmatter")

            idx_text = INDEX_FILE.read_text()
            assert "test-learning-entry" in idx_text, "index line missing"
            print("  [PASS] INDEX.md has entry")

            # --- test 2: second capture on same slug appends seen-again ---
            dest2 = capture(FakeArgs())
            text2 = dest2.read_text()
            assert "Seen again" in text2, "no seen-again section"
            print("  [PASS] duplicate slug appends seen-again section")

            # --- test 3: refuse main-brain/ path ---
            class BadArgs(FakeArgs):
                proposed_target = "main-brain/knowledge.md"

            raised = False
            try:
                refuse_main_brain(BadArgs.proposed_target)
            except SystemExit:
                raised = True
            assert raised, "did not raise SystemExit for main-brain/ path"
            print("  [PASS] refuses main-brain/ path target")

        finally:
            SECOND_BRAIN   = orig_sb
            MAIN_BRAIN     = orig_mb
            INDEX_FILE     = orig_idx
            WORKSPACE_ROOT = orig_root

    if errors:
        for e in errors:
            print(f"  [FAIL] {e}", file=sys.stderr)
        sys.exit(1)
    print("=== All tests passed ===")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Capture a provisional learning into second-brain/."
    )
    p.add_argument("--title",           required=False, help="Short title (required unless --self-test)")
    p.add_argument("--source",          default="conversation",
                   help=f"One of: {', '.join(sorted(VALID_SOURCES))}")
    p.add_argument("--scope",           default="workspace",
                   help="workspace | backend | frontend | module:<name> | workflow:<name>")
    p.add_argument("--confidence",      default="medium",
                   help="low | medium | high")
    p.add_argument("--proposed-target", default="reject",
                   help="main-brain | engine/rules/backend | engine/rules/frontend | "
                        "deep-review/checklist | skill | spec-decision | reject")
    p.add_argument("--evidence",        default=None, help="Evidence citation (path:line or short quote)")
    p.add_argument("--what",            required=False, help="One clear statement of the learning")
    p.add_argument("--why",             required=False, help="What failure this prevents")
    p.add_argument("--boundaries",      default=None, help="Where this does NOT apply")
    p.add_argument("--tags",            nargs="*", default=[], help="Optional tag list")
    p.add_argument("--expires",         default=None, help="Optional revalidation hint")
    p.add_argument("--self-test",       action="store_true", help="Run internal tests and exit")
    return p


def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    if args.self_test:
        self_test()
        return

    # Validate required fields
    missing = []
    if not args.title: missing.append("--title")
    if not args.what:  missing.append("--what")
    if not args.why:   missing.append("--why")
    if missing:
        parser.error(f"Required when not using --self-test: {', '.join(missing)}")

    # Read optional stdin
    stdin_text = ""
    if not sys.stdin.isatty():
        stdin_text = sys.stdin.read()

    capture(args, stdin_text)


if __name__ == "__main__":
    main()
