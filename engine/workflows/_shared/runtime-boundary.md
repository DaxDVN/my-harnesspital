# Runtime Boundary Contract

P3 hardening target: external executors can be powerful, but they must cross a small deterministic
boundary. This document is the shared contract for Claude/Codex/OpenCode/MiMo/agent-browser wrappers.
It is policy + observability in P3, not a breaking runtime migration.

## 1. Boundary Rule

External executor interactions should go through a wrapper or launcher owned by the workflow. The wrapper
is responsible for:

- fixed model/provider selection or an explicit config lookup;
- prompt file path or prompt template path, not ad-hoc pasted prompts;
- log/artifact directory creation;
- output schema or envelope validation;
- state transition validation when the workflow has a state machine;
- diff/allowlist validation before repair writes are accepted;
- read-only enforcement for audit/harvest/RCA phases;
- writing short routing receipts instead of long prompt payloads.

External executors and autonomous workflow loops are owner-gated. A router candidate, keyword match, or
skill trigger is not enough to start a long-running workflow when the manifest has `auto_route_allowed=false`.
In those cases the agent should prepare the scope, required inputs, command, and
validation expectations, then wait for explicit owner approval to run.

## 2. Envelope Contract

Workflows that emit receipts should use the shared envelope dialect:

```bash
python engine/workflows/_shared/validate-envelope.py <envelope.json> --payload <payload>
```

The deprecated progressive/super-test runtimes and their legacy envelope dialects are removed from the
active harness. Do not introduce compatibility adapters for removed runtimes unless the owner explicitly
restores them.

## 3. Prompt Prose vs Runtime Enforcement

Prompt prose can explain intent, but it must not be the only boundary for high-risk actions. Prefer this
ordering:

```text
wrapper config/state check
> schema/envelope validator
> allowlist/diff check
> prompt instruction
```

If the runtime can check a rule cheaply, encode it there instead of asking an LLM to remember it.

## 4. Read-Only Phases

Audit, source discovery, harvest, reproduction, RCA, Codex review, and design preflight are read-only
unless the workflow explicitly transitions into an implementation phase. Read-only phases may write their
own logs/artifacts/envelopes under the workflow run directory, but must not edit source repos.

## 5. Repair Phases

Repair/implementation phases must have:

- an explicit approved plan or owner instruction;
- an allowed write scope;
- validation commands or a recorded reason they could not run;
- a final envelope/report with verdict, payload path, hash, and next recommendation.

When a repair touches API/DTO/schema/security/permission/business/billing/insurance/state-machine or
multi-module flow, the workflow should escalate risk rather than relying on fast-path.

## 6. Wrapper Complexity Budget

Wrappers should stay thin. A good wrapper does these things and no more:

- prepare environment;
- invoke one executor;
- capture logs;
- validate output shape;
- update workflow state;
- fail closed on malformed output.

Do not build a new framework unless file artifacts + envelope + validator + allowlist are demonstrably
insufficient.

## 7. P3 Compatibility Policy

P3 is shared-envelope-first:

- new workflows should use `envelope.schema.json`;
- wrappers stay thin and owner-gated;
- add doctor checks that warn or self-test runtime boundaries;
- migrate only after real-run evidence proves the runtime path is safe.
