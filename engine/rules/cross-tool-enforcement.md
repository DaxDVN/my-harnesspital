# Cross-tool enforcement of the Forbidden Actions

> The BLOCK rules live in **`AGENTS.md` → "Forbidden Actions (ALL agents & tools)"** and apply to
> every agent **by instruction**. This doc is the *machine-enforcement* layer: how to wire the same
> rules into each tool that supports hooks. You cannot make one tool execute another tool's hooks —
> but every tool can call the **one shared script**.

## Single source of truth

`engine/hooks/myhospital_guard.py` — **canonical** (reached via the `.claude/hooks`→`engine/hooks` symlink, `.codex/hooks.json`, and the opencode plugin) — payload-tolerant (reads `tool_name`/`tool`/`name` and
`tool_input`/`params`/`arguments`/`input`), **fail-open** (any error → allow), exits **2** to block
with a `BLOCKED_RULE: …` message on stderr. Validate it any time:

```fish
python .claude/hooks/myhospital_guard.py --self-test    # 64 cases
```

Whatever the tool, the wiring just feeds it a JSON event on stdin and treats **exit 2 = block**.

The guard also enforces the **main-brain gate**: it BLOCKS any agent Write/Edit/Bash-mutate to
`main-brain/` (the gated source of truth) unless `main-brain/.promote-unlock` exists — a marker only the
**owner** creates (via the owner-invoked `/promote` skill; the guard never sees the owner's own shell).
Like every rule here it is a **tripwire, not a sandbox**: it stops autonomous/accidental edits to the SoT;
the instruction layer (`AGENTS.md` → "Self-Learning": never write `main-brain/` except via `/promote`)
covers intent. A determined caller could create the marker — that is out of this tripwire's threat model.

## Per-tool wiring

| Tool | Mechanism | Coverage | Status |
|---|---|---|---|
| **Claude Code** | `.claude/settings.json` → `PreToolUse` (`Bash\|Write\|Edit\|MultiEdit`) runs the guard. | Bash + file writes. | ✅ wired |
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

### opencode (install the plugin)
```fish
mkdir -p ~/.config/opencode/plugin
ln -sf /home/dax/Documents/arabica/roast/scripts/opencode/myhospital-guard.js ~/.config/opencode/plugin/myhospital-guard.js
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
