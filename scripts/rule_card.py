#!/usr/bin/env python3
"""Select the smallest FE/BE rule cards for a task.

The full `engine/rules/frontend.md` and `engine/rules/backend.md` remain canonical fallback docs, but daily
work should start from compact quick/topic cards to avoid paying the full token cost on every task.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


TOPICS = {
    "fe": {
        "quick": "engine/rules/frontend/quick.md",
        "fallback": "engine/rules/frontend.md",
        "topics": [
            ("forms", "engine/rules/frontend/forms.md", {"form", "forms", "sheet", "modal", "input", "field", "zod", "rhf", "validation"}),
            ("data", "engine/rules/frontend/data.md", {"query", "mutation", "react-query", "tanstack", "adapter", "masterdata", "master-data", "cache", "invalidate"}),
            ("contracts", "engine/rules/frontend/contracts.md", {"dto", "api", "contract", "generated", "client", "servicestack", "permission"}),
            ("ui-reuse", "engine/rules/frontend/ui-reuse.md", {"ui", "component", "reuse", "table", "grid", "layout", "label", "i18n", "button"}),
        ],
    },
    "be": {
        "quick": "engine/rules/backend/quick.md",
        "fallback": "engine/rules/backend.md",
        "topics": [
            ("service-data", "engine/rules/backend/service-data.md", {"service", "query", "data", "tenant", "hospital", "scope", "n+1", "batch", "soft-delete"}),
            ("contracts-auth", "engine/rules/backend/contracts-auth.md", {"api", "dto", "contract", "auth", "permission", "requireauth", "errorcodes", "businessexception"}),
            ("migrations", "engine/rules/backend/migrations.md", {"migration", "schema", "db", "sql", "seed", "backfill", "ef", "dto"}),
            ("validation-tests", "engine/rules/backend/validation-tests.md", {"test", "build", "validation", "verify", "suite", "sql"}),
        ],
    },
}


def _norm(text: str) -> set[str]:
    lowered = text.lower()
    return set(re.findall(r"[a-z0-9][a-z0-9+-]*", lowered))


def select_cards(package: str, context: str = "", *, max_topics: int = 3) -> list[str]:
    key = package.lower()
    if key in {"frontend", "ui"}:
        key = "fe"
    elif key in {"backend", "api"}:
        key = "be"
    if key not in TOPICS:
        raise ValueError("package must be fe|frontend|be|backend")

    spec = TOPICS[key]
    words = _norm(context)
    scored: list[tuple[int, str, str]] = []
    for name, path, aliases in spec["topics"]:
        hits = words.intersection(aliases)
        if hits:
            scored.append((len(hits), name, path))
    scored.sort(key=lambda item: (-item[0], item[1]))

    selected = [spec["quick"]]
    selected.extend(path for _, _, path in scored[:max_topics])
    return selected


def render(package: str, context: str = "") -> str:
    key = package.lower()
    if key in {"frontend", "ui"}:
        key = "fe"
    elif key in {"backend", "api"}:
        key = "be"
    if key not in TOPICS:
        raise ValueError("package must be fe|frontend|be|backend")
    cards = select_cards(key, context)
    fallback = TOPICS[key]["fallback"]
    lines = [
        f"Rule cards for {key.upper()}",
        "",
        "Open these first:",
    ]
    lines.extend(f"- {card}" for card in cards)
    lines.extend([
        "",
        f"Fallback: open `{fallback}` only if the selected cards do not cover the task, the task is high-risk, or local evidence conflicts.",
    ])
    return "\n".join(lines)


def self_test() -> int:
    fe = select_cards("fe", "fix form sheet dto react-query reuse")
    assert fe[0] == "engine/rules/frontend/quick.md"
    assert "engine/rules/frontend/forms.md" in fe
    assert "engine/rules/frontend/data.md" in fe
    be = select_cards("backend", "fix service tenant scope migration sql")
    assert be[0] == "engine/rules/backend/quick.md"
    assert "engine/rules/backend/service-data.md" in be
    assert "engine/rules/backend/migrations.md" in be
    print("rule_card self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Select compact FE/BE harness rule cards")
    parser.add_argument("package", nargs="?", help="fe|frontend|be|backend")
    parser.add_argument("context", nargs="*", help="task text")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.package:
        parser.error("provide package: fe|frontend|be|backend")
    context = " ".join(args.context)
    cards = select_cards(args.package, context)
    if args.json:
        import json
        print(json.dumps({"package": args.package, "cards": cards}, indent=2, ensure_ascii=False))
    else:
        print(render(args.package, context))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
