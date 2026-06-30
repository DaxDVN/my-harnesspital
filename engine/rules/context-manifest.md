# Subagent Context Manifest — Hydrate By Reference

How the PM orchestrator transfers memory to a worker subagent: it passes a **manifest of PATHS + QUERIES**, never
copied content. The worker hydrates itself by loading those references live and verifying they are current. This
keeps the coordinator blind (it routes pointers, not bodies), keeps payloads tiny, and guarantees the worker sees
the live conventions/spec rather than a stale snapshot the coordinator pasted.

## Core Rule

- **Reference, not content.** The orchestrator emits the manifest below. It does NOT inline rule text, spec
  prose, note bodies, or source — only the paths/queries that produce them.
- **Verify-live.** The worker MUST re-read each referenced artifact at run time and treat it as the current truth.
  A path the manifest names but the worker cannot find/verify is a STOP, not a guess.
- **Worker self-hydrates.** Loading is the worker's first step; the coordinator never reads these on the worker's
  behalf (that would break the blind-coordinator invariant).
- **Cite the template.** The by-reference + verify-live discipline is operationalized by
  `engine/prompts/subagent-prompt-template.md` (ZONE A = this manifest). Dispatch through that template.

## Manifest Fields

```text
load:
  - rule_card:        <outputs of `python scripts/rule_card.py fe "<task>"` AND `... be "<task>"`>
  - recommended_prompt_file: <engine/prompts/<role>.md the route recommends>
  - recalled_notes:   <second-brain note paths from `learning_recall.py` — paths only>
  - ledger_path:      <engine/workflows/pm-orchestrator/runs/<scope>/run-NNN/00-pm-state.md>
  - spec_sections:    <specs/<module>/NN-*.md#section pointers relevant to this phase>
verify_live:   true
scope:         <one-line goal of this worker unit>
allowlist:     <worktree + exact files/dirs the worker may write>
done_check:    <the concrete condition that proves this unit is complete>
return_format: <the compact blob shape the worker returns to the coordinator (counts/paths/flags, no md dump)>
```

- `load` is a list of references; every entry is a path, a command to run, or a query — never a pasted body.
- `allowlist` is the write boundary (worktree + file allowlist). Missing or too-broad → the worker stops and asks
  for a tighter slice.
- `return_format` is what the coordinator authors the ledger from — keep it compact (see
  `engine/rules/orchestrator-ledger.md`).

## Template

`engine/prompts/subagent-prompt-template.md` is the **REQUIRED** worker-prompt shape for every dispatched worker.
The manifest above is its ZONE A (context, by reference); ZONE B is the ask (intent → task → scope → autonomy →
ponytail → output). Fill that template — do not author a one-off prompt shape.

**Input ordering (load-bearing).** Render the worker prompt long-material-FIRST, ask-LAST: put the referenced
docs at the top and the actual task/instructions at the bottom (queries at the end improve quality up to ~30% on
multi-document inputs). Wrap each referenced doc in `<document>`/`<source>` XML tags so reference vs. instruction
is unambiguous. For long source/spec, have the worker quote the relevant lines first before acting.

`engine/prompts/incremental-impl-worker.md` remains a compatible bounded base (worktree+allowlist, self-validate,
self-review-diff, compact report, stop conditions); the manifest flows into its `Inputs` block.

## Why By-Reference

- The coordinator stays blind and its context stays small (constraint: every-turn/payload token cost).
- Workers always read the **live** rule_card / spec / notes, so convention drift cannot be frozen into a stale
  paste.
- References are auditable: the ledger and reports cite the same paths, so a reviewer can re-open exactly what the
  worker loaded.
