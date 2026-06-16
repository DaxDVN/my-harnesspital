# Independent Harness Review Report

> Independent, evidence-based review of the agent/dev-workflow harness for the MyHospital workspace.
> Date: 2026-06-14. Reviewer session: independent (did NOT read or compare against any other session's review output).
> Method: read-only audit — no files modified, no packages installed, no destructive/dev-server/migration commands run.
> Scope root: `/home/dax/Documents/arabica/roast`.

## A. Executive summary

- **Overall verdict: USABLE WITH ISSUES.** The *worktree/dev-workflow* core is genuinely solid and safe; the *knowledge-graph (graphify)* layer is effectively broken on Linux; and there are a few doc contradictions that will actively misroute agents.
- **The worktree tooling is the strongest part.** `scripts/worktree.py` uses argv lists everywhere (no `shell=True`), a single correct `dry_run` gate (verified: dry-run does **not** fetch, worktree-add, touch Docker, restore, or write files), is cwd-independent, validates SQL identifiers, and gates `cleanup`/`sync-db`/`sync-main` behind confirmation. Both dry-runs ran clean.
- **The graphify subsystem is a stale Windows artifact.** `graphify-out/.graphify_python` = `C:\Users\daxng\...python.exe`, `.graphify_root` = `D:\arabica\roast`, and `graph.json`/`manifest.json` contain 29/134 `D:\arabica` paths. The graph was built on Windows and **never rebuilt on Linux**, yet CLAUDE.md/AGENTS.md mandate it as the first step and hooks enforce it.
- **The advertised "freshness automation" is a permanent silent no-op.** The SessionStart hook does `import graphify.detect`, which fails with `ModuleNotFoundError: No module named 'graphify'` on the system `python`; it swallows the error and returns 0. The `[graphify] … STALE …` line the harness tells every agent to trust **can never print**.
- **Active routing contradiction:** root `CLAUDE.md` says "obey `myhospital-be/CLAUDE.md`" — that file does **not exist** (the real one is `myhospital-be/CONVENTIONS.md`, which AGENTS.md correctly references). An agent following CLAUDE.md's routing finds nothing.
- **`sync-main` is branch-naive and currently risky:** both sub-repos are checked out on `chore/linux-cachyos-tooling-migration`, not `master`/`main`, yet `sync-main` runs `git restore .` + `git pull origin master|main` against whatever HEAD is, with no checkout — it would merge origin/master **into the migration branch** and discard its working changes.
- **The `zorch/zimpl/zls/wtlist/zkillwt` helpers don't exist** (not on PATH, not fish functions, not defined anywhere in-repo — only *referenced* in 3 docs). The verbose `zellij … --layout` fallback **does** work (the `myhospital-orch.kdl`/`myhospital-impl.kdl` layouts exist), but the "join existing" flow instructs bare `zorch bed claude` with no fallback.
- **Linux/fish migration of *active* rules is essentially complete** — PowerShell survives only as a clearly-labeled `scripts/legacy-powershell/` archive; the smoke script is stdlib-only; no Windows/macOS paths leak into active rules (only into the graphify artifacts and one detection regex).
- **Net:** safe to use for the worktree/dev workflow today. Do **not** trust or mandate the graph layer until it's rebuilt on Linux. Fix the BE routing line and the `sync-main` branch assumption before relying on the harness end-to-end.

## B. Scope reviewed

| Area | Files/paths checked | Method | Confidence |
|---|---|---|---|
| Root instructions | `AGENTS.md`, `CLAUDE.md` | Full read (context) + rg | High |
| Worktree tooling | `scripts/worktree.py` (1014 lines) | Full read + `--help`/`list`/dry-runs | High |
| Tooling docs | `scripts/README.md`, `scripts/WORKTREE-TOOLING.md` | Full read | High |
| Claude hooks | `.claude/hooks/myhospital_guard.py`, `graphify_stale_check.py` | Full read + py_compile + import test | High |
| Hook/settings config | `.claude/settings.json`, `settings.local.json`, `.codex/hooks.json` | Full read + json.tool + runtime probe | High |
| Command runner | `justfile` | Full read + `just --list` | High |
| Graph ignore | `.graphifyignore`, `graphifyignore` | Full read (both) | High |
| Graph tooling | `graphify` CLI, `graphify-out/*` (manifest, .graphify_python/_root) | `--help`, version, check-update, grep artifacts | High |
| Graph guide | `docs/graphify-agent-guide.md` | Full read | High |
| Helpers/sessions | `zorch/zimpl/zls/wtlist/zkillwt`, zellij layouts, tools on PATH | `fish type`, `command -v`, layout `ls` | High |
| Sub-repo settings | `myhospital-be/.claude/*`, `myhospital-fe/CLAUDE.md` | find + json.tool + existence | High |
| Legacy/backup | `scripts/legacy-powershell/`, `_db-backups/`, `.linux-migration-backups/` | Shallow `ls` (read-only context) | Med |
| Smoke script | `scripts/careflow_ba_fixes_smoke.py` | Header read + destructive-op grep | High |
| FE/BE git state | branch of each sub-repo | `git -C … rev-parse` | High |

Deliberately **not** scanned deeply: `worktrees/` (empty anyway), `node_modules/`, `.git/`, `bin/obj/dist`, FE/BE source, the 17 MB specs `.docx`. No other session's review output was read.

## C. Validation commands run

| Command | Result | Notes |
|---|---|---|
| `git rev-parse --is-inside-work-tree` (root) | `fatal: not a git repository` | Root harness is untracked |
| `python scripts/worktree.py --help` / `list` | OK / "No worktrees directory found." | 6 subcommands present; zero worktrees exist |
| `worktree.py create … --dry-run` | OK, mutating cmds only echoed | Verified safe: no fetch/add/docker/write |
| `worktree.py sync-main --dry-run` | OK, `restore`/`pull` only echoed | Read-only `ls-files` ran; mutations skipped |
| `just --list` | 4 recipes | agent-audit/graphify-help/status/worktree-help |
| `graphify --version` / `--help` | `0.8.39` | `query/affected/check-update/label` exist; `hook-check` not in help |
| `python -c "import graphify.detect"` | `ModuleNotFoundError: No module named 'graphify'` | **Freshness hook dependency missing** |
| `graphify hook-check </dev/null` | exit 0, empty | `.codex/hooks.json` target = silent no-op |
| `graphify check-update .` | exit 0, empty | Silent (manifest is Windows-keyed) |
| `cat graphify-out/.graphify_python` / `_root` | `C:\Users\daxng\…python.exe` / `D:\arabica\roast` | **Windows-built artifacts** |
| `grep -c 'D:\\arabica' graph.json / manifest.json` | 29 / 134 | Graph citations are Windows paths |
| `python3 -m json.tool` ×3 | all OK | settings/local/codex valid JSON |
| `python3 -m py_compile` ×4 | all OK | worktree, both hooks, smoke compile |
| `fish type -q zorch|zimpl|zls|wtlist|zkillwt` | all MISSING | helpers undefined |
| `ls ~/.config/zellij/layouts/myhospital-{orch,impl}.kdl` | both present | fallback path works |
| existence: `myhospital-be/CLAUDE.md` | MISSING (CONVENTIONS.md exists) | routing contradiction |
| `git -C myhospital-{fe,be} rev-parse --abbrev-ref HEAD` | `chore/linux-cachyos-tooling-migration` (both) | not on master/main |

## D. Findings by severity

| ID | Severity | Area | Evidence | Why it matters | Recommended fix | Confidence |
|---|---|---|---|---|---|---|
| F1 | High | Graph | `.graphify_python`=`C:\Users\daxng\…`, `.graphify_root`=`D:\arabica\roast`; `grep D:\arabica` → graph.json 29, manifest.json 134 | Graph mandated as first step (CLAUDE.md/AGENTS.md) + enforced by hooks, but its `src=` citations are Windows paths that don't exist on Linux, and the manifest can't match Linux files → navigation broken, refresh broken | Rebuild graph on Linux from current root (`/graphify .` with docs+specs scope), or **demote** graphify from "mandatory" to "optional, may be stale" until rebuilt | High |
| F2 | High | Hooks | `graphify_stale_check.py:20-23` + `python -c import graphify.detect` → ModuleNotFoundError; hook uses bare `python` | "Freshness automation" both docs advertise is a permanent silent no-op; agents told to trust a STALE banner that never appears | Call `graphify check-update .` (binary) instead of importing the module, or point the hook at graphify's own interpreter; or remove the claim from the docs | High |
| F3 | High | Docs/Routing | root `CLAUDE.md` "obey `myhospital-be/CLAUDE.md`" → file MISSING; real file `myhospital-be/CONVENTIONS.md` EXISTS; AGENTS.md is correct | Any agent routing BE work via CLAUDE.md loads no conventions → BLOCK/WARN rules silently skipped | One-line fix: CLAUDE.md → `myhospital-be/CONVENTIONS.md` | High |
| F4 | High | Worktree | `worktree.py:878-905` (`restore .`, `pull origin master|main`, no checkout) + both repos on `chore/linux-cachyos-tooling-migration` | `sync-main` merges origin/master **into the migration branch** and `restore .` discards its changes — silent wrong-branch mutation | Add a guard: verify HEAD == target branch (or `checkout` first); abort + report if mismatch | High |
| F5 | High | Hooks/Docs | `settings.json:61,70` ("MANDATORY graphify before reading/grepping source") vs `graphify-agent-guide.md:39,162-165` ("graph has NO code; use rg for code") | The Read/Bash hooks (which also tell **subagents** to comply) force a graph query before reading code the graph can't describe; pure friction + wrong guidance | Restrict the hook to `docs/`+`specs/` paths only; drop "applies to subagents"; align wording with the guide | High |
| F6 | Medium | Sessions | `fish type` all MISSING; `rg` finds defs only in docs; AGENTS.md:127-134 / README:102-110 use bare `zorch/zimpl` with no fallback | Agents instructed to run `zorch bed claude` get "command not found"; only the verbose zellij form works | Define `zorch/zimpl/zls/wtlist/zkillwt` as fish functions (ship `scripts/fish/` + sourcing note) **or** replace doc usages with the working `zellij … --layout` fallback | High |
| F7 | Medium | Worktree | `cleanup()` 816-864 removes worktrees but never deletes `feature/<slug>`; `create()` 420-427 aborts if branch exists | After cleanup, re-`create` with the same slug fails ("branch already exists") — confusing dead-end | Add `git branch -D feature/<slug>` to cleanup (guarded) or a `--keep-branch/--delete-branch` flag; document the reuse path | High |
| F8 | Medium | Worktree | `create_worktree` 442-497: FE `worktree add` (444) then BE (445), env writes, copies — no try/rollback; 404-405 blocks re-run | A mid-run failure (e.g., BE add fails, npm fails) leaves a half-built `worktrees/<slug>` that blocks retry and needs manual `git worktree remove` | Wrap in try/except that rolls back created worktrees+folder on failure, or print exact recovery commands | High |
| F9 | Medium | Security | `safe_slug` 70-76 keeps `.`; `safe_slug('..')` → `'..'` (slashes→`-`, dots kept) | Weak path hygiene; `..`/leading-dot slugs reach `root/worktrees/<slug>` (downstream `.exists()` blunts it, not clean defense) | Reject slugs that are `.`/`..`/empty-after-strip or start with `.`; cap length | High |
| F10 | Medium | Docs | `rg '/home/dax'` → AGENTS.md (≥9), README/WORKTREE-TOOLING fallbacks, guide, `.codex/hooks.json`; vs AGENTS.md:220 "Prefer relative paths" | Hardcoded user-home root makes the harness non-portable and contradicts its own rule; breaks if workspace moves/cloned | Use a `WORKSPACE_ROOT`/`$PWD` convention in docs; keep absolute only where copy-paste truly needs it | High |
| F11 | Medium | Hooks | `myhospital_guard.py:81-97` regex targets `myhospital-fe|be/...`; real edits live in `worktrees/<slug>/...` (no match); default implementer is `opencode` (doesn't run Claude hooks) | The convention guard does **not** fire where work actually happens; net value reduces to main-repo protection (already off-limits) + Bash patterns | Either match `(worktrees/[^/]+/)?(fe\|be)/…` or document the guard as orchestrator-only main-repo protection; don't rely on it for worktree conventions | High |
| F12 | Low | Graph | Two near-identical ignore files (`.graphifyignore` 885B, `graphifyignore` 632B "compatibility copy") | Drift risk; graphify reads only the dotfile, so the copy is dead weight that can diverge silently | Delete `graphifyignore` (or symlink), keep `.graphifyignore` only | High |
| F13 | Low | Hooks | `.codex/hooks.json:9` runs `/home/dax/.local/bin/graphify hook-check`; not in `--help`; exit 0 empty | Per-Bash no-op for Codex; hardcoded abs path breaks if graphify moves; gives a false sense of enforcement | Replace with a real check or remove; use `graphify` from PATH not abs path | High |
| F14 | Low | Security | `worktree.py:26` `DEFAULT_SQL_PASSWORD="Hospital123!"` hardcoded (env-overridable) | Local-dev SA credential in source; copied into worktree `.env` connection strings | Acceptable for local dev; note it; prefer env-only with a clear error if unset | High |
| F15 | Low | Perf/Maint | `settings.json` runs `myhospital_guard.py` + an inline `python3 -c` on every Bash, and a `python3 -c` on every Read/Glob | 1–2 python cold-starts per tool call (latency); giant inline JSON one-liners are untestable/unmaintainable | Consolidate into one small hook script per event; move inline logic into a file | Med |
| F16 | Low | Graph scope | `grep '.ps1' graph.json` → 2; `.linux-migration-backups/` not in `.graphifyignore` (only `*.bak-…` files are) | Deprecated/backup artifacts can leak into a "design-intent" graph | Add `scripts/legacy-powershell/`, `.linux-migration-backups/`, `*.ps1` to `.graphifyignore` | Med |
| F17 | Low | Runner | `justfile:14` `agent-audit` greps `scripts` → always hits `legacy-powershell/*.ps1`; omits `.codex`, `justfile`, `myhospital-fe` | Self-defeating audit (permanent false hits), incomplete coverage | Exclude `scripts/legacy-powershell`; add `.codex`/`justfile`/FE; or invert to "fail if matches outside legacy" | High |
| F18 | Nit | Hooks | `settings.json:70` extension test is substring: `.js` ∈ `.json`, `.c` ∈ `.codex`, `.ts` ∈ many words | Graph "MANDATORY" banner fires on JSON/config reads unrelated to the graph (observed this session) | Match real extensions (`os.path.splitext`), not substrings | High |
| F19 | Nit | Residue | `myhospital-be/.claude/projects/-Users-thuannguyen-MyHospital-…` | macOS contributor session-history residue; harmless | Optional cleanup | High |
| F20 | Nit | Docs | guide:119,135,244 use `graphify codex/claude install`; CLI form is `graphify install --platform <p>` | Likely outdated syntax (not re-tested to avoid mutating); `graphify label` *is* valid | Update guide to `graphify install --platform …`; verify before shipping | Med |

## E. Contradictions / ambiguities

| ID | Files/sections | Contradiction | Impact | Fix |
|---|---|---|---|---|
| C1 | `CLAUDE.md` Routing vs `AGENTS.md` Scope Routing vs filesystem | CLAUDE.md → `myhospital-be/CLAUDE.md` (missing); AGENTS.md → `CONVENTIONS.md` (exists) | **Active** — BE conventions not loaded via CLAUDE.md path | Fix CLAUDE.md to `CONVENTIONS.md` |
| C2 | `settings.json:61,70` vs `graphify-agent-guide.md:39,162-165` | Hooks: "MANDATORY graphify before reading code"; Guide: "graph has no code, use rg" | **Active** — every code read misrouted; subagents told to comply | Scope hook to docs/specs; align text |
| C3 | `AGENTS.md:220` vs AGENTS.md/README/guide bodies | "Prefer relative paths" vs pervasive `/home/dax/...` | Minor — portability/credibility | Relative-path the examples |
| C4 | `CLAUDE.md`/`AGENTS.md` "freshness flags STALE" vs `graphify_stale_check.py` | Hook is a dead no-op (module import fails) | **Active** — false trust in a non-existent signal | Fix hook or delete the claim |
| C5 | AGENTS.md/README/WORKTREE-TOOLING "Prefer helpers `zorch/zimpl`" vs reality | Helpers undefined everywhere; join-flow has no fallback | Medium — copy-paste commands fail | Define helpers or de-reference |
| C6 | `.graphifyignore` vs `graphifyignore` | Duplicate scope files, "compatibility copy" | Low — drift risk | Keep one |
| C7 | `AGENTS.md` Session Start Protocol vs state | "Ask which worktree at first prompt" but `worktrees/` doesn't exist (list: none) | Low — premise unsatisfiable on a fresh tree | Note "if none exist, offer to create"; (FE routing → `myhospital-fe/CLAUDE.md` is **consistent & correct** — no contradiction) |

## F. Safety/security review

- **Command injection: clean in the core.** `worktree.py` uses argv lists for every `subprocess.run` (e.g., 103-111, 281, 421); **no `shell=True`, no `os.system`, no f-string-into-shell**. The smoke script is stdlib `urllib` only (no subprocess). This is the single best safety property here.
- **Path traversal:** `safe_slug` neutralizes `/` (→`-`) but **keeps dots**, so `..`/leading-dot slugs survive (F9). Not cleanly exploitable (downstream `.exists()`/`git worktree add` constrain it), but it's a defense-in-depth gap worth closing.
- **SQL safety:** DB identifiers validated via `assert_safe_sql_name` (251-253) before interpolation (612); backup-derived schema/table names constrained by regex (562). Passwords passed as argv to `sqlcmd` (visible in `ps`, standard for the tool). Hardcoded SA password (F14).
- **Destructive ops are gated.** `cleanup` refuses on a dirty tree (829-840) then requires typing `yes` (842-849); `sync-db`/`sync-main` use `confirm_or_exit` (590, 885); `dry_run` auto-confirms but executes nothing. `worktree remove --force` is scoped to the worktree path. **`sync-main` is the one sharp edge** (F4): correctly warns "tracked changes may be lost," but is branch-naive against the current non-master/main HEAD.
- **Guard hook is a tripwire, not a boundary.** `myhospital_guard.py` is fail-open (empty/invalid stdin → allow, 47-52) and trivially bypassable (`git -C … push` evades the `git push` regex at 63; `rm -fr`/`rm --recursive` evade 67). It also checks `Remove-Item -Recurse` (a PowerShell cmdlet) in a Linux-only workspace. Treat it as a reminder for a cooperative agent, **not** a security control. It does usefully block `git commit/push/reset --hard/clean`, dependency installs, and editing generated/migration files.
- **Secrets/artifacts:** `_db-backups/` holds 19 `*.sql` data dumps at root (potentially sensitive seed data) — correctly excluded from the graph, but unversioned and unencrypted on disk. The graphify artifacts leak the prior Windows username/path (`C:\Users\daxng`, `D:\arabica`) — low impact (local), but confirms cross-OS staleness.
- **Durability risk (cross-cutting):** root is **not** a git repo, so `AGENTS.md`, `CLAUDE.md`, `scripts/`, and `.claude/` hooks have **no version control or rollback** at the workspace level. The only "backup" is the one-shot `.linux-migration-backups/` snapshot. A bad edit to `worktree.py` or the hooks is unrecoverable. This is the user's stated concern, and it's real.

## G. Workflow fit review

- **Linux/fish fit — Good.** Active rules are fully migrated; user-facing commands are fish-valid; automation is shell-agnostic Python; PowerShell exists only as a labeled archive. `just` uses `bash -lc` (acceptable for automation, but it's login-bash, not fish).
- **Worktree create/join/cleanup — Good with gaps.** `create`/`list`/`sync-db`/`sync-main`/`cleanup`/`init-db-slots` all present, dry-run-safe, cwd-independent, FE/BE handled as **separate** git repos (correct), port-in-use guard. Gaps: no rollback on partial create (F8), cleanup leaves branches that block reuse (F7).
- **1 worktree = 2 sessions — Documented and consistent** across AGENTS.md/README/WORKTREE-TOOLING, with correct `mh-<slug>-orch|impl-<tool>` naming. The mechanics (layouts) exist; the **shortcuts** (`zorch/zimpl`) don't (F6).
- **Orchestrator/implementer separation — Conceptually right, weakly enforced.** Default `claude` orchestrator + `opencode` implementer both resolve on PATH. But the Claude guard hooks only bind to the orchestrator session and only match main-repo paths, so **conventions aren't enforced on the implementer or inside worktrees** (F11). No hook blocks the implementer from killing/restarting a dev server (good — that workflow is unobstructed).
- **Zellij readiness — Mostly ready.** Layouts present and fallback commands valid; only the alias helpers are missing. No in-repo guidance on "am I already inside Zellij?" / `Ctrl+p` locked-mode caveat / kill-by-slug (`zkillwt`) — these are referenced or implied but absent.
- **Implementer-run build/dev/regen — Sound.** Docs correctly hand `dotnet run` / `npm run dtos:update` / `client:generate` / `dev` to the implementer; nothing auto-starts a dev server or infra monitor (matches the "no auto-start" rule). `create` does, by design, do destructive DB sync silently (`yes=True`, worktree.py:521) unless `--skip-db-sync`.
- **Root non-git — Functionally fine, durability-risky.** `worktree.py` only ever runs `git -C myhospital-fe|be` (never at root), so root-not-git doesn't break tooling; but harness files have no VCS (see F/durability).

## H. Upgrade backlog

| Priority | Upgrade | Why | Suggested implementation | Effort | Risk |
|---|---|---|---|---|---|
| P0 | Fix BE routing line in `CLAUDE.md` | F3/C1 — breaks BE convention loading | Replace `myhospital-be/CLAUDE.md` → `CONVENTIONS.md` | XS | None |
| P0 | Neutralize the broken graphify mandate | F1/F2/F5 — false trust + friction | Rebuild graph on Linux **or** demote to "optional/may be stale"; scope Read/Bash hooks to docs/specs; fix/disable the dead freshness hook | M | Low |
| P0 | Guard `sync-main` against wrong branch | F4 — silent wrong-branch merge + data loss | Assert/`checkout` target branch before `restore`/`pull`; abort+report on mismatch | S | Low |
| P1 | Put root harness under version control | Durability — no rollback for harness | `git init` at root with `.gitignore` (worktrees, node_modules, _db-backups, bin/obj, .env), or mirror `AGENTS/CLAUDE/scripts/.claude` to a tracked repo | S | Low |
| P1 | Resolve `zorch/zimpl/...` | F6/C5 — failing copy-paste commands | Ship `scripts/fish/helpers.fish` defining them + a "source this" note; or rewrite docs to the zellij fallback | S | Low |
| P1 | cleanup branch deletion + create rollback | F7/F8 — dead-ends / half-state | `--delete-branch` in cleanup; try/except rollback in create | M | Low |
| P2 | `scripts/harness_doctor.py` + `just doctor` | One command to surface every issue above | Checks: root-git, graph Linux-freshness (`.graphify_root`==cwd), `import graphify.detect` reachable, helper/layout presence, routing-target existence, tool PATH, JSON valid, py_compile | M | Low |
| P2 | `scripts/workflow_doctor.py` | Validate worktree/session invariants | Verify slot map vs running containers, dangling branches, orphan worktrees, session naming | M | Low |
| P2 | De-dup ignore files + harden scope | F12/F16 | Delete `graphifyignore`; add legacy/backup excludes to `.graphifyignore` | XS | None |
| P2 | Harden `safe_slug` + relative-path docs | F9/F10 | Reject `.`/`..`/leading-dot; templatize root in docs | S | Low |
| P3 | Consolidate hooks into files | F15/F18 — perf + maintainability | One small `pretooluse.py`; fix extension matcher | S | Low |
| P3 | `agent-audit` recipe scope | F17 | Exclude legacy-powershell; widen targets | XS | None |
| P3 | Add `## Common inline requests → expected commands` doc | Faster, consistent agent dispatch | Table mapping VN/EN intents → exact `worktree.py`/zellij commands | S | None |

## I. Quick wins (safe, small, if you want them later)

1. **CLAUDE.md:** `myhospital-be/CLAUDE.md` → `myhospital-be/CONVENTIONS.md` (F3).
2. **Delete `graphifyignore`** (keep `.graphifyignore`) (F12).
3. **`.graphifyignore`:** add `scripts/legacy-powershell/`, `.linux-migration-backups/`, `*.ps1` (F16).
4. **`safe_slug`:** add `if value in {'.','..'} or value.startswith('.'): raise ToolError(...)` (F9).
5. **`justfile agent-audit`:** add `-g '!scripts/legacy-powershell/**'` and include `.codex justfile` (F17).
6. **Hook wording:** drop "MANDATORY" / "applies to subagents" and scope to docs/specs paths (F5) — removes the per-call noise.
7. **Replace `zorch bed claude`** in the join sections with the working `zellij --layout` fallback, or add the fish helpers (F6).

## J. Questions for user (only what cannot be self-verified)

1. **Graphify:** rebuild the graph on Linux now (needs an LLM/Gemini key or `/graphify` subagent run), or just **demote** it from "mandatory first step" and soften the hooks until you choose to rebuild?
2. **`sync-main` intent:** should it assume the main repos are checked out on `master`/`main` (add a guard that aborts otherwise), or actively `checkout` them first? They're currently on `chore/linux-cachyos-tooling-migration`.
3. **Migration branches:** is `chore/linux-cachyos-tooling-migration` meant to *become* master/main (i.e., the harness migration isn't merged yet)? That affects F4 and `create`'s `origin/master` base.
4. **Helpers:** define `zorch/zimpl/zls/wtlist/zkillwt` as fish functions (where should they live + be sourced?), or remove them from docs in favor of the verbose zellij fallback?
5. **Root VCS:** do you want the root harness put under git (scoped to harness files), or is it intentionally untracked and mirrored elsewhere?

## K. Final recommendation

- **Use it now for the worktree/dev workflow — yes.** The core tooling is safe, dry-run-honest, and shell-correct; `create/list/sync-db/cleanup` are trustworthy today (with `--dry-run` first for `sync-db`/`sync-main`).
- **Do not trust or mandate the graphify layer until rebuilt on Linux.** Right now it cites Windows paths and its freshness signal is dead; following the harness's "graphify-first" rule wastes effort and can mislead.
- **Fix before relying end-to-end:** the BE routing line, the `sync-main` branch assumption, and the graphify mandate/hooks.

**First 3 things to do (independent reviewer's priority):**
1. **F3 — fix the CLAUDE.md BE routing line** (1 character of risk, real correctness impact on every BE task).
2. **F1+F2+F5 — neutralize the broken graphify story:** demote it from "mandatory," scope the hooks to docs/specs, and fix-or-disable the dead freshness hook (then rebuild the graph on Linux when convenient). Removes both the false trust and the per-call friction.
3. **F4 + root VCS — make `sync-main` branch-safe and put the harness under version control** (the two places where the harness can silently lose work).

---

### Appendix — key evidence pointers (file:line)

- Dry-run gate: `scripts/worktree.py:97-99` (print-but-skip on `dry_run=True`).
- create flow: fetch `439-440`, worktree-add `444-445`, branch-exists abort `420-427`, folder-exists abort `404-405`, env writes `449-481`, db path `509-536`.
- cleanup: dirty guard `829-840`, confirm `842-849`, worktree remove `851-856`, no branch delete (whole fn `816-864`).
- sync-main: confirm `885-891`, `restore .` `904`, `pull origin <branch>` `905`, branch list hardcoded `880-883`.
- safe_slug: `70-76`. assert_safe_sql_name: `251-253`. DEFAULT_SQL_PASSWORD: `26`.
- guard Bash blocks: `61-69` (git -C bypass at `63`); path-scoped content blocks: `81-97`.
- settings.json hooks: guard binding `3-55`, inline graphify-grep `61`, Read|Glob graphify `70`, SessionStart `75-88`.
- graphify_stale_check import: `20-23`. `.codex/hooks.json` hook-check: `9`.
- graphify artifacts: `graphify-out/.graphify_python`, `.graphify_root`; `grep 'D:\\arabica'` graph.json=29, manifest.json=134; `grep '.ps1'` graph.json=2.
