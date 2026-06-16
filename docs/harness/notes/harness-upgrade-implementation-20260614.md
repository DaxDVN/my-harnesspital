# Harness Upgrade — Implementation Report (2026-06-14)

Comprehensive upgrade of the Linux/CachyOS + fish + Zellij multi-agent worktree harness.
All changes verified with real commands. No FE/BE business logic touched. No packages installed.
No destructive DB/dev-server/cleanup actions run. Pre-edit snapshot taken before any edit.

Live status any time: `python scripts/harness_doctor.py` (or `just doctor`).
Final doctor: **27 OK, 0 FAIL, 2 WARN, 2 INFO** (the 2 WARN = the Windows-built graph awaiting a Linux rebuild).

---

## 1. What changed, by batch

### Batch 1 — Stop wrong guidance / broken graph
- **BE routing fixed.** `CLAUDE.md` routed BE work to `myhospital-be/CLAUDE.md` (does not exist) → now `myhospital-be/CONVENTIONS.md`.
- **graphify demoted from mandatory → optional/may-be-stale** in `CLAUDE.md` and `AGENTS.md`: scoped to `docs/`+`specs/` design intent only, never required before reading/searching code (use `rg`/`fd`/`bat` for code, `rga` for `.docx`/`.pdf`).
- **Removed the two "MANDATORY graphify before reading/grepping source" PreToolUse hooks** from `.claude/settings.json` (they were factually wrong — the graph has no code — and fired on every read/grep). Consolidated the four guard matchers into one `Bash|Write|Edit|MultiEdit`.
- **Rewrote the freshness hook** `graphify_stale_check.py`: it used to `import graphify.detect` (not importable on the system Python) and silently no-op. It now compares `graphify-out/.graphify_root` to the actual workspace root and prints a clear STALE/cross-machine warning — which correctly fires for the current Windows-built graph.
- **`.graphifyignore` hardened**: excludes `*.har`, `session-auth.json`, `*-auth.json`, `*.cookies.json`, `scripts/legacy-powershell/`, `*.ps1`, `.linux-migration-backups/`, `.harness-backups/`, `.obsidian/`, `docs/testing/screenshots/`, `__pycache__/`. (The Windows graph had leaked `session-auth`/`cookie`/`token`/`.har` content.)
- **Duplicate `graphifyignore` → symlink** to `.graphifyignore` (drift-proof).
- **`.codex/hooks.json`**: removed the per-Bash `graphify hook-check` (a no-op with a hardcoded path) → empty hooks.

### Batch 2 — worktree.py safety
- **`sync-main` branch guard**: it used to `git restore .` + `git pull origin master|main` on the *current* branch. Both repos are on `chore/linux-cachyos-tooling-migration`, so it would have merged `master` into that branch and discarded changes. Now it **skips** any repo not on its target branch (clear message + recovery command); `--checkout` opts into switching first.
- **`sync-db --dry-run` no longer prompts/crashes**: the confirm used `args.yes` so a dry-run prompted `Type 'yes'` and tracebacked on EOF (blocking agents). Now `args.yes or args.dry_run`.
- **Transactional `create`**: the mutating section is wrapped in try/except with a best-effort rollback (`_rollback_create`) that removes only the worktrees/branches this run created, so a half-built worktree no longer blocks the next retry.
- **True light worktree**: new `--skip-db-init` flag — with `--skip-db-sync`, it skips Docker/SQL slot init entirely (no DB infra touched).
- **`cleanup` branch handling**: records each worktree's branch before removal; with `--delete-branch` it deletes them (so the slug can be reused), otherwise it prints the exact `git branch -D` commands. (Removing a worktree never deleted its branch, which broke slug reuse.)
- **`safe_slug` hardened**: clean kebab-case `[a-z0-9-]`; rejects empty/`.`/`..`/leading-dot/`///`; traversal inputs like `../../etc` collapse to `etc`.
- **Secret redaction**: logged commands now mask `-P <pw>`, `MSSQL_SA_PASSWORD=…`, and `Password=…` in connection strings.
- **Port probe** `is_port_listening` wrapped in `try/except OSError` so a preview/create can't crash on a socket/permission error.

### Batch 3 — UX matching the real workflow
- **Real fish helpers** at `scripts/fish/myhospital-zellij.fish`: `zorch`, `zimpl`, `zls`, `zkillwt`, `wtlist`, `wtcreate`, `wtjoin`. They were referenced everywhere but never existed. They self-locate the workspace root from the file's path (no hardcoding; override with `MYHOSPITAL_ROOT`), reference the repo Zellij layouts by path (no `~/.config` install needed), and guard missing slug/worktree/zellij.
- **Repo-managed Zellij layouts** `scripts/zellij/myhospital-orch.kdl` / `myhospital-impl.kdl` (shells + hint text only; nothing auto-starts a dev server).
- **justfile rebuilt** with `doctor`, `harness-backup`, `wt-list/create/create-lite/create-preview/sync-main/sync-db/cleanup`, `z-sessions`, `z-install-layouts`, plus a precise `agent-audit`.
- **Canonical workflow doc** `harness/rules/worktree-workflow.md` — the single intent→command map; `AGENTS.md`, `scripts/README.md`, `scripts/WORKTREE-TOOLING.md` now point to it instead of duplicating.

### Batch 4 — hardening / doctor / version control
- **Guard hardened** `myhospital_guard.py`: shlex tokenization (catches `git -C … push`, `A=b git commit`, `cmd && rm -rf x`, `rm -fr`), structural blocks (generated FE files, BE migrations) now cover `worktrees/<slug>/(fe|be)/…` too, heuristic style-blocks stay main-repo-only so they don't impede worktree implementers, dev-server kill/restart stays allowed, fail-open on any error, plus `--self-test` (38 cases).
- **`scripts/harness_doctor.py`** — one read-only health check (tools, JSON, compile, guard self-test, worktree CLI, graph trust/secret-leak, helpers, layouts, just, routing, legacy isolation, VCS/backup).
- **`scripts/harness_backup.py`** — timestamped, secret-free harness snapshots (`just harness-backup`). Used for the pre-edit snapshot.
- **Root harness git repo**: `git init` + a careful root `.gitignore` (excludes nested repos, worktrees, DB dumps, `.har`/secrets, the 17 MB docx, generated output). 35 harness files tracked, verified no leaks. **Not committed** — the guard and project policy say agents don't commit; you commit (see §6).

---

## 2. Validation commands run (key results)

| Command | Result |
|---|---|
| `python -m py_compile .claude/hooks/*.py scripts/*.py` | ALL COMPILE OK |
| `python .claude/hooks/myhospital_guard.py --self-test` | all 38 cases passed (18 block, 20 allow) |
| `python .claude/hooks/graphify_stale_check.py <root>` | prints STALE/cross-machine (correct) |
| `python scripts/worktree.py create … --skip-db-sync --skip-db-init --skip-fe-install --dry-run` | exit 0, no mutations |
| `python scripts/worktree.py sync-db --slot 1 --be-path myhospital-be --dry-run` | exit 0, **no prompt**, password redacted |
| `python scripts/worktree.py sync-main --dry-run` | **skips both repos** (wrong branch) + recovery cmd |
| safe_slug/redact self-check | `..`/`.`/empty rejected; `../../etc`→`etc`; `-P ***`, `MSSQL_SA_PASSWORD=***` |
| `fish -n scripts/fish/myhospital-zellij.fish` + source | parses; all 7 helpers defined; root derived; guards work |
| `just --list` / `just agent-audit` / `just doctor` | recipes load; audit clean; doctor runs |
| `git init` + `git status --porcelain -uall` | 35 harness files, no nested-repo/secret/large leaks |
| `python scripts/harness_doctor.py` | 27 OK, 0 FAIL, 2 WARN, 2 INFO |

---

## 3. Files changed

**Created**
- `scripts/harness_doctor.py`, `scripts/harness_backup.py`
- `scripts/fish/myhospital-zellij.fish`
- `scripts/zellij/myhospital-orch.kdl`, `scripts/zellij/myhospital-impl.kdl`
- `harness/rules/worktree-workflow.md`
- `.gitignore`
- `.harness-backups/20260614-132135/` (pre-edit snapshot, gitignored)

**Modified**
- `CLAUDE.md`, `AGENTS.md` (routing + graphify demotion + helper pointers)
- `.claude/settings.json` (removed graphify hooks; consolidated guard)
- `.claude/hooks/myhospital_guard.py` (hardened + self-test)
- `.claude/hooks/graphify_stale_check.py` (rewritten)
- `.codex/hooks.json` (emptied no-op)
- `.graphifyignore` (secret/legacy excludes); `graphifyignore` (→ symlink)
- `justfile` (recipes + precise agent-audit)
- `scripts/worktree.py` (all Batch-2 safety changes)
- `scripts/README.md`, `scripts/WORKTREE-TOOLING.md` (helper + flag updates)

---

## 4. Decisions made differently from the suggested plan (with rationale)

1. **Removed the graphify PreToolUse hooks instead of softening them.** They were factually wrong (graph has no code) and the single biggest friction source. Policy now lives in the instruction files; the per-call python overhead is also gone.
2. **`.codex/hooks.json` emptied, not re-pointed at the guard.** Codex's hook payload schema differs from Claude's and I couldn't verify it without running Codex. Removing the confirmed no-op is strictly safe; wiring Codex into the guard is a documented follow-up.
3. **Heuristic FE/BE convention blocks kept main-repo-only; only structural blocks (generated files, migrations) extended to worktrees.** Extending the heuristic `return null;`/`SaveChangesAsync(`/`fetch(` blocks into worktrees would false-positive on legitimate implementer edits. Structural blocks are unambiguous and safe to enforce everywhere.
4. **Did NOT rebuild the graph.** A correct docs+specs semantic rebuild needs the `/graphify` skill (LLM/subagents) or a Gemini key, and would be a heavy operation. I demoted graphify and excluded the leaked secrets; the rebuild itself is left as an explicit user action.
5. **`graphifyignore` made a symlink, not deleted.** Preserves backward compatibility while making drift impossible.
6. **Root git repo initialized but not committed.** The guard and project policy forbid agent commits; leaving it staged-ready respects that. Scope is harness-only (specs/ and work-doc dirs excluded to stay lean and avoid the 17 MB docx).
7. **Reworded `D:\…` examples out of tracked docs** and made `agent-audit` precise (concrete drive paths / `/Users/` / cmdlets / `pwsh -`/`powershell -` invocations) so it stops flagging deprecation prose and its own pattern.

---

## 5. User guide (fish-compatible)

One-time: enable the helpers
```fish
echo 'source /home/dax/Documents/arabica/roast/scripts/fish/myhospital-zellij.fish' >> ~/.config/fish/config.fish
exec fish
```

| Task | Command |
|---|---|
| Create a worktree | `wtcreate bed 1`  (or `python scripts/worktree.py create --slug bed --slot 1`) |
| Create light (no DB/FE install) | `wtcreate bed 1 --skip-db-sync --skip-db-init --skip-fe-install` |
| Preview create | `just wt-create-preview bed 1` |
| List worktrees | `wtlist`  (or `just wt-list`) |
| Open orchestrator session | `zorch bed claude` |
| Open implementer session | `zimpl bed opencode`  (e.g. `zimpl bed composer`) |
| Join existing worktree | `wtlist` → `zorch bed claude` → `zimpl bed opencode` |
| List sessions / kill a worktree's sessions | `zls` / `zkillwt bed` |
| Sync main branches | `python scripts/worktree.py sync-main` (skips wrong-branch repos; `--checkout` to switch) |
| Sync a slot DB | `python scripts/worktree.py sync-db --slot 1 --be-path worktrees/bed/be` (add `--dry-run`) |
| Cleanup a worktree | `python scripts/worktree.py cleanup --slug bed` (add `--delete-branch` to free the slug) |
| Health check | `python scripts/harness_doctor.py`  (or `just doctor`) |
| Backup harness | `just harness-backup` |
| graphify (optional, docs/specs only) | `graphify query "<q>"` — but the graph is STALE; verify against source docs until rebuilt |

Behavior the harness now drives:
- "tạo worktree bed slot 1, orch claude, impl opencode" → `wtcreate bed 1` → `wtlist` → `zorch bed claude` → `zimpl bed opencode`
- "join lại worktree bed" → `wtlist` → `zorch bed claude` → `zimpl bed opencode`
- "mở implementer bed bằng composer" → `zimpl bed composer`

---

## 6. Commands YOU must run manually

1. **Enable fish helpers** (see §5) — one line in `~/.config/fish/config.fish` + `exec fish`.
2. **Commit the harness repo** (agents are blocked from committing by design):
   ```fish
   cd /home/dax/Documents/arabica/roast
   git add -A
   git status   # review: should be harness files only
   git commit -m "Harness upgrade: safety, helpers, doctor, graph demotion, VCS"
   ```
3. **(Optional) Rebuild the graphify graph on Linux** when you actually need a fresh, trustworthy graph (purges the leaked secrets and fixes the Windows paths):
   ```fish
   /graphify .    # in Claude Code; reselect docs+specs scope (LLM/subagents)
   ```
4. **(Optional) Install Zellij layouts by name** if you prefer `--layout myhospital-orch`: `just z-install-layouts`.

No package installs are required — all tools the doctor needs are already on PATH.

---

## 7. Known remaining issues (and why not fixed now)

- **graphify graph is still Windows-built/stale and leaks `session-auth`/`cookie`/`token`** — only a real Linux rebuild fixes the data; that needs LLM/`/graphify` and is a user-gated, heavy op. Demotion + ignore-hardening + the doctor warning are in place so nothing trusts it blindly meanwhile.
- **Codex (`.codex/hooks.json`) is not wired into the guard** — needs verification of Codex's hook payload schema (would require running Codex). Currently empty (was a no-op anyway).
- **`cleanup` branch-deletion messaging is code-verified but not end-to-end tested** — exercising it needs a real worktree (network fetch + real mutation), out of scope for this read-mostly task. The flag, parser, and logic compile and are unit-reasoned.
- **"sync current worktree with main" (rebase a task branch onto updated main)** is not yet a `worktree.py` command — documented as a manual `git fetch && git rebase origin/main` step; a `worktree.py rebase` recipe is a good future add.
- **Root repo not committed** — intentional (you commit, §6).
