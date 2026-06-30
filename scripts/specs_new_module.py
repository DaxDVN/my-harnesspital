#!/usr/bin/env python3
"""Scaffold a 14-file spec folder for a new dev-specs module.

Replaces the manual `cp -r specs/dev-specs/_TEMPLATE/ specs/dev-specs/<module>/`
plus hand-edits. Copies the template, substitutes module/name/date/owner/prefix
placeholders, initializes 00-module-state.md (state: DISCOVERY, started) and
04-traceability.md skeleton, and prints next steps. Stdlib only.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS = ROOT / "specs" / "dev-specs"
TEMPLATE = SPECS / "_TEMPLATE"

# The 14 core numbered/living spec files that define a module folder.
EXPECTED_FILES = (
    "00-module-state.md",
    "00-session-handoff.md",
    "01-source-audit.md",
    "02-requirements.md",
    "03-ui.md",
    "04-traceability.md",
    "05-open-questions.md",
    "06-decision-log.md",
    "07-schema.md",
    "08-api.md",
    "09-test-cases.md",
    "10-plan.md",
    "11-review-checklist.md",
    "12-change-log.md",
)


class ToolError(RuntimeError):
    pass


def validate_module(module: str) -> str:
    value = (module or "").strip().lower()
    if not value:
        raise ToolError("Module slug is empty.")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", value):
        raise ToolError(
            f"Module slug {module!r} must be lowercase with hyphens, no spaces "
            f"(e.g. 'ipd-consultation')."
        )
    if value in {"_template", "_archive"}:
        raise ToolError(f"Reserved module slug {value!r}.")
    return value


def display_name(slug: str) -> str:
    return " ".join(word.capitalize() for word in slug.split("-"))


def prefix(slug: str) -> str:
    return slug.upper().replace("-", "_")


def substitute(text: str, mapping: dict[str, str]) -> str:
    """Replace only the <tokens> present in mapping; leave others untouched."""
    def repl(match: re.Match[str]) -> str:
        return mapping.get(match.group(0), match.group(0))

    return re.sub(r"<[A-Za-z][A-Za-z0-9 _-]*>", repl, text)


def build_mapping(slug: str, owner: str, description: str) -> dict[str, str]:
    mapping = {
        "<module-slug>": slug,
        "<module>": slug,
        "<Module Name>": display_name(slug),
        "<you>": owner,
        "<PREFIX>": prefix(slug),
    }
    if description:
        mapping["<DESCRIPTION>"] = description
    return mapping


def edit_frontmatter(text: str, updates: dict[str, str]) -> str:
    """Set/append frontmatter keys preserving order and comments.

    Updates an existing key in place; appends a new key at the end of the
    frontmatter block. Returns text unchanged if no frontmatter is present.
    """
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    header = text[3:end]
    body = text[end + 4:]
    out: list[str] = []
    seen: set[str] = set()
    for line in header.splitlines():
        if ":" in line and not line.strip().startswith("#"):
            key = line.split(":", 1)[0].strip()
            if key in updates:
                out.append(f"{key}: {updates[key]}")
                seen.add(key)
            else:
                out.append(line)
        else:
            out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}: {value}")
    return "---\n" + "\n".join(out) + "\n---" + body


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def scaffold(module: str, description: str, owner: str, *, dry_run: bool) -> Path:
    if not TEMPLATE.exists():
        raise ToolError(f"Template folder not found: {TEMPLATE}")
    target = SPECS / module
    if target.exists():
        raise ToolError(f"Module folder already exists: {rel(target)}")

    today = date.today().isoformat()
    mapping = build_mapping(module, owner, description)

    print(f"Plan: copy {rel(TEMPLATE)} -> {rel(target)}")
    for entry in sorted(TEMPLATE.rglob("*")):
        dst = target / entry.relative_to(TEMPLATE)
        if entry.is_dir():
            print(f"  dir  {rel(dst)}")
            if not dry_run:
                dst.mkdir(parents=True, exist_ok=True)
        else:
            print(f"  file {rel(dst)}")
            if not dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(entry, dst)

    if dry_run:
        print("\n[dry-run] no files written.")
        return target

    # Substitute placeholders + date in every copied .md.
    for md in sorted(target.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        text = text.replace("YYYY-MM-DD", today)
        text = substitute(text, mapping)
        md.write_text(text, encoding="utf-8")

    # 00-module-state.md: add state: DISCOVERY + started: <date> (additive over
    # the live template's phase/status keys).
    state_path = target / "00-module-state.md"
    text = state_path.read_text(encoding="utf-8")
    text = edit_frontmatter(text, {"state": "DISCOVERY", "started": today})
    state_path.write_text(text, encoding="utf-8")
    print(f"> init {rel(state_path)} (state: DISCOVERY, started: {today})")

    # 04-traceability.md: skeleton already provided by the template (PREFIX +
    # Module Name substituted above); no further clearing needed.
    print(f"> init {rel(target / '04-traceability.md')} (skeleton from template)")

    return target


def command_create(args: argparse.Namespace) -> int:
    module = validate_module(args.module)
    target = scaffold(module, args.description or "", args.owner, dry_run=args.dry_run)
    print()
    print("== Summary ==")
    if args.dry_run:
        print(f"[dry-run] would create module folder: {rel(target)}")
    else:
        count = sum(1 for p in target.rglob("*") if p.is_file())
        print(f"Created {count} entries under {rel(target)}")
    print()
    print("Next steps:")
    print(f"  1. Author specs/dev-specs/{module}/02-requirements.md")
    print(f"  2. Author specs/dev-specs/{module}/07-schema.md")
    print("  3. Run Session 1 (Requirement Discovery) "
          "— see specs/dev-specs/_TEMPLATE/README.md")
    return 0


def self_test() -> int:
    assert TEMPLATE.exists(), f"_TEMPLATE missing: {TEMPLATE}"
    missing = [name for name in EXPECTED_FILES if not (TEMPLATE / name).exists()]
    assert not missing, f"_TEMPLATE missing expected files: {missing}"
    assert validate_module("ipd-consultation") == "ipd-consultation"
    for bad in ("Bad Slug", "with space", "under_score"):
        try:
            validate_module(bad)
        except ToolError:
            pass
        else:
            raise AssertionError(f"validate_module should reject {bad!r}")
    try:
        validate_module("_template")
    except ToolError:
        pass
    else:
        raise AssertionError("validate_module should reject reserved slug")
    assert display_name("ipd-consultation") == "Ipd Consultation"
    assert prefix("ipd-consultation") == "IPD_CONSULTATION"
    out = substitute(
        "hi <module-slug> <field> <Module Name> <PREFIX>",
        build_mapping("ipd-consultation", "owner", ""),
    )
    assert out == "hi ipd-consultation <field> Ipd Consultation IPD_CONSULTATION", out
    # edit_frontmatter appends new keys, updates existing ones.
    fm = edit_frontmatter("---\nmodule: x\nstatus: not-started\n---\n# X\n",
                          {"state": "DISCOVERY", "status": "in-progress"})
    assert "state: DISCOVERY" in fm
    assert "status: in-progress" in fm
    assert "status: not-started" not in fm
    print("specs_new_module self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold a new dev-specs module folder from _TEMPLATE",
    )
    parser.add_argument("module", nargs="?", help="module slug (lowercase, hyphens, no spaces)")
    parser.add_argument("--description", help="one-line module description")
    parser.add_argument("--owner", default="owner",
                        help="owner name for 00-module-state.md (default: owner)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print plan without writing files")
    parser.add_argument("--self-test", action="store_true", help="run built-in self-test")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.module:
        parser.error("provide a module slug")
    try:
        return command_create(args)
    except ToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
