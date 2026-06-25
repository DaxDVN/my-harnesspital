# second-brain index — the APPLICABILITY MAP

Read THIS file to know what second-brain holds + WHEN each note may apply. Do **NOT** read the full
second-brain. To pull only the notes that fit your task:
`python scripts/learning_recall.py --context "<your task>"`. A match MAY apply (or not, or several) —
apply if it fits, but **verify** (second-brain is provisional). Promote a proven note with `/promote`.

## Grouped management view

Prefer `grouped/` when reviewing or promoting batches of related notes:

- [`grouped/README.md`](grouped/README.md) — group policy and file list.
- [`grouped/INDEX.md`](grouped/INDEX.md) — coverage map from all raw notes to grouped files.
- [`grouped/01-freshness-before-diagnosis.md`](grouped/01-freshness-before-diagnosis.md) — generated/runtime/env freshness before diagnosis.
- [`grouped/02-canonical-reuse-gate.md`](grouped/02-canonical-reuse-gate.md) — reuse canonical project patterns before new code.
- [`grouped/03-correct-boundary-data-integrity.md`](grouped/03-correct-boundary-data-integrity.md) — correct boundary and real data contracts.
- [`grouped/04-evidence-verification-gate.md`](grouped/04-evidence-verification-gate.md) — proof required before verified/safe claims.
- [`grouped/05-automation-orchestration-triage.md`](grouped/05-automation-orchestration-triage.md) — automation signal, batching, owner gates.
- [`grouped/06-design-spec-decision-gate.md`](grouped/06-design-spec-decision-gate.md) — clinical design genre and module spec decisions.

Rows below are grouped notes or new uncompressed live notes. Archived raw notes live in `_archive/` and are
opened only as provenance for a grouped rule.

| slug | scope | applies when (tasks · keywords) | conf | → target |
|---|---|---|---|---|
| [01-freshness-before-diagnosis](grouped/01-freshness-before-diagnosis.md) | workspace | fix,implement,review,test,worktree-creation,db-setup · freshness,stale,dto,client,generated | high | engine/rules/quality-gates + worktree setup docs + FE/BE freshness guards |
| [02-canonical-reuse-gate](grouped/02-canonical-reuse-gate.md) | workspace | fix,implement,review,test,design,scaffold · reuse,convention,canonical,hand-roll,component | high | engine/rules/ponytail + frontend/backend reuse checklist + scanners |
| [03-correct-boundary-data-integrity](grouped/03-correct-boundary-data-integrity.md) | workspace | fix,implement,review,test,scaffold · boundary,correctness,data,migration,backfill | high | engine/rules/backend + engine/rules/frontend + deep-review/checklist + scanners |
| [04-evidence-verification-gate](grouped/04-evidence-verification-gate.md) | workspace | fix,implement,review,test,design,scaffold · verified,evidence,proof,validation,test | high | engine/rules/quality-gates + deep-review/checklist + validation gates |
| [05-automation-orchestration-triage](grouped/05-automation-orchestration-triage.md) | workspace | fix,implement,review,test,any · automation,workflow,subagent,browser,e2e | high | engine/workflows/robust-test + workflow docs + prompt docs |
| [06-design-spec-decision-gate](grouped/06-design-spec-decision-gate.md) | workspace | design,implement,review,scaffold,fix · design,clinical-ui,his,ui,mockup | high | skill:clinical-ui-design + specs/<module>/06-decision-log.md |
| [rename-task-scope](_archive/2026-06-22-rename-task-scope-only-rename-what-task-says.md) | workspace | fix,implement,rename,refactor · rename,refactor,class,entity,property,table,file | high | engine/rules/ponytail |
| [revert-git-diff-head-first](_archive/2026-06-22-revert-read-git-diff-head-all-files-first.md) | workspace | fix,revert,implement · revert,undo,back,prescription,lead | high | engine/rules/quality-gates |
| [no-audit-claim-without-manual-crosscheck](_archive/2026-06-22-no-audit-claim-without-manual-crosscheck.md) | workspace | fix,implement,review,rename,audit · audit,all,every,matches,correct,consistent,done,complete | high | engine/rules/quality-gates + 04-evidence-verification-gate |
| [test-data-done-rule](test-data-done-rule.md) | workspace | fix,implement,test,browser,e2e · test-data,seed,done,complete,data,view | high | seed data trước khi báo done; append-only; ưu tiên UI/luồng trước SQL |
