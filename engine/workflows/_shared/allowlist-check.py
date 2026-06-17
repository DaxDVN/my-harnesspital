#!/usr/bin/env python3
"""allowlist-check — enforce a writer worker's ACTUAL diff against its declared allowlist.

The boundary gap (boundary audit 2026-06-17): writer workers (mh-implementer, the progressive-test
mimo executor, /mh-fix) get an allowlist by INSTRUCTION ("stay in scope") but nothing checks the diff
they actually produced. A worker that edits outside its allowlist overreaches silently → context rot +
wasted tokens + scope creep. This turns the instructed "stop if outside allowlist" into a runnable gate.

    # explicit list:
    python engine/workflows/_shared/allowlist-check.py --changed a.ts,b.ts --allow 'src/modules/x/**'
    # from a worktree diff (the usual call):
    git -C worktrees/<slug>/fe diff --name-only <base> | \
        python engine/workflows/_shared/allowlist-check.py --stdin --allow 'src/modules/x/**,forms/*' --forbid '**/generated-*'
    python engine/workflows/_shared/allowlist-check.py --self-test

--allow  : glob(s) (comma-separated) a changed file MUST match at least one of.
--forbid : glob(s) a changed file must match NONE of (e.g. generated files, routing roots).
changed  : from --changed <csv> or piped on stdin (--stdin), one path per line.

Exit 0 = every changed file is inside the allowlist and none forbidden (boundary held)
     2 = OVERREACH — at least one file outside the allowlist or in the forbidden set (STOP)
     1 = usage error.
"""
from __future__ import annotations

import fnmatch
import sys


def _match_any(path: str, globs: list[str]) -> bool:
    # match against the glob and, for "dir/**" patterns, the dir prefix too
    for g in globs:
        if fnmatch.fnmatch(path, g):
            return True
        if g.endswith("/**") and (path == g[:-3] or path.startswith(g[:-2])):
            return True
    return False


def check(changed: list[str], allow: list[str], forbid: list[str]) -> tuple[bool, list[str]]:
    """Return (ok, violations). A file is a violation if it matches a forbid glob,
    or (when an allowlist is given) matches no allow glob."""
    violations: list[str] = []
    for f in changed:
        f = f.strip()
        if not f:
            continue
        if forbid and _match_any(f, forbid):
            violations.append(f"{f}  (forbidden)")
        elif allow and not _match_any(f, allow):
            violations.append(f"{f}  (outside allowlist)")
    return (not violations), violations


def _csv(argv: list[str], flag: str) -> list[str]:
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            return [s.strip() for s in argv[i + 1].split(",") if s.strip()]
    return []


def _self_test() -> int:
    ok, v = check(["src/modules/x/a.ts", "src/modules/x/forms/s.ts"], ["src/modules/x/**"], [])
    assert ok, v
    ok, v = check(["src/modules/x/a.ts", "src/modules/y/evil.ts"], ["src/modules/x/**"], [])
    assert not ok and any("outside" in s for s in v), v
    ok, v = check(["src/modules/x/a.ts", "src/lib/generated-dtos.ts"], ["src/**"], ["**/generated-*"])
    assert not ok and any("forbidden" in s for s in v), v
    # exact-file allowlist
    ok, v = check(["forms/x-schema.ts"], ["forms/x-schema.ts"], [])
    assert ok, v
    # empty diff = trivially inside
    ok, v = check([], ["src/**"], [])
    assert ok, v
    print("allowlist-check self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return _self_test()
    allow = _csv(argv, "--allow")
    forbid = _csv(argv, "--forbid")
    if "--stdin" in argv or not sys.stdin.isatty():
        changed = [ln.strip() for ln in sys.stdin.read().splitlines() if ln.strip()]
    else:
        changed = _csv(argv, "--changed")
    if not allow and not forbid:
        print("usage error: provide --allow and/or --forbid (and --changed or --stdin)")
        return 1
    ok, violations = check(changed, allow, forbid)
    if ok:
        print(f"ALLOWLIST OK: {len(changed)} changed file(s), all inside boundary.")
        return 0
    print(f"OVERREACH ({len(violations)} file(s) outside the worker's boundary) — STOP:")
    for v in violations:
        print(f"  - {v}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
