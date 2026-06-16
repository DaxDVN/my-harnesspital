# Independent Harness Review Report

## A. Executive summary

* Overall verdict: **usable with issues, risky for unattended reliance**.
* Linux/fish direction is mostly clear in active docs, and legacy PowerShell is labeled deprecated.
* Worktree CLI exists and exposes the expected commands, but dry-run behavior is not fully safe/preview-only.
* Root workspace is **not a Git repo**, so root harness files have real versioning/backup risk.
* Hook safety is incomplete: several destructive command variants bypass the active guard.
* Graph tooling is installed, but current graph metadata/scope is suspect: Windows paths remain and runtime auth/test artifacts are included.
* Multi-agent workflow is documented well at a high level, but Zellij helper readiness is not verified in repo.
* No files were edited, no packages installed, no DB/dev-server/destructive commands run.

## B. Scope reviewed

| Area | Files/paths checked | Method | Confidence |
|---|---|---|---|
| Root harness | [AGENTS.md](/home/dax/Documents/arabica/roast/AGENTS.md:1), [CLAUDE.md](/home/dax/Documents/arabica/roast/CLAUDE.md:1) | Read with line numbers, rg patterns | High |
| Worktree tooling | [scripts/worktree.py](/home/dax/Documents/arabica/roast/scripts/worktree.py:1), [scripts/README.md](/home/dax/Documents/arabica/roast/scripts/README.md:1), [scripts/WORKTREE-TOOLING.md](/home/dax/Documents/arabica/roast/scripts/WORKTREE-TOOLING.md:1) | Help, dry-run, source read | High |
| Hooks/config | [.claude/settings.json](/home/dax/Documents/arabica/roast/.claude/settings.json:1), [.codex/hooks.json](/home/dax/Documents/arabica/roast/.codex/hooks.json:1), [.claude/hooks/](/home/dax/Documents/arabica/roast/.claude/hooks/myhospital_guard.py:1) | JSON parse, py_compile, smoke JSON events | High |
| Graph tooling | [.graphifyignore](/home/dax/Documents/arabica/roast/.graphifyignore:1), [graphifyignore](/home/dax/Documents/arabica/roast/graphifyignore:1), [docs/graphify-agent-guide.md](/home/dax/Documents/arabica/roast/docs/graphify-agent-guide.md:1), `graphify-out/manifest.json` | CLI help/version/check, manifest rg | High |
| Command runner | [justfile](/home/dax/Documents/arabica/roast/justfile:1) | `just --list`, source read | High |
| FE/BE local harness | [myhospital-fe/CLAUDE.md](/home/dax/Documents/arabica/roast/myhospital-fe/CLAUDE.md:1), [myhospital-be/CONVENTIONS.md](/home/dax/Documents/arabica/roast/myhospital-be/CONVENTIONS.md:1), `myhospital-be/.claude/settings.local.json` | Read selected harness only, git status/diff | Medium |
| Legacy artifacts | [scripts/legacy-powershell/README.md](/home/dax/Documents/arabica/roast/scripts/legacy-powershell/README.md:1) | Read labels, pattern search | Medium |

## C. Validation commands run

| Command | Result | Notes |
|---|---|---|
| `python scripts/worktree.py list` | OK | `No worktrees directory found.` |
| `python scripts/worktree.py --help` | OK | Commands present: `list`, `init-db-slots`, `create`, `sync-db`, `cleanup`, `sync-main`. |
| `python scripts/worktree.py create --slug audit-smoke --slot 1 --skip-db-sync --skip-fe-install --dry-run` | Failed | Raw `PermissionError` from socket port check. No create performed. |
| `python scripts/worktree.py sync-main --dry-run` | OK | Printed planned `restore`/`pull`; no real git mutation. |
| `python scripts/worktree.py sync-db --help`, `cleanup --help`, `init-db-slots --help` | OK | Help present but terse. |
| `printf 'no\n' \| python scripts/worktree.py sync-db --slot 1 --be-path myhospital-be --dry-run` | Exited 1 | Dry-run still prompts, contradicting docs. |
| `python -m json.tool .claude/settings.json .claude/settings.local.json .codex/hooks.json` | OK | JSON valid. |
| `env PYTHONPYCACHEPREFIX=/tmp/codex-pycache python -m py_compile ...` | OK | Hook/tool scripts compile. |
| `graphify --version` | OK | `graphify 0.8.39`. |
| `graphify --help`, `graphify hook-check --help`, `graphify check-update .` | OK | `check-update` silent exit 0. |
| `python .claude/hooks/graphify_stale_check.py .` | OK | Silent exit 0. |
| `just --list` | OK | Recipes: `agent-audit`, `graphify-help`, `status`, `worktree-help`. |
| `command -v graphify just zellij zorch zimpl zls zkillwt wtlist` | Partial | Found `graphify`, `just`, `zellij`; helper functions not visible in this shell. |
| `git status --short` at root | Failed | Root is not a Git repository. |
| `git status --short` in FE/BE | OK | FE clean; BE has modified `.claude/settings.local.json`. |
| Hook smoke JSON events | Mixed | Blocks `git reset --hard`, `rm -rf`, package install, FE `fetch`; misses `git -C ... reset --hard`, `git clean -fdx`, `rm -fr`. |

## D. Findings by severity

| ID | Severity | Area | Evidence | Why it matters | Recommended fix | Confidence |
|---|---|---|---|---|---|---|
| F01 | High | Root versioning | `git status --short` at root: `fatal: not a git repository`; root harness lives at [AGENTS.md](/home/dax/Documents/arabica/roast/AGENTS.md:220) | Core harness can drift with no normal Git audit trail. | Put root harness/tooling in a Git repo or add explicit backup/export workflow. | High |
| F02 | High | Worktree dry-run | Dry-run create crashed with `PermissionError`; code does real socket check at [worktree.py:256](/home/dax/Documents/arabica/roast/scripts/worktree.py:256) and create calls it at [worktree.py:429](/home/dax/Documents/arabica/roast/scripts/worktree.py:429) | Preview command can fail before showing plan; traceback is not user-grade. | In dry-run, skip socket probes or catch `OSError` as `ToolError`; add tests. | High |
| F03 | High | Hook safety | Smoke: `git -C myhospital-fe reset --hard`, `git clean -fdx`, `rm -fr ...` passed; regex at [myhospital_guard.py:63](/home/dax/Documents/arabica/roast/.claude/hooks/myhospital_guard.py:63) and [myhospital_guard.py:67](/home/dax/Documents/arabica/roast/.claude/hooks/myhospital_guard.py:67) is too narrow | Destructive variants bypass technical guard. | Tokenize shell commands or expand regex for `git -C`, `clean -fdx`, `rm -fr`, separators. | High |
| F04 | High | Graph scope/security | Manifest includes `docs/testing/screenshots/ipd-bed-r16/session-auth.json` at `manifest.json:12`; graph has `session-auth.json` node; ignore lacks `docs/testing/`, `*.har`, `*.json` exclusions at [.graphifyignore:28](/home/dax/Documents/arabica/roast/.graphifyignore:28) | Runtime auth/test artifacts can leak into graph context. | Exclude runtime captures/session JSON/HAR, purge/rebuild graph. | High |
| F05 | High | Graph freshness | Manifest still has `D:\arabica\roast\...` paths at `manifest.json:1-52`; stale checks were silent | Linux migration/path-scope drift may not be detected. | Rebuild graph on Linux; make stale-check detect ignore/path-root changes. | High |
| F06 | Medium | Hook/workflow contradiction | Claude hook says graphify before reading source at [.claude/settings.json:70](/home/dax/Documents/arabica/roast/.claude/settings.json:70); AGENTS says use `rg` for FE/BE code at [AGENTS.md:185](/home/dax/Documents/arabica/roast/AGENTS.md:185) | Agents may waste time or use graph for code it does not contain. | Scope hook to docs/specs/design questions, not all source reads. | High |
| F07 | Medium | Worktree rollback | FE/BE worktree adds are sequential at [worktree.py:444](/home/dax/Documents/arabica/roast/scripts/worktree.py:444) and [worktree.py:445](/home/dax/Documents/arabica/roast/scripts/worktree.py:445), no rollback block | Half-created worktree can remain after partial failure. | Add transactional create with cleanup/report of partial state. | Medium |
| F08 | Medium | `sync-db --dry-run` | Docs say dry-run previews at [WORKTREE-TOOLING.md:32](/home/dax/Documents/arabica/roast/scripts/WORKTREE-TOOLING.md:32); actual dry-run still prompts via [worktree.py:590](/home/dax/Documents/arabica/roast/scripts/worktree.py:590) | Automation cannot preview non-interactively as documented. | Pass `args.yes or args.dry_run` to confirmation. | High |
| F09 | Medium | DB infra behavior | `create --skip-db-sync` still calls `init_db_slots` at [worktree.py:528](/home/dax/Documents/arabica/roast/scripts/worktree.py:528) | “Light/no DB sync” can still start Docker DB infra. | Document clearly or add `--skip-db-init`. | High |
| F10 | Medium | Secrets/logging | `run()` prints full argv at [worktree.py:97](/home/dax/Documents/arabica/roast/scripts/worktree.py:97); SQL password is passed in argv at [worktree.py:623](/home/dax/Documents/arabica/roast/scripts/worktree.py:623) | Passwords can appear in logs/session transcript. | Redact sensitive argv/env values in command logging. | High |
| F11 | Medium | Slug validation | `safe_slug` allows dot-leading slugs at [worktree.py:70](/home/dax/Documents/arabica/roast/scripts/worktree.py:70); dry-run converted `"../Bad Slug!!"` to `worktrees/..-bad-slug` | Hidden/dot-ish worktree and branch names are confusing and risky. | Reject `.`/`..`, leading dots, repeated dot segments; require `[a-z0-9][a-z0-9-]*`. | High |
| F12 | Medium | Codex hook parity | [.codex/hooks.json:9](/home/dax/Documents/arabica/roast/.codex/hooks.json:9) only runs hardcoded graphify hook, no MyHospital guard | Codex-local config does not mirror Claude safety guard. | Add Codex-compatible guard or document that runtime sandbox is the only guard. | Medium |
| F13 | Low | justfile | [justfile:1](/home/dax/Documents/arabica/roast/justfile:1) forces `bash -lc`; recipes are minimal | Command runner is not fish-aligned and not a workflow front door. | Add shell-agnostic/Python recipes: `doctor`, `wt-list`, `wt-create-dry`, `graph-check`. | High |
| F14 | Low | Zellij helpers | Docs reference `zorch`/`zimpl` at [AGENTS.md:97](/home/dax/Documents/arabica/roast/AGENTS.md:97), but `command -v` only found `zellij`; no repo fish helper files found | User may not have expected helper commands. | Add helper install docs or checked-in fish functions; document fallback. | Medium |
| F15 | Nit | Slot defaults | Slot map includes 4 slots at [AGENTS.md:18](/home/dax/Documents/arabica/roast/AGENTS.md:18); `init-db-slots` defaults to `[1,2,3]` at [worktree.py:939](/home/dax/Documents/arabica/roast/scripts/worktree.py:939) | Small surprise when slot 4 is expected. | Default all four or document why slot 4 is opt-in. | High |

## E. Contradictions / ambiguities

| ID | Files/sections | Contradiction | Impact | Fix |
|---|---|---|---|---|
| C01 | [.claude/settings.json:70](/home/dax/Documents/arabica/roast/.claude/settings.json:70), [AGENTS.md:185](/home/dax/Documents/arabica/roast/AGENTS.md:185), [graphify guide:162](/home/dax/Documents/arabica/roast/docs/graphify-agent-guide.md:162) | Hook demands graphify before source reads; docs say graph is not for code navigation. | Workflow friction and wrong tool choice. | Scope hook to docs/specs only. |
| C02 | [.graphifyignore:3](/home/dax/Documents/arabica/roast/.graphifyignore:3), [AGENTS.md:189](/home/dax/Documents/arabica/roast/AGENTS.md:189), `graphify-out/manifest.json` | Docs promise harness/tooling tracking; manifest does not show scripts/hooks/settings, but does show testing auth artifact. | Graph scope is not what docs say. | Rebuild after tightening ignore. |
| C03 | [WORKTREE-TOOLING.md:32](/home/dax/Documents/arabica/roast/scripts/WORKTREE-TOOLING.md:32), [worktree.py:590](/home/dax/Documents/arabica/roast/scripts/worktree.py:590) | Dry-run described as preview path; `sync-db --dry-run` still prompts. | Non-interactive agents get stuck/cancel. | Treat dry-run as non-confirming preview. |
| C04 | [myhospital-fe/CLAUDE.md:13](/home/dax/Documents/arabica/roast/myhospital-fe/CLAUDE.md:13), [AGENTS.md:141](/home/dax/Documents/arabica/roast/AGENTS.md:141) | FE says ask user to run DTO regen; root says agent regenerates FE DTO/client after BE. | Cross-package tasks may stop unnecessarily. | Clarify: implementer may run regen inside worktree when task scope includes it. |
| C05 | [justfile:1](/home/dax/Documents/arabica/roast/justfile:1), [AGENTS.md:14](/home/dax/Documents/arabica/roast/AGENTS.md:14) | just uses bash; user-facing workflow emphasizes fish and shell-agnostic Python. | Minor portability mismatch. | Keep recipes as Python wrappers or document bash dependency. |
| C06 | [AGENTS.md:97](/home/dax/Documents/arabica/roast/AGENTS.md:97) | Helper commands expected but not present in repo and not visible to this shell. | Join/create session UX may fail. | Add helpers or a `scripts/zellij.py` wrapper. |

## F. Safety/security review

* Command injection risk in `worktree.py` is generally low because subprocess calls use argv lists, not `shell=True`.
* Path traversal is partially handled by `safe_slug`, but dot-leading/dot-segment slugs remain too permissive.
* Cleanup has confirmation and dirty-worktree guard, but uses `git worktree remove --force`; this is acceptable only with the current prompt.
* Hook guard is useful but incomplete. It fails open on invalid JSON and misses common destructive variants.
* Graph scope is the biggest exposure risk: runtime session JSON/HAR files are present under docs/testing and at least one session-auth file is already in graph output.
* SQL password defaults and `-P <password>` commands can be printed by `worktree.py` logging.
* No evidence of active PowerShell runtime in current docs; legacy PowerShell is labeled deprecated.

## G. Workflow fit review

* Linux/fish fit: mostly good in docs; active examples use fish fences. justfile and Claude inline hooks are shell-specific.
* Worktree create/join/cleanup fit: routing is clear, but create dry-run and sync-db dry-run need fixes before relying on automation.
* 1 worktree = 2 sessions fit: clearly documented in [AGENTS.md:92](/home/dax/Documents/arabica/roast/AGENTS.md:92).
* Orchestrator/implementer separation: documented in [AGENTS.md:203](/home/dax/Documents/arabica/roast/AGENTS.md:203), but no local tooling enforces roles.
* Zellij helper readiness: fallback docs exist; helpers were not found in this shell and no helper files were found in repo.
* Implementer-run dev server/build/regen behavior: FE validation docs say run dev server for visible UI, but workflow does not auto-start servers globally, which matches user preference.
* Root non-Git harness risk: confirmed. This should be treated as a workflow reliability risk, not a theoretical concern.

## H. Upgrade backlog

| Priority | Upgrade | Why | Suggested implementation | Effort | Risk |
|---|---|---|---|---|---|
| P0 | Tighten graph ignore and rebuild graph | Current graph includes session auth/runtime artifacts and Windows paths. | Add `docs/testing/**/*.har`, `docs/testing/**/session*.json`, `docs/session-notes/*.har`, sensitive JSON patterns; rebuild on Linux. | M | Low |
| P0 | Fix destructive hook guard false negatives | Current guard misses common destructive variants. | Tokenize commands with `shlex` or expand regex tests; add smoke fixtures. | S | Low |
| P0 | Fix worktree dry-run robustness | Preview must not traceback or prompt unexpectedly. | Catch socket errors, skip port probes in dry-run, make `sync-db --dry-run` non-interactive. | S | Low |
| P1 | Add root harness versioning/backup | Root is not Git-tracked. | Initialize separate root harness repo or add `scripts/harness_backup.py` plus documented backup target. | M | Medium |
| P1 | Add `scripts/harness_doctor.py` / `just doctor` | Single onboarding/check command is missing. | Check root Git status, graph scope, hooks JSON, helper availability, worktree CLI dry-runs. | M | Low |
| P1 | Add transactional worktree create | Avoid half-created FE/BE worktrees. | Track created resources and rollback on failure; print recovery commands. | M | Medium |
| P1 | Provide Zellij helper implementation | Docs refer to helpers but repo has none. | Add fish functions doc or Python wrapper: `zorch`, `zimpl`, `zls`, `zkillwt`, `wtlist`. | M | Low |
| P2 | Redact secrets in worktree logs | Avoid password leakage. | Redact argv keys following `-P`, env names containing password/token/secret. | S | Low |
| P2 | Harden slug validation | Avoid hidden/weird branch/path names. | Reject leading dot and dot segments; add `worktree.py validate-slug`. | S | Low |
| P2 | Improve just recipes | Current justfile is too thin. | Add `wt-list`, `wt-dry-create`, `graph-check`, `hooks-check`, `doctor`. | S | Low |
| P3 | Reduce duplicate graphify docs | AGENTS/CLAUDE duplicate sections. | Keep one canonical graph section and short pointers. | S | Low |

## I. Quick wins

* Change `sync_db` confirmation to use `args.yes or args.dry_run`.
* Catch `OSError` around `is_port_listening` and render `ERROR:` instead of traceback.
* Add graph ignore entries for HAR/session JSON/runtime screenshots before next graph rebuild.
* Add hook smoke tests for `git -C ... reset --hard`, `git clean -fdx`, `rm -fr`.
* Add `*.har` and `docs/testing/screenshots/**/session*.json` to graph ignores.
* Add `just doctor` that only runs non-destructive checks.
* Document that `--skip-db-sync` still starts DB slot, or add `--skip-db-init`.

## J. Questions for user

* Are `zorch`, `zimpl`, `zls`, `zkillwt`, and `wtlist` installed as fish functions outside this repo?
* Do you want root harness files versioned in a new root Git repo, or backed up into one of the existing repos?
* Should `docs/testing/**` ever be in graphify scope, or should graphify be limited to `harness/rules`, `docs/tasks`, and `specs`?

## K. Final recommendation

Use the harness for manual, supervised work, but do **not** rely on it as a fully safe autonomous workflow yet.

First three priorities I would handle:

1. Fix graph scope and rebuild on Linux, because auth/runtime artifacts and Windows manifest paths are concrete evidence of drift.
2. Fix hook guard false negatives for destructive commands.
3. Fix worktree dry-run behavior and add a `doctor` command so every new session can verify the harness without creating worktrees or touching DB/dev servers.
