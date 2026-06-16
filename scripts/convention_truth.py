#!/usr/bin/env python3
"""convention_truth — detect drift between the convention DOCS and live CODE.

The BE audit (`velvet/notes/myhospital-be-conventions-audit-2026-06-15.md`)
found `myhospital-be/CONVENTIONS.md` factually wrong in 5 places (D1–D6) while
`harness/rules/backend-rules-conventions-patterns.md` was largely correct.
Because `mh-review` D2 trusts those docs, a stale doc poisons review.

This checker asserts each documented claim against the live code and flags the
doc that drifted. Read-only. Fail-open (missing file = WARN, never crash).

    python scripts/convention_truth.py            # report, exit 0
    python scripts/convention_truth.py --strict    # exit 1 if any FAIL
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONV = ROOT / "myhospital-be" / "CONVENTIONS.md"
BE_RULES = ROOT / "harness" / "rules" / "backend-rules-conventions-patterns.md"
FUNCTIONS = ROOT / "myhospital-be" / "MyHospital.Utilities" / "Constants" / "Functions.cs"
MODELS = ROOT / "myhospital-be" / "MyHospital.ServiceInterface" / "Models"

OK, FAIL, WARN, INFO = "OK", "FAIL", "WARN", "INFO"
_results: list[tuple[str, str, str]] = []


def add(status: str, name: str, detail: str) -> None:
    _results.append((status, name, detail))


def _read(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


def check_doc_prefix() -> None:
    """audit D1 — CONVENTIONS.md §5 listed LK/CL/CDHA/TT/...; real = MV/CS/DI/BI/IV/RC/AP/RF."""
    conv = _read(CONV)
    if conv is None:
        add(WARN, "doc:prefix-table", "CONVENTIONS.md unreadable")
        return
    stale = re.search(r"`CDHA`|MedicalVisit\s*\|\s*`?LK`?|`LK`\s*\n|ClinicalService\s*\|\s*`?CL`?", conv)
    if stale:
        add(INFO, "doc:prefix-table",
            "CONVENTIONS.md §5 still lists STALE prefixes (LK/CL/CDHA…); real = MV/CS/DI/BI/IV/RC/AP/RF "
            "and they live on entity `static CodePrefix` (audit D1). Fix the table.")
    else:
        add(OK, "doc:prefix-table", "no stale LK/CL/CDHA prefix table in CONVENTIONS.md")


def check_doc_settingkeys() -> None:
    """audit D2 — CONVENTIONS.md said Commons/SettingKeys.cs; real = Constants/Commons.cs + *SettingKeys.cs."""
    conv = _read(CONV)
    if conv is None:
        add(WARN, "doc:settingkeys", "CONVENTIONS.md unreadable")
        return
    if "Commons/SettingKeys.cs" in conv:
        add(INFO, "doc:settingkeys",
            "CONVENTIONS.md §4 says `Commons/SettingKeys.cs` (no such dir); real = "
            "`Constants/Commons.cs` (class SettingKeys) + per-module *SettingKeys.cs (audit D2).")
    else:
        add(OK, "doc:settingkeys", "no `Commons/SettingKeys.cs` path in CONVENTIONS.md")


def check_doc_actions() -> None:
    """audit D4 — doc said CanCreate/CanApprove; code has CanInsert and no CanApprove."""
    conv = _read(CONV)
    funcs = _read(FUNCTIONS)
    if funcs is not None:
        has_insert = "CanInsert" in funcs
        has_create = re.search(r'"CanCreate"|const\s+string\s+CanCreate', funcs) is not None
        add(OK if (has_insert and not has_create) else WARN, "code:action-constants",
            "Functions.cs uses CanInsert, no CanCreate" if (has_insert and not has_create)
            else "unexpected action constants in Functions.cs")
    if conv is None:
        add(WARN, "doc:actions", "CONVENTIONS.md unreadable")
        return
    if re.search(r"CanCreate|CanApprove", conv):
        add(INFO, "doc:actions",
            "CONVENTIONS.md §7.2 references CanCreate/CanApprove — neither exists; real actions = "
            "CanView/CanInsert/CanUpdate/CanDelete/CanImport/CanExport/CanShare (audit D4).")
    else:
        add(OK, "doc:actions", "no CanCreate/CanApprove in CONVENTIONS.md")


def check_doc_endpoints() -> None:
    """audit D3 — doc said /types/typescript-types exports all DTOs; that is /types/typescript."""
    conv = _read(CONV)
    if conv is None:
        add(WARN, "doc:ts-endpoints", "CONVENTIONS.md unreadable")
        return
    # the wrong claim: typescript-types == all DTO/interface
    if re.search(r"typescript-types`?\*?\*?\s*[—-].{0,40}(tất cả|all).{0,20}DTO", conv, re.IGNORECASE | re.DOTALL):
        add(INFO, "doc:ts-endpoints",
            "CONVENTIONS.md §8 says `/types/typescript-types` exports all DTOs — wrong; DTOs come from "
            "`/types/typescript` (NativeTypes). `-types` = Utilities.Types only (audit D3).")
    else:
        add(OK, "doc:ts-endpoints", "no wrong typescript-types=all-DTO claim detected")


def check_doc_transaction() -> None:
    """audit D6 — CONVENTIONS.md 'không dùng transaction' is absolute; reality has 9 legacy ones.
    The agent-rules doc already frames this correctly (no NEW; legacy allowed)."""
    conv = _read(CONV)
    if conv is None:
        return
    absolute = re.search(r"không dùng transaction", conv, re.IGNORECASE)
    nuance = re.search(r"legacy|mới|new transaction", conv, re.IGNORECASE)
    if absolute and not nuance:
        add(WARN, "doc:transaction",
            "CONVENTIONS.md §1.1 states an absolute no-transaction rule; code has 9 legacy transactions "
            "(audit D6/V6). Align with agent-rules wording: 'no NEW transactions; legacy inv/prescription allowed'.")
    else:
        add(OK, "doc:transaction", "transaction rule wording acknowledges legacy/new distinction")


def check_rules_dotnet() -> None:
    """The agent-rules backend doc itself noted a .NET 8 vs .NET 10 drift; flag if present."""
    rules = _read(BE_RULES)
    if rules is None:
        add(WARN, "rules:dotnet-version", "harness/rules backend canon unreadable (path moved?)")
        return
    mentions8 = re.search(r"\.NET\s*8|net8\.0", rules)
    aware10 = re.search(r"\.NET\s*10|net10\.0", rules)
    if mentions8 and not aware10:
        add(WARN, "rules:dotnet-version",
            "harness/rules backend canon mentions .NET 8 with no .NET 10 — update to net10.0.")
    else:
        add(OK, "rules:dotnet-version", "canon version refs acknowledge net10 (no stale .NET 8 claim)")


def main() -> int:
    strict = "--strict" in sys.argv[1:]
    print(f"convention-truth — doc-vs-code drift check — {ROOT}\n")
    for fn in (check_doc_prefix, check_doc_settingkeys, check_doc_actions,
               check_doc_endpoints, check_doc_transaction, check_rules_dotnet):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            add(WARN, fn.__name__, f"check crashed: {exc}")
    width = max((len(n) for _, n, _ in _results), default=0)
    counts = {OK: 0, WARN: 0, FAIL: 0, INFO: 0}
    for status, name, detail in _results:
        counts[status] = counts.get(status, 0) + 1
        print(f"  [{status:4}] {name.ljust(width)}  {detail}")
    print(f"\nSummary: {counts[OK]} OK, {counts[WARN]} WARN, {counts[INFO]} INFO, {counts[FAIL]} FAIL")
    if counts[INFO]:
        print("Note: CANON = harness/rules/backend-rules-conventions-patterns.md (authoritative, verified correct). "
              "The 'doc:*' items are the SUPERSEDED myhospital-be/CONVENTIONS.md (legacy) — advisory only, "
              "NO project edit required (decision 2026-06-16; canon supersedes). "
              "Optional hygiene diff kept at docs/harness/pending/CONVENTIONS.fixed.md.")
    if counts[FAIL]:
        print("Action: a CANON doc (harness/rules) drifted from code — fix the harness rule (not the project).")
    return 1 if (strict and counts[FAIL]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
