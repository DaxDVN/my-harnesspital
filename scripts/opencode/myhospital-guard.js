// MyHospital cross-tool guard — opencode plugin.
//
// Makes opencode enforce the SAME BLOCK rules as Claude Code / Codex by shelling
// out to the shared guard script (.claude/hooks/myhospital_guard.py). Single
// source of truth = that Python script; this is just the opencode wiring.
// See engine/rules/cross-tool-enforcement.md.
//
// Install (copy or symlink into opencode's plugin dir):
//   mkdir -p ~/.config/opencode/plugin
//   ln -sf "$PWD/scripts/opencode/myhospital-guard.js" ~/.config/opencode/plugin/myhospital-guard.js
//
// Caveats:
// - opencode's tool.execute.before does NOT currently intercept tool calls made
//   by SUBAGENTS (known opencode limitation) — the AGENTS.md "Forbidden Actions"
//   rules still apply there by instruction.
// - This is a cooperative tripwire, not a sandbox. It fails OPEN: if anything
//   goes wrong it allows the command rather than wedging opencode.

import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";

function findGuard(startDir) {
  let dir = startDir;
  for (let i = 0; i < 10; i++) {
    const candidate = join(dir, ".claude", "hooks", "myhospital_guard.py");
    if (existsSync(candidate)) return candidate;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return process.env.MYHOSPITAL_GUARD && existsSync(process.env.MYHOSPITAL_GUARD)
    ? process.env.MYHOSPITAL_GUARD
    : null;
}

export const MyHospitalGuard = async () => {
  return {
    "tool.execute.before": async (input, output) => {
      let rule = null;
      try {
        const tool = (input && input.tool) || "";
        if (tool !== "bash") return; // only shell commands are guarded here
        const command = (output && output.args && output.args.command) || "";
        if (!command) return;
        const guard = findGuard(process.cwd());
        if (!guard) return; // fail open: guard not found
        const payload = JSON.stringify({ tool_name: "Bash", tool_input: { command } });
        const res = spawnSync("python3", [guard], { input: payload, encoding: "utf8" });
        if (res.status === 2) {
          rule = (res.stderr || "BLOCKED_RULE: blocked by MyHospital guard").trim();
        }
      } catch {
        return; // any internal error → fail open
      }
      if (rule) {
        throw new Error(
          `${rule}\n(MyHospital guard — see AGENTS.md → Forbidden Actions. ` +
          `If this is intentional, run it yourself in your terminal.)`
        );
      }
    },
  };
};
