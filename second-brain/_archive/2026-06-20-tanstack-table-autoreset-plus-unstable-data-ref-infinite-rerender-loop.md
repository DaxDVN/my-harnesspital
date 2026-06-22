---
title: "TanStack Table autoReset* + a new-ref-every-render `data` array → infinite re-render loop (page 'slowing down')"
date: "2026-06-20"
status: provisional
source: harness-rca
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/frontend.md
tags: [frontend, performance, rerender, infinite-loop, tanstack-table, react-table, usecallback, memo]
applies_tasks: [fix, review, implement, test]
applies_globs: [worktrees/*/fe/src/**/*.tsx, myhospital-fe/src/**/*.tsx]
applies_keywords: [useReactTable, autoResetExpanded, getUserDisplayName, useUserTitleMap, slowing down, re-render, rerender, performance, commits, getExpandedRowModel]
---

# What

`useReactTable({ data, ... })` with TanStack Table v8: `autoResetExpanded` / `autoResetPageIndex` / `autoResetAll`
default to **true**. They reset table UI state whenever the `data` **reference** changes. If `data` is a memo that
gets a NEW reference on (nearly) every render, the auto-reset calls `onExpandedChange(setExpanded)` → re-render →
new `data` ref → reset → re-render → **infinite loop (~350 React commits/sec)**. Symptom: Firefox "this page is
slowing down", general jank — but **NO React error** (it's an async effect-driven loop, not render-phase setState,
so React's "Maximum update depth" guard never trips). Per-interaction latency looks fine, so naive testers report
"perf PASS".

The usual reason `data` is unstable: the data-deriving `useMemo` lists a function in its deps that is **a fresh
reference every render** — e.g. `getUserDisplayName` from `useUserTitleMap` (a plain function, not `useCallback`).
That made the history `groupedData` memo recompute a new array each render.

# How to detect (code-reading MISSES this — Codex couldn't find it)

Instrument at runtime via the React DevTools hook (works in headless Chrome via agent-browser `eval`):
```js
const h = window.__REACT_DEVTOOLS_GLOBAL_HOOK__; let n=0, oc=h.onCommitFiberRoot;
h.onCommitFiberRoot=function(){n++;return oc.apply(this,arguments)};
setTimeout(()=>{ h.onCommitFiberRoot=oc; console.log('commits/Ns', n); }, 3000);
```
Idle on a healthy screen ≈ 0 commits in 3s; a loop ≈ hundreds–thousands. Then bisect which subtree (localStorage-
gated block removal + re-measure) and which `<input>` mutates (MutationObserver) to localize. CPU profiler/trace
may capture this (it's slow-not-frozen), unlike a hard freeze.

# Fix

1. On the table: `autoResetExpanded: false, autoResetPageIndex: false, autoResetAll: false` (also correct UX — don't
   reset expansion when the data merely refreshes).
2. Root cause: stabilize the function(s) the data-memo depends on — wrap `getUserTitle`/`getUserDisplayName` (and
   similar hook-returned helpers) in `useCallback`. This stops the data memo from producing a new array every render
   and prevents this class app-wide.

# Evidence

vital-signs Sinh hiệu tab (2026-06-20): `vital-signs-history-inpatient.tsx` `useReactTable` had default autoResets +
`groupedData` dep on unstable `getUserDisplayName` (`use-user-title-map.ts`, plain fn). Measured **1052 commits/3s**;
after the fix **0 commits/3s**, hover of 60 cells = 1 commit. Related: [[capture-proof-sync-freeze-bisect-with-localstorage-gated-blocks]].

# Why It Matters

This is a hidden, severe perf bug: no error, naive interaction tests pass, but the page continuously burns CPU.
Any `useReactTable` whose `data`/`columns`/`state` objects are rebuilt each render is at risk — audit for it.
