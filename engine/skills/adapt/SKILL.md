---
name: adapt
description: Owner-invoked semi-automated harness adaptation. Two modes: (A) RCA + fix a workflow whose machinery failed during a run (threshold same root-cause >=2); (B) design + build a new workflow for a repeated task pattern (threshold >=3, conflict-checked). POST-run only; six safety gates (owner-gated, no-self-fix, pin-version, threshold, conflict-check). Reuses mh-rca + mh-fix + harness_doctor + harness_backup. Trigger "/adapt", "adapt workflow X", "build a workflow for Y".
---

# adapt

Token-light discovery stub.

Before executing this skill, read `DETAILS.md` in this directory fully and follow it as the authoritative runbook. Do not act from this stub alone.

This is a META-workflow — it changes harness machinery, not product source. Six safety gates apply; owner approves every apply. Never self-invoke.
