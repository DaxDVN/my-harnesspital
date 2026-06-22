---
name: bug-fix
description: Owner-invoked bug investigation -> RCA -> fix -> verify, from ANY source (QA / lead / user / log / failed build/test / code-review / E2E). REUSES the mh-rca agent (RCA) + the /mh-fix skill (the fix). Envelope + state-machine driven; the only code edits happen via /mh-fix in a worktree. Trigger "/bug-fix", "investigate bug", "RCA this", "fix bug from <source>".
---

# bug-fix

Token-light discovery stub.

Before executing this skill, read `DETAILS.md` in this directory fully and follow it as the authoritative runbook. Do not act from this stub alone.

Keep the RCA/fix/verify loop artifact-backed. Return compact findings and paths instead of long payloads.
