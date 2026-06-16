# Implementation Notes

## Implemented

- Standalone `.agentflow/` tree with config, state, prompts, schemas, wrappers, logs, and rounds.
- Bash OpenCode wrappers for TEST_ONLY, IMPLEMENT_ONLY, RETEST_ONLY.
- Python stdlib validator/state helper.
- `validate-artifact`, `update-state`, `init-round`, `summarize-round`, `doctor`.
- `tests/mock-opencode` for mock OpenCode/agent-browser behavior.
- `tests/run-smoke-tests` full contract smoke flow.
- Fixtures for all required artifact types.
- Vendored Vercel Labs `agent-browser@0.27.3` package under `.agentflow/vendor/agent-browser-package`.
- Project-local `.agentflow/bin/agent-browser` shim.
- Project-local OpenCode skill at `.opencode/skills/agent-browser/SKILL.md`.
- Local `.opencode/opencode.jsonc` allowing the `agent-browser` skill.
- Browser/capability probes for webfetch, low-level headless screenshot, and real `agent-browser` automation.

## Tests Run

Status: PASS in this implementation session. Commands run successfully:

Required commands:

```bash
.agentflow/bin/doctor
tests/run-smoke-tests
.agentflow/bin/validate-artifact state .agentflow/state.json
.agentflow/bin/validate-artifact bug-packet tests/fixtures/sample-bug-packet.json
.agentflow/bin/validate-artifact rca-plan tests/fixtures/sample-rca-plan.json
.agentflow/bin/validate-artifact codex-review tests/fixtures/sample-codex-review.json
.agentflow/bin/validate-artifact implementation-report tests/fixtures/sample-implementation-report.json
.agentflow/bin/validate-artifact retest-report tests/fixtures/sample-retest-report.json
```

Real OpenCode/browser commands also run successfully:

```bash
.agentflow/bin/capabilities
timeout 240s .agentflow/bin/probe-agent-browser-with-opencode https://example.com
.agentflow/bin/init-round round-real-agent-browser-1781616011 "Open https://example.com with Vercel Labs agent-browser CLI..."
AGENTFLOW_TARGET_URL=https://example.com timeout 300s .agentflow/bin/test-with-opencode round-real-agent-browser-1781616011
AGENTFLOW_TARGET_URL=https://example.com timeout 300s .agentflow/bin/retest-with-opencode round-real-agent-browser-1781616011
.agentflow/bin/summarize-round round-real-agent-browser-1781616011
```

## Mocked vs Real

Mocked in smoke tests: OpenCode executor behavior, MiMo provider behavior, source implementation, and agent-browser behavior.

Real in setup/probes: wrapper execution, logs, state transitions, artifact generation, validation, summary generation, OpenCode CLI, `xiaomi-token-plan-sgp/mimo-v2.5`, Vercel Labs `agent-browser` CLI, Chrome navigation, accessibility-tree snapshot refs, screenshots, OpenCode skill loading.

Implementation remains mock-tested by default because real implementation should only run against a real approved plan and allowlisted source files.

## Integration Notes

The wrappers keep the logical contract model as:

```yaml
executor:
  model: mimo-v2.5
  cli_model: xiaomi-token-plan-sgp/mimo-v2.5
```

They call OpenCode with:

```bash
opencode run --model xiaomi-token-plan-sgp/mimo-v2.5 "<prompt>"
```

If provider syntax differs later, change only `.agentflow/config.yaml` or the wrapper scripts. Keep `.agentflow/config.yaml` as the model/provider source.

## TODO

- Full JSON Schema validation is intentionally avoided to keep stdlib-only.
- Real Claude RCA subagent and Codex plugin invocation are represented by instruction files + artifact contracts; orchestrator integration comes later.
- Provider token/credit usage fields are schema-ready but remain `null` until OpenCode exposes usage.

## Current Environment Notes

- `opencode` was found by doctor at `/home/dax/.opencode/bin/opencode`.
- `agent-browser` is available through the project-local shim `.agentflow/bin/agent-browser`.
- `agent-browser` version: `0.27.3`.
- `agent-browser install` installed Chrome at `/home/dax/.agent-browser/browsers/chrome-149.0.7827.115`.
- OpenCode loads `.opencode/skills/agent-browser/SKILL.md` and shows `Skill "agent-browser"` in real run logs.
- Smoke test uses `AGENTFLOW_MOCK_OPENCODE=1`, so it validates the contract loop without burning OpenCode tokens.


## Capability Probe Update

Added:

- `.agentflow/bin/capabilities` to inspect OpenCode model availability, MCP servers, agent permissions, webfetch/websearch, local `agent-browser`, browser install, and skills.
- `.agentflow/bin/probe-web-with-opencode <url>` to test real OpenCode web inspection using the `explore` agent and `xiaomi-token-plan-sgp/mimo-v2.5`.

Important distinction:

- `webfetch`/`websearch` can inspect/search web content.
- They are not equivalent to `agent-browser`; they cannot click/fill/wait/snapshot like browser automation.


## Browser Capability Guard

Real `TEST_ONLY` and `RETEST_ONLY` now require `agent-browser` by default. If the project-local or PATH `agent-browser` shim is not detected, wrappers stop with `AGENT_BROWSER_NOT_AVAILABLE` instead of allowing a false PASS. Set `AGENTFLOW_REQUIRE_AGENT_BROWSER=0` only for low-level OpenCode smoke/debug runs, not for E2E validation.

Additional probes:

```bash
.agentflow/bin/probe-web-with-opencode https://example.com
.agentflow/bin/probe-browser-with-opencode https://example.com
.agentflow/bin/probe-agent-browser-with-opencode https://example.com
```

The first uses OpenCode webfetch/websearch. The second asks OpenCode to drive Firefox headless via bash as a low-level browser smoke. The third uses Vercel Labs `agent-browser` CLI and is the real E2E browser automation probe.


## Real Capability Probe Results

Latest real probes:

- `xiaomi-token-plan-sgp/mimo-v2.5` is available under the Xiaomi Token Plan Singapore provider.
- `opencode` is available at `/home/dax/.opencode/bin/opencode`.
- OpenCode MCP list exposes `codegraph` only; browser automation is CLI-based through `agent-browser`, not MCP.
- OpenCode agent list exposes `webfetch`, `websearch`, and `bash` capabilities.
- OpenCode agent list also shows project-local skill permission for `agent-browser`.
- `agent-browser` is available at `/home/dax/Documents/arabica/tools/agentflow-opencode/.agentflow/bin/agent-browser`.
- Firefox exists at `/usr/bin/firefox`.
- `agent-browser` Chrome exists at `/home/dax/.agent-browser/browsers/chrome-149.0.7827.115`.

Real probe commands run:

```bash
.agentflow/bin/capabilities
timeout 120s .agentflow/bin/probe-web-with-opencode https://example.com
timeout 120s .agentflow/bin/probe-browser-with-opencode https://example.com
timeout 240s .agentflow/bin/probe-agent-browser-with-opencode https://example.com
```

Results:

- `probe-web-with-opencode` succeeded using OpenCode `WebFetch` on `https://example.com`.
- `probe-browser-with-opencode` succeeded by asking OpenCode to run `firefox --headless --screenshot`, producing a screenshot in `.agentflow/logs/`.
- `probe-agent-browser-with-opencode` succeeded using OpenCode Bash calls to `agent-browser skills get core`, `agent-browser open`, `agent-browser snapshot -i`, `agent-browser screenshot`, and `agent-browser close`.
- Real `test-with-opencode` succeeded for `https://example.com` and wrote a valid `01-bug-packet.json`.
- Real `retest-with-opencode` succeeded for `https://example.com` and wrote a valid `06-retest-report.json`.

Conclusion: current environment can run browser automation through Vercel Labs `agent-browser` inside OpenCode. Playwright MCP is no longer registered as the browser path for this tool.


## Harness integration + envelope/triage/orchestration (2026-06-16, Opus 4.8)

Moved the whole tool into the harness: `engine/workflows/agentflow-opencode/` (relative ROOT = `parents[2]`,
so the move was self-contained; doctor + smoke pass from the new location). Driven by the new owner-invoked
`engine/skills/agentflow/SKILL.md` orchestrator skill (Claude reaches it via the `.claude/skills`→`engine/skills` symlink).

Added (envelope-native + hybrid triage + orchestration realization):
- **Envelope layer** (`lib`: `derive_envelope`/`validate_envelope`/`write_envelope`; `schemas/envelope.schema.json`;
  `bin/write-envelope`, `bin/validate-envelope`). Every payload `<x>` gets a short `<x>.envelope.json`
  (verdict/risk/next/`summary_for_router` + `content_sha256` binding). The 3 OpenCode wrappers now emit their
  envelope automatically; the orchestrator reads ONLY envelopes + validator results, never long payloads.
  `validate-envelope` re-hashes the payload and rejects on drift (proven).
- **Hybrid triage** (`bin/classify`): deterministic NARROW whitelist on bug-packet evidence
  (undefined-symbol / missing-import signatures) → TRIVIAL fast-lane (writes a constrained import-only
  `04-approved-plan.md`, skips RCA+Codex); everything else → NEEDS_RCA (Opus). Conservative by design.
- **Approved-plan builder** (`bin/build-approved-plan`): templates `04-approved-plan.md` from the rca-plan
  (+ codex-review if present → approval=APPROVED_BY_CODEX; REJECT refuses).
- New state transition `BUG_PACKET_READY → DIRECT_PATCH_APPROVED` for the trivial fast-lane.

RCA + Codex are realized at orchestration time by the `/agentflow` skill: RCA = an Opus subagent (Agent tool)
fed the bug-packet path + `prompts-or-instructions/rca-agent-instructions.md`; Codex = the codex plugin fed
the rca-plan path + `codex-review-instructions.md`. The orchestrator then writes their envelopes. (Codex is
NOT OpenCode, so it is not a bash wrapper — constraint 7 is OpenCode-only.)

### Git / portability
The harness `.gitignore` re-includes `.agentflow/bin/` (the global `bin/` rule would hide the wrappers) and
**ignores `.agentflow/vendor/` (~73 MB agent-browser package) + per-round `rounds/round-*/` output**. On a
fresh clone/migrate, RESTORE the browser: re-vendor `agent-browser` (Vercel Labs, v0.27.3) into
`.agentflow/vendor/agent-browser-package/` and run `.agentflow/bin/agent-browser install` (Chrome). Source
(bin/lib/schemas/prompts/config/tests/docs) is tracked.

### Safety seam (IMPORTANT)
IMPLEMENT_ONLY edits source. The harness guard FORBIDS editing `myhospital-fe|be` outside a worktree, so for
MyHospital the agentflow target MUST be a **worktree** (target repo path + URL via config/env). Generic
targets are unaffected.

### Mock vs real (honest)
Smoke (`AGENTFLOW_MOCK_OPENCODE=1`) proves the full wiring: test→classify→RCA→build-plan→implement→retest with
all envelopes validated incl. sha256 + the TRIVIAL fast-lane. Real executor (OpenCode/mimo + agent-browser)
is proven against example.com. NOT yet proven: a full Claude-orchestrated real bug-fix on a real FE (mimo's
fix quality) — that first real run is the owner's gate.
