#!/usr/bin/env python3
"""main_brain_draft — distill a second-brain note into a LEAN main-brain entry draft.

`main_brain_promotion_candidates.py scan` reports provisional second-brain notes that
look ready for promotion. Promotion itself is owner-gated via the `/promote` skill
(the guard blocks direct writes to `main-brain/`). This script does the distillation
half: read the note, read `main-brain/knowledge.md` to mirror its lean format, and
emit a DRAFT entry (1–3 bullets) to stdout or a file OUTSIDE `main-brain/`. It NEVER
writes into `main-brain/` — that remains owner-gated.

Usage:
    python scripts/main_brain_draft.py <note-path> [--output <path>] [--dry-run]
    python scripts/main_brain_draft.py --self-test
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN_BRAIN = ROOT / "main-brain"
KNOWLEDGE = MAIN_BRAIN / "knowledge.md"
MAX_BULLET_CHARS = 220
MAX_BULLETS = 3


class MainBrainWriteError(RuntimeError):
    """Raised if an output path resolves under main-brain/ (guard-bounded)."""


def _read(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def _trim(text: str, limit: int = MAX_BULLET_CHARS) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _extract_bold_field(text: str, field: str) -> str | None:
    """Pull the text after a `**Field:**` marker, until the next blank line or bold field."""
    m = re.search(rf"\*\*{re.escape(field)}:\*\*\s*(.+?)(?:\n\n|\n\*\*|\Z)", text, re.DOTALL)
    if not m:
        return None
    return _trim(m.group(1))


def _h1(text: str) -> str | None:
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def distill(note_path: Path, knowledge_text: str | None) -> str:
    """Produce a lean `## <Title>` + 1-3 bullets draft from a second-brain note."""
    text = _read(note_path)
    if text is None:
        raise FileNotFoundError(f"note not readable: {note_path}")
    fm = parse_frontmatter(text)
    title = _h1(text) or fm.get("title") or fm.get("slug") or note_path.stem

    bullets: list[str] = []

    rule = _extract_bold_field(text, "Rule")
    if rule:
        bullets.append(rule)
    apply_ = _extract_bold_field(text, "Apply")
    if apply_:
        bullets.append(apply_)
    why = _extract_bold_field(text, "Why")
    if why:
        bullets.append(why)

    # fall back to other structured bold fields if the primary trio is thin
    if len(bullets) < 2:
        for field in ("Append-only", "Priority"):
            extra = _extract_bold_field(text, field)
            if extra and extra not in bullets:
                bullets.append(extra)
                if len(bullets) >= MAX_BULLETS:
                    break

    # last resort: first few markdown bullet lines
    if not bullets:
        for line in text.splitlines():
            if re.match(r"^\s*[-*]\s+", line) and "status:" not in line:
                bullets.append(_trim(re.sub(r"^\s*[-*]\s+", "", line)))
                if len(bullets) >= MAX_BULLETS:
                    break

    if not bullets:
        # final fallback: first non-frontmatter, non-heading prose line
        for line in text.splitlines():
            s = line.strip()
            if not s or s.startswith("---") or s.startswith("#") or ":" in s and s.split(":", 1)[0].islower():
                continue
            bullets.append(_trim(s))
            break

    bullets = bullets[:MAX_BULLETS]
    try:
        rel = note_path.relative_to(ROOT) if note_path.is_absolute() else note_path
    except ValueError:
        rel = note_path
    scope = fm.get("scope", "")
    scope_note = f" (scope: {scope})" if scope else ""

    lines = [f"## {title}{scope_note}", ""]
    for b in bullets:
        lines.append(f"- {b}")
    lines.append("")
    lines.append(
        f"<!-- DRAFT distilled from `{rel}` — review then `/promote` to write into "
        f"main-brain/knowledge.md (owner-gated). Do not write `main-brain/` directly. -->"
    )
    return "\n".join(lines) + "\n"


def assert_outside_main_brain(out: Path) -> None:
    """Refuse any --output that resolves under main-brain/ (the guard-bounded path)."""
    try:
        resolved = out.resolve()
        mb = MAIN_BRAIN.resolve()
        if resolved == mb or mb in resolved.parents:
            raise MainBrainWriteError(
                f"refused: --output {out} resolves under main-brain/ "
                f"(owner-gated; use /promote or pick a path outside main-brain/)."
            )
    except MainBrainWriteError:
        raise
    except Exception:
        # if resolution fails (e.g. parent missing), still do a lexical check
        s = str(out).replace("\\", "/")
        if s.startswith("main-brain/") or "/main-brain/" in s or s == "main-brain":
            raise MainBrainWriteError(
                f"refused: --output {out} appears to target main-brain/ (owner-gated)."
            )


def command_draft(note_path: Path, output: Path | None, dry_run: bool) -> int:
    knowledge = _read(KNOWLEDGE)
    if knowledge is None:
        print(f"main_brain_draft: format reference missing: {KNOWLEDGE}", file=sys.stderr)
        return 1
    if not note_path.exists():
        print(f"main_brain_draft: note not found: {note_path}", file=sys.stderr)
        return 1
    draft = distill(note_path, knowledge)

    if output is not None:
        assert_outside_main_brain(output)

    if dry_run:
        print("--- DRAFT (dry-run, nothing written) ---")
        print(draft, end="")
        print("--- end draft ---")
        print("\nReview draft, then /promote to write to main-brain/ (owner-gated).")
        return 0

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(draft, encoding="utf-8")
        print(f"draft written: {output}")
    else:
        print(draft, end="")
    print("\nReview draft, then /promote to write to main-brain/ (owner-gated).")
    return 0


def self_test() -> int:
    failures = 0

    def check(cond: bool, msg: str) -> None:
        nonlocal failures
        if not cond:
            failures += 1
            print(f"FAIL: {msg}")

    # 1. format reference present
    check(KNOWLEDGE.exists(), f"main-brain/knowledge.md missing at {KNOWLEDGE}")

    # 2. distill on a synthetic note → lean shape (## header + 1-3 bullets + DRAFT comment)
    synthetic = (
        "---\nslug: no-empty-done\nscope: workspace\nconfidence: high\n"
        "applies_when: fix,implement\ncreated: 2026-06-29\n---\n\n"
        "# Rule: never report done empty\n\n"
        "**Rule:** Don't say done when there's no data to render on the UI.\n\n"
        "**Why:** Owner saw empty dialogs and could not verify anything on 2026-06-25.\n\n"
        "**Apply:** Before reporting done, ask: is there data to render? If not, seed first.\n"
    )
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        note = Path(d) / "note.md"
        note.write_text(synthetic, encoding="utf-8")
        draft = distill(note, "# main-brain knowledge\n")
        check(draft.startswith("## "), "draft does not start with a ## header")
        check("<!-- DRAFT" in draft, "draft missing the DRAFT/owner-gated comment")
        bullet_lines = [l for l in draft.splitlines() if l.startswith("- ")]
        check(1 <= len(bullet_lines) <= MAX_BULLETS, f"draft has {len(bullet_lines)} bullets (expected 1-{MAX_BULLETS})")
        # lean: must NOT contain the frontmatter verbatim
        check("confidence: high" not in draft, "draft leaked frontmatter (not lean)")
        check("applies_when" not in draft, "draft leaked frontmatter field applies_when")
        # each bullet within length budget
        for b in bullet_lines:
            check(len(b) <= MAX_BULLET_CHARS + 3, f"bullet too long ({len(b)} chars): {b[:60]}...")

    # 3. main-brain write refusal
    for bad in (MAIN_BRAIN / "knowledge.md", MAIN_BRAIN / "x.md", Path("main-brain/foo.md")):
        try:
            assert_outside_main_brain(bad)
            check(False, f"main-brain guard did NOT refuse {bad}")
        except MainBrainWriteError:
            check(True, "")

    # 4. an outside path must NOT be refused
    try:
        assert_outside_main_brain(ROOT / "docs" / "harness" / "notes" / "draft.md")
        check(True, "")
    except MainBrainWriteError as e:
        check(False, f"guard wrongly refused an outside path: {e}")

    if failures:
        print(f"main_brain_draft self-test: {failures} FAILED")
        return 1
    print("main_brain_draft self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="main_brain_draft",
        description="Distill a second-brain note into a lean main-brain entry DRAFT (never writes main-brain/).",
    )
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the draft, write nothing")
    ap.add_argument("--output", type=Path, default=None,
                    help="write the draft to this path (must be OUTSIDE main-brain/); default: stdout")
    ap.add_argument("note_path", nargs="?", type=Path, help="second-brain note to distill")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.note_path is None:
        ap.print_help()
        return 2
    return command_draft(args.note_path, args.output, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
