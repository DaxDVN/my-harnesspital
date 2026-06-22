# Quality Gates

Always-on quality gates for fix, implement, review, and test work. These gates are small artifacts/checks,
not long prompts. Use them to make senior-review behavior repeatable.

## Gate Matrix

| Trigger | Required gate | Why |
|---|---|---|
| New helper/component/service/pattern, or visible FE UI work | Reuse evidence | Prevent duplicate or hand-rolled patterns |
| BLOCK/HIGH bug, non-trivial fix, unclear RCA, or cross-file change | Fix plan | Prevent symptom patches and scope creep |
| API/DTO/schema/shared hook/adapter/service/permission/business/clinical/billing change | Regression map | Prevent breaking existing callers |
| Weak-model deep-review finding BLOCK/HIGH | Strong adjudication | Cheap models find candidates; strong models decide |
| Browser/E2E bug candidate | Robust triage | Prevent false positives from bad test setup |
| Repeated bug class | Scanner promotion check | Move repeatable quality into deterministic checks |
| Any completed work | Definition of done validation | Report real validation, not vibes |

## Reuse Evidence Gate

Before creating a new FE/BE pattern, record:

```text
searched:
- <existing exemplar file:line> — <what it proves>
- <existing exemplar file:line> — <what it proves>
decision: reuse | extend | create-new
why: <one short reason>
```

No evidence means no new pattern. For visible FE UI, D3/D10 must include the semantic reuse matrix from
`engine/workflows/deep-review/checklist.md`.

## Fix Plan Gate

For BLOCK/HIGH or non-trivial fixes, record:

```text
root_cause:
allowed_files:
forbidden_files:
reuse_evidence:
regression_map:
risk:
validation:
rollback:
```

The fix may be small, but the plan must name the boundary. Do not fix findings with
`review_status=NEEDS_ADJUDICATION`; adjudicate first.

## Regression Map Gate

When touching shared/API/DTO/schema/security/permission/business/clinical/billing/state-machine code:

```text
changed_surface:
callers_checked:
- <file:line or route> — <safe because | needs test>
not_checked:
- <item> — <why acceptable or blocked>
validation:
```

Use CodeGraph first for source callers.

## Definition Of Done By Task Class

| Task class | Minimum validation |
|---|---|
| T0 label/copy/local null guard | targeted grep/repro; explain why build not needed |
| FE visible/form/table | `tsc -p tsconfig.app.json` or equivalent, scanner if available, targeted smoke |
| BE service/API | `dotnet build`, targeted test or API/request repro |
| FE+BE contract | BE build -> DTO/client regen -> FE typecheck |
| Review/audit | findings schema + coverage ledger + adjudication for BLOCK/HIGH |
| robust-test | per-bug folders + triage + retest gaps + review-ready bundle |

Full BE test suite failures must be attributed by error signature. If live SQL is absent, use the targeted
InMemory-runnable subset and record SQL-dependent tests as skipped with reason.

## Scanner Promotion

Every real bug/finding must record:

```text
bug_class: <stable-key | none>
scanner_candidate: yes | no
```

Use `bug_class: none` only for true one-off defects and state why in the artifact. Stable keys should describe
the reusable failure shape, not the current file name, for example `missing-hospital-scope-filter` rather than
`patient-service-bug`.

When the same bug class appears twice, decide:

```text
bug_class:
scanner_possible: yes | no
candidate_rule:
where: guard | mh_scan | eslint/ast-grep | review-checklist
reason:
```

Prefer deterministic scanner/guard over another prose rule when feasible.
Run `python scripts/harness_scanner_promotion.py scan` to find repeated `bug_class:` markers in review,
robust-test, and second-brain artifacts.

## Main-Brain Budget

`main-brain/knowledge.md` is mandatory standing memory. Keep it lean:

```text
target: <=1500 words
hard review threshold: >2000 words
```

If an entry needs detail, link to `engine/`, `docs/`, or `second-brain/` instead of copying detail.

## Fabricated Authority Check

If code or a fix plan cites a decision ID (`DL-*`, `DL-FIX-*`, etc.), verify the ID exists in `docs/` or
`specs/`. A business/clinical/billing/state-machine change citing a non-existent decision ID is BLOCK.
