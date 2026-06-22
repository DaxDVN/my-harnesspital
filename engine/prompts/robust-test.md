# robust-test prompt

Use this only when the owner explicitly invokes `robust-test`.

You are running an owner-gated robust testing protocol, not an autonomous repair loop.

Read first:

```text
AGENTS.md
engine/workflows/robust-test/manifest.json
engine/workflows/robust-test/README.md
engine/skills/robust-test/DETAILS.md
```

Rules:

- do not launch subagents or external implementers;
- do not edit source code;
- write artifacts only under `engine/workflows/robust-test/runs/**`;
- create one `bugs/BUG-NNN/` folder for every captured bug candidate;
- triage false positives before RCA;
- stop for owner approval before any fix;
- when all bugs are believed fixed/routed, write `04-review-ready-bundle.md` for a higher-reasoning review agent.
