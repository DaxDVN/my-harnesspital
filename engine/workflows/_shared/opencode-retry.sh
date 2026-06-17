#!/usr/bin/env bash

# Shared retry helper for OpenCode/MiMo executor wrappers.
# Retry only on the specific upstream request error pattern that tends to fail
# transiently when the payload is large or the provider chokes on the request.

supertest_request_error_is_retryable() {
  local errfile="${1:-}"
  [ -n "$errfile" ] && grep -Eqi 'Request Error status 400|non-retryable' "$errfile"
}

supertest_run_with_retry() {
  local outlog="$1"
  local errlog="$2"
  local stdin_file="${3:-}"
  shift 3

  local max_attempts="${SUPERTEST_OPENCODE_RETRY_ATTEMPTS:-2}"
  local delay_secs="${SUPERTEST_OPENCODE_RETRY_DELAY_SECS:-5}"
  local run_timeout_secs="${SUPERTEST_OPENCODE_RUN_TIMEOUT_SECS:-1800}"
  local timeout_kill_after_secs="${SUPERTEST_OPENCODE_TIMEOUT_KILL_AFTER_SECS:-30}"
  case "$max_attempts" in
    ''|*[!0-9]*) max_attempts=2 ;;
  esac
  case "$delay_secs" in
    ''|*[!0-9]*) delay_secs=5 ;;
  esac
  case "$run_timeout_secs" in
    ''|*[!0-9]*) run_timeout_secs=0 ;;
  esac
  case "$timeout_kill_after_secs" in
    ''|*[!0-9]*) timeout_kill_after_secs=30 ;;
  esac
  if [ "$max_attempts" -lt 1 ]; then max_attempts=1; fi
  if [ "$delay_secs" -lt 0 ]; then delay_secs=0; fi
  if [ "$run_timeout_secs" -lt 0 ]; then run_timeout_secs=0; fi
  if [ "$timeout_kill_after_secs" -lt 0 ]; then timeout_kill_after_secs=0; fi

  local attempt=1 status=0 used_timeout=0 tmp_out tmp_err
  tmp_out="$(mktemp "${TMPDIR:-/tmp}/supertest-out.XXXXXX")"
  tmp_err="$(mktemp "${TMPDIR:-/tmp}/supertest-err.XXXXXX")"
  : >"$outlog"
  : >"$errlog"

  while :; do
    : >"$tmp_out"
    : >"$tmp_err"

    set +e
    used_timeout=0
    if [ "$run_timeout_secs" -gt 0 ] && command -v timeout >/dev/null 2>&1; then
      used_timeout=1
      if [ -n "$stdin_file" ]; then
        timeout --signal=TERM --kill-after="${timeout_kill_after_secs}s" "$run_timeout_secs" "$@" <"$stdin_file" >"$tmp_out" 2>"$tmp_err"
      else
        timeout --signal=TERM --kill-after="${timeout_kill_after_secs}s" "$run_timeout_secs" "$@" >"$tmp_out" 2>"$tmp_err"
      fi
    else
      if [ "$run_timeout_secs" -gt 0 ] && ! command -v timeout >/dev/null 2>&1; then
        printf '[retry] timeout command not found; running without stuck watchdog\n' >>"$errlog"
      fi
      if [ -n "$stdin_file" ]; then
        "$@" <"$stdin_file" >"$tmp_out" 2>"$tmp_err"
      else
        "$@" >"$tmp_out" 2>"$tmp_err"
      fi
    fi
    status=$?
    set -e

    if [ "$status" -eq 0 ]; then
      cat "$tmp_out" >"$outlog"
      if [ -s "$tmp_err" ]; then
        cat "$tmp_err" >>"$errlog"
      fi
      rm -f "$tmp_out" "$tmp_err"
      return 0
    fi

    if supertest_request_error_is_retryable "$tmp_err" && [ "$attempt" -lt "$max_attempts" ]; then
      printf '[retry] matched Request Error status 400 / non-retryable; sleeping %ss before retry %s/%s\n' \
        "$delay_secs" "$((attempt + 1))" "$max_attempts" >>"$errlog"
      cat "$tmp_err" >>"$errlog"
      sleep "$delay_secs"
      attempt=$((attempt + 1))
      continue
    fi

    if [ "$used_timeout" -eq 1 ] && [ "$status" -eq 124 ] && [ "$attempt" -lt "$max_attempts" ]; then
      printf '[retry] opencode timed out after %ss; sleeping %ss before retry %s/%s\n' \
        "$run_timeout_secs" "$delay_secs" "$((attempt + 1))" "$max_attempts" >>"$errlog"
      cat "$tmp_err" >>"$errlog"
      sleep "$delay_secs"
      attempt=$((attempt + 1))
      continue
    fi

    cat "$tmp_err" >>"$errlog"
    cat "$tmp_out" >"$outlog"
    rm -f "$tmp_out" "$tmp_err"
    return "$status"
  done
}
