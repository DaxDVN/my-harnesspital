#!/usr/bin/env bash
# Runtime-plural executor for Super-Test — BOTH opencode and mimo-code can drive the workflow.
# Source this; then call:  run_executor <prompt_file> <stdout_log> <stderr_log>
#
# Selection (env, overridable):
#   SUPERTEST_RUNTIME      auto | opencode | mimo-code        (default: auto)
#   SUPERTEST_CLI_MODEL    model for opencode                 (default: xiaomi-token-plan-sgp/mimo-v2.5)
#   SUPERTEST_MIMO_CODE_BIN  mimo-code binary                 (default: mimo)
#   SUPERTEST_MIMO_CODE_CMD  full command template; {prompt_file} is substituted; else prompt on stdin
#
# auto = prefer opencode if on PATH, else mimo-code. So whichever the owner has, Super-Test runs.

SUPERTEST_EXECUTOR_LIB_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$SUPERTEST_EXECUTOR_LIB_DIR/../../_shared/opencode-retry.sh"

supertest_pick_runtime() {
  local r="${SUPERTEST_RUNTIME:-auto}"
  if [ "$r" = auto ]; then
    if command -v opencode >/dev/null 2>&1; then echo opencode; return; fi
    if command -v "${SUPERTEST_MIMO_CODE_BIN:-mimo}" >/dev/null 2>&1; then echo mimo-code; return; fi
    echo none; return
  fi
  echo "$r"
}

# Echo the resolved runtime (for logs/state); never fails.
supertest_runtime() { supertest_pick_runtime; }

run_executor() {
  local prompt_file="$1" outlog="$2" errlog="$3"
  local rt cli_model; rt="$(supertest_pick_runtime)"
  cli_model="${SUPERTEST_CLI_MODEL:-xiaomi-token-plan-sgp/mimo-v2.5}"
  case "$rt" in
    opencode)
      command -v opencode >/dev/null 2>&1 || { echo "OPENCODE_NOT_FOUND" >"$errlog"; return 127; }
      supertest_run_with_retry "$outlog" "$errlog" "" opencode run --model "$cli_model" "$(cat "$prompt_file")"
      return $? ;;
    mimo-code)
      local bin="${SUPERTEST_MIMO_CODE_BIN:-mimo}"
      if [ -n "${SUPERTEST_MIMO_CODE_CMD:-}" ]; then
        local cmd="${SUPERTEST_MIMO_CODE_CMD//\{prompt_file\}/$prompt_file}"
        supertest_run_with_retry "$outlog" "$errlog" "" bash -lc "$cmd"
        return $?
      fi
      command -v "$bin" >/dev/null 2>&1 || { echo "MIMO_CODE_NOT_FOUND ($bin) — set SUPERTEST_MIMO_CODE_BIN/_CMD" >"$errlog"; return 127; }
      supertest_run_with_retry "$outlog" "$errlog" "$prompt_file" "$bin"
      return $? ;;
    *)
      echo "NO_EXECUTOR_RUNTIME — need opencode OR mimo-code on PATH (or set SUPERTEST_RUNTIME / SUPERTEST_MIMO_CODE_CMD)" >"$errlog"
      return 127 ;;
  esac
}
