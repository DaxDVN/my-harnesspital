---
name: espresso-test
description: Owner-invoked agent-orchestrated review->fix->re-review convergence loop. A thin coordinator agent spawns a review subagent (runs deep-review), routes the findings file to a stronger fixer subagent (RCA + mh-fix, fans out mh-implementer), then re-reviews -- looping until a round reports 0 BLOCK/HIGH OPEN or the round cap is hit. The coordinator never reads output md and never loads rules; it only routes paths + compact status and decides stop. Trigger "/espresso-test", "espresso-test", "review-fix loop", "lặp review fix", "tự fix tới sạch".
---

# espresso-test

Token-light discovery stub.

Before executing this skill, read `DETAILS.md` in this directory and `engine/workflows/espresso-test/README.md`
fully. Follow them as the authoritative runbook. Do not act from this stub alone.

You are the **coordinator**: spawn subagents, route file PATHS + compact status, decide stop. Do NOT read any
review/findings/fix output md, do NOT load rules, do NOT read or edit source. Reasoning lives in the reviewer
(`deep-review`) and the fixer (`mh-rca` + `/mh-fix` + `mh-implementer`). Owner-gated; stop at the round cap with
an honest residual report rather than looping forever or claiming clean.

**Autonomy (default):** the only owner-blocking step is the round-0 pre-sweep question batch at invoke
(`ask_window: gate-only`). After that the run is fire-and-forget — a business ambiguity becomes a logged
`PROVISIONAL-FIXED` decision (cited basis, `DL-PROV-<n>` in `06-decision-log`, mirrored to `05-open-questions`)
or, if closing it needs an irreversible-data/migration op, a `PARKED-NEEDS-OWNER` finding (loop continues on
the rest). Never block mid-run; never invent a rule without cited provenance. The final report batches all
provisional decisions for the owner to confirm/correct later.
