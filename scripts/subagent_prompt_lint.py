#!/usr/bin/env python3
"""subagent_prompt_lint.py — gate worker / coding-tool prompts against the Anthropic
prompt-engineering guideline (docs/anthropic-guideline/), as distilled in
engine/prompts/subagent-prompt-template.md.

Purpose
-------
The orchestrator (Opus) hand-authors the prompt it sends to a Claude SUBAGENT (Task
tool) or to an external coding tool (opencode / grok / agy via agent_exec / oc_worker).
A passive template doc did NOT make those prompts conform (the live rooms-refactor
prompt scored ~65%). This linter is the deterministic, machine-checkable bar; the
PreToolUse hook engine/hooks/subagent_prompt_guard.py calls it and BLOCKS (exit 2) a
sub-standard worker prompt before dispatch, telling Opus exactly what to add.

It is regex-only (no model call), fast, and importable as `lint_prompt(...)`.

Profiles
--------
worker   — mutating / code-generating dispatch. Full guideline bar (score >= 0.80,
           plus GOAL/INTENT and write-allowlist are CRITICAL = always required,
           plus a destructive action must carry a stop/verify gate).
readonly — search / review / explore dispatch. Light bar, advisory only (never blocks).

Channels
--------
task — Claude subagent via the Task tool. NO PREAMBLE is auto-injected, so the FULL
       checklist must be present in the authored prompt.
oc   — opencode / grok / agy via agent_exec / oc_worker. oc_worker.PREAMBLE is
       auto-prepended on every dispatch, so the PREAMBLE-covered checks
       (subagent-identity/autonomy, ponytail, grounding, output-TLDR) are credited
       automatically; the author must still supply intent / allowlist / xml / validation.

Guideline sources (docs/anthropic-guideline/):
  build-with-claude-prompt-engineering-claude-prompting-best-practices.md
    §Add context, §Structure prompts with XML tags, §Long context prompting,
    §Tool usage, §Balancing autonomy and safety, §Overeagerness, §Minimizing hallucinations
  build-with-claude-prompt-engineering-prompting-claude-opus-4-8.md
    §More literal instruction following, §Code review harnesses
  build-with-claude-prompt-engineering-prompting-claude-fable-5.md
    §Give the reason, §State the boundaries, §Strong instruction following, §Ground progress claims
  test-and-evaluate-strengthen-guardrails-reduce-hallucinations.md

Run: python scripts/subagent_prompt_lint.py --self-test
     python scripts/subagent_prompt_lint.py --prompt-file p.md --channel oc [--read-only] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

THRESHOLD_WORKER = 0.80

# Agents that are STRUCTURALLY read-only (their own system prompt forbids edits).
# NOTE: general-purpose / claude are intentionally NOT here — they can mutate, so
# their dispatch is classified by the mutating-verb heuristic instead.
READONLY_AGENTS = {
    "explore", "plan", "mh-reviewer", "mh-rca", "mh-rule-auditor", "distiller",
    "code-explorer", "code-reviewer", "feature-dev:code-explorer",
    "feature-dev:code-reviewer", "statusline-setup", "claude-code-guide",
}

# Verbs that mark a mutating / code-generating dispatch on the Task channel when the
# subagent_type is ambiguous (e.g. general-purpose).
_MUTATING = (
    r"\b(implement|fix the|fix bug|refactor|rewrite|scaffold|migrate|patch the|"
    r"convert|apply (the )?fix|remove (the|a|that|this)|delete |drop (table|column))\b"
    r"|add\b[\s\S]{0,25}\b(column|field|button|endpoint|page|sheet|component|service|route)\b"
    r"|create\b[\s\S]{0,25}\b(component|page|file|endpoint|service|migration|sheet)\b"
)


def _has(text: str, *patterns: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE | re.DOTALL) for p in patterns)


# ---- Check predicates (each: is this guideline signal present in the prompt?) ----
def c_intent(p: str) -> bool:
    return _has(
        p, r"\bgoal\b", r"\bintent\b", r"\bobjective\b", r"\bwhy\b", r"working on",
        r"\bso that\b", r"they need", r"owner (needs|wants)", r"mục tiêu", r"lý do",
        r"<(intent|goal|why|context)\b", r"i'?m (working|building|improving|refactor)",
        r"the reason", r"this (is for|enables|matters)",
    )


def c_allowlist(p: str) -> bool:
    # POSITIVE write boundary — a generic "don't edit generated files" does NOT count.
    return _has(
        p, r"allow[\s_-]?list", r"files? you may (write|edit|touch|modify|change)",
        r"\bmay write\b", r"only (edit|modify|write|change|touch)\b",
        r"writable (files|paths|dirs)", r"\bscope:\s", r"scope_is_literal",
        r"forbidden_files", r"do[_\s]?not[_\s]?touch", r"<(scope|allowlist)\b",
    )


def c_xml(p: str) -> bool:
    return _has(
        p, r"<[a-zA-Z][\w-]*>[\s\S]*?</[a-zA-Z][\w-]*>",
        r"<(document|documents|source|task|scope|context|instructions|input|"
        r"allowlist|intent|goal|output|autonomy|ponytail|boundaries)\b",
    )


def c_output(p: str) -> bool:
    return _has(
        p, r"return[_\s]?format", r"report back", r"\bTLDR\b", r"respond with",
        r"your (output|deliverable|report)", r"compact (blob|summary|report)",
        r"#+\s*(report|output|deliverable)", r"output contract", r"lead with the outcome",
    )


def c_grounding(p: str) -> bool:
    return _has(
        p, r"do ?n'?o?t invent", r"\binvestigate\b", r"\bdiscover\b",
        r"read [\w\s,./'-]{0,40}before", r"\bground(ed|s|ing)?\b", r"\bcite\b",
        r"\bevidence\b", r"\bquote", r"do ?n'?o?t speculate", r"reuse evidence", r"\bverify\b",
    )


def c_ponytail(p: str) -> bool:
    return _has(
        p, r"\bponytail\b", r"minimal[\s-]?correct", r"\breuse\b", r"smallest",
        r"over[\s-]?(engineer|build)", r"do ?n'?o?t add\b", r"do ?n'?o?t rewrite",
        r"minimal (diff|change)",
    )


def c_validation(p: str) -> bool:
    return _has(
        p, r"\bvalidat", r"\btypecheck\b", r"\btsc\b", r"dotnet build", r"npm run",
        r"run [\s\S]{0,20}test", r"\btests?\b", r"scanner", r"mh-scan", r"\blint\b",
    )


def c_autonomy(p: str) -> bool:
    return _has(
        p, r"\bsubagent\b", r"do ?n'?o?t ask", r"not the main", r"needs[\s-]owner[\s-]decision",
        r"\bSTOP\b", r"proceed autonomously", r"no human", r"operating autonomously",
    )


def has_destructive(p: str) -> bool:
    return _has(
        p, r"\bdelete\b", r"\bremove\b", r"\bdrop (table|column|database)\b",
        r"\brm -[rf]", r"force[\s-]?push", r"reset --hard", r"--no-verify",
        r"\bdiscard\b", r"\bpurge\b",
    )


def has_gate(p: str) -> bool:
    return _has(
        p, r"verify [\s\S]{0,60}(first|before)", r"usage search", r"report (it|back|only|the)",
        r"do ?n'?o?t (delete|remove|drop)", r"\bSTOP\b", r"\bconfirm\b",
        r"owner (approve|approval|decision|confirm)",
        r"check [\s\S]{0,40}(depend|referenc|usage|nothing else)", r"needs[\s-]owner",
        r"nothing else depends",
    )


# key, predicate, preamble_covered, label, guideline cite, fix hint
WORKER_CHECKS = [
    ("intent", c_intent, False, "GOAL/INTENT — the why",
     "best-practices §Add context; fable-5 §Give the reason",
     "Open with the reason: \"I'm working on X for <who>; they need <what the output enables>.\""),
    ("allowlist", c_allowlist, False, "write-allowlist / scope boundary",
     "fable-5 §State the boundaries; subagent-prompt-template §3",
     "Add an explicit allowlist: <exact files/dirs the worker may write> + do_not_touch:"),
    ("xml_structure", c_xml, False, "XML-tagged structure",
     "best-practices §Structure prompts with XML tags / §Long context",
     "Wrap context/scope/task in tags, e.g. <documents>/<scope>/<task>...</task>"),
    ("output_contract", c_output, True, "explicit output contract",
     "fable-5 §Strong instruction following; template §6",
     "Specify return_format / 'Report back' and tell it to lead with the TLDR outcome"),
    ("grounding", c_grounding, True, "anti-hallucination grounding",
     "best-practices §Minimizing hallucinations; reduce-hallucinations",
     "Add: investigate/read before acting, don't invent paths, cite file:line evidence"),
    ("ponytail", c_ponytail, True, "minimal-diff / reuse",
     "best-practices §Overeagerness; ponytail rule",
     "Add: reuse existing pattern first, smallest correct diff, don't over-engineer"),
    ("validation", c_validation, False, "validation commands",
     "subagent-prompt-template DoD; quality-gates",
     "Name the exact validation to run (typecheck/build/scanner) and report real output"),
    ("autonomy_identity", c_autonomy, True, "subagent identity + no-ask autonomy",
     "fable-5 §Rare cases of early stopping; template §0/§4",
     "Mark it a SUBAGENT, no human to ask; STOP + NEEDS-OWNER-DECISION on real ambiguity"),
]
_CRITICAL = {"intent", "allowlist"}

READONLY_CHECKS = [
    ("has_task", lambda p: bool(p.strip()) and len(p.strip()) > 40),
    ("grounding", c_grounding),
    ("output", c_output),
]


def classify(prompt: str, channel: str, read_only: bool, subagent_type: str | None) -> str:
    st = (subagent_type or "").lower().strip()
    if read_only:
        return "readonly"
    if st == "mh-implementer":
        return "worker"
    if st in READONLY_AGENTS:
        return "readonly"
    if channel == "oc":
        # agent_exec / oc_worker default to a coding worker unless --read-only.
        return "worker"
    # task channel, ambiguous agent: worker only if the prompt asks for a mutation.
    if re.search(_MUTATING, prompt, re.IGNORECASE):
        return "worker"
    return "readonly"


def lint_prompt(prompt: str, channel: str = "task", read_only: bool = False,
                subagent_type: str | None = None) -> dict:
    """Lint a worker/coding prompt. Returns a result dict:
    {profile, channel, score, threshold, passed, hard_fail, present:[...], missing:[{...}]}."""
    p = prompt or ""
    profile = classify(p, channel, read_only, subagent_type)

    if profile == "readonly":
        present = [k for k, fn in READONLY_CHECKS if fn(p)]
        score = len(present) / len(READONLY_CHECKS)
        return {
            "profile": "readonly", "channel": channel, "score": round(score, 3),
            "threshold": 0.5, "passed": score >= 0.5, "hard_fail": False,
            "present": present, "missing": [],
            "note": "read-only dispatch — advisory only, never hard-blocked",
        }

    present: list[str] = []
    missing: list[dict] = []
    critical_missing = False
    for key, fn, preamble_cov, label, cite, fix in WORKER_CHECKS:
        credited = fn(p) or (channel == "oc" and preamble_cov)
        if credited:
            present.append(key)
        else:
            missing.append({"key": key, "label": label, "cite": cite, "fix": fix,
                            "critical": key in _CRITICAL})
            if key in _CRITICAL:
                critical_missing = True

    score = len(present) / len(WORKER_CHECKS)

    hard_fail = False
    if has_destructive(p) and not has_gate(p):
        hard_fail = True
        missing.append({
            "key": "destructive_gate",
            "label": "destructive action (delete/remove/drop) without a stop/verify gate",
            "cite": "best-practices §Balancing autonomy and safety",
            "fix": "A subagent can't confirm — require report-only OR a verify-usage-first gate "
                   "before any delete/remove/drop",
            "critical": True,
        })

    passed = (score >= THRESHOLD_WORKER) and not critical_missing and not hard_fail
    return {
        "profile": "worker", "channel": channel, "score": round(score, 3),
        "threshold": THRESHOLD_WORKER, "passed": passed, "hard_fail": hard_fail,
        "present": present, "missing": missing,
    }


def format_block_message(result: dict) -> str:
    """Render the exit-2 stderr message the orchestrator (Opus) reads on a block."""
    lines = [
        f"subagent-prompt-substandard (profile={result['profile']} channel={result['channel']} "
        f"score={result['score']} < {result['threshold']}"
        + (", CRITICAL field missing" if any(m.get("critical") for m in result["missing"]) else "")
        + (", destructive-without-gate" if result.get("hard_fail") else "") + ")",
        "Missing vs Anthropic guideline (docs/anthropic-guideline/ + engine/prompts/subagent-prompt-template.md):",
    ]
    for m in result["missing"]:
        tag = " [CRITICAL]" if m.get("critical") else ""
        lines.append(f"  - {m['label']}{tag}  [{m['cite']}]")
        lines.append(f"      fix: {m['fix']}")
    lines.append("Re-author the worker prompt via engine/prompts/subagent-prompt-template.md "
                 "(ZONE A context-by-reference + XML tags, ZONE B intent→task→scope→autonomy→ponytail→output), "
                 "then re-dispatch.")
    lines.append("Self-check: python scripts/subagent_prompt_lint.py --prompt-file <file> "
                 f"--channel {result['channel']}")
    return "\n".join(lines)


# ---- Self-test ----------------------------------------------------------------
_ROOMS = """# TASK: Refactor bed-management Rooms (FE-first, BE only if contract needs it)
You work inside the worktree worktrees/ipd-improve-v5. FE app is in fe/, BE in be/.
Use CodeGraph first then ripgrep to DISCOVER the existing code. Do NOT invent paths.
## Problem
1. /rooms/new is a standalone page. It MUST instead be a Sheet opened from /rooms.
   After the change, remove the dead standalone page/route if nothing else depends on it
   (verify with a usage search first).
2. REMOVE that add-bed column from the rooms list.
3. ADD more room-info columns from fields the API already returns.
## Hard rules
- Minimal-correct diff (Ponytail): reuse the existing add/edit form logic; do not rewrite it.
- Do NOT hand-edit generated FE DTO/client or Constants.ts, nor BE EF migrations.
## Validation
- FE typecheck: tsc -p tsconfig.app.json. Any available FE scanner / mh-scan.
## Report back (compact)
- Files changed. Reuse evidence (file:line). Validation run + result. Residual risk.
"""

_GOOD = """You are a SUBAGENT dispatched by the PM orchestrator; no human is watching, do not ask.
On genuine ambiguity, STOP and emit a NEEDS-OWNER-DECISION finding. Proceed autonomously otherwise.

<intent>
I'm working on the inpatient Rooms screen for ward nurses. They need to add/edit a room
without leaving the list and to see the room's real attributes at a glance.
</intent>

<documents>
  <document index="1"><source>rule_card outputs (fe + be)</source></document>
  <document index="2"><source>specs/bed-management/03-ui.md#rooms</source></document>
</documents>

<scope>
allowlist: worktrees/ipd-improve-v5/fe/src/modules/bed-management/rooms/**
do_not_touch: generated DTO/client, Constants.ts, BE EF migrations, other modules
</scope>

## Task
Convert the rooms add page to a Sheet. Investigate the existing sibling Sheet pattern and
reuse it; do not invent paths. Quote the lines you copy as reuse evidence.

Ponytail: reuse first, smallest correct diff, do not over-engineer.

## Validation
Run tsc -p tsconfig.app.json and the FE scanner; report real output, no truncation.

## return_format
Lead with the TLDR outcome, then files changed, reuse evidence (file:line), validation result.
"""

_EXPLORE = """Search the FE codebase for every module that renders a list page plus an add/edit
Sheet. Report each as file:line with a one-line note on the pattern it uses. Investigate
before answering; do not invent paths. Return a compact list."""

# A destructive worker prompt with NO gate language anywhere -> must hard-fail.
_DESTR = """<intent>cleaning up dead code for the inpatient team</intent>
<scope>allowlist: fe/src/legacy</scope>
Delete the legacy rooms folder entirely and rip out its imports."""


def _self_test() -> int:
    checks: list[tuple[bool, str]] = []

    def ck(cond: bool, msg: str) -> None:
        checks.append((bool(cond), msg))
        print(f"  {'PASS' if cond else 'FAIL'}: {msg}")

    # Rooms prompt (the real ~65% prompt) must FAIL on both channels.
    r_oc = lint_prompt(_ROOMS, channel="oc")
    ck(r_oc["profile"] == "worker", f"rooms/oc classified worker (got {r_oc['profile']})")
    ck(not r_oc["passed"], f"rooms/oc FAILS the bar (score={r_oc['score']})")
    miss = {m["key"] for m in r_oc["missing"]}
    ck("intent" in miss, "rooms/oc flags missing intent")
    ck("allowlist" in miss, "rooms/oc flags missing allowlist")
    ck("xml_structure" in miss, "rooms/oc flags missing xml")
    ck("validation" not in miss, "rooms/oc credits validation (tsc/scanner present)")
    ck(not r_oc["hard_fail"], "rooms/oc destructive 'remove' has a usage-search gate -> not hard-fail")

    r_task = lint_prompt(_ROOMS, channel="task")
    ck(not r_task["passed"], f"rooms/task FAILS the bar (score={r_task['score']})")

    # Canonical template-shaped prompt must PASS on both channels.
    g_oc = lint_prompt(_GOOD, channel="oc")
    ck(g_oc["passed"], f"good/oc PASSES (score={g_oc['score']}, missing={[m['key'] for m in g_oc['missing']]})")
    g_task = lint_prompt(_GOOD, channel="task")
    ck(g_task["passed"], f"good/task PASSES (score={g_task['score']}, missing={[m['key'] for m in g_task['missing']]})")

    # Read-only Explore prompt must NOT be hard-blocked.
    e = lint_prompt(_EXPLORE, channel="task", subagent_type="Explore")
    ck(e["profile"] == "readonly", f"explore classified readonly (got {e['profile']})")
    ck(e["passed"], "explore not blocked (advisory only)")

    # Destructive without any gate language -> hard fail.
    d = lint_prompt(_DESTR, channel="oc")
    ck(d["hard_fail"], "destructive 'delete' with no gate -> hard_fail")
    ck(not d["passed"], "destructive-without-gate -> not passed")

    # mh-implementer is always worker even with a terse prompt.
    m = lint_prompt("Edit the file and make it work.", channel="task", subagent_type="mh-implementer")
    ck(m["profile"] == "worker", "mh-implementer forced to worker profile")
    ck(not m["passed"], "terse mh-implementer prompt fails the bar")

    failed = [m for ok, m in checks if not ok]
    print(f"\nsubagent_prompt_lint self-test: {'OK' if not failed else 'FAIL'} "
          f"({len(checks)} assertions, {len(failed)} failed)")
    return 0 if not failed else 1


# ---- CLI ----------------------------------------------------------------------
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Lint a worker/coding prompt against the Anthropic guideline.")
    ap.add_argument("--prompt", default="", help="inline prompt text (or --prompt-file)")
    ap.add_argument("--prompt-file", help="path to a file containing the prompt")
    ap.add_argument("--channel", choices=["task", "oc"], default="task",
                    help="task = Claude subagent (no PREAMBLE); oc = opencode/grok/agy (PREAMBLE auto-added)")
    ap.add_argument("--read-only", action="store_true", help="dispatch is read-only -> readonly profile")
    ap.add_argument("--subagent-type", default=None, help="Task subagent_type, for profile classification")
    ap.add_argument("--json", action="store_true", help="emit the full result as JSON")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    text = args.prompt
    if args.prompt_file:
        try:
            text = Path(args.prompt_file).read_text("utf-8")
        except OSError as e:
            print(f"cannot read prompt file: {e}", file=sys.stderr)
            return 2
    if not (text or "").strip():
        print("empty prompt (need --prompt or --prompt-file)", file=sys.stderr)
        return 2

    result = lint_prompt(text, channel=args.channel, read_only=args.read_only,
                         subagent_type=args.subagent_type)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"profile={result['profile']} channel={result['channel']} "
              f"score={result['score']} passed={result['passed']}")
        if not result["passed"]:
            print(format_block_message(result), file=sys.stderr)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
