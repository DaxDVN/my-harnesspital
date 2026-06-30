#!/usr/bin/env python3
"""oc_bakeoff.py — controlled per-role bake-off harness (integration plan Phase 7).

Validate a non-Anthropic model BEFORE the harness trusts it (the lifecycle gate):
compare the cheap glm-5.2 `audit` role against an Opus baseline on a REAL changeset,
measuring unique true-positives each finds + the false-positive rate, so the owner can
ratify (or not) the cross-model lane with EVIDENCE instead of vendor benchmarks.

A plain script CANNOT spawn an Opus agent, so this is a HALF-AUTOMATED ledger: it drives
the glm-5.2 side via scripts/oc_worker.py, then writes a structured markdown ledger with a
placeholder + instructions for the owner to run `deep-review` (Anthropic D1 + Opus
adjudication) on the SAME scope and fill in the comparison/metrics. FP adjudication is
owed to Opus 4.8 xhigh (the trusted decider) — cheap models propose, the strong model
decides.

Safety: the DEFAULT action is a dry plan; NOTHING calls opencode (no dollar-capped Go
quota burn) unless `--run` is explicitly passed to the `run` subcommand. Fail-open.

Usage:
  python scripts/oc_bakeoff.py plan --scope <dir> --files f1,f2,...
  python scripts/oc_bakeoff.py run  --scope <dir> --files f1,f2,... \
      --out docs/harness/evals/oc-bakeoff-<label>.md --run
  python scripts/oc_bakeoff.py --self-test
"""
from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OC_WORKER = ROOT / "scripts" / "oc_worker.py"

AUDIT_PROMPT = (
    "Audit ONLY these files for BLOCK/HIGH bugs; one line each: "
    "SEVERITY | file:line | title | evidence. Files: {files}"
)
SECTION_KEYS = ("## (a)", "## (b)", "## (c)", "## (d)", "## (e)")


def parse_files(files: str) -> list[str]:
    return [f.strip() for f in (files or "").split(",") if f.strip()]


def build_audit_prompt(files: list[str]) -> str:
    return AUDIT_PROMPT.format(files=", ".join(files) or "(none)")


def resolve_out(args: argparse.Namespace) -> tuple[str, str]:
    """Return (out_path, label). --out wins; else derive from --label or a timestamp."""
    if args.out:
        label = args.label or Path(args.out).stem.replace("oc-bakeoff-", "")
        return args.out, label
    label = args.label or datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"docs/harness/evals/oc-bakeoff-{label}.md", label


def glm_artifact_for(out: str) -> str:
    return str(Path(out).with_suffix("")) + ".glm-findings.md"


def oc_worker_cmd(scope: str, prompt: str, out_path: str) -> list[str]:
    """The exact glm-5.2 (role=audit, read-only) command `run --run` would invoke."""
    return [sys.executable, str(OC_WORKER), "--role", "audit",
            "--scope", scope, "--out", out_path, "--prompt", prompt]


def plan_lines(scope: str, files: list[str], out: str, prompt: str) -> list[str]:
    cmd = oc_worker_cmd(scope, "<prompt:%d chars>" % len(prompt), glm_artifact_for(out))
    return [
        "oc_bakeoff DRY PLAN (no opencode call made; pass --run to execute)",
        f"  scope            : {scope}",
        f"  files            : {', '.join(files) or '(none)'}",
        f"  ledger out       : {out}",
        f"  glm-5.2 artifact : {glm_artifact_for(out)}",
        "  would run (glm-5.2 audit, read-only):",
        "    " + " ".join(cmd),
        f"  audit prompt     : {prompt}",
        "  opus baseline    : owner runs `deep-review` (Anthropic D1 + Opus adjudication)",
        "                     on the SAME scope, then fills the ledger comparison/metrics.",
        "  WARNING: --run burns the dollar-capped Go quota. Default stays dry on purpose.",
    ]


def ledger_template(scope: str, files: list[str], label: str,
                    blob: dict[str, Any], glm_artifact: str, glm_findings: str) -> str:
    findings = glm_findings.strip() or (
        "(no artifact captured — oc_worker blob: " + json.dumps(blob)[:300] + ")"
    )
    return "\n".join([
        f"# OpenCode bake-off ledger — {label}",
        "",
        f"- generated: {datetime.now().isoformat(timespec='seconds')}",
        f"- scope: {scope}",
        f"- files: {', '.join(files) or '(none)'}",
        f"- glm-5.2 run ok: {bool(blob.get('ok'))}  artifact: {glm_artifact}",
        f"- glm-5.2 summary: {blob.get('summary', '') or '(none)'}",
        "",
        "## (a) glm-5.2 findings (role=audit, cheap cross-model lane)",
        "",
        "```",
        findings,
        "```",
        "",
        "## (b) Opus baseline findings (PLACEHOLDER — owner action)",
        "",
        "Run `deep-review` (Anthropic D1 partition + Opus adjudication) on the SAME scope/files,",
        "then paste its findings here OR point to the findings file:",
        "",
        "    findings_file: <docs/audit/... or deep-review run path>",
        "",
        "## (c) Comparison (one row per distinct finding; merge duplicates across models)",
        "",
        "| finding | found-by (glm/opus/both) | true-positive? (adjudicate) | notes |",
        "|---|---|---|---|",
        "| <paste finding> | glm \\| opus \\| both | yes \\| no \\| ? | |",
        "",
        "## (d) Metrics & verdict (fill after adjudication)",
        "",
        "- glm-5.2 unique true-positives: <fill>",
        "- Opus unique true-positives: <fill>",
        "- shared true-positives (both found): <fill>",
        "- glm-5.2 false-positive rate: <fill>  (glm FP / total glm findings)",
        "- VERDICT — ratify the cross-model `audit` lane (glm-5.2)? yes / no",
        "- rationale: <fill>",
        "",
        "## (e) Adjudication note (who decides true-vs-false)",
        "",
        "> FP/TP adjudication MUST be done by Opus 4.8 xhigh (role=adjudicate / final_review in",
        "> scripts/tier_policy.json) — the trusted decider. Cheap models propose candidates; the",
        "> strong model decides. Do NOT let glm-5.2 grade its own findings.",
        "",
    ])


def _read(path: str) -> str:
    try:
        return Path(path).read_text("utf-8")
    except OSError:
        return ""


def cmd_run(args: argparse.Namespace) -> int:
    scope = args.scope
    files = parse_files(args.files)
    out, label = resolve_out(args)
    prompt = build_audit_prompt(files)

    if not args.run:  # SAFE DEFAULT: refuse to call oc_worker; print the plan instead.
        print("\n".join(plan_lines(scope, files, out, prompt)))
        return 0
    if not files:
        print("oc_bakeoff: no --files given; nothing to audit", file=sys.stderr)
        return 2

    glm_artifact = glm_artifact_for(out)
    cmd = oc_worker_cmd(scope, prompt, glm_artifact)
    blob: dict[str, Any] = {}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
        tail = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
        try:
            blob = json.loads(tail[-1]) if tail else {}
        except Exception:
            blob = {"ok": False, "error": "could not parse oc_worker blob",
                    "stdout_tail": (proc.stdout or "")[-300:]}
    except FileNotFoundError:
        blob = {"ok": False, "error": "python/oc_worker not found"}
    except subprocess.TimeoutExpired:
        blob = {"ok": False, "error": f"timeout after {args.timeout}s"}

    ledger = ledger_template(scope, files, label, blob, glm_artifact, _read(glm_artifact))
    try:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(ledger, "utf-8")
    except OSError as e:
        print(json.dumps({"ok": False, "error": f"cannot write ledger: {e}", "out": out}))
        return 1
    print(json.dumps({"ok": bool(blob.get("ok")), "out": out, "glm_artifact": glm_artifact,
                      "glm_summary": blob.get("summary", ""), "scope": scope, "files": files}))
    return 0


def self_test() -> int:
    assert parse_files(" a.py, b.py ,, c.py") == ["a.py", "b.py", "c.py"]
    prompt = build_audit_prompt(["x.py", "y.py"])
    assert "BLOCK/HIGH" in prompt and "x.py" in prompt and "y.py" in prompt, prompt

    cmd = oc_worker_cmd("worktrees/x/be", prompt, "out.md")
    assert "--role" in cmd and "audit" in cmd, cmd
    assert "--out" in cmd and "--scope" in cmd and "--prompt" in cmd, cmd

    ledger = ledger_template("scope/x", ["a.py"], "demo", {"ok": True, "summary": "2 bugs"},
                             "g.md", "BLOCK | a.py:10 | bug | evidence")
    for key in SECTION_KEYS:
        assert key in ledger, f"ledger missing section {key}"
    assert "deep-review" in ledger and "Opus 4.8 xhigh" in ledger, "ledger missing owner/adjudicate cues"

    # `run` WITHOUT --run must refuse to call oc_worker (prints the plan instead).
    orig_run = subprocess.run

    def _guard(*a: Any, **k: Any) -> Any:
        raise AssertionError("oc_worker must not be called without --run")

    subprocess.run = _guard  # type: ignore[assignment]
    try:
        ns = argparse.Namespace(scope=".", files="scripts/oc_worker.py",
                                out=None, label="selftest", run=False, timeout=900)
        with redirect_stdout(io.StringIO()):
            rc = cmd_run(ns)
        assert rc == 0, rc
    finally:
        subprocess.run = orig_run  # type: ignore[assignment]

    print("oc_bakeoff self-test: OK")
    return 0


def _add_common(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--scope", default=".", help="changeset/worktree dir audited by both models")
    sp.add_argument("--files", default="", help="comma-separated files to bound the audit")
    sp.add_argument("--out", help="ledger path (default docs/harness/evals/oc-bakeoff-<label>.md)")
    sp.add_argument("--label", help="label for the ledger/artifact names")
    sp.add_argument("--timeout", type=int, default=900, help="seconds for the glm-5.2 audit run")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Per-role bake-off harness (lifecycle gate).")
    p.add_argument("--self-test", action="store_true")
    sub = p.add_subparsers(dest="action")
    _add_common(sub.add_parser("plan", help="dry plan only; no opencode call (default)"))
    rp = sub.add_parser("run", help="drive glm-5.2 + write the ledger (needs --run)")
    _add_common(rp)
    rp.add_argument("--run", action="store_true", help="actually call oc_worker (burns Go quota)")
    args = p.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.action or args.action == "plan":
        if not getattr(args, "scope", None):  # bare `oc_bakeoff.py` with no subcommand
            p.error("provide `plan`/`run --scope ... --files ...`, or --self-test")
        args.run = False  # plan never runs
        return cmd_run(args)
    return cmd_run(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
