#!/usr/bin/env python3
"""mh_scan — deterministic convention scanners for the MyHospital BE.

Each scanner encodes ONE mechanical bug-class found in the BE audit
(`velvet/notes/myhospital-be-conventions-audit-2026-06-15.md`, finding ids V1–V16).
The pack is the harness's "deterministic floor": its findings (a) feed the
`mh-review` reviewers as a per-dimension candidate list (recall up → fewer
rounds), (b) back the `myhospital-rule-auditor` quick-check, (c) can gate CI.

Design mirrors `.claude/hooks/myhospital_guard.py`:
  - `rg`-backed, pure-stdlib otherwise.
  - **fail-open**: any scanner error is swallowed; the run never aborts.
  - **string-testable**: every classifier runs on a text fixture in --self-test,
    so the pack can't silently rot (checked by harness_doctor).

Output is compatible with `harness/review/findings-schema.md`
(severity / dimension / location / title / evidence).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable, Optional

# --------------------------------------------------------------------------
# Workspace / scope
# --------------------------------------------------------------------------
WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_ROOT = os.path.join(WORKSPACE, "myhospital-be")
FIRST_PARTY = [
    "MyHospital",
    "MyHospital.Apis",
    "MyHospital.ServiceInterface",
    "MyHospital.Utilities",
    "MyHospital.Reporting",
]
EXCLUDE_GLOBS = ["!**/bin/**", "!**/obj/**", "!**/Migrations/**", "!**/*ModelSnapshot.cs"]

# Legacy paths where transactions/locks are an accepted exception (audit V6 +
# agent-rules backend doc §"Known Legacy Exceptions"). New ones elsewhere = WARN.
TX_LEGACY_ALLOW = (
    "PrescriptionHoldService",
    "PrescriptionManagementService",
    "BatchAdjustmentService",
    "TransferService",
    "LisResultService",
)

# auth_coverage scanner removed 2026-06-16 (owner: BE endpoints flagged were public by design).


# --------------------------------------------------------------------------
# Finding + Scanner model
# --------------------------------------------------------------------------
@dataclass
class Finding:
    scanner: str
    severity: str          # BLOCK | HIGH | WARN | INFO
    dimension: str         # mh-review dimension id (D1..D10)
    audit_ref: str         # V-id in the source audit
    path: str
    line: int
    title: str
    snippet: str = ""

    def as_dict(self) -> dict:
        return {
            "scanner": self.scanner,
            "severity": self.severity,
            "dimension": self.dimension,
            "audit_ref": self.audit_ref,
            "location": f"{self.path}:{self.line}",
            "title": self.title,
            "evidence": f"scanner:{self.scanner}",
            "snippet": self.snippet.strip()[:200],
        }


@dataclass
class Scanner:
    id: str
    dimension: str
    severity: str
    audit_ref: str
    title: str
    pattern: str
    globs: tuple = ("*.cs",)
    multiline: bool = False
    # classify(path, matched_line_text) -> keep?  (default: keep all hits)
    classify: Callable[[str, str], bool] = field(default=lambda p, t: True)
    note: str = ""

    def run(self, root: str, scope: list[str]) -> list[Finding]:
        out: list[Finding] = []
        try:
            for path, line, text in _rg(self.pattern, scope, root, self.globs, self.multiline):
                try:
                    if self.classify(path, text):
                        out.append(Finding(self.id, self.severity, self.dimension,
                                           self.audit_ref, path, line, self.title, text))
                except Exception:
                    out.append(Finding(self.id, self.severity, self.dimension,
                                       self.audit_ref, path, line, self.title, text))
        except Exception:
            pass  # fail-open: a broken scanner must not abort the run
        return out


# --------------------------------------------------------------------------
# rg helper
# --------------------------------------------------------------------------
def _rg(pattern: str, scope: list[str], root: str, globs, multiline: bool):
    cmd = ["rg", "-n", "--no-heading", "--color=never"]
    if multiline:
        cmd += ["-U", "--multiline-dotall"]
    for g in EXCLUDE_GLOBS:
        cmd += ["-g", g]
    for g in globs:
        cmd += ["-g", g]
    cmd += ["-e", pattern, "--"]
    cmd += scope
    try:
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=120)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return
    for raw in proc.stdout.splitlines():
        # path:line:text  (path may contain no colon on these trees)
        m = re.match(r"^(.*?):(\d+):(.*)$", raw)
        if m:
            yield m.group(1), int(m.group(2)), m.group(3)


def _is_comment(text: str) -> bool:
    s = text.lstrip()
    return s.startswith("//") or s.startswith("*") or s.startswith("/*")


# --------------------------------------------------------------------------
# Regex-pattern scanners (V3,V4,V6,V8,V9,V10,V11,V12,V13,V15,V16)
# --------------------------------------------------------------------------
def _not_tx_legacy(path: str, _t: str) -> bool:
    return not any(name in path for name in TX_LEGACY_ALLOW)


def _contract_layer(path: str, _t: str) -> bool:
    base = os.path.basename(path)
    return ("MyHospital.Apis/" in path.replace("\\", "/")
            or base.endswith(("Request.cs", "Response.cs", "Dto.cs", "Result.cs")))


def _is_api_file(path: str, _t: str) -> bool:
    return "MyHospital.Apis/" in path.replace("\\", "/") and path.endswith("Api.cs")


def _softdelete_redundant(path: str, _t: str) -> bool:
    p = path.replace("\\", "/")
    if p.endswith("MyHospitalContext.cs") or "/Migrations/" in p:
        return False
    return "IS NULL" not in _t  # skip raw-SQL string filters


SCANNERS: list[Scanner] = [
    Scanner("error_code_literal", "D2", "HIGH", "V3",
            "BusinessException with string-literal code (use ErrorCodes.*)",
            r'new BusinessException\(\s*"'),
    Scanner("legacy_listing", "D2", "INFO", "V4",
            "legacy manual filter parse (use [FilterField]+ParseAllFilters)",
            r'\b(ParseStringEquality|ParseBooleanEquality|ParseNumericEquality|ParseContains|ParseInOperator|ExtractDateFilter)\s*\(',
            classify=lambda p, t: not p.endswith("ODataRequest.cs")),
    Scanner("new_transaction", "D5", "WARN", "V6",
            "DB transaction/scope outside legacy allowlist (no-transaction rule)",
            r'(BeginTransactionAsync|TransactionScope|OpenTransaction|UseTransaction)\b',
            classify=_not_tx_legacy,
            note="legacy inventory/prescription paths allowed; new = WARN→BLOCK"),
    Scanner("hard_delete", "D5", "INFO", "V10",
            "Db.Remove/RemoveRange (SaveChangesAsync net soft-deletes TrackingBase)",
            r'\.(Remove|RemoveRange)\s*\(',
            classify=lambda p, t: bool(re.search(r'\b_?[Dd]b\b|\bcontext\b', t))),
    Scanner("raw_exception", "D4", "HIGH", "V12",
            "throw new Exception (use BusinessException + ErrorCodes)",
            r'throw new Exception\(',
            classify=lambda p, t: not _is_comment(t)),
    Scanner("swallow_catch", "D4", "WARN", "V11",
            "empty/null-returning catch (do not swallow; let it bubble)",
            r'catch\s*(\([^)]*\))?\s*\{\s*(return null;)?\s*\}',
            multiline=True),
    Scanner("contract_dict", "D7", "WARN", "V13",
            "Dictionary<string,object>/dynamic at contract layer (use typed DTO)",
            r'(Dictionary\s*<\s*string\s*,\s*object|\bdynamic\s+[A-Za-z_])',
            classify=_contract_layer),
    Scanner("redundant_softdelete", "D5", "INFO", "V9",
            "manual .Where(DeletedAt==null) is redundant (global query filter)",
            r'DeletedAt\s*==\s*null',
            classify=_softdelete_redundant),
    Scanner("manual_codegen", "D2", "WARN", "V15",
            "manual code string (use BaseService.CreateUniqueCodeAsync)",
            r'\bCode\s*=\s*\$"'),
    Scanner("magic_status", "D2", "INFO", "V16",
            "status/type compared to string literal (use a constant)",
            r'\.(Status|PaymentMethod|AdjustmentMethod|Type|Kind|Mode)\s*[!=]=\s*"'),
    Scanner("fat_api", "D2", "INFO", "V8",
            "direct Db access inside *Api.cs (move logic to a service)",
            r'\bDb\.',
            classify=_is_api_file),
]


# --------------------------------------------------------------------------
# Custom file-parsing scanners (V2 hospital scope)
# --------------------------------------------------------------------------


_RE_DBQ = re.compile(r'\b_?[Dd]b\.\w+\s*\.\s*(Where|FirstOrDefault\w*|Single\w*|Any\w*|Count\w*|First\w*)\s*\(')


def scan_missing_hospital_scope(content: str, path: str) -> list[Finding]:
    """Candidate (needs agent confirm the entity is :Base): a direct Db.<Set> query
    that filters TenantId but not HospitalId, bypassing GetAllByTenantAndHospital."""
    out: list[Finding] = []
    if not path.endswith("Service.cs"):
        return out
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if not _RE_DBQ.search(line):
            continue
        window = " ".join(lines[i:i + 4])  # predicate may wrap
        if "TenantId" in window and "HospitalId" not in window:
            out.append(Finding("missing_hospital_scope", "HIGH", "D5", "V2", path, i + 1,
                               "direct Db query scoped by TenantId but NOT HospitalId (confirm entity is :Base)",
                               line.strip()))
    return out


CUSTOM = [scan_missing_hospital_scope]
CUSTOM_GLOBS = {"scan_missing_hospital_scope": "Service.cs"}


def _iter_files(root: str, scope: list[str], suffix: str):
    for base in scope:
        full = os.path.join(root, base)
        if os.path.isfile(full):
            if full.endswith(suffix):
                yield full
            continue
        for dirpath, dirnames, filenames in os.walk(full):
            dirnames[:] = [d for d in dirnames if d not in ("bin", "obj", "Migrations")]
            for fn in filenames:
                if fn.endswith(suffix) and not fn.endswith("ModelSnapshot.cs"):
                    yield os.path.join(dirpath, fn)


def run_custom(root: str, scope: list[str]) -> list[Finding]:
    out: list[Finding] = []
    for fn in CUSTOM:
        suffix = CUSTOM_GLOBS[fn.__name__]
        for full in _iter_files(root, scope, suffix):
            try:
                with open(full, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                rel = os.path.relpath(full, root)
                out.extend(fn(content, rel))
            except Exception:
                continue
    return out


# --------------------------------------------------------------------------
# FE bridge — ast-grep structural scanners (FE audit FE-V1..FE-V3)
# Lets `mh_scan` cover the React FE too, so dev/fix/review use ONE entry.
# BE runs are unaffected: the bridge is gated to FE roots/scopes and the
# tsx/ts rules never match .cs. FE rules live in scripts/sgconfig/.
# Source: velvet/notes/myhospital-fe-convention-audit-2026-06-15.md
# --------------------------------------------------------------------------
SGCONFIG_FE = os.path.join(WORKSPACE, "scripts", "sgconfig", "sgconfig.yml")

_FE_RULE_MAP = {
    "mh-no-raw-fetch-tsx": ("D3", "FE-V2"),
    "mh-no-raw-fetch-ts": ("D3", "FE-V2"),
    "mh-masterdata-name-compare-tsx": ("D3", "FE-V3"),
    "mh-masterdata-name-compare-ts": ("D3", "FE-V3"),
    "mh-servicestackclient-in-component": ("D3", "FE-V2"),
    "mh-dead-dtos-import-tsx": ("D7", "FE-V1"),
    "mh-dead-dtos-import-ts": ("D7", "FE-V1"),
}
_FE_SEV = {"error": "HIGH", "warning": "WARN", "info": "INFO", "hint": "INFO"}


def _looks_fe(root: str, scope: list[str]) -> bool:
    r = root.replace("\\", "/").rstrip("/")
    if "myhospital-fe" in r or r.endswith("/fe") or os.path.basename(r) == "fe":
        return True
    return any(str(s).endswith((".ts", ".tsx")) for s in (scope or []))


def run_fe_ast_grep(root: str, scope: list[str]) -> list[Finding]:
    """Bridge ast-grep FE structural rules into the Finding model. Fail-open:
    no ast-grep / no sgconfig / non-FE scope → []. BE scans never touch this."""
    if not _looks_fe(root, scope) or not os.path.isfile(SGCONFIG_FE):
        return []
    targets = [os.path.join(root, s) for s in scope] if scope else [root]
    cmd = ["ast-grep", "scan", "-c", SGCONFIG_FE, "--json=stream", *targets]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    out: list[Finding] = []
    for raw in proc.stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            m = json.loads(raw)
        except json.JSONDecodeError:
            continue
        rule = m.get("ruleId") or "fe-rule"
        dim, ref = _FE_RULE_MAP.get(rule, ("D3", "FE"))
        sev = _FE_SEV.get(str(m.get("severity", "")).lower(), "WARN")
        rng = (m.get("range") or {}).get("start") or {}
        line = int(rng.get("line", 0)) + 1  # ast-grep line is 0-based
        path = m.get("file") or ""
        try:
            path = os.path.relpath(path, root)
        except Exception:
            pass
        title = (m.get("message") or rule).split("\n")[0][:120]
        snippet = (m.get("text") or "").split("\n")[0]
        out.append(Finding(rule, sev, dim, ref, path, line, title, snippet))
    return out


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------
SEV_ORDER = {"BLOCK": 0, "HIGH": 1, "WARN": 2, "INFO": 3}


def scan_all(root: str, scope: list[str], only: Optional[set] = None) -> list[Finding]:
    findings: list[Finding] = []
    for sc in SCANNERS:
        if only and sc.id not in only:
            continue
        findings.extend(sc.run(root, scope))
    if not only or any(fn.__name__ in only or fn.__name__.replace("scan_", "") in only for fn in CUSTOM):
        findings.extend(run_custom(root, scope))
    if not only:
        findings.extend(run_fe_ast_grep(root, scope))  # FE ast-grep bridge (gated to FE)
    findings.sort(key=lambda f: (SEV_ORDER.get(f.severity, 9), f.path, f.line))
    return findings


def _finding_line(f: "Finding") -> str:
    return f"- **{f.severity}** [{f.audit_ref}/{f.dimension}] `{f.path}:{f.line}` — {f.title}\n"


def render_md(findings: list[Finding], root: str, advisory: bool = False) -> str:
    """Signal-first report. BLOCK/HIGH ("actionable") are always listed in full;
    WARN/INFO ("advisory") are rolled up by scanner so the actionable findings are
    not drowned — pass advisory=True (--advisory) to expand them. The `json` format
    stays complete (the recall feed for mh-review reviewers); this only shapes the
    human view."""
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    act = [f for f in findings if f.severity in ("BLOCK", "HIGH")]
    adv = [f for f in findings if f.severity in ("WARN", "INFO")]
    head = (f"# mh-scan — {os.path.basename(root)} — {len(findings)} findings\n\n"
            + " · ".join(f"{k}={counts.get(k,0)}" for k in ("BLOCK", "HIGH", "WARN", "INFO")) + "\n"
            + f"\n**Actionable (BLOCK+HIGH): {len(act)}** · Advisory (WARN+INFO): {len(adv)}\n")
    # per-scanner rollup (all rules) — quick shape of the run
    by_scanner: dict[str, int] = {}
    for f in findings:
        by_scanner[f.scanner] = by_scanner.get(f.scanner, 0) + 1
    head += "\n| scanner | audit | sev | n |\n|---|---|---|---|\n"
    for sid in sorted(by_scanner, key=lambda s: -by_scanner[s]):
        ex = next((f for f in findings if f.scanner == sid), None)
        head += f"| {sid} | {ex.audit_ref if ex else ''} | {ex.severity if ex else ''} | {by_scanner[sid]} |\n"
    # actionable — ALWAYS in full
    head += f"\n## Actionable findings — {len(act)} (BLOCK, HIGH)\n"
    head += "".join(_finding_line(f) for f in act) if act else "_none_\n"
    # advisory — rolled up by default; full only with --advisory
    head += f"\n## Advisory — {len(adv)} (WARN, INFO)\n"
    if not adv:
        head += "_none_\n"
    elif advisory:
        head += "".join(_finding_line(f) for f in adv)
    else:
        adv_by: dict[str, int] = {}
        for f in adv:
            adv_by[f.scanner] = adv_by.get(f.scanner, 0) + 1
        head += "_rolled up — run `--advisory` for the full list:_\n\n"
        head += "| scanner | sev | n | title |\n|---|---|---|---|\n"
        for sid in sorted(adv_by, key=lambda s: -adv_by[s]):
            ex = next((f for f in adv if f.scanner == sid), None)
            head += f"| {sid} | {ex.severity if ex else ''} | {adv_by[sid]} | {ex.title if ex else ''} |\n"
    return head


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="mh_scan", description="MyHospital BE convention scanners")
    ap.add_argument("--root", default=DEFAULT_ROOT, help="BE repo root (default: ./myhospital-be)")
    ap.add_argument("--scope", nargs="*", default=None,
                    help="subpaths/files relative to root (default: first-party projects)")
    ap.add_argument("--only", nargs="*", default=None, help="run only these scanner ids")
    ap.add_argument("--format", choices=["md", "json", "summary"], default="md")
    ap.add_argument("--fail-on", choices=["never", "block", "high", "warn"], default="never",
                    help="exit 1 if a finding at/above this severity exists (CI gate; use 'high' to gate on the actionable tier only)")
    ap.add_argument("--advisory", action="store_true",
                    help="list WARN/INFO findings in full (md default rolls them up by scanner so actionable signal leads)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    if not os.path.isdir(args.root):
        print(f"mh_scan: root not found: {args.root}", file=sys.stderr)
        return 0  # fail-open
    scope = args.scope or FIRST_PARTY
    only = set(args.only) if args.only else None
    findings = scan_all(args.root, scope, only)

    if args.format == "json":
        print(json.dumps([f.as_dict() for f in findings], indent=2, ensure_ascii=False))
    elif args.format == "summary":
        counts: dict[str, int] = {}
        for f in findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        act = counts.get("BLOCK", 0) + counts.get("HIGH", 0)
        adv = counts.get("WARN", 0) + counts.get("INFO", 0)
        print(f"mh-scan: {len(findings)} findings — "
              + ", ".join(f"{k}={counts.get(k,0)}" for k in ("BLOCK", "HIGH", "WARN", "INFO"))
              + f"  |  actionable={act} (BLOCK+HIGH) · advisory={adv} (WARN+INFO)")
    else:
        print(render_md(findings, args.root, args.advisory))

    gate = {"never": 99, "block": 0, "high": 1, "warn": 2}[args.fail_on]
    if any(SEV_ORDER.get(f.severity, 9) <= gate for f in findings):
        return 1
    return 0


# --------------------------------------------------------------------------
# Self-test — every classifier checked on a string fixture (no FS needed)
# --------------------------------------------------------------------------
def _self_test() -> int:
    failures = 0

    def check(cond: bool, msg: str):
        nonlocal failures
        if not cond:
            failures += 1
            print(f"FAIL: {msg}")

    # regex scanners: (id, text, path, expect_match_and_keep)
    sc = {s.id: s for s in SCANNERS}
    cases = [
        ("error_code_literal", 'throw new BusinessException("ANTHROPIC.X", "m");', "X.cs", True),
        ("error_code_literal", 'throw new BusinessException(ErrorCodes.Patient.NotFound, "m");', "X.cs", False),
        ("legacy_listing", 'var q = request.ParseStringEquality("q");', "LabTestApi.cs", True),
        ("legacy_listing", 'public string ParseStringEquality(string f) {}', "ODataRequest.cs", False),
        ("new_transaction", 'using var tx = await Db.Database.BeginTransactionAsync();', "FooService.cs", True),
        ("new_transaction", 'using var tx = await Db.Database.BeginTransactionAsync();', "PrescriptionHoldService.cs", False),
        ("raw_exception", 'throw new Exception("x");', "X.cs", True),
        ("raw_exception", '// throw new Exception("x");', "X.cs", False),
        ("hard_delete", 'Db.UserRolePermissions.RemoveRange(items);', "RoleService.cs", True),
        ("hard_delete", 'myList.Remove(x);', "X.cs", False),
        ("contract_dict", 'public Dictionary<string, object?> EntityData { get; set; }', "MyHospital.Apis/SettingApi.cs", True),
        ("contract_dict", 'var tmp = new Dictionary<string, object>();', "MyHospital.ServiceInterface/SomeService.cs", False),
        ("redundant_softdelete", '.Where(x => x.DeletedAt == null)', "BidService.cs", True),
        ("redundant_softdelete", 'entityType.HasQueryFilter(... DeletedAt == null)', "MyHospitalContext.cs", False),
        ("manual_codegen", 'Code = $"RSR-{now}";', "RetailReturnApi.cs", True),
        ("magic_status", 'if (bi.Status == "Cancelled")', "BillingService.cs", True),
        ("fat_api", 'var v = await Db.MedicalVisits.FirstOrDefaultAsync();', "MyHospital.Apis/CashierApi.cs", True),
        ("fat_api", 'var v = await Db.MedicalVisits.FirstOrDefaultAsync();', "MyHospital.ServiceInterface/CashierService.cs", False),
    ]
    for sid, text, path, expect in cases:
        s = sc[sid]
        hit = bool(re.search(s.pattern, text)) and s.classify(path, text)
        check(hit == expect, f"{sid} on {path!r} {text!r} expected {expect} got {hit}")

    # every pattern must COMPILE in rg (Rust regex has no look-around) — else it
    # silently returns 0 live (fail-open). Catch that here, not in production.
    for s in SCANNERS:
        flags = ["-U", "--multiline-dotall"] if s.multiline else []
        try:
            rc = subprocess.run(["rg", *flags, "-e", s.pattern, "-"],
                                input="sample text\n", capture_output=True, text=True, timeout=10).returncode
        except Exception:
            rc = 0  # rg absent — skip (fail-open)
        check(rc != 2, f"{s.id}: pattern does not compile in rg: {s.pattern!r}")

    # (auth_coverage scanner + self-test removed 2026-06-16 — endpoints public by design)

    # hospital scope
    miss = 'var p = await Db.Products.FirstOrDefaultAsync(p => p.Id == id && p.TenantId == tid);'
    ok = 'var p = await Db.Products.FirstOrDefaultAsync(p => p.TenantId == tid && p.HospitalId == hid);'
    check(len(scan_missing_hospital_scope(miss, "ProductService.cs")) == 1, "scope: missing-hospital not flagged")
    check(len(scan_missing_hospital_scope(ok, "ProductService.cs")) == 0, "scope: scoped query falsely flagged")

    # FE ast-grep bridge (only when ast-grep + sgconfig present — hermetic temp file)
    if os.path.isfile(SGCONFIG_FE):
        try:
            ag_ok = subprocess.run(["ast-grep", "--version"], capture_output=True,
                                   text=True, timeout=10).returncode == 0
        except Exception:
            ag_ok = False
        if ag_ok:
            import tempfile
            with tempfile.TemporaryDirectory() as td:
                with open(os.path.join(td, "x.tsx"), "w") as fh:
                    fh.write("import { HelloResponse } from '@/lib/dtos/dtos';\n"
                             "const r = fetch('/x');\n")
                fe = run_fe_ast_grep(td, ["x.tsx"])
                check(any(f.audit_ref == "FE-V1" for f in fe), "fe-bridge: dead @/lib/dtos/dtos import not flagged")
                check(any(f.audit_ref == "FE-V2" for f in fe), "fe-bridge: raw fetch() not flagged")

    total = len(cases) + 2 + len(SCANNERS)
    if failures:
        print(f"mh_scan self-test: {failures}/{total} FAILED")
        return 1
    print(f"mh_scan self-test: all {total} cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
