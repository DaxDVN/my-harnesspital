# Harness Router - P1 Dry-Run

P1 status: read-only dry-run router. It classifies intent, risk tier, lifecycle, and files-to-load. It does not execute workflows, enforce fast-path, edit files, thin context by itself, or change runtime behavior.

## Purpose

The router is the future governance boundary between a user prompt and a workflow. It should reduce token waste by choosing the smallest safe workflow and the exact files to load, while preserving quality through conservative escalation.

## Command

```bash
python scripts/harness_router.py "<user prompt>"
python scripts/harness_router.py --json "<user prompt>"
python scripts/harness_router.py --self-test
python scripts/harness_preflight.py "<user prompt>"
```

The script uses only Python stdlib and reads:

```text
engine/workflows/*/manifest.json
engine/skills/*/SKILL.md existence
engine/workflows/*/README.md existence
```

It also has built-in non-enforcing entries for skill-only routes currently not represented by workflow manifests:

```text
mh-implement
mh-fix
mh-scaffold
ponytail
harness-maintenance
```

## Dry-Run Output

The router prints a machine-readable decision like:

```yaml
intent:
risk_tier: UNKNOWN # T0|T1|T2|T3|UNKNOWN
candidate_workflow:
entry_skill:
lifecycle_status:
lifecycle_evidence:
  ok: false
  reason:
auto_route_allowed:
confidence: low # high|medium|low
uncertainty: []
skills_to_apply: []
candidate_agents: []
external_agents: []
rules_to_apply: []
required_inputs: []
required_gates: []
owner_confirmation:
  required:
  action:
  reason:
prompt_file_recommended:
prompt_file_required: false
prompt_file_policy:
files_to_load: []
do_not_load: []
allowed_writes: []
validators: []
budget:
  max_context_files: 0
  max_payload_inline_chars: 0
fast_path:
  allowed: false
  reason:
reason:
```

For owner-facing natural-language use, prefer `scripts/harness_preflight.py`. It wraps the same decision into a
compact confirmation card and remains read-only. Agents must not execute the predicted route until the owner
confirms when `owner_confirmation.required=true`. Preflight enriches the raw router output with inferred FE/BE
package scope, package rule files, and matched worktree when the selected route actually needs one.

## Risk Tiers

| Tier | Meaning | Default handling |
|---|---|---|
| T0 | Trivial/local; no contract/business/security uncertainty | Candidate for minimal workflow only after deny-on-uncertainty gates pass |
| T1 | Ordinary scoped bug/feature | Recall, CodeGraph/source discovery, scanner, targeted validation |
| T2 | API/DTO/schema/security/permission/business/billing/insurance/state-machine/migration risk | Impact/design preflight and targeted review/validation |
| T3 | High-risk, broad module, clinical/financial/security, merge/audit gate | Deep review partitioning, deterministic scan, E2E/robust-test as appropriate |
| UNKNOWN | Insufficient information | Ask clarification or escalate; never fast-path |

## P1 Rules

- P1 router is dry-run only.
- It must not execute workflows.
- It must not enforce fast-path.
- It must not edit files.
- Explicit workflow names may select a candidate workflow, but lifecycle still controls auto-route.
- Workflows below `PROVEN` cannot auto-route.
- `PROVEN` / `DEFAULT` workflows also need a real `eval_summary.artifact_path` before auto-route.
- Fast-path is denied on uncertainty.
- API/schema/DTO/security/permission/business/billing/insurance/state-machine/migration/multi-module uncertainty escalates risk tier.
- Ambiguous intent should ask for clarification in later enforcing versions.
- Router output lists what to load and what not to load.
- Router output lists predicted skills, agents, external agents, and rules so the owner can confirm the route.
- Router output may recommend a prompt file, but it must not auto-load that file for normal daily work.
  Prompt files are session/external-agent runbooks, not lightweight workflow docs.
- Router output is advisory until a later owner-approved phase turns any part into enforcement.
- A candidate workflow is not execution approval. If the manifest has `auto_route_allowed=false` or lifecycle
  below `PROVEN`, the agent may prepare scope/inputs/commands but must not launch the workflow without an
  explicit owner instruction.
- Natural-language preflight is the default UX for actionable work: predict route -> show card -> wait for owner
  confirmation -> execute only the confirmed route.

## Manifest Inputs

The router should read only lightweight manifest metadata first:

```text
engine/workflows/*/manifest.json
```

Relevant P0 fields:

```text
name
kind
entry_skill
public_entry
auto_route_allowed
lifecycle_status
required_inputs
allowed_writes
validators
budget
eval_summary
recommended_prompt_file
```

P4 lifecycle evidence fields:

```text
eval_summary.last_real_run
eval_summary.artifact_path
eval_summary.verdict
```

The router treats missing eval evidence as an auto-route blocker. It may still suggest the workflow as a
candidate for explicit owner invocation.

Workflow runbooks and protocol docs should be loaded only after the dry-run decision names the candidate workflow and files to load.

`engine/rules/ponytail.md` is a default modifier for fix/implement/scaffold/design/review routes. It is not a
separate workflow gate; it makes reuse/minimal-correct-diff the default without requiring the owner to say
"ponytail".

`harness-maintenance` is an advisory route for harness/routing/eval/tooling/memory/index optimization. It exists
to avoid misrouting maintenance prompts into source implementation workflows. It is owner-gated, has
`auto_route_allowed=false`, and should validate with doctor/router/eval scans rather than source feature tests.

Prompt library files under `engine/prompts/` are different from workflow runbooks. The router reports them via
`prompt_file_recommended` so the owner, a fresh agent session, or a wrapper can choose a high-control system
prompt when appropriate. They are not included in `files_to_load` by default because loading them for every daily
task would reintroduce token waste.

Recommended usage:

```text
Daily small/normal work:
  router -> files_to_load -> skill/workflow docs

External/high-control work:
  router -> prompt_file_recommended -> wrapper/session prompt
```

## Conservative Escalation

The router must prefer false negatives over false positives for fast-path:

```text
If not clearly low-risk, do not classify as low-risk.
If uncertainty touches contract/business/security/data/state, escalate.
If lifecycle evidence is missing, block auto-route and require explicit owner intent.
```

## Public/Internal/Advisory Semantics

- `workflow`: user-facing workflow candidate, but not necessarily auto-routable.
- `internal`: subroutine called by another workflow; explicit advanced invocation may still exist, but router should not offer it as a normal public choice.
- `advisory`: read-only/preflight workflow; can be suggested as a gate before implementation.

## Non-Goals For P1

- No enforcing classifier.
- No execution orchestration.
- No root thinning.
- No workflow deprecation.
- No envelope migration.
- No wrapper behavior change.
- No review/test/validation gate removal.
