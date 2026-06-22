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
    "confidence", "owner_confirmed", "proposed_target", "tags",
    "applies_tasks", "applies_globs", "applies_keywords", "expires",
]

# INDEX.md is the applicability MAP (kept in sync with learning_recall.rebuild_map's format)
INDEX_HEADER = (
    "# second-brain index — the APPLICABILITY MAP\n\n"
    "Read THIS file to know what second-brain holds + WHEN each note may apply. Do **NOT** read the full\n"
    "second-brain. Pull only fitting notes: `python scripts/learning_recall.py --context \"<your task>\"`.\n"
    "A match MAY apply (or not, or several) — apply if it fits, but **verify** (provisional). `/promote` when proven.\n\n"
    "## Grouped management view\n\n"
    "Prefer `grouped/` when reviewing or promoting batches of related notes:\n\n"
    "- [`grouped/README.md`](grouped/README.md) — group policy and file list.\n"
    "- [`grouped/INDEX.md`](grouped/INDEX.md) — coverage map from all raw notes to grouped files.\n"
    "- [`grouped/01-freshness-before-diagnosis.md`](grouped/01-freshness-before-diagnosis.md) — generated/runtime/env freshness before diagnosis.\n"
    "- [`grouped/02-canonical-reuse-gate.md`](grouped/02-canonical-reuse-gate.md) — reuse canonical project patterns before new code.\n"
    "- [`grouped/03-correct-boundary-data-integrity.md`](grouped/03-correct-boundary-data-integrity.md) — correct boundary and real data contracts.\n"
    "- [`grouped/04-evidence-verification-gate.md`](grouped/04-evidence-verification-gate.md) — proof required before verified/safe claims.\n"
    "- [`grouped/05-automation-orchestration-triage.md`](grouped/05-automation-orchestration-triage.md) — automation signal, batching, owner gates.\n"
    "- [`grouped/06-design-spec-decision-gate.md`](grouped/06-design-spec-decision-gate.md) — clinical design genre and module spec decisions.\n\n"
    "Rows below are grouped notes or new uncompressed live notes. Archived raw notes live in `_archive/` and are\n"
    "opened only as provenance for a grouped rule.\n\n"
    "| slug | scope | applies when (tasks · keywords) | conf | → target |\n"
    "|---|---|---|---|---|\n"
)
EMPTY_ROW = "| _(none yet)_ | | | | |\n"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:60].rstrip("-")


def _yaml_list(xs) -> str:
    return "[" + ", ".join(xs) + "]" if xs else "[]"


def build_frontmatter(args, today: str) -> str:
    expires = args.expires or '""'
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
        f"tags: {_yaml_list(args.tags or [])}",
        f"applies_tasks: {_yaml_list(args.applies_tasks or [])}",
        f"applies_globs: {_yaml_list(args.applies_globs or [])}",
        f"applies_keywords: {_yaml_list(args.applies_keywords or [])}",
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
    """Create INDEX.md (the applicability map) with header if it does not exist."""
    if not index_path.exists():
        index_path.write_text(INDEX_HEADER + EMPTY_ROW, encoding="utf-8")


def append_index_line(index_path: Path, slug: str, filename: str, args) -> None:
    content = index_path.read_text(encoding="utf-8")
    content = content.replace(EMPTY_ROW, "")
    content = content.replace("_(empty — no learnings captured yet.)_\n", "")  # legacy placeholder
    content = content.rstrip()
    when = (",".join(args.applies_tasks or []) or "any") + " · " + (",".join(args.applies_keywords or []) or "—")
    row = f"\n| [{slug}]({filename}) | {args.scope} | {when} | {args.confidence} | {args.proposed_target} |"
    index_path.write_text(content + row + "\n", encoding="utf-8")


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

VALID_TARGET_EXACT = {"main-brain", "deep-review/checklist", "skill", "spec-decision", "reject"}


def validate(args) -> None:
    """Enforce the schema enums/patterns (F1) — help text alone let bad metadata rot second-brain."""
    errs = []
    if args.source not in VALID_SOURCES:
        errs.append(f"--source {args.source!r}; choose: {', '.join(sorted(VALID_SOURCES))}")
    if args.confidence not in VALID_CONFS:
        errs.append(f"--confidence {args.confidence!r}; choose: {', '.join(sorted(VALID_CONFS))}")
    if args.scope not in VALID_SCOPES and not re.match(r"^(module|workflow):.+$", args.scope or ""):
        errs.append(f"--scope {args.scope!r}; use workspace|backend|frontend|module:<name>|workflow:<name>")
    t = args.proposed_target or ""
    if not (t in VALID_TARGET_EXACT or t.startswith("engine/rules/")
            or t.startswith("engine/skills/") or t.startswith("deep-review/")):
        errs.append(f"--proposed-target {t!r}; use main-brain|engine/rules/*|engine/skills/*|"
                    "deep-review/checklist|skill|spec-decision|reject")
    if errs:
        for e in errs:
            print(f"ERROR: invalid {e}", file=sys.stderr)
        sys.exit(2)


def find_existing_provisional(slug):
    """Find an existing provisional entry for this slug on ANY date (F2: cross-day recurrence)."""
    for p in sorted(SECOND_BRAIN.glob(f"*-{slug}.md")):
        try:
            if "status: provisional" in p.read_text(encoding="utf-8")[:500]:
                return p
        except Exception:
            continue
    return None


def capture(args, stdin_text: str = "") -> Path:
    validate(args)
    refuse_main_brain(args.proposed_target)
    today     = date.today().isoformat()
    slug      = slugify(args.title)
    filename  = f"{today}-{slug}.md"
    dest      = SECOND_BRAIN / filename

    existing = find_existing_provisional(slug)
    if existing is not None:
        # Append a "seen again" section instead of duplicating (matches ANY date — recurrence not fragmented)
        seen = build_seen_again_section(today, args)
        existing.write_text(existing.read_text(encoding="utf-8") + seen, encoding="utf-8")
        print(f"[learning_capture] Recurrence — appended 'seen again' to {existing.relative_to(WORKSPACE_ROOT)}")
        return existing

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
                applies_tasks  = ["fix", "review"]
                applies_globs  = ["myhospital-be/**"]
                applies_keywords = ["listing"]
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

            # --- test 4: validate() rejects bad enums/patterns (F1) ---
            for field, bad in [("source", "bogus"), ("confidence", "bogus"),
                               ("scope", "nonsense"), ("proposed_target", "random/path")]:
                V = type("V", (FakeArgs,), {field: bad})
                raised = False
                try:
                    validate(V())
                except SystemExit:
                    raised = True
                assert raised, f"validate did not reject bad {field}={bad}"
            print("  [PASS] validate rejects bad source/scope/confidence/target")

            # --- test 5: cross-day recurrence appends to existing provisional (F2) ---
            CD = type("CD", (FakeArgs,), {"title": "Cross day entry"})
            old_entry = sb / "2020-01-01-cross-day-entry.md"
            old_entry.write_text("---\nstatus: provisional\n---\n# What\nold\n", encoding="utf-8")
            ret = capture(CD())
            assert ret == old_entry, f"cross-day did not reuse existing file: {ret}"
            assert "Seen again" in old_entry.read_text(encoding="utf-8"), "cross-day did not append"
            assert not (sb / f"{date.today().isoformat()}-cross-day-entry.md").exists(), "cross-day made a new file"
            print("  [PASS] cross-day recurrence appends to existing provisional")

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
    p.add_argument("--source",          default="conversation", choices=sorted(VALID_SOURCES),
                   help=f"One of: {', '.join(sorted(VALID_SOURCES))}")
    p.add_argument("--scope",           default="workspace",
                   help="workspace | backend | frontend | module:<name> | workflow:<name>")
    p.add_argument("--confidence",      default="medium", choices=sorted(VALID_CONFS),
                   help="low | medium | high")
    p.add_argument("--proposed-target", default="reject",
                   help="main-brain | engine/rules/backend | engine/rules/frontend | "
                        "deep-review/checklist | skill | spec-decision | reject")
    p.add_argument("--evidence",        default=None, help="Evidence citation (path:line or short quote)")
    p.add_argument("--what",            required=False, help="One clear statement of the learning")
    p.add_argument("--why",             required=False, help="What failure this prevents")
    p.add_argument("--boundaries",      default=None, help="Where this does NOT apply")
    p.add_argument("--tags",            nargs="*", default=[], help="Optional tag list")
    p.add_argument("--applies-tasks",   nargs="*", default=[], dest="applies_tasks",
                   help="applies_when TASKS: fix review implement design scaffold test any")
    p.add_argument("--applies-globs",   nargs="*", default=[], dest="applies_globs",
                   help="applies_when GLOBS: file patterns that signal relevance (e.g. myhospital-be/**)")
    p.add_argument("--applies-keywords", nargs="*", default=[], dest="applies_keywords",
                   help="applies_when KEYWORDS: terms that signal relevance (used by learning_recall)")
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
