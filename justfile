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

# --- Bootstrap (fresh machine) --------------------------------------------

# Stand up the harness on a fresh clone (idempotent). `just bootstrap --check` = prereqs + doctor only, no mutation.
bootstrap *ARGS:
    python scripts/bootstrap.py {{ARGS}}

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

# Prune gitignored artifacts older than N days (default 30). Preview with --dry-run. Usage: just prune-artifacts 7
prune-artifacts days="30" *ARGS:
    @echo "Pruning artifacts older than {{days}} days (preview with --dry-run):"
    find _db-backups -type f -mtime +{{days}} -name '*.sql' -delete {{ARGS}}
    find docs/testing/screenshots -type f -mtime +{{days}} -name '*.png' -delete {{ARGS}}
    find graphify-out -type f -mtime +{{days}} -delete {{ARGS}}
    @echo "Done. For full cleanup: rm -rf graphify-out/ && codegraph init (rebuild fresh)"

# Scan ACTIVE harness files for stray Windows/macOS artifacts (concrete drive paths / cmdlets / invocations — not the word "powershell" in deprecation prose; excludes the legacy archive and self-referential pattern files).
agent-audit:
    rg -n -g '!scripts/legacy-powershell/**' 'C:\\[A-Za-z]|D:\\[A-Za-z]|\\Users\\|/Users/|Get-ChildItem|textutil|pwsh -|powershell -' \
        AGENTS.md CLAUDE.md .codex scripts harness docs/graphify-agent-guide.md myhospital-be/.claude \
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

# Reset a slot DB from staging DB data (CLEAR-ALL — wipes mock data). Usage: just wt-sync-db bed 1  (add --dry-run to preview)
wt-sync-db slug slot *ARGS:
    python scripts/worktree.py sync-db --slot {{slot}} --be-path worktrees/{{slug}}/be {{ARGS}}

# MERGE sync: UPSERT staging baseline into slot, PRESERVES mock rows. Usage: just wt-sync-db-merge bed 1
wt-sync-db-merge slug slot *ARGS:
    python scripts/worktree.py sync-db --slot {{slot}} --be-path worktrees/{{slug}}/be --merge {{ARGS}}

# Pull main FE/BE + re-sync all active worktree slot DBs (MERGE — preserves mock). Add --dry-run to preview.
wt-sync-main-db *ARGS:
    python scripts/worktree.py sync-main --sync-db {{ARGS}}

# Pull main FE/BE + re-sync all active worktree slot DBs (CLEAR-ALL — wipes mock). Add --dry-run to preview.
wt-sync-main-db-clear *ARGS:
    python scripts/worktree.py sync-main --sync-db-clear {{ARGS}}

# Run a worktree backend with its .env loaded safely. Usage: just wt-run-be bed --no-build
wt-run-be slug *ARGS:
    python scripts/worktree.py run-be --be-path worktrees/{{slug}}/be {{ARGS}}

# Remove a clean worktree (prompts). Usage: just wt-cleanup bed  (add --delete-branch to free the slug)
wt-cleanup slug *ARGS:
    python scripts/worktree.py cleanup --slug {{slug}} {{ARGS}}

# Worktree CLI help.
worktree-help:
    python scripts/worktree.py --help

# --- CodeGraph (source-code index) ----------------------------------------
# Source code is explored with CodeGraph, indexed per code repo (never at root).
# Policy + command table: engine/rules/source-discovery.md

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

# --- Harness helpers (toil reduction scripts) -----------------------------

# Session start ritual: worktree list + rule_card fe/be + learning_recall. Usage: just session-start "fix IPD admission bug"
session-start task:
    python scripts/harness_session_start.py "{{task}}"

# Build context-manifest for PM-orchestrator worker dispatch. Usage: just ctx-build "fix bug" bugfix rca
ctx-build task workflow phase:
    python scripts/context_manifest_build.py "{{task}}" --workflow {{workflow}} --phase {{phase}}

# Regen FE DTO/client after BE contract change. Usage: just fe-regen ipd-improve-v5
fe-regen slug:
    python scripts/fe_regen_from_be.py --be-path worktrees/{{slug}}/be --fe-path worktrees/{{slug}}/fe

# Browser login to a slot FE. Usage: just browser-login 4
browser-login slot:
    python scripts/browser_login_slot.py {{slot}}

# Apply CONVENTIONS.fixed.md → demote CONVENTIONS.md to pointer. Preview with --dry-run.
conventions-apply *ARGS:
    python scripts/conventions_sync.py apply {{ARGS}}

# Doctor with explain mode (WARN/FAIL cause + fix). Usage: just doctor-explain
doctor-explain:
    python scripts/harness_doctor.py explain

# Scaffold a new spec module (14 files). Usage: just spec-new ipd-admission --description "IPD admission module"
spec-new module *ARGS:
    python scripts/specs_new_module.py {{module}} {{ARGS}}

# Finish a module (archive + state DONE + promotion check). Usage: just module-finish ipd-admission
module-finish module *ARGS:
    python scripts/module_finish.py {{module}} {{ARGS}}

# Add a provisional decision log entry. Usage: just dl-prov ipd-admission "decision text" --basis "src"
dl-prov module text *ARGS:
    python scripts/decision_log_add.py {{module}} --provisional "{{text}}" {{ARGS}}

# Refresh CodeGraph index if stale. Usage: just codegraph-refresh be
codegraph-refresh repo *ARGS:
    python scripts/codegraph_refresh.py --repo {{repo}} {{ARGS}}

# Pre-edit risk classify + suggest gates. Usage: just pre-edit myhospital-be/ServiceInterface/MyServices/BedService.cs
pre-edit file:
    python scripts/harness_pre_edit.py {{file}}

# --- Agentic coding tool adapter (3 backends + fallback) -----------------
# Dispatch a code task to one of 3 agentic tools: opencode (paid, $12/5h cap),
# grok (Claude Code-style, --effort ladder), agy (Antigravity, Gemini/Claude/GPT-OSS).
# Fallback chain fires when primary backend quota-exhausts/times-out/auth-fails.
# Review roles (audit/final_review) force glm-5.2/Opus — no fallback per owner.

# Dispatch a role to its primary backend. Usage: just agent-exec agentic_primary worktrees/ipd-improve-v5/be "fix the bug"
agent-exec role scope prompt *ARGS:
    python scripts/agent_exec.py --role {{role}} --scope {{scope}} --prompt "{{prompt}}" {{ARGS}}

# Dispatch via a specific backend (override role.backend). Usage: just agent-exec-with grok agentic_primary worktrees/ipd-improve-v5/be "fix the bug"
agent-exec-with backend role scope prompt *ARGS:
    python scripts/agent_exec.py --role {{role}} --scope {{scope}} --prompt "{{prompt}}" --backend {{backend}} {{ARGS}}

# Dispatch with rule-card injection (convention contract). Usage: just agent-exec-rc agentic_primary worktrees/x/be "fix" engine/rules/backend/quick.md
agent-exec-rc role scope prompt rulecard *ARGS:
    python scripts/agent_exec.py --role {{role}} --scope {{scope}} --prompt "{{prompt}}" --rule-card {{rulecard}} {{ARGS}}

# Dry-run: preview the resolved command + fallback chain. Usage: just agent-exec-dry agentic_primary worktrees/x/be "fix"
agent-exec-dry role scope prompt *ARGS:
    python scripts/agent_exec.py --role {{role}} --scope {{scope}} --prompt "{{prompt}}" --dry-run {{ARGS}}

# List available backends + their current status. Usage: just agent-backends
agent-backends:
    @echo "Agentic backends (scripts/agent_exec.py):"
    @which opencode 2>/dev/null && opencode --version 2>/dev/null | head -1 || echo "  opencode: NOT FOUND"
    @which grok 2>/dev/null && grok --version 2>/dev/null | head -1 || echo "  grok: NOT FOUND"
    @which agy 2>/dev/null && agy --version 2>/dev/null | head -1 || echo "  agy: NOT FOUND"


# --- graphify -------------------------------------------------------------

graphify-help:
    graphify --help
