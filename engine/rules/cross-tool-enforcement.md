# Cross-tool enforcement of the Forbidden Actions

> The BLOCK rules live in **`AGENTS.md` §4 (Hard Safety Rules)** and apply to
> every agent **by instruction**. This doc is the *machine-enforcement* layer: how to wire the same
> rules into each tool that supports hooks. You cannot make one tool execute another tool's hooks —
> but every tool can call the **one shared script**.

## Single source of truth

`engine/hooks/myhospital_guard.py` — **canonical** (reached via the `.claude/hooks`→`engine/hooks` symlink, `.codex/hooks.json`, and the opencode plugin) — payload-tolerant (reads `tool_name`/`tool`/`name` and
`tool_input`/`params`/`arguments`/`input`), **fail-open** (any error → allow), exits **2** to block
with a `BLOCKED_RULE: …` message on stderr. Validate it any time:

```fish
python .claude/hooks/myhospital_guard.py --self-test    # 88 cases
```

Whatever the tool, the wiring just feeds it a JSON event on stdin and treats **exit 2 = block**.

The guard also enforces the **main-brain gate**: it BLOCKS any agent Write/Edit/Bash-mutate to
`main-brain/` (the gated source of truth) unless `main-brain/.promote-unlock` exists — a marker only the
**owner** creates (via the owner-invoked `/promote` skill; the guard never sees the owner's own shell).
Like every rule here it is a **tripwire, not a sandbox**: it stops autonomous/accidental edits to the SoT;
the instruction layer (`AGENTS.md` §6: never write `main-brain/` except via `/promote`)
covers intent. A determined caller could create the marker — that is out of this tripwire's threat model.

## Second guard — worker-prompt lint gate (prompt QUALITY, not Forbidden Actions)

A separate PreToolUse guard, `engine/hooks/subagent_prompt_guard.py`, enforces that every prompt the orchestrator
authors for a **Claude subagent** (`Task` tool) or an **external coding tool** (`scripts/agent_exec.py` /
`scripts/oc_worker.py` → opencode/grok/agy) follows the Anthropic prompt-engineering guideline
(`docs/anthropic-guideline/`) as distilled in `engine/prompts/subagent-prompt-template.md`. It calls the
deterministic linter `scripts/subagent_prompt_lint.py` and **exits 2 (BLOCK)** on a sub-standard *mutating-worker*
prompt, naming the missing elements; read-only/search/review dispatches get a light advisory bar and are never
hard-blocked. Wired in `.claude/settings.json` → `PreToolUse` matcher `Task|Bash`. Fail-open like the guard above.
Validate: `python scripts/subagent_prompt_lint.py --self-test` and `python
engine/hooks/subagent_prompt_guard.py --self-test`. Known limit: the `Bash` path only lints top-level
`agent_exec`/`oc_worker` invocations with a readable `--prompt`/`--prompt-file`; prompts dispatched from inside the
`Workflow` runtime's `agent()` (not via `Task`/`Bash`) are out of this hook's reach (instruction layer covers those).

## Blind-PM boundary gate

The guard also enforces the **blind-PM boundary** (`AGENTS.md` §0): the main interactive session IS the
`pm-orchestrator` and must route PATHs, not content. For the **main session only** (hook payload `agent_id`
is empty), the guard BLOCKS: `Read`/`Grep`/`Glob` into source trees (`myhospital-fe`, `myhospital-be`,
`worktrees/<slug>/(fe|be)`) or worker output (`docs/audit/`), all `mcp__agent-browser__*` tools,
`git diff`/`show`/`log -p` of source (path-list forms `--stat`/`--name-only` stay allowed), AND — while a
PM run is active (`.claude/.pm-run-active` marker) — `Write`/`Edit`/`MultiEdit` on any product source
(main repos + worktrees). The owner opens a direct-work window (`AGENTS.md` §3) with a `.direct-mode`
marker at the repo root (gitignored, same pattern as `main-brain/.promote-unlock`) or `MH_DIRECT=1` to
override. Claude subagents carry a non-null `agent_id` → exempt (they read/write source as their job);
external `agent_exec` workers (grok/agy/opencode) are separate processes that never reach this hook.
Wired via the `Bash|Write|Edit|MultiEdit|Read|Grep|Glob` matcher and a `^mcp__agent-browser__.*` matcher
in `.claude/settings.json`. Validate: `--self-test`. Tripwire, not a sandbox — it stops autonomous PM
drift (the common mistake), not a determined caller.

## PM drift guard (anti-forget, PreToolUse)

`engine/hooks/orchestrator_drift_guard.py` is a PreToolUse hook that closes the long-session drift bug
(the PM forgets it is a blind coordinator and starts doing work). While `.pm-run-active` exists it
re-injects a compact blind-PM invariant on **every tool call** (not just UserPromptSubmit), so a
multi-tool autonomous turn stays refreshed. It also checks the `orchestrator_invariants` heartbeat and
warns if it is stale/missing (silent fail-open detection). It NEVER blocks — blocking is the guard's
job. Fail-open. The run marker lifecycle is owned by `scripts/pm_run.py start|end` (deterministic, not
agent-authored).

## Per-tool wiring

| Tool | Mechanism | Coverage | Status |
|---|---|---|---|
| **Claude Code** | `.claude/settings.json` → `PreToolUse` (`Bash\|Write\|Edit\|MultiEdit`) runs the guard; `UserPromptSubmit` nudges learning recall and natural-language preflight confirmation. | Bash + file writes; prompt-time preflight reminder. | ✅ wired |
| **Codex CLI** | `.codex/hooks.json` → `PreToolUse` `matcher: Bash` — hook **walks up from cwd** to find `engine/hooks/myhospital_guard.py`, works from root or `worktrees/<slug>/fe|be`. Exit 0 if not found (fail-open). | Bash calls only. Does **not** cover `apply_patch` file edits — those are instruction-only. | ✅ wired (walk-up) |
| **opencode** | Global plugin `~/.config/opencode/plugin/myhospital-guard.js` + project graphify plugin. Guard also walks up from cwd (10 levels) or uses `MYHOSPITAL_GUARD` env var. | Bash calls only. Subagent tool calls NOT intercepted (known opencode bug). | ✅ guard installed globally; graphify plugin local |
| **mimocode** | opencode fork — auto-loads `AGENTS.md` from cwd as the instruction canon (Forbidden Actions in scope). Same global guard plugin applies. | AGENTS.md instruction + guard bash calls. | by instruction + inherited guard |
| **Antigravity** | No pre-exec command hook. It reads `AGENTS.md` directly as the single instruction canon (incl. Forbidden Actions). | instruction only | by instruction (`AGENTS.md`) |
| Cursor / Grok / others | No standard pre-exec hook → read `AGENTS.md` directly (the single instruction canon). | instruction only | by instruction |

### Codex
Wired via `.codex/hooks.json` (project-level). The hook command **walks up from the cwd** (up to 12
levels) looking for `engine/hooks/myhospital_guard.py`, so it works correctly whether Codex runs
from the workspace root **or** from a `worktrees/<slug>/fe|be` subdirectory. If no guard is found,
it exits 0 (fail-open). Equivalent global form in `~/.codex/config.toml`:

```toml
[[hooks.PreToolUse]]
matcher = "^Bash$"
[[hooks.PreToolUse.hooks]]
type = "command"
command = 'python3 /ABS/PATH/engine/hooks/myhospital_guard.py'
timeout = 10
```

**Coverage honest note:** the Codex hook fires on `Bash` tool calls only. It does **not** intercept
`apply_patch` file edits. Consequently the generated-file / migration BLOCK rules are enforced by
instruction (AGENTS.md) for `apply_patch`, not by this hook. After an implementation session a quick
`git diff` + `just mh-scan` is still advised to catch any drift.

For natural-language route confirmation, use the cooperative wrapper before edits/workflows:

```bash
python scripts/codex_preflight.py "<user prompt>"
```

### opencode (install the plugin)
```fish
mkdir -p ~/.config/opencode/plugin
ln -sf "$PWD/scripts/opencode/myhospital-guard.js" ~/.config/opencode/plugin/myhospital-guard.js
```
The plugin walks up from the cwd to find `.claude/hooks/myhospital_guard.py` (or honors
`MYHOSPITAL_GUARD`), so it works from the root or a worktree.

## Known limits (be honest about these)

- **Tripwire, not a sandbox.** All layers fail-open and are bypassable by a determined caller; they
  catch the common mistakes, not a hostile actor. The user's own terminal is never affected.
- **Codex: Bash only, not `apply_patch`.** The Codex `PreToolUse` hook fires on `Bash` commands.
  `apply_patch` file edits are not intercepted; the generated-file / migration BLOCK rules apply there
  by instruction only. After a Codex implementation session: `git diff` + `just mh-scan` is advised.
- **opencode: Bash only, subagents unguarded.** `tool.execute.before` fires only for the primary
  agent's bash calls. Subagent tool calls are not intercepted (known opencode limitation). AGENTS.md
  instruction layer covers those paths — which is why the rules must live there too.
- **File edits (Claude).** Claude Code's `Write`/`Edit`/`MultiEdit` PreToolUse hooks cover file
  mutation. Other tools' file edits are instruction-only.
- **mimocode.** mimocode is an opencode fork that auto-loads `AGENTS.md` — the cross-tool instruction
  canon including Forbidden Actions. The global guard plugin applies to its bash calls (same as
  opencode). Subagent calls are unguarded (same limit as opencode).

## Sources
- Codex hooks (config.toml `[hooks]` / `hooks.json`, PreToolUse, stdin fields, exit-2 / deny): https://developers.openai.com/codex/hooks
- opencode `tool.execute.before` plugin pattern (block by throw, shell-out): https://open-code.ai/en/docs/plugins
