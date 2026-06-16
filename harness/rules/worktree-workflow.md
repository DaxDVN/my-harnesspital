# Worktree + Zellij workflow — canonical reference

> Single source of truth for the multi-agent worktree workflow. `AGENTS.md` and
> `scripts/README.md` point here instead of duplicating it. User-facing commands
> are **fish**. Automation is `scripts/worktree.py` (shell-agnostic Python).

## Model

- **1 worktree = 2 Zellij sessions.** Orchestrator (read/plan/review/coordinate)
  and implementer (build/test/dev server/regen DTO+client). Never one giant session.
- Session names: `mh-<slug>-orch-<tool>` and `mh-<slug>-impl-<tool>`.
- Worktree layout: `worktrees/<slug>/fe` and `worktrees/<slug>/be`.
- Default tools: orchestrator `claude`, implementer `opencode` (override per request).
- **Nothing auto-starts a dev server.** Layout panes open shells with hint text only.
- `myhospital-fe/` and `myhospital-be/` (the main repos) are **never** edited directly.

## One-time setup (helpers)

The short commands (`zorch`, `zimpl`, `zls`, `zkillwt`, `wtlist`, `wtcreate`, `wtjoin`)
are fish functions. Source them once:

```fish
echo 'source /home/dax/Documents/arabica/roast/scripts/fish/myhospital-zellij.fish' >> ~/.config/fish/config.fish
exec fish
```

They self-locate the workspace root from the file's path (override with
`set -gx MYHOSPITAL_ROOT <path>`) and reference the repo Zellij layouts directly,
so no `~/.config` install is required. (Optional: `just z-install-layouts` also
installs the layouts by name.)

If the helpers are **not** sourced, use the fallback commands in the last column.

## Helper reference

| Helper | Does | Fallback (no helper) |
|---|---|---|
| `wtlist` | list worktrees | `python scripts/worktree.py list` |
| `wtcreate <slug> <slot> [flags]` | create worktree | `python scripts/worktree.py create --slug <slug> --slot <slot>` |
| `zorch <slug> [tool=claude]` | open orchestrator session | see fallback block below |
| `zimpl <slug> [tool=opencode]` | open implementer session | see fallback block below |
| `zls` | list `mh-*` sessions | `zellij list-sessions \| grep mh-` |
| `zkillwt <slug>` | kill that worktree's sessions | `zellij delete-session mh-<slug>-orch-<tool>` (per session) |
| `wtjoin <slug>` | validate + print open commands | `python scripts/worktree.py list` |

Session fallback (fish), run from the worktree dir:

```fish
cd /home/dax/Documents/arabica/roast/worktrees/<slug>
zellij attach mh-<slug>-orch-claude 2>/dev/null; or zellij --session mh-<slug>-orch-claude --layout ../../scripts/zellij/myhospital-orch.kdl
```

## Common inline requests → exact commands

| You say… | Agent runs |
|---|---|
| "tạo worktree bed slot 1, orch claude, impl opencode" | `wtcreate bed 1` → `wtlist` → `zorch bed claude` → `zimpl bed opencode` |
| "tạo worktree bed slot 2, light / no DB" | `wtcreate bed 2 --skip-db-sync --skip-db-init --skip-fe-install` |
| "preview worktree bed slot 1" | `python scripts/worktree.py create --slug bed --slot 1 --skip-db-sync --skip-db-init --skip-fe-install --dry-run` |
| "join lại worktree bed" | `wtlist` → `zorch bed claude` → `zimpl bed opencode` |
| "mở implementer bed bằng composer" | `zimpl bed composer` |
| "mở orchestrator bed bằng codex" | `zorch bed codex` |
| "cleanup worktree bed" | `python scripts/worktree.py cleanup --slug bed` (prompts; add `--delete-branch` to free the slug) |
| "kill sessions của bed" | `zkillwt bed` |
| "sync main branches" | `python scripts/worktree.py sync-main` (skips repos not on master/main; add `--checkout` to switch) |
| "reset DB slot 1 cho bed" | `python scripts/worktree.py sync-db --slot 1 --be-path worktrees/bed/be` (preview with `--dry-run`) |
| "run BE của bed" | `python scripts/worktree.py run-be --be-path worktrees/bed/be` or `just wt-run-be bed` (loads `.env` without shell-sourcing it) |
| "regen DTO FE sau khi BE contract đổi" | in `worktrees/bed/fe` (implementer): `npm run dtos:update` then `npm run client:generate` |

`just` equivalents also exist: `just wt-create bed 1`, `just wt-create-lite bed 1`,
`just wt-list`, `just wt-sync-main --dry-run`, `just wt-cleanup bed`, `just z-sessions`.

## CodeGraph index (per worktree)

Source-code exploration uses **CodeGraph**, indexed **per code repo** (full policy:
`harness/rules/source-discovery.md`). A worktree's `be`/`fe` are separate working
trees, so each gets its own `.codegraph/` index when the worktree becomes an active task.

| You say… | Agent runs |
|---|---|
| (after `wtcreate bed 1`) "index bed cho codegraph" | `just codegraph-init-worktree bed` → `codegraph init` in `worktrees/bed/be` + `.../fe` |
| "codegraph status của bed" | `just codegraph-status-worktree bed` |
| "sync codegraph bed" | `just codegraph-sync-worktree bed` (only if status shows stale) |

- After **create**, optionally `just codegraph-init-worktree <slug>` to build the index up
  front (otherwise the first `codegraph` call in that repo initializes lazily).
- On **join**, prefer `just codegraph-status-worktree <slug>`; init only if it reports no index.
- CodeGraph honors each repo's `.gitignore` and **auto-syncs on edit** (~2 s debounce), so you
  rarely re-init or re-sync by hand.
- The stable main repos are indexed once via `just codegraph-init-main`. **Never** index the
  workspace root (root `.gitignore` excludes FE/BE/worktrees, so a root index sees no code).

## Notes & current caveats

- **`create` defaults to a full DB sync** (drops/rebuilds the slot DB, no extra prompt) unless
  you pass `--skip-db-sync`. Use `--skip-db-sync --skip-db-init` for a true light worktree that
  touches no Docker/SQL.
- **`sync-main` only updates a repo if it is on its target branch** (`master`/`main`). Today both
  main repos are on `chore/linux-cachyos-tooling-migration`, so `sync-main` will skip them until you
  switch (or pass `--checkout`). This is intentional — it prevents merging `master` into the wrong branch.
- **"sync current worktree with main"** (rebasing a task branch onto updated main) is **not** a
  `worktree.py` command yet. Do it manually after `sync-main`, e.g.
  `git -C worktrees/bed/be fetch origin && git -C worktrees/bed/be rebase origin/main`. A future
  `worktree.py rebase` recipe is a candidate.
- Run `python scripts/harness_doctor.py` (or `just doctor`) to check tools, helpers, layouts, and graph trust.
