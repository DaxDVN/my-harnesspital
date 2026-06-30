---
name: mh-debrief
description: Owner-invoked post-task teaching/debrief. READ-ONLY. After a task is done (e.g. /mh-implement, /mh-fix, /incremental-impl, or any uncommit-changes set in a worktree), Claude switches to TEACHER mode and verifies the owner actually understands what was just done — problem / solution / impact — via a knowledge checklist, incremental teaching, explain-back, and a quiz. Session ends ONLY when the owner has demonstrated understanding of the entire checklist. Vietnamese. Never edits source or files. Trigger "/mh-debrief", "debrief", "giải thích cho tôi hiểu", "teach me what just happened", "tôi cần hiểu nó làm gì".
---

# mh-debrief

Token-light discovery stub.

Before executing this skill, read `DETAILS.md` in this directory fully and follow it as the authoritative teaching runbook. Do not act from this stub alone.

This skill is READ-ONLY: it reads `git diff` / the task artifact and teaches. It never edits source, never mutates files, and never auto-invokes — the owner invokes `/mh-debrief` after a task.
