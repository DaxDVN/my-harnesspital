# mh-implement / mh-fix — Definition-of-Done gate (B4 / F3)

Run before self-review-diff. All commands run **inside the worktree** (`worktrees/<slug>/fe|be`) — dev/build/test/regen are explicitly ALLOWED by the guard hook. One-shot runner:

```fish
python scripts/mh_scan --root worktrees/<slug>/fe --scope (git -C worktrees/<slug>/fe diff --name-only <base>) --format summary
```

`scripts/mh_scan` is the unified FE+BE deterministic floor (ast-grep FE rules + rg BE scanners); it emits findings-schema JSON (`--format json`) and exits non-zero on a HIGH/BLOCK with `--fail-on high`. Run it plus the type/lint steps below:

## FE gate
1. **Types** — `npx tsc --noEmit` from the worktree fe. Catches dead/renamed imports (audit **V1**: `@/lib/dtos/dtos` does not exist — real path `@/lib/dtos/generated-dtos`) and contract drift. BLOCK on error.
2. **Lint (scoped)** — `npx eslint <changed files> --no-fix`. **Never `npm run lint`** (applies global fixes — `frontend-rules…md`). After the ESLint pack is applied (see `docs/harness/pending/fe-main-repo-diffs-2026-06-16.md`) this catches banned imports (axios/zustand/…/`@/lib/dtos/dtos`), raw `fetch(` in `.tsx`, `useForm` without resolver (audit V4).
3. **Structural lint** — `python scripts/mh_scan --root worktrees/<slug>/fe --scope <changed> --format summary` (wraps the ast-grep pack in `scripts/sgconfig/`). Flags dead `@/lib/dtos/dtos` import (**FE-V1**, HIGH), raw `fetch()` in UI (**FE-V2/V5**), master-data name-compare like `=== 'kinh'` (**FE-V3**), `serviceStackClient.*` in a component. WARN hits are advisory — verify against audit §6 legit exceptions (blob fetch, dynamic-form, sub-form FormProvider) before "fixing".
4. **No committed backups** — `fd -t f '\.(bak|orig|v2\.bak)$' <changed dir>` must be empty (audit **V12**: 14 `.v2.bak` in retail).
5. **Contract** — if a generated file would change: `npm run dtos:update && npm run client:generate`, then re-run step 1. Never hand-edit generated files.
6. **Browser** — for visible UI, run the dev server and verify (smoke login: customer `bvtest3` / `lynkhanh9822@gmail.com` / `12.[s7HXZQ;NfAoF`).

## BE gate (if BE touched)
- `dotnet build` clean. EF: change the model + `dotnet ef migrations add` (never hand-edit a generated migration). Conventions per `backend.md` (BaseService, no transaction/lock, no N+1, tenant scope, soft-delete/audit auto).

## Pass criteria
0 type errors · 0 ESLint errors on changed files · ast-grep warnings each either fixed or justified (audit §6 exception, with an `eslint-disable`/comment rationale — do not widen rules) · no committed `.bak` · generated artifacts regenerated not hand-edited. Then proceed to self-review-diff (B5/F4).
