# Harness migration → fresh CachyOS PC (one-time, no confidential push)

Goal: move the whole agent/dev harness from this machine to a freshly-installed
CachyOS box **without** sending confidential content (specs / DB / code) to any
git remote. Transfer is direct (USB or rsync over LAN/SSH). One-time, not realtime sync.

Tool: `scripts/migrate_harness.py` (`plan` | `pack` | `fixup` | `verify`).

## What travels vs. what is rebuilt

| Bucket | How | Why |
|---|---|---|
| Root harness working tree (tracked **+ untracked** edits) + `specs/` | tarball `harness-workspace.tar.zst` | `git clone` would drop untracked harness dirs (`.agents/`, `.opencode/`, `.codex/config.toml`, new `harness/rules/*`, `scripts/opencode/`, `skills-lock.json`) |
| `~/.claude` essentials: `CLAUDE.md`, `settings.json`, `skills/`, project `memory/` | tarball `claude-home.tar.gz` | identical agent behavior; caches/plugins/creds excluded |
| `myhospital-fe` (master) / `myhospital-be` (main) | `git clone` from GitHub | authorized company remotes; saves 373M, drops node_modules/bin/obj |
| `_db-backups` (412M) | `worktree.py sync-db` on target (or `pack --include-db`) | heavy, regenerable |
| `graphify-out` (52M) | rebuild on Linux via `/graphify` | current build is stale Windows |

Bundle size with defaults ≈ **59M** (specs + docs dominate). Nothing confidential leaves the two machines.

## Source machine

```fish
cd /home/dax/Documents/arabica/roast
python scripts/migrate_harness.py plan            # sanity-check inclusions
python scripts/migrate_harness.py pack            # -> ~/harness-migration-<date>/
# python scripts/migrate_harness.py pack --include-db   # if office has no DB to sync from
```

Move the output folder by USB, or direct over LAN/SSH (no cloud):

```fish
rsync -avh --progress ~/harness-migration-<date>/ dax@<target>:~/harness-migration-<date>/
```

## Target machine (fresh CachyOS)

```fish
# 0. tools
sudo pacman -S --needed git python just ripgrep fd bat ripgrep-all zellij nodejs npm rsync zstd
#    + dotnet SDK, claude-code, opencode, codex, codegraph via their installers

# 1. workspace — KEEP user 'dax' + same path => zero fixup
mkdir -p /home/dax/Documents/arabica/roast
tar -C /home/dax/Documents/arabica/roast -xf <bundle>/harness-workspace.tar.zst

# 2. ~/.claude essentials, then re-auth (creds are NOT in the bundle)
tar -C ~/.claude -xzf <bundle>/claude-home.tar.gz
claude    # /login

# 3. re-clone code
git clone https://github.com/MyHospital-Vn/myhospital-fe /home/dax/Documents/arabica/roast/myhospital-fe
git clone https://github.com/MyHospital-Vn/myhospital-be /home/dax/Documents/arabica/roast/myhospital-be
cd /home/dax/Documents/arabica/roast/myhospital-fe; and npm ci

# 4. regenerate DB + graph (see table)

# 5. ONLY if user/home differ from source:
python scripts/migrate_harness.py fixup --old-root /home/dax/Documents/arabica/roast --new-root /home/<you>/<path>/roast

# 6. verify
python scripts/migrate_harness.py verify   # == harness_doctor.py
just doctor
```

## Gotchas

- **Path fixup**: 7 tracked files hardcode `/home/dax/Documents/arabica/roast` (AGENTS.md, `.claude/settings.local.json`, worktree-workflow.md, graphify-agent-guide.md, `scripts/fish/myhospital-zellij.fish`, scripts/README.md, scripts/WORKTREE-TOOLING.md). Same username `dax` + same path ⇒ nothing to do. Also hand-check `~/.claude/settings.json` and `~/.local/bin/graphify`.
- **graphify** rebuild is required regardless — old graph is Windows-built/stale.
- **CodeGraph** indexes are per-repo and not shipped; they auto-build after clone.
- `.credentials.json` deliberately excluded — log in fresh on the target.
