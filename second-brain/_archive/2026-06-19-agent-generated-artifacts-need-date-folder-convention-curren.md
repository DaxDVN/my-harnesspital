---
title: "Agent-generated artifacts → per-day folder (NOW a harness rule)"
date: "2026-06-19"
status: implemented
source: conversation
scope: workspace
confidence: high
owner_confirmed: true
proposed_target: engine/rules/backend
tags: [file-organization, artifacts, date-folder, workspace-hygiene]
applies_tasks: [any]
applies_globs: [docs/tasks/**, docs/session-notes/**, docs/testing/**, docs/audit/**]
applies_keywords: [save, report, audit, prompt, plan, generate, artifact, docs/tasks]
expires: ""
---

# What

Agent-generated artifacts MUST go into a per-day folder `<dir>/<YYYY-MM-DD>/<file>` (today=`date +%F`),
auto-created (`mkdir -p`). Applies to `docs/audit/`, `docs/tasks/`, `docs/session-notes/`, `docs/testing/`.
Pre-existing flat files stay; rule applies to NEW files only. Specs + scripts NOT date-foldered.

**Now implemented (2026-06-19), no longer a proposal:**
- AGENTS.md → "Workspace File Organization" carries BOTH the Date-folder rule AND the Audit round-versioning rule (canon, all agents).
- **Round-versioning (docs/audit only):** every audit doc = `<base>.round-<N>.md`; N auto-increments off the highest existing `<base>.round-*` anywhere under docs/audit (first=1). This rule OVERRIDES whatever filename a prompt/skill specifies. Resolve deterministically with `python scripts/audit_path.py "<base>"` (prints `docs/audit/<today>/<base>.round-<N>.md`, mkdir -p; `--vi` = same-round .vi.md clone; `--current` = highest existing; `--dry-run`). The bilingual .vi.md shares the round.
- engine/workflows/deep-review/findings-schema.md output = `docs/audit/<YYYY-MM-DD>/<base>.round-<N>.md`.
- engine/prompts/deep-audit-orchestrator.md resolves master path via scripts/audit_path.py (no literal filename).
NOT yet a hook — enforced by instruction + helper only. A PreToolUse guard nudging flat/unversioned writes is the next layer.

# Evidence

- Was flat before: docs/audit/ + docs/tasks/ mixed naming, date only sometimes in filename, no day-folders.

# Why It Matters

Flat dir + inconsistent naming => artifacts pile up undiscoverable; cannot find 'what did we generate today'. A deterministic date-folder layout + auto-mkdir makes session output greppable and self-organizing.

# How To Apply

_See # What above._

# Boundaries

Does NOT apply to committed harness docs (docs/harness/**), specs/<module>/**, or source code. Scope = ephemeral session artifacts (tasks/session-notes/testing/audit dumps). Convention proposal only — not yet a hook.

# Promotion Recommendation

Promote to: engine/rules/backend
Reason: (fill in before promoting)
