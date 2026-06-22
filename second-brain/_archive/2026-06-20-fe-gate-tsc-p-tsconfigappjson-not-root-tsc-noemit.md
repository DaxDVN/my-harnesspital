---
title: "FE gate: tsc -p tsconfig.app.json, not root tsc --noEmit"
date: "2026-06-20"
status: provisional
source: user-correction
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: reject
tags: [fe, tsc, verification, tsconfig.app.json, reference-error]
applies_tasks: [fe, bug-fix, verification]
applies_globs: [**/*.tsx, **/*.ts]
applies_keywords: [tsc, verify, build, ReferenceError, is not defined, tsconfig]
expires: ""
---

# What

Root 'tsc --noEmit' uses the ROOT tsconfig which does NOT type-check src/** app files. The real FE build gate is 'npx tsc -p tsconfig.app.json --noEmit'. TS2304 'Cannot find name X' is the exact compile signature of a runtime ReferenceError (undefined identifier). tsconfig.app.json is broadly red repo-wide from pre-existing debt (bwip-js, embla, form-builder, nurse-handover, examination-schema ZodCoercedNumber) because Vite/esbuild transpiles without type-checking — so the gate is 'no NEW errors in changed files', diffed against HEAD, not 'zero project errors'.

# Evidence

- Owner hit runtime 'Uncaught ReferenceError: commitFieldChange is not defined' in vital-signs form; my 'npx tsc --noEmit' (root tsconfig) reported 0 and I falsely closed F-001 as stale. tsc -p tsconfig.app.json caught TS2304 at vital-signs-form.tsx:611,656 plus 5 more real errors in changed files.

# Why It Matters

Vite dev/build uses esbuild (transpile only, no type-check), so type errors and undefined-identifier ReferenceErrors reach the browser. The wrong gate gives false-green and ships crashes the owner then finds.

# How To Apply

_See # What above._

# Boundaries

FE worktrees (myhospital-fe + worktrees/<slug>/fe). Filter app-tsc output to changed files; ignore pre-existing errors that also exist on HEAD.

# Promotion Recommendation

Promote to: reject
Reason: (fill in before promoting)
