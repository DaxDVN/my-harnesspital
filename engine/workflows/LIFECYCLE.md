# Workflow Lifecycle and Consolidation Policy

This is the governance layer for P5. It exists to prevent prompt sprawl and unsafe deprecation.

## Lifecycle

```text
DRAFT -> LAB -> PROVEN -> DEFAULT -> DEPRECATED
```

| status | meaning | routing policy |
|---|---|---|
| `DRAFT` | design/docs exist; no reliable run evidence | never auto-route |
| `LAB` | runnable/scaffolded enough for explicit owner invocation | never auto-route |
| `PROVEN` | at least one real run eval artifact with validation evidence | may become route candidate if manifest allows |
| `DEFAULT` | repeated representative evals and owner accepts normal routing | may auto-route when manifest allows |
| `DEPRECATED` | compatibility only; replacement documented | never auto-route |

Promotion must be backed by `docs/harness/evals/**` and summarized in `manifest.eval_summary`.

## Prompt File Recommendation

Workflow manifests may declare:

```json
"recommended_prompt_file": "engine/prompts/<name>.md"
```

This is an advisory bridge from workflow governance to the reusable prompt library. It tells a router, owner, or
external-executor wrapper which self-contained system prompt is appropriate for a high-control/fresh-agent run.
It is **not** an auto-load instruction and does not make the workflow auto-routable.

Policy:

- daily execution should prefer router `files_to_load` plus lightweight skill/workflow docs;
- prompt files are for owner-selected sessions, external executors, or wrapper-selected runs;
- doctor/governance should warn if a declared `recommended_prompt_file` path is stale;
- lifecycle and eval evidence still control auto-route.

## Taxonomy

| class | purpose | examples |
|---|---|---|
| `workflow` | public/user-facing entry candidate | `bug-fix`, `deep-review`, `robust-test`, `ui-spec`, `technical-design`, `task-slicing` |
| `internal` | subroutine owned by another workflow/skill | `incremental-impl` |
| `advisory` | read-only or preflight support | `impact-analysis` |

`public_entry=true` means explicit owner invocation is acceptable. It does not mean auto-route.

## Current Consolidation Decisions

Do not collapse these pairs without eval evidence:

| pair/group | current split | decision |
|---|---|---|
| `mh-fix` skill vs `bug-fix` workflow | direct approved patch vs full investigate/RCA/fix/verify | keep split |
| `robust-test` replaces `super-test` + `progressive-test` | owner disabled autonomous agent handoff; keep targeted and sweep modes in one manual protocol | remove legacy runtimes; old names route conceptually to `robust-test` only |
| `mh-implement` vs `incremental-impl` | public feature implementation vs internal per-slice executor | keep split |
| `technical-design` vs `ui-spec` | API contract design vs UI reuse/spec generation | keep split |
| `task-slicing` vs `incremental-impl` | plan vertical slices vs execute one approved slice | keep split |
| `impact-analysis` vs source discovery | workflow preflight artifact vs local CodeGraph exploration | keep `impact-analysis` advisory |

## Deprecation Rules

A workflow can become `DEPRECATED` only when all are true:

- replacement workflow is named in `replacement_workflow` or `deprecation.replacement_workflow`;
- compatibility alias/path is documented if users or scripts may still call the old name;
- at least one eval or owner decision explains why the replacement is better;
- doctor/governance scan stays green;
- router will not auto-route the deprecated workflow.

Current owner decision removes `super-test` and `progressive-test` in favor of `robust-test`; this is an
explicit governance override, not an eval-derived auto-promotion. Future removals still require the rules
above unless explicitly owner-authorized.

## Commands

```bash
python scripts/harness_workflow_governance.py scan
python scripts/harness_workflow_governance.py summary
python scripts/harness_workflow_governance.py --self-test
```

Doctor runs the governance scan as part of harness health.
