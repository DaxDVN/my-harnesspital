# MyHospital workspace command runner.
#
# `just` runs recipes in bash (below) for portability; this does NOT change your
# interactive fish shell. All real work is shell-agnostic Python (scripts/*.py),
# so recipes behave the same from fish, bash, or CI.
#
# Run `just --list` to see everything. Worktree create/cleanup/sync recipes are
# thin wrappers over scripts/worktree.py and inherit its confirmation prompts.

set shell := ["bash", "-lc"]

# Show this list.
default:
    @just --list

# --- Health / status ------------------------------------------------------

# Full harness self-check (read-only).
doctor:
    python scripts/harness_doctor.py

# Deterministic BE convention scan (audit bug-classes). Usage: just mh-scan  |  just mh-scan --only auth_coverage --format md
mh-scan *ARGS:
    python scripts/mh_scan {{ARGS}}

# Doc-vs-code convention drift check (flags a stale CONVENTIONS.md).
convention-truth:
    python scripts/convention_truth.py

# Short git status of both main repos.
status:
    git -C myhospital-fe status --short
    git -C myhospital-be status --short

# Snapshot harness files (no secrets/DB/build output).
harness-backup:
    python scripts/harness_backup.py

# Scan ACTIVE harness files for stray Windows/macOS artifacts (concrete drive paths / cmdlets / invocations — not the word "powershell" in deprecation prose; excludes the legacy archive and self-referential pattern files).
agent-audit:
    rg -n -g '!scripts/legacy-powershell/**' 'C:\\[A-Za-z]|D:\\[A-Za-z]|\\Users\\|/Users/|Get-ChildItem|textutil|pwsh -|powershell -' \
        AGENTS.md CLAUDE.md .codex scripts docs/graphify-agent-guide.md docs/agent-rules myhospital-be/.claude \
        || echo "agent-audit: clean (no active cross-OS artifacts)"

# --- Worktrees ------------------------------------------------------------

# List active task worktrees.
wt-list:
    python scripts/worktree.py list

# Create a full worktree (FE+BE+DB slot). Usage: just wt-create bed 1
wt-create slug slot:
    python scripts/worktree.py create --slug {{slug}} --slot {{slot}}

# Create a light worktree (no DB sync, no DB init, no FE install). Usage: just wt-create-lite bed 1
wt-create-lite slug slot:
    python scripts/worktree.py create --slug {{slug}} --slot {{slot}} --skip-db-sync --skip-db-init --skip-fe-install

# Preview a create without changing anything. Usage: just wt-create-preview bed 1
wt-create-preview slug slot:
    python scripts/worktree.py create --slug {{slug}} --slot {{slot}} --skip-db-sync --skip-db-init --skip-fe-install --dry-run

# Pull main FE/BE (guarded; skips repos not on master/main). Pass-through args. Usage: just wt-sync-main --dry-run
wt-sync-main *ARGS:
    python scripts/worktree.py sync-main {{ARGS}}

# Reset a slot DB from main DB data. Usage: just wt-sync-db bed 1  (add --dry-run to preview)
wt-sync-db slug slot *ARGS:
    python scripts/worktree.py sync-db --slot {{slot}} --be-path worktrees/{{slug}}/be {{ARGS}}

# Run a worktree backend with its .env loaded safely. Usage: just wt-run-be bed --no-build
wt-run-be slug *ARGS:
    python scripts/worktree.py run-be --be-path worktrees/{{slug}}/be {{ARGS}}

# Remove a clean worktree (prompts). Usage: just wt-cleanup bed  (add --delete-branch to free the slug)
wt-cleanup slug *ARGS:
    python scripts/worktree.py cleanup --slug {{slug}} {{ARGS}}

# Worktree CLI help.
worktree-help:
    python scripts/worktree.py --help

# --- Zellij ---------------------------------------------------------------

# List MyHospital (mh-*) Zellij sessions.
z-sessions:
    zellij list-sessions 2>/dev/null | grep -F 'mh-' || echo "(no mh-* worktree sessions)"

# Install the repo Zellij layout templates into ~/.config/zellij/layouts/.
z-install-layouts:
    mkdir -p ~/.config/zellij/layouts
    cp scripts/zellij/myhospital-orch.kdl scripts/zellij/myhospital-impl.kdl ~/.config/zellij/layouts/
    @echo "Installed myhospital-orch / myhospital-impl layouts."

# --- CodeGraph (source-code index) ----------------------------------------
# Source code is explored with CodeGraph, indexed per code repo (never at root).
# Policy + command table: docs/agent-rules/source-discovery.md

# Index status for both main repos (does not abort if a repo is not yet indexed).
codegraph-status:
    -cd myhospital-be && codegraph status
    -cd myhospital-fe && codegraph status

# One-time: build the CodeGraph index for both main repos.
codegraph-init-main:
    cd myhospital-be && codegraph init
    cd myhospital-fe && codegraph init

# Force incremental sync for both main repos (auto-sync usually handles this).
codegraph-sync-main:
    cd myhospital-be && codegraph sync
    cd myhospital-fe && codegraph sync

# Build the CodeGraph index for an active worktree (be+fe). Usage: just codegraph-init-worktree bed
codegraph-init-worktree slug:
    cd worktrees/{{slug}}/be && codegraph init
    cd worktrees/{{slug}}/fe && codegraph init

# Index status for a worktree. Usage: just codegraph-status-worktree bed
codegraph-status-worktree slug:
    -cd worktrees/{{slug}}/be && codegraph status
    -cd worktrees/{{slug}}/fe && codegraph status

# Force sync a worktree's indexes. Usage: just codegraph-sync-worktree bed
codegraph-sync-worktree slug:
    cd worktrees/{{slug}}/be && codegraph sync
    cd worktrees/{{slug}}/fe && codegraph sync

# Wire CodeGraph MCP server into installed agents (re-runnable). Preview a target with --print-config.
codegraph-install:
    codegraph install --target=auto --location=global --yes

# --- graphify -------------------------------------------------------------

graphify-help:
    graphify --help
