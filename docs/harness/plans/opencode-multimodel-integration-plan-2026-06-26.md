# OpenCode multi-model integration plan (Fugu harness) — 2026-06-26

> Goal: let the blind PM orchestrator (Claude Opus 4.8) dispatch **non-Anthropic models via OpenCode**
> as drop-in workers — primarily a cross-model **audit** lane (owner-validated: `glm-5.2 --variant max`
> caught real bugs Opus 4.8 missed, confirmed by Opus xhigh) and a cheap **bulk-fixer** lane — while
> keeping every existing safety floor, gate, and the blind-PM contract intact.
>
> Status: PLAN / not built. Lifecycle target: **LAB** behind explicit owner opt-in until the bake-off
> eval floor (Phase 7) passes — same maturity discipline as `pm-orchestrator` auto-route.

## 0. Ground truth (verified from the live machine, not benchmarks)

- **OpenCode v1.17.11 installed**; **OpenCode Go authed** (`opencode auth list` → "OpenCode Go" + "Xiaomi Token Plan (SGP)" + Google `GEMINI_API_KEY`).
- **13 Go models addressable**: `opencode-go/{glm-5.2,glm-5.1,deepseek-v4-pro,deepseek-v4-flash,kimi-k2.7-code,kimi-k2.6,minimax-m3,minimax-m2.7,qwen3.7-max,qwen3.7-plus,qwen3.6-plus,mimo-v2.5,mimo-v2.5-pro}`. (Free `opencode/*-free` variants exist but are **NOT used** — owner directive 2026-06-26: rate-limit risk; use PAID `deepseek-v4-flash` for the cheap lane.)
- **Headless contract** (verified on the live CLI v1.17.11): `-m provider/model`, `--variant <high|max|minimal>` (reasoning effort), `--agent <name>`, `--dir <path>` (scope to worktree), `--format json` (NDJSON events), `-c/--session/--fork` (session continuity), `--pure` (no plugins), `--attach http://127.0.0.1:4096` (attach to a persistent `opencode serve` to avoid MCP cold-boot per call), `--dangerously-skip-permissions`. **There is NO `-q/--quiet` flag** (an early research guess; the live spike rejected it — caught by Phase 0). See §9 for the verified `--format json` parsing contract + smooth-calling guide.
- **Read-only sandbox is native**: built-in `--agent plan` / `explore` agents make NO modifications; per-agent frontmatter `permission: {edit:deny, bash:deny}` or `tools:{write:false}`; global `permission` wildcard block (`"rm -rf *":"deny"`). NOTE: **default posture is allow-all** — must explicitly add deny/ask to sandbox. There is **no native per-file allowlist** (closest = `--dir` + `plan` agent + permission deny; rely on worktree scoping + the harness gate).
- **Go endpoints** (single-shot mode, optional): OpenAI-compat `https://opencode.ai/zen/go/v1/chat/completions` + Anthropic-compat `/v1/messages`, authed by `OPENCODE_API_KEY` (`~/.local/share/opencode/auth.json`).
- **Harness already tool-neutral**: `.opencode/opencode.json` loads `AGENTS.md` + `engine/rules/README.md` as instructions and a graphify plugin; `~/.config/opencode/opencode.jsonc` wires codegraph MCP; `.codex/hooks.json` runs the shared `engine/hooks/myhospital_guard.py` on Bash. Guard + rules are NOT Claude-locked.
- **Tool choice = OpenCode** (primary): the 13 Go models work out-of-the-box as `opencode-go/*`, with the read-only `plan` agent + `--format json` contract. CORRECTION (research 2026-06-26): `pi` (`@mariozechner/pi-coding-agent`, also installed) CAN consume Go too — via a custom OpenAI-compatible provider pointed at the Go endpoint; OpenCode's own page names Pi/Claude Code/Codex as Go-compatible. But the Go seat is a **single dollar-capped workspace seat** ($12/5h, $30/wk, $60/mo) — parallel multi-agent burns it fast. OpenCode stays the cleanest native consumer; keep `pi` as a secondary lightweight lane.

## 1. Why this fits the existing Fugu harness with ~no new abstraction

The blind PM already "routes a PATH → gets a compact blob back; never reads source itself." Claude's native
`Agent`/Workflow `agent()` can only spawn Anthropic models. Non-Anthropic models enter via **`opencode run`
over Bash**, which preserves the blind-PM contract exactly: PM shells out → OpenCode runs the chosen model in
its own agent loop scoped to `--dir <worktree>` → writes an artifact → returns JSON → PM records a compact blob
+ artifact path. A Bash call from the main loop is a tool call, not a nested `Agent` spawn, so the
"fan-out only from the main loop" rule is honored.

`tier_policy.json` is already a tier→(model,effort) map. We extend it to tier/role→(provider, model, variant,
backend). That is the whole conceptual change.

## 2. The two highest-ROI lanes (build these first; everything else is optional)

### Lane A — Cross-model adversarial AUDIT (read-only · zero convention risk · owner-proven)
Add `glm-5.2 --variant max` (and optionally `deepseek-v4-pro`) as an **independent reviewer dimension** in
`deep-review`, over the SAME changeset the Claude reviewers see. Model-family diversity ⇒ different failure
modes ⇒ higher recall (this is exactly where the owner saw GLM beat Opus). Survivors flow into the EXISTING
adjudication pass; cross-adjudicate (Opus judges GLM's findings and vice-versa — the owner already did this by
hand). Read-only ⇒ auto-dispatchable under gate-by-risk; no mutation, no convention risk. **Start here.**

### Lane B — Cheap bulk FIXER tier (mechanical T0/T1 · gated)
Route units tagged `complexity ∈ {simple, layout}` AND `risk_class ∈ {none, cosmetic}` to
`opencode-go/deepseek-v4-flash` / `mimo-v2.5` (or the `-free` variants) via the adapter, behind the SAME
build/typecheck/scanner gate before accept. ~30–40× cheaper output than Opus. Escalate-on-gate-fail
(flash → sonnet → opus). Convention-heavy / clinical / billing / permission / migration units stay on Claude.

## 3. Safety floors preserved (non-negotiable)

- **risk_class_floor unchanged for GENERATION**: clinical / billing / permission / migration *code generation*
  stays on the Anthropic Opus floor (or a model that has passed a per-class eval). Cross-model **AUDIT** of
  those (read-only) is encouraged.
- **The harness gate is the verification floor regardless of author model**: a cheap model's edit is accepted
  only if it passes the same `tsc` / `dotnet build` / scanner the harness already runs. "VERIFIED = real
  evidence" rule unchanged.
- **Guard coverage** (`myhospital_guard.py`): fix-lane workers run scoped to `--dir worktrees/<slug>` and are
  re-validated by the harness gate after; hardening option in Phase 5 wires the guard into OpenCode's own
  permission/plugin layer.
- **Privacy flag** (refined by research): via the **Go gateway**, inference routes through OpenCode (SST/US)
  infra to backends in **US/EU/Singapore** (per /docs/go) — NOT necessarily China-hosted. Via the **vendors'
  own APIs** it would be China-hosted. Either way it is third-party inference = a compliance event for
  clinical/PII source. Owner OK'd for staging. The bigger *practical* risk per reporting is inference-backend
  variance (same weights behave differently per provider/call), not a China-specific backdoor. Keep these
  models on non-sensitive code / synthetic snippets off-staging.
- **Lifecycle**: LAB / explicit opt-in until Phase 7 eval floor passes.

## 4. Phased build

### Phase 0 — Spike (1 round-trip proof; cheap, read-only)
Run one real audit and confirm the contract end-to-end:
```bash
opencode run "Audit this file for bugs; output a findings list (id, severity, file:line, why)." \
  -m opencode-go/glm-5.2 --variant max --dir worktrees/<slug> --format json --pure
```
Confirm: JSON parses · `--variant max` honored · `--dir` scopes it · authed Go model returns · it surfaces
something real. Make-or-break, ~minutes.

### Phase 1 — `scripts/oc_worker.py` adapter (the core; ~1 file, Ponytail)
Uniform wrapper = the OpenCode analog of dispatching a Claude subagent. Drop-in interchangeable from the PM's view.
- **Input**: `--role {audit|fix|bulk} --model <id> --variant <v> --scope <dir> --prompt-file <p> --out <artifact> [--read-only]`.
- **Context by reference (reuse existing machinery, don't reinvent)**: build the prompt from the SAME inputs the
  harness gives Claude workers — `scripts/rule_card.py fe|be` output + the routed `recommended_prompt` +
  `learning_recall` notes + the `engine/prompts/subagent-prompt-template.md` shape.
- **Invoke**: `opencode run "<prompt>" -m <model> --variant <v> --agent <agent> --dir <scope> --format json`
  (+ `--dangerously-skip-permissions` only for the fix role; audit runs read-only).
- **Return (harness worker-blob shape)**: `{role, model, files_changed[], validation{cmd,result},
  findings_path|artifact_path, summary, est_cost}`. PM gets the blob + path, never the body.
- For **fix**: after the run, the adapter (or PM) runs the harness gate and records REAL validation.

### Phase 2 — `tier_policy.json` provider/backend extension
Each tier/role entry: `{provider: anthropic|opencode, model, variant|effort, backend: native|opencode-cli|opencode-api}`.
Add a `roles` block: `audit_second_opinion → opencode-go/glm-5.2 (variant max)`,
`bulk_mechanical → opencode-go/deepseek-v4-flash` (PAID; no free variants per owner). (Superseded by §5 owner-lock.)
Keep `risk_class_floor` Anthropic for generation. Add `provider_budget` hints (Go $ caps) for routing.
Router (`scripts/harness_router.py select_model_effort`) gains provider/backend awareness; preflight card shows it.

### Phase 3 — Wire Lane A into deep-review
Add optional `cross_model_audit` stage: a thin Claude shim agent (or main-loop Bash step) calls
`oc_worker.py --role audit --model opencode-go/glm-5.2 --variant max` over the changeset → findings md → merged
into the existing adjudication pass. Read-only ⇒ auto-dispatch OK.

### Phase 4 — Wire Lane B into batch-bugfix / implement
In the fan-out, dispatch `simple/layout + risk_class∈{none,cosmetic}` units to the cheap/free model via the
adapter, SAME gate before accept, escalate-on-fail. Log every drop/cap (no silent truncation).

### Phase 5 — Guard coverage for OpenCode edits
v1: rely on worktree `--dir` scoping + post-run harness gate (cheapest, uses the existing floor).
Hardening: add an OpenCode permission config / plugin (`.opencode/plugins/`) that invokes
`myhospital_guard.py` on Edit/Bash so OpenCode fix-workers hit the same guard as Claude/Codex.

### Phase 6 — Budget guard + telemetry
`scripts/oc_budget.py`: tally per-dispatch model + est cost; keep within $12/5h by reserving `glm-5.2` for the
high-value audit pass and using `deepseek-v4-flash` / `-free` for volume. Never silent-cap; log skipped work.

### Phase 7 — Bake-off eval before trust (lifecycle gate)
Controlled comparison on a real changeset:
- **Audit recall**: Opus xhigh vs `glm-5.2 max` vs merged; FP rate adjudicated by the other model.
- **Mechanical-fix pass-rate**: `flash + gate` vs Claude.
Record in `pm-orchestrator/manifest.json` eval_summary. Flip cross-model lanes LAB→enabled only when the floor
passes. Mirrors the existing auto_route maturity gate.

## 5. Model routing — LOCKED by owner 2026-06-26 (ratify quality via Phase 7 bake-off)

Orchestrator is FIXED: **Opus 4.8 low**, always — it spawns the per-task model. Owner directives:
**no free OpenCode variants** (rate-limit risk → use PAID `deepseek-v4-flash`); **glm-5.2 is AUDIT-ONLY**
(too token-heavy for agentic loops); **agentic edit uses deepseek-pro / minimax-m3**, **kimi-k2.7 only when
those two can't cover**; **mimo-v2.5 for tests/docs/chores**; Opus only at the top — **xhigh** by default when
Opus is needed, **max** only for whole-module refactor / dangerous / irreversible; **Sonnet dropped** from the
default ladder.

### 5.0 Role → model map

| Role / situation | Model | Variant/effort | Mutates? | Gate |
|---|---|---|---|---|
| Orchestrator (fixed) | Anthropic opus | low | no | — |
| Audit / review (read-only, primary) | `opencode-go/glm-5.2` | max | no | adjudicated |
| Audit second lens (optional) | `opencode-go/deepseek-v4-pro` | high | no | adjudicated |
| Adjudicate findings | Anthropic opus | xhigh | no | — |
| Tests / docs / chores (lặt vặt) | `opencode-go/mimo-v2.5` | high | yes | build/test |
| Simple mechanical code fix / bulk | `opencode-go/deepseek-v4-flash` (PAID) | high | yes | tsc/build + scanner |
| Agentic fix/implement — primary | `opencode-go/deepseek-v4-pro` | high | yes | build + scanner + self-review |
| Agentic — harder | `opencode-go/minimax-m3` | high | yes | same |
| Agentic — complex (when above can't cover) | `opencode-go/kimi-k2.7-code` | high | yes | same |
| Clinical/billing/permission/migration — gen OR fix | Anthropic opus | xhigh | yes | floor + regression-map |
| Whole-module refactor / dangerous / irreversible | Anthropic opus | max | yes | regression-map + full build/test |

### 5.1 "Sinh code" (generation) broken down — the vague role made explicit

"Generation" is not one thing. Sub-types, each with WHEN + model + why:

| Sub-type | When | Model | Why |
|---|---|---|---|
| **Scaffold** (mh-scaffold) | "new endpoint/service/listing/module/page/list/form" — emit canonical template | `deepseek-v4-pro` | near-deterministic template fill; scanner enforces convention |
| **Implement slice — non-clinical** | new logic/UI for an approved slice, conventions scannable | `deepseek-v4-pro → minimax-m3 → kimi-k2.7` | cheap agentic + scanner/rule_card/self-review-diff catch drift |
| **Implement slice — clinical/billing/permission/migration** | new logic in a sensitive domain | **opus xhigh** (floor) | safety; never a cheap model for new clinical logic |
| **Fix existing — non-clinical** | edit to correct a defect | `deepseek-v4-pro / minimax-m3`, `kimi-k2.7` if complex | owner directive; agentic edit |
| **Fix existing — clinical/billing/permission/migration** | defect in a sensitive domain | **opus xhigh** | fixing clinical logic is as sensitive as writing it |
| **Local refactor** | bounded restructure to a pattern | `deepseek-v4-pro / minimax-m3` | + regression-map |
| **Whole-module / dangerous refactor** | module-wide or irreversible | **opus max** | highest stakes |
| **Generated artifacts** (DTO/client/EF migration files) | contract regen | **NOT model-generated** — tool regen only | hard rule; never hand-edited |

### 5.2 Escalation ladder (agentic generation/fix, non-clinical)

`deepseek-v4-pro → minimax-m3 → kimi-k2.7-code → opus xhigh → opus max`. Escalate the **variant** before
escalating the **model**. Escalate a tier when: the gate fails twice on the same unit, OR the unit is judged
beyond the current model's reliable envelope (orchestrator's call), OR it crosses into a
clinical/billing/permission/migration class (jump straight to opus xhigh).

### 5.3 Dropping Sonnet — honest evaluation (owner decision: remove from default ladder)

The owner reports the Chinese models now beat Sonnet 4.6 (benchmarks + own use). I CANNOT verify the benchmark
claims — every point-version is post-cutoff and only vendor pages exist (§5.4) — so I do not endorse them as
fact; but the owner's empirical use is valid evidence and the decision is sound STRUCTURALLY:
- What Sonnet uniquely gave this harness = Anthropic-family **convention + tool-use reliability at mid cost**.
- Now covered by: deterministic **scanners** (mh_scan / FE scanner) + **rule_card** injection +
  **self-review-diff**, with **opus xhigh** as the floor for anything sensitive or convention-uncovered.
- Net shape = a **barbell**: cheap Chinese models at the bottom, Opus at the top, no Anthropic mid-tier.
- **The one residual risk**: a NON-scannable convention rule on NEW non-clinical code written by a cheap model
  that knows MyHospital idioms less well. **Mitigation (harness-native, NOT "bring Sonnet back")**: treat the
  first real runs as a convention-drift watch; if a convention class slips twice, PROMOTE a scanner (the
  existing scanner-promotion gate). Keep Sonnet only as an emergency manual fallback, never in the auto ladder.

### 5.4 Research findings (2026-06-26) — lineage-grounded; exact point-versions UNVERIFIED post-cutoff

Every exact version (GLM-5.2, DeepSeek V4, Kimi K2.7, Qwen3.7, MiniMax M3, MiMo-V2.5) is newer than the
Jan-2026 cutoff; the ONLY web sources are vendor/benchmark pages (the kind the owner distrusts). No independent
practitioner consensus exists for these point-versions. Reads below = lineage reputation (GLM-4.6, Kimi K2,
DeepSeek V3/R1, Qwen3-Coder, MiniMax M1/M2, Xiaomi MiMo-7B) + an unverified flag. **Treat all as
candidate-finders adjudicated by a strong model** — consistent with the existing "cheap finds, strong decides" gate.

| model | audit/review (lineage) | agentic multi-file edit (lineage) |
|---|---|---|
| Kimi K2.7-code / K2.6 | thorough | **best-regarded open model for long autonomous tool-use** |
| GLM-5.2 / 5.1 | decent FE/logic, cheap; owner-proven on real bug | strong FE/full-stack; popular cheap Claude-Code backend |
| DeepSeek V4 Pro | strong deep-reasoning audit; verbose | **historically flakiest at strict tool-call formatting**; value pick, 1M-ctx |
| Qwen3.7 Max/Plus, Qwen3.6 Plus | solid, efficient | reliable/efficient, mid on long autonomy |
| MiniMax M3 / M2.7 | less proven in Western circles | improving anecdotally, thin track record |
| DeepSeek V4 Flash | speed tier, lower recall | fast but shallow multi-step |
| MiMo-V2.5 / -Pro | least known/proven | weakest evidence for multi-file tool-use |

Practical: cheapest **non-Anthropic auditor** → favor **Kimi (long tool-use)** + **GLM (FE/logic, cheap, owner-proven)**;
DeepSeek = deep-reasoning value pick but flakiest at agentic tool-calling → prefer it for read-only audit, not fix.

## 6. Open questions / caveats

- Benchmarks unreliable (owner's stance) → trust the Phase 7 bake-off + harness gates, per-role.
- Agentic multi-file edit reliability varies by model → keep weak/cheap models on audit + simplest mechanical first.
- Privacy: third-party inference for source — staging-only unless re-authorized.
- OpenCode plugin/permission guard wiring (Phase 5) needs a small spike to confirm the hook surface.
- `pi` could become a Gemini-backed lightweight lane later, but is out of scope for the Go-plan integration.

## 7. Mandatory Opus 4.8 xhigh final review (owner invariant 2026-06-26)

Every code-mutating workflow (feature / fix / batch-bugfix / espresso / scaffold / refactor — any gen-code)
MUST end with an **Opus 4.8 xhigh review of the produced diff — ALWAYS**, even if a non-Anthropic model
(glm-5.2 / kimi-2.7 / deepseek / …) already reviewed. Non-Anthropic review is **additive, never a substitute**.
Rationale: cheap models are allowed to IMPLEMENT to spare Claude quota, but are NOT trusted; Opus does the
final careful review. This is a HARD gate, independent of gate-by-risk. Encoded in:
`scripts/tier_policy.json` → `mandatory_final_review` (skippable=false) + each mutating `recipe_depth.phases`
ends with `opus-xhigh-final-review (mandatory)`; `engine/rules/quality-gates.md` gate matrix; surfaced on the
preflight card ("⚠ BẮT BUỘC review cuối").

## 8. Build status

### Increment 1 — foundation + adapter (DONE, validated 2026-06-26)
- `scripts/tier_policy.json` — owner-locked routing: `orchestrator`/`roles`/`agentic_ladder`/
  `mandatory_final_review`/`providers`; `risk_class_floor` → opus **xhigh**; Sonnet dropped from dispatch;
  mutating recipes end with a mandatory opus-xhigh review phase.
- `scripts/harness_router.py` — new `select_worker_routing()` (provider-aware: recipe + risk_class + cheap
  path-stripped signals → role → model); `TIER_POLICY_FALLBACK` updated; decision exposes `worker_routing`;
  self-tests extended (clinical floor → xhigh; worker_routing assertions). `select_model_effort` kept as the
  Anthropic-equivalent baseline.
- `scripts/harness_preflight.py` — card now headlines the real worker dispatch + the mandatory-final-review
  line + the Anthropic floor baseline; self-tests extended.
- `scripts/oc_worker.py` — NEW adapter: resolves an OpenCode role → builds `opencode run -m opencode-go/<m>
  --variant <v> [--agent plan] --dir <scope> --format json`; injects rule-card/preamble; refuses Anthropic
  roles; `--dry-run` + `--self-test`; returns a compact blob (PM reads the blob, not the body).
- `engine/rules/quality-gates.md` — gate-matrix row for the mandatory Opus xhigh final review.
- Validation: `harness_router --self-test` OK · `harness_preflight --self-test` OK · `oc_worker --self-test` OK
  · routing battery correct (docs-path no longer mis-triggers trivial; local-refactor ≠ opus-max) ·
  `harness_doctor` 80 OK / 0 FAIL (4 pre-existing WARN unrelated: graphify/codegraph staleness).

### Increment 2 — deep-review reviewers → glm-5.2 (Option B, owner-chosen 2026-06-26; static-validated)
Owner chose to DROP Sonnet from deep-review (not just add a glm lane). `engine/workflows/deep-review/workflow.js`:
  - `DEFAULT_TP` owner-lock (coordinator opus/low; adjudication + clinical floor opus/**xhigh**;
    `verifier.find` → haiku so no Sonnet leaks when no policy is injected).
  - `anthropicModel(m, fallback)` coercion on every `agent()` model from `tier_policy` — an injected policy
    naming an OpenCode model (e.g. `verifier.find = glm-5.2`) can't break `agent()` (Anthropic-only). The cheap
    model still runs — via the shim.
  - **Find tier restructured**: **D1** (business-logic vs clinical BA — highest judgment) stays **Anthropic
    Opus** multi-pass; **D2-D7** run on **glm-5.2** via the `reviewGlmShim` (a thin Anthropic wrapper that only
    runs `oc_worker.py --role audit` per dimension + structures the output), **batched 2** to respect the
    single dollar-capped Go seat.
  - Filter passes (self-adversarial + verify + completeness) → **haiku** (cheap Anthropic; Sonnet gone).
  - Surviving BLOCK/HIGH → **Opus xhigh adjudication** (the trusted decider — "cheap finds, Opus decides").
  - Return reports `lanes` (opus reviewers, glm5_2 reviewers, haiku filters, adjudication tier). **No Sonnet anywhere.**
- batch-bugfix mandatory final review: enforced at the policy layer (recipe phases end with
  `opus-xhigh-final-review (mandatory)` + `mandatory_final_review` in tier_policy + quality-gates row); the PM
  dispatches it as the closing phase (no separate workflow.js to edit — batch-bugfix is a PM recipe).
- Validation: `node` parse-check OK · doctor 80 OK / 0 FAIL · workflow-governance + runtime-contract scans clean
  (no new external-boundary violation from the oc_worker Bash call inside the shim). NOT yet run end-to-end
  (owner-gated; first real deep-review run on a module = the live test).

### Increment 3 — batch-bugfix recipe → OpenCode dispatch + mandatory final review (DONE 2026-06-26)
`engine/workflows/pm-orchestrator/manifest.json` (batch-bugfix recipe):
- `analyze`: analyst tags each confirmed bug complexity→**role** per `tier_policy.roles`/`agentic_ladder`
  (simple/mechanical→deepseek-v4-flash · medium→deepseek-v4-pro/minimax-m3 · complex→kimi-k2.7-code ·
  doc/test→mimo-v2.5 · clinical/billing/permission/migration→opus xhigh floor · whole-module→opus max).
- `fix`: per-bug worker = a Claude shim running `oc_worker.py --role <bug.role> --allow-edit` for OpenCode roles,
  or mh-implementer (Claude opus) for the clinical floor; depth-1 from the main loop; **every fix re-validated by
  the harness gate** (tsc/build/scanner) regardless of author model; gate-fail twice → escalate up the ladder.
- `final-review` (renamed from self-review): **MANDATORY Opus 4.8 xhigh review of the fix diff — non-skippable**,
  even after cheap-model self-review (owner invariant). Validation: manifest JSON valid · doctor 80 OK / 0 FAIL.

### Phase 5 — guard for OpenCode mutating edits (DONE 2026-06-26)
- `.opencode/opencode.json`: new **`mh-fixer`** agent with an explicit `permission` map — `edit:allow`,
  `bash` denies `git push/commit/reset --hard/clean`, `rm -rf`, dependency installs, EF migration/`database
  update`; `webfetch:deny`. Verified registered (`opencode agent list` → `mh-fixer (all)`).
- `scripts/oc_worker.py`: mutating roles now run `--agent mh-fixer` (no headless hang, no blanket
  `--dangerously-skip-permissions`); read-only stays `--agent plan`. Self-test updated + green.

### Phase 6 — budget guard (DONE 2026-06-26)
- `scripts/oc_budget.py`: caps ($12/5h, $30/wk, $60/mo) + 13 baked model prices; `record`/`status`/`can-spend`/
  `recommend` subcommands; 7d/30d trust `opencode stats`, 5h from a local tally (`.claude/.oc_budget.json`,
  gitignored); fail-open. `--self-test` green.

### Phase 7 — bake-off eval scaffold (DONE 2026-06-26)
- `scripts/oc_bakeoff.py`: `plan` (dry, default, zero opencode calls) / `run` (gated behind `--run`) → runs the
  glm-5.2 audit side via `oc_worker` and emits a 5-section comparison ledger to `docs/harness/evals/`; the Opus
  baseline is filled by running `deep-review` on the same scope; FP adjudication owed to Opus xhigh. `--self-test` green.

### Increment 2.1 — calling-method fix (run-001 live test surfaced it; FIXED + PROVEN 2026-06-26)
The first live `deep-review` (run-001, ipd-improve-v3) failed: glm shims returned ~100B planning-only stubs
(ZERO tool calls); owner manually fell back to mh-reviewer. ROOT CAUSE = the CALLING METHOD, NOT glm (owner had
run glm interactively on a full FE+BE review → it found real issues Opus agreed with):
- **`--agent plan`** = opencode's PLAN-MODE agent (emits a plan, does not execute a review).
- **`--dir <worktree>` does NOT walk up** → the harness `.opencode/opencode.json` (AGENTS.md, rules, custom
  agents) is NOT loaded; glm ran with generic config + zero MyHospital context = "giao việc vớ vẩn".
- loading the MAIN opencode.json into a worker is ALSO wrong — its `instructions:[AGENTS.md]` is the blind-PM
  bootloader, which would tell a worker to "route, don't do".
FIX:
- New **`.opencode/worker.json`** (worker-only; NO AGENTS.md instructions) with **`mh-reviewer-oc`** (read-only,
  system prompt forces a full review + findings-as-reply — NOT plan-mode) + **`mh-fixer`** (moved here).
- `scripts/oc_worker.py` sets **`OPENCODE_CONFIG=<harness>/.opencode/worker.json`** + `--agent mh-reviewer-oc`
  (audit) / `--agent mh-fixer` (mutating) — never `--agent plan`.
- gotcha: opencode REJECTS unknown config keys (`_comment` → "Configuration is invalid", whole file dropped).
- `reviewGlmShim` prompt fixed (no harness-root path refs; inject rule-card+checklist via `--rule-card`) +
  **auto-fallback**: a glm dimension with empty coverage → re-run on the Anthropic reviewer (never lose coverage).
- **PROVEN**: re-test (glm-5.2 audit of 2 BE files via the fixed path) → glm ran `git diff` + codegraph +
  `dotnet test` and found a real BLOCK (dead Dispensed→Stopped feature, proven by 8/10 failing tests) + 1 MED +
  3 LOW = 6KB grounded findings. **The model was never the problem; the call was.**

### Remaining — owner-gated LIVE validation
- Re-run a real `deep-review` on a module (now with the fixed glm path + auto-fallback) end-to-end.
- Run `oc_bakeoff.py run --run` → ratify with EVIDENCE → flip deep-review / batch-bugfix LAB → trusted.

## 9. Smooth-calling guide (verified — live CLI v1.17.11 + Phase 0 spike + research 2026-06-26)

### 9.1 `--format json` parsing contract (load-bearing)
- Output is **NDJSON** (one JSON object per line). Top-level `type` ∈ {`step_start`,`text`,`tool_use`,`step_finish`,`error`}.
- **Final assistant answer = `part.text` of `type=="text"` events emitted AFTER the last `type=="tool_use"` event.**
  Tool/file-read content lives ONLY in `tool_use` events; thinking is not emitted as text. So slicing after the
  last `tool_use` drops file dumps + inter-tool narration and yields just the conclusion.
- **Do NOT rely on `step_finish`** as the completion signal — a known bug drops it; use stream EOF / process exit.
- This is exactly the bug the Phase 0 spike exposed: the first `extract_text` did a greedy walk of every `text`
  key and wrote the audited file's own source into the artifact (1531 lines). `oc_worker.extract_text` now
  implements the after-last-`tool_use` rule (+ self-test).
- jq equivalent: `jq -s '[.[]|select(.type=="text" or .type=="tool_use")] as $e | (($e|map(.type=="tool_use")|rindex(true))//-1) as $i | [$e[($i+1):][]|select(.type=="text")|.part.text]|join("")'`

### 9.2 Latency / cost knobs (usage-capped seat)
- **Biggest win = `opencode serve` (port 4096, loopback) + `--attach http://127.0.0.1:4096`** per call → pays
  MCP/plugin/provider cold-boot ONCE, not per call. The cold-boot (incl. the codegraph MCP wired in
  `~/.config/opencode`) is why the spike took >2 min. `oc_worker.py` now accepts `--attach`.
- `--pure` skips external plugins (not MCP). Disable MCP per workload via a slim config `{"mcp":{"<n>":{"enabled":false}}}`.
- Session reuse `-c/--session/--fork` keeps prompt-cache warm → cheaper. `--variant max` is slowest/costliest;
  use `high` for routine, reserve `max` for the audit/adjudication call only.
- `opencode run --format json` BUFFERS stdout and flushes at the end (not streamed) — so an external timeout
  that fires mid-run captures nothing; size the timeout to the model+variant.

### 9.3 Process hygiene (avoid orphaned billing)
- `opencode run` spawns MCP/subagent children that survive a bare PID kill (known issue). Run in its own
  process group and kill the GROUP on timeout. `oc_worker.py` uses `start_new_session=True` + `os.killpg`
  (SIGTERM→SIGKILL). Shell equivalent: `timeout --signal=TERM --kill-after=15s N setsid opencode run …`.

### 9.4 Permissions
- Read-only audit: `--agent plan` (native read-only). Belt-and-suspenders: config `permission:{edit:deny,bash:deny}`.
- Mutating fix WITHOUT interactive hang and WITHOUT blanket `--dangerously-skip-permissions`: a dedicated agent
  with an explicit `permission` map (every hit tool = `allow`/`deny`, never `ask`; hard-deny `git push`,`rm *`).
  Phase 5 hardening will ship such an agent + wire `myhospital_guard.py`.
- `run --attach` against a password-protected server has open auth bugs → bind `serve` to loopback, no password.

### 9.5 opencode version
- Installed **1.17.11** = npm `latest` (binary built 2026-06-25). `opencode upgrade` → "already latest". Newer
  tags are only `snapshot-*` previews (unstable) — NOT installed.
