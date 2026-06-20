---
title: "Fix-flow auto-decides blocking business questions and writes a decision-log named after the audit file"
date: "2026-06-19"
status: provisional
source: user-correction
scope: workspace
confidence: high
owner_confirmed: false
proposed_target: main-brain
tags: [decision-log, bug-fix, autonomy, demo]
applies_tasks: [fix]
applies_globs: []
applies_keywords: [decision-log, auto-decide, demo, fix]
expires: ""
---

# What

Owner authorizes the fixer to auto-decide a business question blocking a fix: investigate, pick the most defensible option (provisional), fix, and MUST write a decision-log named after the report (<base>.round-N.decision-log.md + .vi.md, same date-folder, back-refs report). Entries DEC-NNN with options/decision/rationale/source_basis/reversibility/risk_if_wrong. Owner refers at BA demo; edits the log to overturn.

# Evidence

- engine/prompts/bugfix-from-report.md 1.5 AUTO-DECIDE + 1.6

# Why It Matters

Blocking stalls the demo; owner wants progress plus a referenceable reversible artifact.

# How To Apply

_See # What above._

# Boundaries

Only bugfix-from-report fix-flow, owner-authorized; not normal dev/scaffold.

# Promotion Recommendation

Promote to: main-brain
Reason: (fill in before promoting)
