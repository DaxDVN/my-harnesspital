# Harness Round 2 Audit — 2026-06-17

Scope: root harness only (`AGENTS.md`, `CLAUDE.md`, `engine/`, `scripts/`, tool configs, `main-brain/`, `second-brain/`, tracked harness docs). FE/BE app code was not modified.

Mode: read-only audit. I created this report only.

## Executive Summary

Round 2 status is materially better than round 1.

- `python scripts/harness_doctor.py`: **72 OK, 0 WARN, 0 FAIL, 2 INFO**.
- Git status for the root harness was clean before creating this report.
- CodeGraph indexes for `myhospital-be` and `myhospital-fe` are fresh.
- Guard self-test passes: **64/64**.
- Learning intake is wired and self-tested.
- Super-Test MiMo/OpenCode preflight exists and strict mode passes when URL + target worktree are set.
- Progressive-test doctor passes.

The remaining issues are not broad architectural failures. They are mostly schema enforcement gaps, doc drift, cleanup/packaging hygiene, and workflow maturity gates.

## Findings

### H2-01 — `learning_capture.py` accepts invalid metadata values

Severity: **MEDIUM**

Evidence:

- `scripts/learning_capture.py:31-39` defines `VALID_SOURCES`, `VALID_SCOPES`, and `VALID_CONFS`.
- `scripts/learning_capture.py:281-301` exposes those fields as CLI args, but only as help text.
- `scripts/learning_capture.py:313-326` validates only missing `--title`, `--what`, and `--why`.
- Probe result: calling `capture()` with `source=bad-source`, `scope=bad-scope`, `confidence=bogus` still created a second-brain entry.

Why it matters:

The learning intake is meant to become a reliable queue for `/promote`. If metadata is free-form, filtering by `learning_list --confidence high` or `--target engine/rules` becomes unreliable, and future promotion decisions can be based on malformed records that `learning_check.py` does not reject.

Recommended fix:

1. Add `choices=sorted(VALID_SOURCES)` for `--source`.
2. Add `choices=sorted(VALID_CONFS)` for `--confidence`.
3. Add a scope validator:
   - allow `workspace`, `backend`, `frontend`
   - allow `module:<slug>`
   - allow `workflow:<name>`
4. Add a proposed-target allowlist or validator:
   - `main-brain`
   - `engine/rules/backend`
   - `engine/rules/frontend`
   - `engine/workflows/deep-review/checklist`
   - `engine/skills/<slug>`
   - `spec-decision`
   - `reject`
5. Extend `learning_capture --self-test` and `learning_check --self-test` to include invalid enum cases.

### H2-02 — Duplicate learning detection is same-day only

Severity: **MEDIUM**

Evidence:

- `scripts/learning_capture.py:167-170` derives the destination as `YYYY-MM-DD-<slug>.md`.
- `scripts/learning_capture.py:174-180` appends `Seen again` only when that exact dated path already exists.

Why it matters:

If the same lesson appears on different days, the intake creates multiple files instead of strengthening the existing provisional entry. This weakens the “recurring bug-class” signal and makes `/promote` review noisier.

Recommended fix:

Before creating a new file, search `second-brain/*-<slug>.md` for an existing provisional entry. If found, append a `## Seen again (<date>)` section to that older file and update the index if needed. Keep one open provisional record per canonical slug.

### H2-03 — Learning docs still point at `.claude/skills` as the skill home

Severity: **LOW**

Evidence:

- `main-brain/README.md:5` says detail lives in `.claude/skills`.
- `second-brain/README.md:17` says graduated skills go into `.claude/skills/<x>`.
- `engine/skills/promote/SKILL.md:3` description still says graduate into `.claude/skills`.
- The corrected canonical instruction is in `AGENTS.md:73-75`: graduate into `engine/skills/<x>`, because `.claude/skills` is a symlink to `engine/skills`.
- `engine/skills/promote/SKILL.md:22-24` also correctly says to create `engine/skills/<slug>/SKILL.md`.

Why it matters:

This is low risk for Claude because the flow body is correct, but cross-tool agents that read only a README or description can create a real directory/copy in `.claude/skills` or describe the wrong canonical target.

Recommended fix:

Replace stale `.claude/skills` wording with:

```text
engine/skills/<slug>/SKILL.md (`.claude/skills` is only a symlink/pointer)
```

Files to update:

- `main-brain/README.md`
- `second-brain/README.md`
- `engine/skills/promote/SKILL.md` frontmatter description
- `CLAUDE.md:25` should say exact detail lives in `engine/skills` / `engine/`.

### H2-04 — `mh-implementer` still instructs agents to use removed component catalogs

Severity: **MEDIUM**

Evidence:

- `engine/agents/mh-implementer.md:18` says: “Check the component-inventory / reuse-catalog and `rg` before writing a new component/hook/adapter.”
- `engine/rules/frontend.md:56` says the legacy generated catalogs and `npm run components:index` were removed and never existed in `myhospital-fe`.
- `engine/rules/frontend.md:439` says reuse-check is CodeGraph + `/ui-spec` reuse-map.
- `AGENTS.md:187` repeats the corrected rule.

Why it matters:

This is a worker-agent instruction, not just a doc. A spawned implementer can waste time looking for nonexistent catalogs, or worse, treat a missing catalog as a blocker even though the current rule is CodeGraph + `03-ui.md`.

Recommended fix:

Replace `mh-implementer.md` hard rule 3 with:

```text
Reuse before authoring. Use CodeGraph first from the target FE repo; if a spec exists, consume specs/<module>/03-ui.md from /ui-spec; then bounded rg. Do not use legacy component-inventory/reuse-catalog generated docs unless they actually exist in the target repo state.
```

### H2-05 — Graphify status wording is inconsistent: absent vs stale

Severity: **LOW**

Evidence:

- `CLAUDE.md:19-20` correctly says `graphify-out/` is currently absent.
- `AGENTS.md:239` also says `graphify-out/` does not exist.
- `engine/rules/source-discovery.md:22` says graphify is currently stale.
- `engine/rules/source-discovery.md:74` says it is currently stale / Windows-built.
- `python scripts/harness_doctor.py` reports: `graphify no graph.json`.

Why it matters:

Agents may waste time trying to verify a stale graph that does not exist, or report a “stale graph” warning when the right behavior is simply “graph unavailable, read source docs.”

Recommended fix:

Update `engine/rules/source-discovery.md` to:

```text
graphify is optional for docs/specs design intent only. Current graph may be absent; if `graphify-out/graph.json` is missing, skip graphify entirely. If present, verify freshness/root before trusting it.
```

### H2-06 — Tracked progressive-test probe screenshots are runtime artifacts

Severity: **LOW**

Evidence:

Tracked files:

- `engine/workflows/progressive-test/.agentflow/logs/agent-browser/example-agent-browser.png`
- `engine/workflows/progressive-test/.agentflow/logs/agent-browser/opencode-agent-browser-1781615931.png`
- `engine/workflows/progressive-test/.agentflow/logs/agent-browser/opencode-agent-browser-1781620057.png`
- `engine/workflows/progressive-test/.agentflow/logs/agent-browser/opencode-agent-browser-1781620436.png`

Command evidence:

- `git ls-files engine/workflows/progressive-test/.agentflow/logs engine/workflows/progressive-test/.agentflow/rounds engine/workflows/progressive-test/.agentflow/vendor` returned those four PNGs plus `.gitkeep`.
- `.gitignore` ignores `*.log`, `rounds/round-*`, and vendor, but not these PNGs.
- `du -sh engine/workflows/progressive-test/.agentflow/logs`: 60K.

Why it matters:

Small today, but this blurs the source/runtime boundary. Probe screenshots are evidence artifacts, not workflow source. Keeping old probe screenshots in git history makes future audits noisier.

Recommended fix:

1. Move durable example screenshots, if needed, into `docs/harness/notes/` with explicit context; otherwise remove from tracking.
2. Add an ignore pattern for `.agentflow/logs/**` except `.gitkeep`, for example:

```gitignore
engine/workflows/progressive-test/.agentflow/logs/**
!engine/workflows/progressive-test/.agentflow/logs/.gitkeep
```

### H2-07 — Many workflows are intentionally scaffolded but doctor reports this as OK only

Severity: **MEDIUM**

Evidence:

`scripts/harness_doctor.py` currently reports maturity as OK:

```text
maturity 9 workflows declare maturity (bug-fix=scaffolded, deep-review=smoke-tested, impact-analysis=scaffolded, incremental-impl=scaffolded, progressive-test=smoke-tested, super-test=scaffolded, task-slicing=scaffolded, technical-design=scaffolded, ui-spec=scaffolded)
```

Scaffolded / owner-gated workflows:

- `impact-analysis`
- `bug-fix`
- `technical-design`
- `task-slicing`
- `incremental-impl`
- `ui-spec`
- `super-test`

Why it matters:

The maturity declaration exists, which is good. But `doctor` presenting all scaffolded workflows as OK can make a future operator believe the whole harness is production-proven. The docs themselves correctly say first real run is owner gate / UNPROVEN.

Recommended fix:

Add a separate doctor summary:

- `OK` when every workflow declares maturity.
- `INFO` or `WARN` when any owner-facing entry workflow remains `scaffolded`.
- Show the exact “safe to use by default” set vs “owner-gated first real run” set.

Suggested policy:

```text
smoke-tested/proven: OK
scaffolded owner-entry workflow: INFO normally, WARN under --strict-maturity
```

### H2-08 — Cross-tool guard remains cooperative, not a sandbox

Severity: **INFO / ACCEPTED RISK**

Evidence:

- `engine/rules/cross-tool-enforcement.md:31-32` says Claude covers Bash + file writes, Codex hook covers Bash only and not `apply_patch`.
- `engine/rules/cross-tool-enforcement.md:68-71` says tripwire, not sandbox; Codex `apply_patch` is instruction-only.
- `scripts/opencode/myhospital-guard.js:14-15` says opencode does not intercept subagent tool calls.
- `scripts/opencode/myhospital-guard.js:43` only guards bash.
- `engine/hooks/myhospital_guard.py:6` says fail-open by design.

Why it matters:

This is not a new defect, but it must stay visible. The guard is useful and tested, but enforcement depends on tool coverage. File writes outside Claude remain policy/instruction-bound unless the tool routes them through the Python guard.

Recommended fix:

No immediate block. Keep stating this in `cross-tool-enforcement.md`. For higher assurance, add post-diff validators:

- generated-file diff detector
- main-repo direct-edit detector
- migration hand-edit detector
- allowlist-check wrapper for all implementation workflows

### H2-09 — `learning_check --self-test` emits expected `[FAIL]` lines

Severity: **LOW**

Evidence:

Running `python scripts/learning_check.py --self-test` prints expected failure lines for negative tests:

- dead index link
- missing frontmatter keys
- stale `.promote-unlock`

It then prints `=== All tests passed ===` and exits 0.

Why it matters:

A human or log parser can misread expected negative-test output as a real failure. `harness_doctor.py` avoids this by taking only the last output line, but direct runs are noisy.

Recommended fix:

In self-test mode, make negative-case checks use `[EXPECTED_FAIL]` or capture stderr during expected-failure assertions.

## What Improved Since Round 1

1. **Codex guard wiring improved.** `.codex/hooks.json` now walks up from cwd to `engine/hooks/myhospital_guard.py`, so it works from worktree cwd for Bash.
2. **Learning intake exists.** `learning_capture.py`, `learning_check.py`, `learning_list.py` are present, self-tested, and wired into doctor.
3. **Main-brain gate remains strong.** Guard self-test includes main-brain write protection and passes.
4. **Super-Test MiMo readiness improved.** `mimocode-preflight` exists; regular preflight has no FAIL and strict mode passes when env is set.
5. **OpenCode config improved.** `.opencode/opencode.json` loads `AGENTS.md` and `engine/rules/*.md`.
6. **Graphify docs mostly corrected.** Top-level instructions now acknowledge `graphify-out/` can be absent.
7. **Frontend reuse canon mostly corrected.** `AGENTS.md`, `frontend.md`, `ui-spec`, `mh-implement` now say CodeGraph + `/ui-spec` reuse-map instead of nonexistent generated component inventory.

## Current Self-Learning Behavior

Current behavior is **human-curated harness learning**, not model-weight learning.

Flow:

1. Trigger happens when the owner says “nhớ cái này / để ý cái này / từ giờ / always / never / remember this”, or when a review/bug-fix surfaces a recurring cross-cutting bug-class.
2. Agent runs `python scripts/learning_capture.py ...`.
3. A structured provisional entry is created in `second-brain/YYYY-MM-DD-slug.md`.
4. `second-brain/INDEX.md` is updated.
5. `python scripts/learning_list.py` shows the provisional queue.
6. `python scripts/learning_check.py` validates the queue.
7. Owner later invokes `/promote`.
8. `/promote` either:
   - distills into `main-brain/knowledge.md` after owner unlocks `main-brain/.promote-unlock`, or
   - graduates a reusable procedure into `engine/skills/<slug>/SKILL.md`.

Current content:

- `second-brain/` has no real provisional learning entries.
- `main-brain/knowledge.md` has no promoted knowledge entries.

Assessment:

The loop is operational but still cold. The next proof is to capture one real durable learning, list it, run health check, and later promote or reject it.

## Validation Commands Run

```bash
git status --short --untracked-files=all
python scripts/harness_doctor.py
just convention-truth
just codegraph-status
engine/workflows/progressive-test/.agentflow/bin/doctor
python scripts/worktree.py list
python scripts/convention_truth.py --strict
python engine/hooks/myhospital_guard.py --self-test
python scripts/mh_scan --self-test
python engine/workflows/_shared/validate-envelope.py --self-test
python engine/workflows/_shared/gate-check.py --self-test
python engine/workflows/_shared/module-state.py --self-test
python engine/workflows/_shared/allowlist-check.py --self-test
python scripts/learning_capture.py --self-test
python scripts/learning_check.py --self-test
python scripts/learning_list.py --self-test
python scripts/learning_check.py
python scripts/learning_list.py
python scripts/learning_list.py --stale
python scripts/learning_list.py --confidence high
python scripts/learning_list.py --target engine/rules
find engine scripts -path '*/__pycache__' -prune -o -name '*.py' -print | sort | xargs -r python -m py_compile
find engine/workflows -path '*/__pycache__' -prune -o -path '*/vendor/*' -prune -o -type f \( -path '*/bin/*' -o -name '*.sh' \) -print | sort | while IFS= read -r f; do if head -1 "$f" | grep -q 'bash\|sh'; then bash -n "$f" || exit 1; fi; done
bash engine/workflows/super-test/bin/mimocode-preflight
AGENTFLOW_TARGET_URL=http://localhost:3003 SUPERTEST_TARGET_REPO=/home/dax/Documents/arabica/roast/worktrees/vital-signs/fe bash engine/workflows/super-test/bin/mimocode-preflight --strict
git check-ignore -v ...
git ls-files ...
```

Notes:

- One broad compile attempt accidentally fed shell scripts to `python -m py_compile` and failed on `_executor-lib.sh`; rerun was corrected by compiling only `.py`.
- One shell syntax attempt accidentally included vendored `agent-browser` binaries; rerun was corrected by pruning vendor.

## Recommended Fix Order

1. **Fix learning metadata validation + cross-day dedupe** (`H2-01`, `H2-02`).
2. **Clean stale docs around skill home and graphify status** (`H2-03`, `H2-05`).
3. **Fix `mh-implementer` reuse instruction** (`H2-04`).
4. **Remove tracked probe screenshots / tighten `.agentflow/logs` ignore** (`H2-06`).
5. **Upgrade doctor maturity reporting** (`H2-07`).
6. **Optional: make learning self-tests quieter** (`H2-09`).

## Bottom Line

The harness is now coherent enough to use, with guardrails and health checks materially stronger than round 1. The highest-leverage remaining work is not another architecture rewrite; it is tightening the learning-intake schema, eliminating stale instruction drift, and making scaffolded workflow maturity impossible to misread as fully proven.
