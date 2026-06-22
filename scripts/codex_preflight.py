#!/usr/bin/env python3
"""Codex-oriented wrapper around harness_preflight.

Codex cannot be fully prompt-hooked from this repo the way Claude Code can, so this script is the standard
manual/cooperative entrypoint: run it at the start of a Codex task, show the card, then wait for owner
confirmation before edits/workflows.

Usage:
    python scripts/codex_preflight.py "<user prompt>"
    python scripts/codex_preflight.py --json "<user prompt>"
    python scripts/codex_preflight.py --self-test
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import harness_preflight  # noqa: E402
from harness_preflight import build_preflight, render_card  # noqa: E402


def render_codex_card(prompt: str) -> str:
    preflight = build_preflight(prompt)
    prefix = [
        "Codex Preflight",
        "",
        "Policy: show this route to the owner and wait for confirmation before apply_patch, workflow execution, subagents, browser/E2E, or external executors.",
        "",
    ]
    return "\n".join(prefix) + render_card(preflight)


def self_test() -> int:
    original_loader = harness_preflight._load_worktrees

    def fake_worktrees() -> list[dict[str, str]]:
        return [{
            "slug": "fix-bug-noi-tru",
            "slot": "2",
            "fe_url": "http://localhost:3002",
            "be_url": "http://localhost:5002",
            "sql": "localhost,1435/MyHospital",
            "status": "OK",
        }]

    harness_preflight._load_worktrees = fake_worktrees
    try:
        card = render_codex_card("sửa bug sheet nội trú trong worktree fix-bug-noi-tru")
        assert "Codex Preflight" in card
        assert "mh-fix" in card
        assert "fix-bug-noi-tru" in card
    finally:
        harness_preflight._load_worktrees = original_loader
    print("codex_preflight self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Codex preflight confirmation wrapper")
    parser.add_argument("prompt", nargs="*")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    prompt = " ".join(args.prompt).strip()
    if not prompt:
        parser.error("provide a prompt, or --self-test")
    if args.json:
        print(json.dumps(build_preflight(prompt), indent=2, ensure_ascii=False))
    else:
        print(render_codex_card(prompt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
