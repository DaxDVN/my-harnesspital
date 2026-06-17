# Harness Self-Operation Audit — Deterministic Spine (2026-06-17)

Independent, adversarial, READ-ONLY audit. Scope = the **deterministic spine only**
(guard hook, doctor, mh_scan, convention_truth, _shared primitives, symlink wiring,
CodeGraph, justfile). EXCLUDES the SDLC build chain (ui-spec / technical-design /
task-slicing / incremental-impl), which the owner drives by hand.

Method: every claim below was produced by RUNNING the tool and reading the output /
source. Verdicts: **REAL** (runs + does what it claims) · **PARTIAL** (runs but real
gaps) · **SCAFFOLD** (exists but doesn't really work).

## Verdict table

| # | Component | Verdict | One-line basis |
|---|---|---|---|
| 1 | Guard hook (`myhospital_guard.py`) | **PARTIAL** | Self-test 55/55, registered as PreToolUse, live-fired on my own `rm -rf`. Catches its advertised canonical forms but misses many real-world equivalents (`find -delete`, `bash -c`, `env`, pipe→`xargs rm -rf`, `npx rimraf`, `pip install`). Fail-open by design. |
| 2 | `harness_doctor.py` (~53 checks) | **PARTIAL** | Runs, 53 OK / 0 FAIL; checks are mostly meaningful (presence/JSON/compile/self-tests/symlink-dangling/manifest-refs) and `--strict` would fail on a real FAIL. But several checks assert *existence*, not *efficacy* — notably CodeGraph index freshness (a 4.5h-stale index reports OK) and guard efficacy (only re-runs the author's self-test). |
| 3 | `mh_scan` | **REAL** | Self-test 31/31. Fired on real code: BE 832 findings / 38 actionable (V12 raw Exception, V3 literal error codes, V2 hospital-scope) — true positives verified at `file:line`. FE ast-grep bridge fired (73 findings / 3 HIGH dead-dtos) once invoked with `--root myhospital-fe`. One ergonomics footgun (below). |
| 4 | `convention_truth.py` | **SCAFFOLD-leaning PARTIAL** | Runs, but only checks 6 hardcoded string patterns in `myhospital-be/CONVENTIONS.md` — a doc the harness itself declares *superseded/advisory*. All output is INFO; `--strict` is structurally incapable of FAILing against the live canon (only one `.NET 8` string check touches `engine/rules`). Detects real historical drift facts, in a doc nobody is told to trust. |
| 5 | `_shared` primitives (gate-check / validate-envelope / module-state) | **REAL** | All self-test OK. gate-check proven to CLOSE on missing file, missing module, empty/stub file, and unresolved `BLOCKING` tag; OPEN on a real populated module. validate-envelope proven to FAIL (exit 1) on sha256 payload drift, missing required field, and bad enum. Fail-closed works. |
| 6 | Symlink wiring `.claude/{skills,agents,hooks,workflows}` → `engine/` | **REAL** | All four resolve to real `engine/` dirs (not dangling). 12 `SKILL.md` + 4 agent `.md` reachable through the symlinks; `mh-review/SKILL.md` and `deep-review/protocol.md` readable via the `.claude` path. Doctor would catch a dangling link (verified by simulating the logic). |
| 7 | CodeGraph | **REAL (tool) / PARTIAL (freshness governance)** | Binary `codegraph 1.0.1` on PATH; real ~100 MB `.codegraph/codegraph.db` per repo; live `codegraph explore "BusinessException"` in BE returned 221 symbols, 711 callers w/ `file:line`, blast radius, test-coverage gaps, relationship edges. Powerful and working. But the BE index is ~4.5h stale vs newest `.cs` and nothing in the spine detects or corrects that. |
| 8 | `justfile` | **REAL** | `just --list` loads; `just doctor`, `just mh-scan`, `just codegraph-status` all present and run. |

Doctor summary as run: **53 OK, 0 WARN, 0 FAIL, 2 INFO** (exit 0; `--strict` exit 0).

---

## Per-component evidence

### 1. Guard hook — PARTIAL (cooperative tripwire with real holes)
- `python .claude/hooks/myhospital_guard.py --self-test` → `all 55 cases passed (22 block, 23 allow)`.
- Registered: `.claude/settings.json` → PreToolUse matcher `Bash|Write|Edit|MultiEdit`.
- **Live-fired**: while running an unrelated command containing the literal `rm -rf`, this very session got `PreToolUse:Bash hook error … BLOCKED_RULE: destructive-delete (recursive rm)`. The hook is genuinely active, not just configured.
- Advertised blocks all PASS via stdin JSON: `git push`, `git -C <path> push`, `rm -rf`, `npm install <pkg>`, edit generated DTO (`file_path` AND `path` key), write `main-brain/`.
- **Bypasses it misses (all return exit 0 = allowed; each is a real, executable destructive command):**
  - `find node_modules -delete` — recursive tree delete; guard only matches `cmd0=='rm'` with `-r`.
  - `find . | xargs rm -rf` — `_segments` splits on `|`, so segment 2 is `xargs rm -rf` → `cmd0=='xargs'` → miss.
  - `env git push` — `cmd0=='env'`, not `git`.
  - `bash -c 'git push'` / `sh -c 'rm -rf x'` — `cmd0=='bash'/'sh'`.
  - `npx rimraf dist`, `pip install requests`, `node -e`/`python -c` arbitrary code.
  - `git pUsH` is **not** a bypass — git rejects the subcommand case-sensitively, so it's harmless.
- This is consistent with the file's own docstring (lines 2-7): "a cooperative tripwire, NOT a sandbox … deliberately fail-open." Verdict is PARTIAL, not SCAFFOLD: it does block the honest-mistake forms an agent most likely emits, but it should not be relied on against creative or adversarial commands. The FALSE sense of security is real if anyone reads "No recursive delete / no git mutation" as enforced.

### 2. harness_doctor.py — PARTIAL (meaningful, but existence ≠ efficacy)
- `python scripts/harness_doctor.py` → 53 OK / 0 WARN / 0 FAIL / 2 INFO, exit 0.
- Meaningful checks that *would* FAIL on real breakage: invalid JSON (`json.loads`), non-compiling hook (`py_compile`), guard self-test nonzero exit, dangling symlink (`target.exists()` → FAIL; verified by simulating the branch → prints `FAIL dangling`), manifest refs that don't resolve to pool files, missing routing docs. `--strict` returns `1 if (strict and counts[FAIL])` — so it does gate on real FAIL.
- **Blind spots (checks that report OK when the underlying thing could be broken):**
  - **CodeGraph freshness:** `check_codegraph` only asserts `.codegraph/` *exists* (line ~245). Measured: BE `codegraph.db` built `11:21`, newest BE `.cs` modified `15:58` same day → **~4.5h stale, still reports `indexed … OK`.** Agents are told to trust CodeGraph first; a silently stale index is the worst failure mode and the doctor is blind to it.
  - **Guard efficacy:** re-runs the author's own `--self-test` (line ~127). It cannot discover a new bypass class; "guard OK" means "the cases the author thought of still pass."
  - **mh_scan correctness:** runs `--self-test` only (line ~299); never asserts the scanners fire on live code.
  - **Hook registration:** doctor verifies the guard self-tests, but never checks that `settings.json` actually wires it as PreToolUse. (It happens to be wired — but a deleted hook block would not show up as a doctor FAIL.)
  - 2 INFO are benign (no harness-backups yet; no graphify graph.json).

### 3. mh_scan — REAL
- `python scripts/mh_scan --self-test` → `all 31 cases passed`.
- BE default run: `# mh-scan — myhospital-be — 832 findings` (BLOCK=0 HIGH=38 WARN=51 INFO=743). Signal-first md rolls advisory up by scanner; actionable tier listed with `file:line`.
- **True positives verified against source:**
  - V12 `ActiveIngredientService.cs:120` → real `throw new Exception($"…not found")`.
  - V3 `ClaudeAnalyzeService.cs:30` → real `throw new BusinessException("ANTHROPIC.MISSING_KEY", …)` (string literal, not `ErrorCodes.*`).
  - V2 `BatchAdjustmentService.cs:243` → real `Db.Products.FirstOrDefaultAsync(… p.TenantId == tenantId)` scoped by TenantId only. (V2 is correctly phrased as a *confirm* — "scoped by TenantId but NOT HospitalId (confirm entity is :Base)" — i.e. a judgment-call HIGH, expected to carry some false positives by design.)
- FE ast-grep bridge is REAL: 9 rules in `scripts/sgconfig/rules/`, `ast-grep` on PATH, `run_fe_ast_grep` gated to FE roots, self-test asserts FE-V1/FE-V2 fire. Correct run `--root myhospital-fe --scope src` → 73 findings, **3 HIGH** dead `@/lib/dtos/dtos` imports (build-breaking) at real `file:line`.
- FP/FN estimate: BE literal/structural scanners (V12 raw Exception, V3 literal code, FE-V1 dead import) are near-zero FP — they match unambiguous syntax. V2 hospital-scope and the rolled-up INFO classes (V9 redundant soft-delete 404, V8 fat-api 182) are heuristic and will carry FPs / need human triage; that's why they're INFO/advisory, not actionable. FN risk: scanners cover V1-V16 bug-classes only; anything outside that catalog is unseen (by design — it's a "floor," not a full linter).
- **Footgun (ergonomics, not correctness):** `--scope` is interpreted *relative to* `--root` (default `./myhospital-be`). `python scripts/mh_scan --scope myhospital-fe` silently scans a nonexistent BE subpath → `# mh-scan — myhospital-be — 0 findings`, exit 0. The `agent-shortcuts.md` "FE → just mh-scan (ast-grep bridge, FE-gated)" wording invites exactly this mistake; FE requires `--root myhospital-fe`.

### 4. convention_truth.py — SCAFFOLD-leaning PARTIAL
- `python scripts/convention_truth.py` → 3 OK / 4 INFO / 0 FAIL; `--strict` → exit 0.
- It hardcodes 6 checks (D1 prefixes, D2 settingkeys, D4 actions, D3 ts-endpoints, D6 transaction, .NET version). Five target `myhospital-be/CONVENTIONS.md` — which the harness itself labels SUPERSEDED/advisory ("NO project edit required (decision 2026-06-16; canon supersedes)"). So every drift it finds is emitted as **INFO about a doc nobody is told to trust**, and there is essentially **no input that makes it FAIL** (only `check_rules_dotnet` even looks at the canon `engine/rules/backend.md`, and only for a `.NET 8` string). It is not "doc-vs-code drift detection" in any live sense — it's a frozen checklist of already-known historical doc errors. Detects real trivia; cannot guard the canon.

### 5. _shared primitives — REAL (fail-closed proven)
- gate-check: OPEN on `vital-signs --require 02-requirements,03-ui` and `07-schema,08-api`. CLOSED (exit 2) on missing file (`99-nonexistent`), missing module (`no-such-module`), empty/stub file (`TODO`), and synthetic `- BLOCKING: …` in 05 → `has 1 unresolved BLOCKING item(s)`. Genuinely gates.
- validate-envelope: valid envelope+payload → `OK` exit 0; after tampering the payload → `FAIL … content_sha256 drift … (payload changed since the receipt)` exit 1; missing `status` → `missing required field 'status'` exit 1; `risk_level=BOGUS` → enum FAIL exit 1. The envelope↔payload binding actually works.
- module-state: `--self-test` OK (state machine for `specs/<m>/00-module-state.md`).

### 6. Symlink wiring — REAL
- `readlink -f` for all four `.claude/{skills,agents,hooks,workflows}` → real `engine/<name>` dirs.
- `find -L .claude/skills -name SKILL.md` = 12; `find -L .claude/agents -name '*.md'` = 4. `mh-review/SKILL.md` and `deep-review/protocol.md` readable through the `.claude` path → an asset placed in `engine/` is discoverable to Claude.

### 7. CodeGraph — REAL tool, PARTIAL freshness governance
- `codegraph --version` → `1.0.1`. `.codegraph/codegraph.db`: BE ~101 MB, FE ~97 MB.
- `cd myhospital-be && codegraph explore "BusinessException"` → `Found 221 symbols across 49 files`, blast radius with `file:line` + caller counts (e.g. `BusinessException … 711 callers`), test-coverage gaps (`⚠️ no covering tests found`), `extends`/`calls` edges. This is the single strongest piece of real infrastructure in the spine.
- Caveat: index staleness is ungoverned (see #2). Root has no `.codegraph/` (correct — root excludes FE/BE/worktrees). Note the root MCP banner says "workspace not indexed" — correct by design; CodeGraph must be invoked from inside a repo, and the per-repo indexes are real.

### 8. justfile — REAL
- `just --list` enumerates recipes; `doctor`, `mh-scan *ARGS`, `codegraph-status` all present and executed successfully during this audit.

---

## Top gaps that most undermine real self-operation

1. **CodeGraph staleness is invisible and ungoverned (highest impact).** Agents are instructed to trust CodeGraph *first* for "how/where/what-calls/what-breaks," yet the BE index measured ~4.5h behind source and `just doctor` reports it green. Stale "blast radius / callers / coverage" is worse than no graph because it's authoritative-looking and wrong. The "auto-sync ~2s debounce" only holds while the daemon is live; batch/offline edits leave it stale silently. *Fix:* doctor should compare `codegraph.db` mtime to newest tracked source mtime and WARN; add a freshness gate before relying on CodeGraph output.
2. **Guard gives a false sense of "enforced" while being a fail-open tripwire with broad holes.** It misses `find -delete`, pipe→`xargs rm -rf`, `bash -c`/`sh -c`, `env <cmd>`, `npx rimraf`, `pip install`, and arbitrary `node -e`/`python -c`. The cross-tool docs read as hard `BLOCK`s. *Fix:* either harden (recurse into `bash -c`/`xargs`/`find -delete`, treat unknown `cmd0` wrappers conservatively) or relabel everywhere as "best-effort tripwire, not enforcement," and never claim the listed actions are prevented.
3. **Doctor validates existence/self-tests, not efficacy — so "53 OK / 0 FAIL" overstates health.** It cannot catch a new guard bypass, a stale CodeGraph index, an mh_scan that stopped firing, or a guard that got un-wired from settings.json. The green board is reassuring beyond what it proves. *Fix:* add efficacy probes (guard bypass corpus, mh_scan fires-on-known-violation canary, settings.json hook-registration assertion).
4. **convention_truth guards the wrong artifact.** It checks a doc the harness declares superseded, emits only INFO, and structurally cannot FAIL against the live canon. As a "doc-vs-code truth" guard it is effectively inert. *Fix:* point its assertions at `engine/rules/*` (the canon agents actually load) vs live code, with real FAIL on canon drift — or retire it and fold the one useful canon check into doctor.
5. **mh_scan FE invocation is a silent-zero footgun.** `--scope myhospital-fe` (the natural reading of the shortcut docs) scans a nonexistent BE subpath and returns "0 findings, exit 0" — a false all-clear. *Fix:* error on a `--scope` path that resolves outside/under a non-existent `--root`, or auto-detect FE scope and switch root; fix the `agent-shortcuts.md` wording to show `--root myhospital-fe`.

**Bottom line:** The deterministic spine is mostly REAL and genuinely self-operates — mh_scan, gate-check, validate-envelope, the symlink wiring, and CodeGraph-the-tool all do what they claim, verified by live runs against real code/modules. The weak links are **governance/observability** (no CodeGraph freshness gate; a doctor that confirms presence over efficacy), one **PARTIAL safety tripwire** that is easy to over-trust, one near-**inert** checker (convention_truth), and one **ergonomic footgun** (FE scan). None of these are "aspirational scaffold that doesn't run" — they all run; the risk is a green dashboard that reads as stronger guarantees than the spine actually provides.
