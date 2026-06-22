# robust-test

Authoritative workflow doc: `engine/workflows/robust-test/README.md`.

## Required Behavior

- Owner invocation is required.
- Ask for `mode=targeted|sweep`, target scope, worktree slug, URL/slot, and actor/data preconditions if missing.
- Write artifacts only under `engine/workflows/robust-test/runs/**`.
- Create `bugs/BUG-NNN/` immediately for every captured bug candidate.
- Triage false positives before RCA.
- Do not launch subagents, Codex, Claude, OpenCode, or MiMo as a self-running chain.
- Do not edit source code from this workflow.
- When all bugs are believed fixed/routed, write `04-review-ready-bundle.md` for a higher-reasoning review pass.

## Output Contract

Final chat response should be compact:

```text
Run folder: <path>
Bug folders: BUG-001 ... BUG-NNN
Confirmed: <ids>
Not bugs: <ids>
Needs owner: <ids>
Review bundle: <path>
Validation/retest: <summary>
Next owner decision: <exact options>
```
