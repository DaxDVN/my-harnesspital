---
name: robust-test
description: Owner-invoked robust testing workflow for targeted E2E reproduction or module sweep. Creates one folder per captured bug, triages false positives, writes RCA/fix-plan/retest artifacts, and prepares a final review-ready bundle for a higher-reasoning agent. It never self-launches other agents or implementation. Trigger "/robust-test", "robust-test", "test chắc", "kiểm thử chắc", "sweep bugs".
---

# robust-test

Token-light discovery stub.

Before executing this skill, read `DETAILS.md` in this directory and `engine/workflows/robust-test/README.md` fully. Follow them as the authoritative runbook. Do not act from this stub alone.

Do not edit source code. Create one bug folder per bug candidate and stop for owner approval before any fix.
