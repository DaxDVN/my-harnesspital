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
python .claude/hooks/myhospital_guard.py --self-test    # 55 cases
```

Whatever the tool, the wiring just feeds it a JSON event on stdin and treats **exit 2 = block**.

The guard also enforces the **main-brain gate**: it BLOCKS any agent Write/Edit/Bash-mutate to
`main-brain/` (the gated source of truth) unless `main-brain/.promote-unlock` exists — a marker only the
**owner** creates (via the owner-invoked `/promote` skill; the guard never sees the owner's own shell).
Like every rule here it is a **tripwire, not a sandbox**: it stops autonomous/accidental edits to the SoT;
the instruction layer (`AGENTS.md` → "Self-Learning": never write `main-brain/` except via `/promote`)
covers intent. A determined caller could create the marker — that is out of this tripwire's threat model.

## Per-tool wiring

| Tool | Mechanism | Status |
|---|---|---|
| **Claude Code** | `.claude/settings.json` → `PreToolUse` (`Bash\|Write\|Edit\|MultiEdit`) runs the guard. | ✅ wired |
| **Codex CLI** | `.codex/hooks.json` → `PreToolUse` `matcher: Bash` (same schema as Claude: `tool_name`+`tool_input.command` on stdin, exit 2 / `permissionDecision:deny` to block). | ✅ wired |
| **opencode** | TS plugin `tool.execute.before` shells out to the guard and throws on exit 2. | ✅ provided, needs install |
| **Antigravity** | No pre-exec command hook. It reads `AGENTS.md` directly as the single instruction canon (incl. Forbidden Actions). | by instruction (`AGENTS.md`) |
| Cursor / Grok / others | No standard pre-exec hook → read `AGENTS.md` directly (the single instruction canon). | by instruction |

### Codex
Already wired via `.codex/hooks.json` (project-level). It runs the guard only when the guard exists
at the cwd (`.claude/hooks/myhospital_guard.py`), so it is a no-op (fail-open) when Codex runs from a
worktree subdir. Equivalent global form in `~/.codex/config.toml`:

```toml
[[hooks.PreToolUse]]
matcher = "^Bash$"
[[hooks.PreToolUse.hooks]]
type = "command"
command = 'python3 /ABS/PATH/.claude/hooks/myhospital_guard.py'
timeout = 10
```

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
- **Subagents leak.** opencode's `tool.execute.before` does not intercept subagent tool calls (a known
  opencode bug); Codex's PreToolUse only catches "simple" shell calls. The AGENTS.md instruction layer
  is the only thing that covers those paths — which is why the rules must live there too.
- **File edits.** The guard's generated-file/migration blocks rely on Claude's `Write`/`Edit` shapes.
  Codex `apply_patch` and opencode edits are covered by instruction, not by this hook.

## Sources
- Codex hooks (config.toml `[hooks]` / `hooks.json`, PreToolUse, stdin fields, exit-2 / deny): https://developers.openai.com/codex/hooks
- opencode `tool.execute.before` plugin pattern (block by throw, shell-out): https://open-code.ai/en/docs/plugins
