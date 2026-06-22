---
title: "Diagnosing a capture-proof synchronous UI freeze: localStorage-gated block bisect (profiler/trace are useless)"
date: "2026-06-20"
status: provisional
source: harness-session
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/frontend.md
tags: [frontend, debugging, freeze, infinite-loop, agent-browser, radix, recharts, bisect]
applies_tasks: [fix, test, e2e]
applies_globs: [worktrees/*/fe/src/**/*.tsx]
applies_keywords: [freeze, hang, infinite loop, unresponsive, CDP timeout, popover, multiselect, recharts, profiler, trace]
---

# What

A SILENT synchronous hard-freeze (a real interaction pegs the renderer; CDP commands time out ~2min; console empty; page-errors empty) is NOT a React "Maximum update depth" loop (that logs to console.error and throws fast). It is a synchronous infinite loop in userland/library code. Chrome `profiler_start/stop` AND `trace_start/stop` BOTH fail to flush under such a peg ("No profiling/tracing in progress") — and even `reload` can't recover (must close --all + reopen). So **do not spend time on capture-based RCA**; use a code bisect.

# How To Apply (the bisect that worked)

1. Add a temporary `localStorage`-gated switch to the suspect container so you can skip sub-blocks without re-editing each time:
   `const dbg = typeof window!=='undefined' ? (localStorage.getItem('vsdbg')||'') : '';` then wrap each block in `{dbg !== 'noX' && (<Block/>)}`.
2. Per test (each freeze hard-locks the session, so a fresh browser session + re-login is needed each time): open → `eval localStorage.setItem('vsdbg','noX')` BEFORE the component mounts (set it on the login page or the parent route; same origin so it persists) → navigate by clicking → trigger the interaction with a SHORT click timeout (8-10s) so a freeze returns fast instead of hanging 2min.
3. Tag the trigger element via `eval` (`el.setAttribute('data-dbg','x')`) then click `[data-dbg="x"]` — avoids huge snapshots.
4. Result interpretation: freeze GONE with block removed → that block is the culprit; freeze REMAINS → innocent, move to the next.
5. REVERT all debug gates when done (mixed-tab files: use a Python regex replace, Edit's exact-match fails on tabs).

# Evidence

Vital-signs Sinh hiệu tab freeze (2026-06-20): bisect proved the freeze is NOT the new inline form NOR recharts `<ResponsiveContainer>` — it is the Radix overlay open path. **CONFIRMED root cause: React 19.2 + radix-ui 1.4.3 overlay primitives (`Popover`/`Select`/`ComboBox`→InputAutoSuggest→Popover, `DateTimePicker`→Popover, `MultiSelect`→Popover) trigger a silent synchronous infinite re-render/hang on this page on any React state update.** Fix = replace the Radix controls with native + chip equivalents: MultiSelect→horizontal chip `<button>` row; RadioGroup→chip buttons; DateTimePicker→`<input type="datetime-local">`; ComboBox→chip buttons or native `<select>`. The chart's `MultiSelect` (BUG-002) was pre-existing (never interaction-tested); the always-mounted Block-2 inline-edit form's Radix controls (BUG-004) were newly added and also froze — same React19+Radix cause. See `docs/testing/2026-06-20/vital-signs-e2e-bug-catalog.round-1.md`.

NOTE (broader risk): this React19+Radix freeze is NOT vital-signs-specific in principle — other pages using Radix overlays could hit it. Only the vital-signs components were de-Radix'd; a systemic fix (radix/react dep bump, or a guarded overlay wrapper) is a separate owner decision.

# CORRECTION (2026-06-21) — the "Radix overlay = freeze" causation was OVERGENERALIZED

Empirically re-tested on the live Sinh hiệu tab after the re-render loop was fixed: the **Radix `Popover`-based `DatePicker` opens and works fine** — calendar grid renders (35 day cells), only ~10 React commits to open, page responsive, date picks + saves succeed, no freeze. So the blanket claim above (that `Popover`/`DateTimePicker`/Radix overlays freeze this page on any state update) is **wrong**. The actual freeze root cause was the **TanStack-Table `autoReset*` + unstable `getUserDisplayName` infinite re-render loop** (see `2026-06-20-tanstack-table-autoreset-plus-unstable-data-ref-infinite-rerender-loop.md`). Once that loop was fixed, Radix overlays are fine.

Consequence: the de-Radix'ing of the datetime field to `<input type="datetime-local">` was an **unnecessary over-correction** and was itself a convention violation (the system uses `DatePicker` + `TimeInput24`). Reverted to the canonical `DatePicker` (date) + `TimeInput24` (time) on 2026-06-21. The Radix-freeze rationale should NOT be used to justify skipping shared Radix components (e.g. `KeyboardShortcutsHelp`'s Popover) without first re-testing live — the freeze premise no longer holds. The bisect TECHNIQUE in this note is still valid; only the Radix-causation conclusion is retracted. (`Select`/`ComboBox`/`MultiSelect` were not individually re-tested — verify live before assuming either way.)

# Why It Matters

Stops you burning a whole session on profiler/trace that physically cannot capture a full sync peg. The localStorage-gated bisect is deterministic and converges in a few rounds. Pragmatic fix for a capture-proof Radix-overlay freeze: swap the offending overlay control (e.g. MultiSelect) for a non-Popover equivalent (toggle chips) rather than chasing the library internal.
