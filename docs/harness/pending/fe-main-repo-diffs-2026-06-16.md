# FE main-repo diffs — apply yourself (myhospital-fe is edit-forbidden)

> From the FE-harness build (2026-06-16). These touch files inside `myhospital-fe/` (ESLint config,
> stale docs, `package.json`, committed backups) which agents must NOT edit directly (AGENTS.md hard BLOCK).
> Apply directly with your approval, or via an FE worktree + PR. Source findings: `[AUDIT] =
> velvet/notes/myhospital-fe-convention-audit-2026-06-15.md`. Everything else in the harness (mh_scan FE
> bridge, ast-grep pack, guard advisory, skills, checklist, rules-doc) is already built under `roast/`.

---

## 1. ESLint pack — `myhospital-fe/eslint.config.js`  (FE-V1, V2, banned libs)

The deterministic floor that runs **in worktrees** (`npx eslint <file>`). Merge into the `rules: {}` block
of the existing flat config (after `...reactHooks.configs.recommended.rules,`):

```js
      // --- MyHospital convention floor (FE audit) ---
      'no-restricted-imports': ['error', {
        paths: [
          { name: 'axios', message: 'Use the module adapter (extends GeneratedApiClient), not axios. FE-V2.' },
          { name: '@/lib/dtos/dtos', message: "Dead path — import from '@/lib/dtos/generated-dtos'. FE-V1." },
        ],
        patterns: [
          { group: ['zustand', 'jotai', 'redux', 'react-redux', '@reduxjs/*', 'mobx', 'mobx-*',
                    'react-icons', 'react-icons/*', 'react-modal'],
            message: 'Banned lib — approved stack only (no new global-state/icon/modal libs).' },
        ],
      }],
      'no-restricted-syntax': ['warn',
        { selector: "CallExpression[callee.name='fetch']",
          message: 'Raw fetch() in UI — route through a module adapter + useMasterData. Verify vs legacy exceptions ([AUDIT] §6). FE-V2.' },
      ],
```

Notes:
- `fetch` is **warn** (legit exceptions exist: blob viewers, query-provider, retail-log — [AUDIT] §6). Scoped
  `npx eslint <changed>` only lints touched files, so legacy isn't re-flagged unless edited; justify with an
  `// eslint-disable-next-line no-restricted-syntax` + reason when intentional.
- `useForm`-without-`zodResolver` (FE-V4) is not expressible as a stable lint rule → caught by `mh_scan`
  advisory + checklist D3 + review.
- `react-router` vs `react-router-dom` (FE-V14) is intentionally NOT restricted (≈60 legit `react-router`
  imports; an error would be pure noise). Treat as a slow manual normalization, not a gate.

---

## 2. `npm run create:page` is broken (FE-V9) — `myhospital-fe/package.json`

`scripts/create-page.js` does not exist; `create-module.js` builds from a deleted `demo` template ([AUDIT]
§3.D). The agentic replacement is **`/mh-scaffold`** (FE templates). Minimal fix — remove the dead script line:

```diff
   "create:module": "node scripts/create-module.js",
-  "create:page": "node scripts/create-page.js",
   "dtos:update": "node scripts/update-dtos.js",
```

(Optionally also drop `create:module` and point the team to `/mh-scaffold`; or restore a real
`scripts/create-page.js` if you still want an npm path.)

---

## 3. Stale-doc banners (FE-V10) — prepend to two files

Both docs misdescribe the live system ([AUDIT] V10: bearer-vs-cookie, Infinity-vs-staleTime:0, reducer-vs-RQ,
demo/samples, "no tests"). Prepend this banner so no one trusts them blindly:

`myhospital-fe/ARCHITECTURE-OVERVIEW.md` and `myhospital-fe/BEST-PRACTICES-NEW-PAGE.md`:

```md
> ⚠️ **PARTIALLY STALE (audited 2026-06-15).** This document predates the current app and is wrong in
> places (auth is cookie `ss-id` not bearer; React Query default is `staleTime:0`/`gcTime:5m` not Infinity;
> the live data pattern is RQ-hooks-via-adapter + `useMasterData`, not the Context+reducer shown here;
> `demo`/`samples` modules and `/demo`,`/samples` routes no longer exist; Playwright e2e DOES exist).
> **Live canon:** `harness/rules/frontend-rules-conventions-patterns.md` + the audit at
> `velvet/notes/myhospital-fe-convention-audit-2026-06-15.md`. Trust live code over this file.
```

---

## 4. `components.json` `rsc: true` (FE-V15) — `myhospital-fe/components.json`

This is a Vite SPA, not Next/RSC — the flag can make the shadcn CLI regenerate components with wrong RSC
assumptions:

```diff
-  "rsc": true,
+  "rsc": false,
```

---

## 5. Committed backup files (FE-V12) — 14 `.v2.bak` in `retail/`

```fish
# from an FE worktree (or with approval), then commit the removal:
git -C myhospital-fe rm (fd -t f '\.v2\.bak$' myhospital-fe/src/modules/retail)
```

(14 files under `src/modules/retail/` — pharmacy-pos v2 backups. `mh_scan`/DoD also flags committed `.bak`.)

---

## Apply order
1 (ESLint) is the highest value — it makes the FE floor run in worktrees alongside `mh_scan`. 2–5 are cleanups.
After applying 1, confirm: `cd myhospital-fe && npx eslint src/modules/retail/adapters/retail-customer-adapter.ts`
should report the `fetch` warning; an `import … from '@/lib/dtos/dtos'` should error.
