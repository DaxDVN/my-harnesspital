# Worker Task Contract (H11) — cross-tool multi-agent

Defines the **prompt fields** a worker receives and the **result format** it must return.
Deep-review and any other owner-approved harness that fans out parallel subagents use this
contract so a coordinating agent can parse results identically regardless of the tool
(Claude Agent, Codex worker, opencode/mimocode run).

---

## PROMPT fields (what the orchestrator injects)

| Field | Required | Description |
|---|---|---|
| `scope` | yes | Dimension or slice being handled (e.g. "D3 — data-layer" or "task-04-be-service") |
| `allowlist` | yes | Exhaustive list of files/directories the worker may read AND edit. No other paths. |
| `inputs` | yes | Paths to read-only input artifacts (spec sections, DTO files, bug catalog, etc.) |
| `done_check` | yes | Deterministic command(s) the worker must run to self-validate before returning |
| `return_format` | yes | Must be `worker-task-result` (see below) |
| `context` | no | Short briefing — the worker is not alone; other workers own disjoint scopes |
| `timeout_hint` | no | Soft time budget (e.g. "≤5 min") — worker stops and reports `BLOCKED` if exceeded |

### Invariants the orchestrator guarantees

- Allowlists across all workers for one round are **disjoint** — no file is in two allowlists.
- Inputs are **read-only** — workers must not edit input artifacts.
- Workers are spawned by dependency-safe rounds; all workers in a round are independent.

---

## RESULT format (`worker-task-result`)

The worker returns a single structured block after completing its work:

```
worker-task-result
  scope: <same value as PROMPT.scope>
  status: DONE | BLOCKED | PARTIAL
  files_changed:
    - path/to/file.ts   # relative to repo root
    - path/to/other.ts
  validation:
    - command: "npm run build --filter=myhospital-fe"
      outcome: PASS | FAIL | SKIPPED
      note: "<optional short note>"
  blockers:            # empty list if status=DONE
    - "<short description of what is blocking>"
  learnings:           # optional — cross-cutting facts worth capturing
    - "<short paraphrase for learning_capture.py>"
  notes: |
    <optional free-text, max 5 lines>
```

Rules:
- `status: DONE` requires at least one `validation` entry with `outcome: PASS`.
- `status: BLOCKED` means the worker could not finish and the orchestrator must decide.
- `status: PARTIAL` means some tasks done, some blocked — list both in `files_changed` and `blockers`.
- Workers must **not** amend other workers' files or revert orchestrator changes.
- Workers must **not** make architecture, cross-contract, or business-rule decisions — those return as `BLOCKED` with a clear blocker description.

---

## Adapter notes

### Claude Agent tool
Pass the PROMPT fields inside the agent `prompt` parameter. Spawn all workers in one message
(multiple Agent tool calls) so they run concurrently. Collect `worker-task-result` blocks from
each agent response. Workers use `subagent_type: "mh-implementer"` for code tasks or
`subagent_type: "mh-reviewer"` for read-only audit tasks.

### Codex worker
Include PROMPT fields in the Codex task description. The worker reads `engine/workflows/_shared/worker-task.md`
at the top of its run and emits the result block as the last output before stopping.
The orchestrator reads it from `docs/tasks/<session>/<scope>-result.md` if the worker writes it there,
or parses it from the final assistant message.

### opencode / mimocode run
Pass PROMPT fields via the opencode instruction file or `--instructions` flag. The worker must
write the result block to `docs/tasks/<session>/<scope>-result.md` so the orchestrator
(separate process) can read it as a file artifact. The orchestrator polls or waits for the file
before starting the next round.

---

## Integration with deep-review

Each review dimension (D1–D7) maps to one worker:
- `scope` = dimension label (e.g. "D3 — BE data-layer conventions")
- `allowlist` = the files the dimension covers (BE services, FE hooks, etc.)
- `inputs` = `engine/workflows/deep-review/checklist.md` + the relevant source files
- `done_check` = "attests: read N files, found M findings, none missed" (per checklist coverage rule)
- Worker emits findings in `docs/audit/<module>-review-v<round>-<date>.md`

## Integration with robust-test/browser testing

If the owner explicitly approves external/browser worker fan-out, each test-batch or page-flow maps to one worker:
- `scope` = flow name (e.g. "admission-form-happy-path")
- `allowlist` = the page files + test fixture files
- `inputs` = bug catalog from prior sweep, spec test-cases from `specs/<m>/09-test-cases.md`
- `done_check` = "playwright run <flow> exits 0" or equivalent
- Worker appends findings to the robust-test per-bug dossier artifact
