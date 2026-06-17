# Harness Self-Operation Audit — AGENTIC LAYER (independent, adversarial)

> Date: 2026-06-17 · Auditor: independent adversarial pass · READ-ONLY (ran read-only probes only).
> Question: does the agentic layer (autonomous loops + routing + self-learning) actually SELF-OPERATE,
> or is it human-steered / aspirational? **SDLC build chain (ui-spec/technical-design/task-slicing/
> incremental-impl) is OUT OF SCOPE** (owner steers it). Verdict per component: REAL / PARTIAL / SCAFFOLD.
>
> Method: ran `node --check`, the progressive-test smoke suite, the guard self-test + 9 payload probes,
> `codegraph impact/callers`, and a dangling-reference scan. Spot-checked the bug-trace BE `file:line`
> citations against the live `myhospital-be` checkout. "Exists as a .md" was NOT accepted as "self-operates".

## Verdict table

| # | Component | Verdict | One-line basis (evidence) |
|---|---|---|---|
| 1 | deep-review (partition D1–D10) | **REAL (orchestration) / UNPROVEN (end-to-end)** | `workflow.js` parses (`node --check` exit 0); pipeline fan-out + adversarial verify + bounded completeness loop are coherent and call a real `mh-reviewer` agent type. No evidence of a real multi-agent run; the only proof is structural. |
| 2 | progressive-test runtime | **REAL (state machine, PROVEN by smoke) / UNPROVEN (real executor)** | `tests/run-smoke-tests` → `SMOKE TEST PASS` (envelope validate, routing NEEDS_RCA/TRIVIAL, state RETEST_PASSED→DONE). But smoke uses `tests/mock-opencode`. The real path needs opencode + mimo-v2.5 + agent-browser + dev server — none verified present. |
| 3 | bug-fix + bug-trace playbook | **REAL (coherent, runnable, playbook now carried)** | `mh-rca.md` embeds the condensed L1–L6 playbook + 3 governing facts + verdict set, and links the full doc. BE citation spot-check below: **both flagged claims HOLD**, one wording correction. |
| 4 | impact-analysis (wraps CodeGraph) | **REAL (CodeGraph step) / UNPROVEN (risk-framing)** | `codegraph impact BaseService` → 2577 affected symbols; `codegraph callers GetAllByTenant` → 16 real callers w/ file:line. BE index live (1,400 files / 31,958 nodes / 76,012 edges). Skill self-admits framing quality unproven. |
| 5 | agent-shortcuts routing | **REAL** | Every referenced skill (11/11), justfile recipe (6/6), and script (6/6) EXISTS. Zero dangling aliases. |
| 6 | self-learning (main-brain/second-brain/promote) | **REAL (gate) / EMPTY (content)** | Guard BLOCKS a main-brain Write (probe → exit 2) AND blocks `touch main-brain/.promote-unlock` via Bash (self-test). Loop is coherent. But main-brain/knowledge.md is empty and second-brain has only README+INDEX — never exercised. |
| 7 | cross-tool ("add a tool = add pointers once") | **PARTIAL** | Claude: full symlinks `.claude/{skills,agents,hooks,workflows}`→`engine/`. Codex: re-wires the SAME guard (Bash only). opencode: ONLY a graphify plugin — NO guard, NO engine/skill pointers. The claim is real for Claude, half for Codex, ~unwired for opencode. |

---

## Per-component evidence

### 1. deep-review — REAL orchestration, UNPROVEN end-to-end
- `node --check engine/workflows/deep-review/workflow.js` → exit 0 (parses).
- `workflow.js` is a coherent deterministic engine: `pipeline(DIMENSIONS, audit, verify)` fan-out, adversarial REFUTE of every BLOCK/HIGH (`CRITIC_SCHEMA`, default refuted=true), dedup by `(location|severity|title)`, bounded completeness loop (`k<2`, ≤16 cells/wave, never re-audits whole scope), Vietnamese verdict (`CHƯA ĐÓNG`/`ĐÓNG`). Spawns `agentType: 'mh-reviewer'` at per-dimension tiers (D1 opus, D7/D10 haiku, rest sonnet).
- `engine/agents/mh-reviewer.md` exists; the `mh-reviewer` agent type is registered (in the session's agent list). `SKILL.md` Steps 0–6 mirror `workflow.js` and describe the parallel Agent-tool fan-out.
- **Gap:** the partition design is sound on paper, but there is **no artifact of a real end-to-end review run** in this audit (no fresh `docs/audit/*` from a workflow.js run). The power-mode needs the Workflow tool (explicit opt-in). The `SKILL.md`-path (parallel Agent calls) is what would actually run, and that depends on the orchestrator actually fanning out — coherent but unproven here.

### 2. progressive-test — state machine PROVEN (mock), real executor UNPROVEN
- `engine/workflows/progressive-test/.agentflow/lib/agentflow.py` compiles (`py_compile` OK). All 17 `bin/` scripts have correct shebangs + exec bits.
- `tests/run-smoke-tests` → **`SMOKE TEST PASS`** (exit 0). It exercises: bug-packet write + schema-validate, envelope validate, `ROUTE: NEEDS_RCA`, rca-plan validate, approved-plan (`DIRECT_PATCH_BY_CLAUDE`), implementation-report + retest-report validate, `STATE RETEST_PASSED -> DONE`, final summary, AND a second `ROUTE: TRIVIAL (missing-import-or-undefined-symbol)` fast-path. So the **envelope + state-machine runtime is genuinely REAL and self-validating.**
- **Executor wiring is REAL, not stubbed:** `bin/test-with-opencode` calls `opencode run --model "$CLI_MODEL"` for real; enforces `executor.model == mimo-v2.5` (MVP guard); has `require_agent_browser_or_fail` that hard-FAILs `AGENT_BROWSER_NOT_AVAILABLE` unless an agent-browser/playwright/puppeteer MCP or binary is detected. The mock is a **test-only fork** gated behind `AGENTFLOW_MOCK_OPENCODE=1`.
- **Gap (what's UNPROVEN):** the *real* loop has never been shown to run here. It requires (a) `opencode` CLI, (b) `mimo-v2.5` via `mimo-token-plan`, (c) a real agent-browser capability, (d) a running FE dev server + the smoke login (bvtest3/lynkhanh9822@gmail.com/12.[s7HXZQ;NfAoF). None verified present. So: state machine + envelopes + routing = PROVEN; real browser-driven test→RCA→implement→retest = UNPROVEN.

### 3. bug-fix — REAL; the playbook is now carried by mh-rca
- `engine/agents/mh-rca.md` (modified 23:52, newest agent) now embeds a **condensed bug-trace playbook**: the 3 governing facts (200≠success; master-data/permissions from IndexedDB; two caches), the ordered L1→L6 layer walk, the "top traps" list, and the 4-verdict set (DIRECT_PATCH / CODEX_REQUIRED / MORE_EVIDENCE / HUMAN_DECISION). It links the full doc `docs/harness/plans/bug-trace-workflow-research-2026-06-16.md`. So **yes — mh-rca carries the playbook now**, not just a "investigate the source" stub.
- `engine/skills/bug-fix/SKILL.md` + `engine/workflows/bug-fix/README.md` exist; the playbook explicitly plugs into bug-fix step 2 (REPRODUCE) + step 3 (RCA) without new orchestration. Coherent and runnable (it reuses `mh-rca` + `/mh-fix` + `progressive-test`).

#### BE-citation spot-check (parent flagged these as unverified)

**Claim (b) — `BaseService.GetAllByTenant<T>()` throws when tenant is 0 — VERIFIED, line-exact.**
`myhospital-be/MyHospital.ServiceInterface/BaseService.cs`:
- `:153` `protected IQueryable<T> GetAllByTenant<T>()`
- `:157` `if (type.GetProperty("TenantId") != null)` (only for tenant-scoped entities)
- `:159` `if (EffectiveTenantId == 0)`
- `:161-163` `throw new InvalidOperationException(..."requires authenticated session with CurrentTenantId > 0..."`)
The doc's `:159-163` citation is exact. The parallel `GetAllByTenantAndHospital<T>()` (`:259`) check at `:267` / throw at `:269` also holds. **HOLDS** (minor: the doc says `CurrentTenantId`, the code field is `EffectiveTenantId`, and the throw is gated on the entity having a `TenantId` property — the triage conclusion "missing-tenant → 500 not empty list" is correct).

**Claim (a) — "BE returns HTTP 200 even on business error; success = body `Code === "SUCCESS"`" — VERIFIED with ONE wording correction.**
- FE side EXACT: `myhospital-fe/src/lib/server/servicestack-client.ts:15-18` docstring states verbatim "All API responses return HTTP 200 with structure `{ Code, Message, Data }`; `Code = "SUCCESS"` means success". `checkResponse()` at `:97`; `codeStr !== ErrorCodes.Success` throw at `:106`/`:146`; `new ApiError(...)` at `:124`/`:164`; `wrapInfrastructureError` body-`Code`-first logic at `:279-343`. FE citations accurate.
- BE side CONFIRMS the envelope `{ Code, Message, Data }`: `StandardResponsePlugin.cs` success → `Code = ErrorCodes.Success` (`:122`), business error via `HttpError` → `Code = errorCode, Data = null` (`:82-90`).
- **CORRECTION:** the bald claim "the BE returns **HTTP 200** even for business errors" is **stale for the HttpError/BusinessException path**. This plugin version explicitly **overrides the status from `httpError.StatusCode`** (`:81`, applied at `:133`), and the in-code comment at `:78-80` documents fixing exactly the old "FE saw 200 + Data:null → crash" bug. So `BusinessException.NotFound` now returns **HTTP 404**, `Conflict`→409, etc. The "always 200" premise only reliably holds for the older `IHasResponseStatus`-with-`ErrorCode` path (`:93-104`), where `statusCode` is left as-is. **Net:** the FE defensive rule "read body `Code`, don't trust the status" is still 100% correct triage advice; but the *reason* ("because the BE always sends 200") is no longer accurate — the BE now sends real 4xx/5xx for BusinessException. The playbook should soften Fact A to "a 200 can still be a business error (read `Code`); and a 4xx/5xx is the BusinessException path — both surface via `Code !== SUCCESS`."

**Spot-check verdict: both BE behaviors HOLD in the code; (b) is line-exact; (a)'s mechanism description is partly stale (status is now overridden for BusinessException), but the triage rule it motivates remains correct.**

### 4. impact-analysis — REAL CodeGraph wrap
- CodeGraph CLI 1.0.1 installed; **both repos indexed** (the MCP "workspace not indexed" message refers to repo ROOT only; `.codegraph/` exists in `myhospital-be/` and `myhospital-fe/`). `codegraph status` (BE): 1,400 files / 31,958 nodes / 76,012 edges / node:sqlite WAL.
- `codegraph impact BaseService` → "2577 affected symbols" with file:line. `codegraph callers GetAllByTenant` → "Callers (16)" with file:line. The dependency engine the skill wraps is **real and returns real data**.
- `impact-analysis/SKILL.md` step 2 calls exactly `codegraph impact <symbol>` + `codegraph affected <path>`, writes an envelope on the shared schema, emits a 4-value verdict.
- **Gap (skill's own words):** "the CodeGraph step is REAL; the risk-framing quality is UNPROVEN — first real run = owner gate." Honest. The layering of BE/FE/API/business/test dimensions onto the CodeGraph output is human-judgment-shaped and unproven.

### 5. agent-shortcuts routing — REAL (no dangling aliases)
- Skills: mh-scaffold, mh-implement, mh-fix, impact-analysis, bug-fix, technical-design, task-slicing, incremental-impl, mh-review, promote, agentflow → **all 11 present** (`engine/skills/<x>/SKILL.md`).
- Recipes: doctor, mh-scan, convention-truth, codegraph-status, codegraph-sync-main, harness-backup → **all 6 present** in `justfile`.
- Scripts: worktree.py, harness_doctor.py, mh_scan, `_shared/gate-check.py`, `_shared/validate-envelope.py`, `_shared/envelope.schema.json` → **all present**.
- The USER-DRIVEN guardrails (review/promote/worktree explicit-only) are stated in both the shortcuts file and AGENTS.md. No alias points at a missing target.

### 6. self-learning — REAL gate, EMPTY content
- **Gate is REAL (probed):**
  - Write to `main-brain/knowledge.md` with no `.promote-unlock` → `BLOCKED_RULE: main-brain-protected` exit 2.
  - `git commit` → blocked; `git -C <path> commit` → blocked; `rm -rf` → blocked; `npm install <pkg>` → blocked; generated DTO Write → blocked. Benign `ls` → allowed.
  - Guard `--self-test`: **55/55 pass** (22 block, 23 allow). The self-test even asserts `touch main-brain/.promote-unlock` via Bash is BLOCKED — so an agent cannot self-unlock; only the owner's raw `! touch` (which the hook never sees) can. **The owner-gate is genuinely enforced, not ceremonial.**
- `/promote` skill is coherent: confirm intent → draft → owner types `! touch main-brain/.promote-unlock` → apply → re-lock (`rm`) → tombstone in `second-brain/INDEX.md` → `harness_doctor.py`.
- **But the loop has never run:** `main-brain/knowledge.md` is empty ("nothing promoted yet"); `second-brain/` holds only `README.md` + `INDEX.md` (no actual learning entries). The machinery is real and safe; it is simply **unexercised** — usable, not yet used.

### 7. cross-tool claim — PARTIAL
- **Claude — REAL:** `.claude/{agents,hooks,skills,workflows}` are genuine symlinks → `../engine/...`. Guard wired in `.claude/settings.json` (PreToolUse: Bash|Write|Edit|MultiEdit) + SessionStart graphify check.
- **Codex — PARTIAL:** `.codex/hooks.json` re-invokes the SAME guard (`python3 .claude/hooks/myhospital_guard.py`) — so the BLOCK rules ARE cross-tool for Codex. BUT: (a) matcher is **Bash only** (no Write/Edit → the generated-file / main-brain *edit* blocks and the FE/BE forbidden-pattern blocks do NOT fire for Codex edits; only the Bash-side main-brain-writer block does), and (b) `.codex` has **no skill/engine pointers at all** (only `config.toml` = model). Codex reaching engine's skills/rules is by-instruction (AGENTS.md), not wired.
- **opencode — ~UNWIRED:** `.opencode/opencode.json` registers ONLY `plugins/graphify.js`. **No guard, no engine rules glob, no skill pointers.** The harness's own table claims "opencode: `instructions` glob" — that is **not present** in `opencode.json`. So for opencode the cross-tool guarantees are essentially aspirational beyond graphify.
- **Net:** "engine/ is canonical, add a tool = add pointers once" is TRUE for Claude, HALF-true for Codex (guard only, Bash only), and NOT yet realized for opencode. The guard being payload-tolerant (`_parse` accepts `tool`/`name`/`params`/`arguments`) is real and supports the claim — but the *pointers* only exist for Claude.

---

## Top gaps (ranked)

1. **Nothing autonomous has a proven full run.** Every loop is PROVEN only at the structural/mock level: deep-review (no real multi-agent run), progressive-test (mock-opencode only), impact-analysis (CodeGraph real, framing unproven). The agentic layer is **build-complete + smoke-validated, not field-proven.** It will self-operate only when an orchestrator actually fans out / a real executor is wired — both currently human-initiated.

2. **progressive-test real executor is unverified end-to-end.** The wiring to `opencode run --model mimo-v2.5` + agent-browser is real code, but requires opencode + mimo + agent-browser + a live dev server, none confirmed in this environment. Until one real round runs, the browser-driven half is UNPROVEN. (The orchestration/envelope half IS proven.)

3. **bug-trace Fact A is partly stale.** The BE no longer "always returns HTTP 200" for BusinessException — `StandardResponsePlugin.cs:81/:133` overrides the status to `httpError.StatusCode` (404/409/403/…). The triage rule ("read body `Code`") is still correct, but the stated mechanism is outdated and should be corrected so an RCA agent doesn't expect a 200 on every business error. (Claim (b) is line-exact and fine.)

4. **cross-tool parity is Claude-only in practice.** Codex gets the guard for Bash only (no Write/Edit interception, no skill pointers); opencode gets only graphify. The "add a tool = add pointers once" claim and the AGENTS.md "opencode: instructions glob" line overstate the current wiring. Either wire the pointers or downgrade the claim.

5. **self-learning is real but cold.** main-brain empty, second-brain has no entries. The gate works; the loop has never carried a single learning. Risk: it stays ceremony unless the owner actually drops `second-brain/` notes and runs `/promote`. (Low-effort to exercise; high-value to prove.)

## What is genuinely solid (no flattery, just true)
- The **guard** is real, payload-tolerant, fail-open, and 55/55 self-tested; the owner-gate on main-brain cannot be self-unlocked by an agent. This is the strongest, most-proven piece.
- The **progressive-test envelope + state machine** passes its own smoke suite end-to-end (mock executor) — a real, working artifact, not a doc.
- **CodeGraph** is live in both repos and returns real impact/caller data — impact-analysis and mh-review's blast-radius step have a real engine under them.
- **Routing has zero dangling references** — every alias resolves to a present skill/recipe/script.
- **mh-rca now carries the bug-trace playbook**, and the BE facts it cites are real in the code.
