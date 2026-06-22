# Main-Brain Promotion Candidates

This report is advisory. Agents must not write `main-brain/` directly.

## Additive NOT NULL DEFAULT column consumed by a new query needs a backfill SQL
- path: second-brain/2026-06-17-additive-not-null-default-column-consumed-by-a-new-query-nee.md
- confidence: high
- proposed_target: deep-review/checklist
- scope: backend

## BE full test suite needs live SQL — validate batches via the InMemory my-area subset
- path: second-brain/2026-06-17-be-full-test-suite-needs-live-sql-validate-batches-via-the-i.md
- confidence: high
- proposed_target: engine/rules/backend
- scope: backend

## Clone real server data to local dev DBs
- path: second-brain/2026-06-17-clone-real-server-data-to-local-dev-dbs.md
- confidence: high
- proposed_target: engine/skills (a `clone-server-data` recipe) or main-brain
- scope: backend / dev-data

## Fabricated DL-FIX decision IDs in code = invented authority
- path: second-brain/2026-06-17-fabricated-dl-fix-decision-ids-in-code-invented-authority.md
- confidence: high
- proposed_target: deep-review/checklist
- scope: workspace

## FE custom onError must route through handleApiError, not raw error.message — or forced-i18n breaks
- path: second-brain/2026-06-17-fe-custom-onerror-must-route-through-handleapierror-not-raw.md
- confidence: high
- proposed_target: engine/rules/frontend
- scope: frontend

## Fix một LIST bug: gộp theo PHASE (BE hết → build/regen/test 1 lượt → FE hết → typecheck 1 lượt), không chạy nhiều chu kỳ nhỏ
- path: second-brain/2026-06-17-fix-một-list-bug-gộp-theo-phase-be-hết-buildregentest-1-lượt.md
- confidence: high
- proposed_target: main-brain
- scope: workspace

## Guard blocks all Migrations/*.cs edits — additive data-backfill needs owner bypass
- path: second-brain/2026-06-17-guard-blocks-all-migrationscs-edits-additive-data-backfill-n.md
- confidence: high
- proposed_target: engine/rules/backend
- scope: backend

## In-memory batch dedup must match the table's real unique index, else silent data loss
- path: second-brain/2026-06-17-in-memory-batch-dedup-must-match-the-tables-real-unique-inde.md
- confidence: high
- proposed_target: deep-review/checklist
- scope: backend

## Multi-round fix/review harness: batch reporting + per-phase validation + trust-but-spot-check existing audits to cut cost without losing recall
- path: second-brain/2026-06-17-multi-round-fixreview-harness-batch-reporting-per-phase-vali.md
- confidence: medium
- proposed_target: main-brain
- scope: workspace

## ServiceStack: re-declaring an inherited DTO property with 'new' silently drops it when the service reads via the BASE type
- path: second-brain/2026-06-17-servicestack-re-declaring-an-inherited-dto-property-with-new.md
- confidence: high
- proposed_target: engine/rules/backend
- scope: backend

## Shift-on-duty enforcement binds at the service-order path, not at inpatient admission-receive
- path: second-brain/2026-06-17-shift-on-duty-enforcement-binds-at-the-service-order-path-no.md
- confidence: high
- proposed_target: engine/rules/backend
- scope: backend

## Worktree slot DBs are sync-from-main, NOT EF-migration-managed — apply schema via direct DDL, not 'ef database update'
- path: second-brain/2026-06-17-worktree-slot-dbs-are-sync-from-main-not-ef-migration-manage.md
- confidence: high
- proposed_target: engine/rules/backend
- scope: backend

## clinical-ui-design v2: calm != bland; generic là failure mode; variant theo METAPHOR không theo effort
- path: second-brain/2026-06-18-clinical-ui-design-v2-calm-bland-generic-là-failure-mode-var.md
- confidence: high
- proposed_target: skill
- scope: workflow:clinical-ui-design

## Disabled React Query (enabled:false) keeps isPending=true → guard loading UI on the gate, not isPending
- path: second-brain/2026-06-18-disabled-react-query-enabledfalse-keeps-ispendingtrue-guard.md
- confidence: high
- proposed_target: engine/rules/frontend
- scope: frontend

## FE UI quality: harness/skill quyết định chứ không phải model -> đừng đổi committer
- path: second-brain/2026-06-18-fe-ui-quality-harnessskill-quyết-định-chứ-không-phải-model-đ.md
- confidence: medium
- proposed_target: main-brain
- scope: workspace

## Seed table command skips non-empty tables and gitignore can hide seed CSVs
- path: second-brain/2026-06-18-seed-table-command-skips-non-empty-tables-and-gitignore-can.md
- confidence: high
- proposed_target: engine/rules/backend
- scope: backend

## Slot DB may miss an entire feature schema, not just the latest migration
- path: second-brain/2026-06-18-slot-db-may-miss-an-entire-feature-schema-not-just-the-lates.md
- confidence: high
- proposed_target: engine/rules/backend
- scope: workspace

## Validate FE fixes with vite/esbuild, not bare 'npx tsc --noEmit'
- path: second-brain/2026-06-18-validate-fe-fixes-with-viteesbuild-not-bare-npx-tsc-noemit.md
- confidence: high
- proposed_target: engine/rules/frontend
- scope: frontend

## Audit migration-drift claim: check ALL migrations, not just baseline
- path: second-brain/2026-06-19-audit-migration-drift-claim-check-all-migrations-not-just-ba.md
- confidence: high
- proposed_target: deep-review/checklist
- scope: backend

## audit migration findings must check later migrations and snapshot
- path: second-brain/2026-06-19-audit-migration-findings-must-check-later-migrations-and-sna.md
- confidence: high
- proposed_target: deep-review/checklist
- scope: backend

## Audit 'parallelize sequential EF queries with Task.WhenAll' is UNSAFE on a shared DbContext
- path: second-brain/2026-06-19-audit-parallelize-sequential-ef-queries-with-taskwhenall-is.md
- confidence: high
- proposed_target: deep-review/checklist
- scope: backend

## Bed reservation (Đặt lịch) form follows mockup (lean), not doc-text §5.2
- path: second-brain/2026-06-19-bed-reservation-đặt-lịch-form-follows-mockup-lean-not-doc-te.md
- confidence: high
- proposed_target: spec-decision
- scope: module:bed-management

## Calendar-day business logic must bucket in hospital-local TZ, not raw UTC .Date
- path: second-brain/2026-06-19-calendar-day-business-logic-must-bucket-in-hospital-local-tz.md
- confidence: high
- proposed_target: engine/rules/backend
- scope: backend

## clinical-ui-design v3: ground vào data hệ thống thật + gu là của owner + đừng lead bằng table
- path: second-brain/2026-06-19-clinical-ui-design-v3-ground-vào-data-hệ-thống-thật-gu-là-củ.md
- confidence: high
- proposed_target: skill
- scope: workflow:clinical-ui-design

## clinical-ui-design v4: constraint != quality; thêm kỹ thuật legible-density + ép đa dạng theo JOB + fresh-eyes critique
- path: second-brain/2026-06-19-clinical-ui-design-v4-constraint-quality-thêm-kỹ-thuật-legib.md
- confidence: high
- proposed_target: skill
- scope: workflow:clinical-ui-design

## clinical-ui-design v5: genre FIRST (sơ đồ=MAP); variant=design-approach cùng 1 màn KHÔNG phải feature bổ sung; schematic>=geographic; overview!=list
- path: second-brain/2026-06-19-clinical-ui-design-v5-genre-first-sơ-đồmap-variantdesign-app.md
- confidence: high
- proposed_target: skill
- scope: workflow:clinical-ui-design

## Controlled draft-input must guard its value-sync useEffect with isFocused, or RHF round-trip clobbers the value mid-type
- path: second-brain/2026-06-19-controlled-draft-input-must-guard-its-value-sync-useeffect-w.md
- confidence: high
- proposed_target: engine/rules/frontend.md
- scope: frontend

## deactivate-by-absence over collapsed multi-category payload drops untouched categories
- path: second-brain/2026-06-19-deactivate-by-absence-over-collapsed-multi-category-payload.md
- confidence: high
- proposed_target: deep-review/checklist
- scope: backend

## FE bug fix needs BE up + dtos:update first; migrations may run freely if data restorable via make migrate-data
- path: second-brain/2026-06-19-fe-bug-fix-needs-be-up-dtosupdate-first-migrations-may-run-f.md
- confidence: high
- proposed_target: main-brain
- scope: workspace

## FE has no facility/cơ-sở-y-tế master data
- path: second-brain/2026-06-19-fe-has-no-facilitycơ-sở-y-tế-master-data.md
- confidence: high
- proposed_target: engine/rules/frontend
- scope: frontend

## FE label fix via t() fallback is a NO-OP when the key exists in vi.json — must edit vi.json
- path: second-brain/2026-06-19-fe-label-fix-via-t-fallback-is-a-no-op-when-the-key-exists-i.md
- confidence: high
- proposed_target: engine/rules/frontend.md
- scope: frontend

## Fix-flow auto-decides blocking business questions and writes a decision-log named after the audit file
- path: second-brain/2026-06-19-fix-flow-auto-decides-blocking-business-questions-and-writes.md
- confidence: high
- proposed_target: main-brain
- scope: workspace

## Data-backfill migrations are guard-blocked in worktrees → need owner bypass
- path: second-brain/2026-06-19-guard-blocks-data-backfill-migration-edits-needs-owner-bypass.md
- confidence: high
- proposed_target: engine/rules (source-discovery / backend) or guard refinement
- scope: workspace

## IValidatableObject.Validate must pass an object (not a string/collection) to NestedValidation
- path: second-brain/2026-06-19-ivalidatableobjectvalidate-must-pass-an-object-not-a-stringc.md
- confidence: high
- proposed_target: deep-review/checklist
- scope: backend

## Language policy: agent-facing=English, owner-facing=Vietnamese, MD deliverables=2 bản (EN canonical + VN clone)
- path: second-brain/2026-06-19-language-policy-agent-facingenglish-owner-facingvietnamese-m.md
- confidence: high
- proposed_target: main-brain
- scope: workspace

## Mass-parallel subagent spawn botches tool-call across runtimes → prompts cần fallback inline
- path: second-brain/2026-06-19-mass-parallel-subagent-spawn-botches-tool-call-across-runtim.md
- confidence: high
- proposed_target: engine/rules/backend
- scope: workspace

## Naming prefixes follow resource owner, not module folder
- path: second-brain/2026-06-19-naming-prefixes-follow-resource-owner-not-module-folder.md
- confidence: high
- proposed_target: engine/rules/frontend
- scope: workspace

## new BaseService write paths recurringly bypass tenant-scope helper + skip audit stamps
- path: second-brain/2026-06-19-new-baseservice-write-paths-recurringly-bypass-tenant-scope.md
- confidence: high
- proposed_target: deep-review/checklist
- scope: backend

## Page-mode form sheets need modal outside block and one-shot hydration
- path: second-brain/2026-06-19-page-mode-form-sheets-need-modal-outside-block-and-one-shot.md
- confidence: high
- proposed_target: engine/rules/frontend.md
- scope: frontend

## PatientHeaderDto carries precomputed *Display fields — reuse them for patient headers
- path: second-brain/2026-06-19-patientheaderdto-carries-precomputed-display-fields-prefer-over-recompute.md
- confidence: high
- proposed_target: frontend-rules
- scope: frontend

## Restart slot backend before regenerating FE DTOs after BE contract changes
- path: second-brain/2026-06-19-restart-slot-backend-before-regenerating-fe-dtos-after-be-co.md
- confidence: high
- proposed_target: engine/rules/frontend.md
- scope: workspace

## Reusable audit+fix system prompts live in engine/prompts/
- path: second-brain/2026-06-19-reusable-auditfix-system-prompts-live-in-engineprompts.md
- confidence: high
- proposed_target: engine/rules/backend
- scope: workspace

## ServiceStack: never re-declare base-payload fields with 'new' when the service reads the base type
- path: second-brain/2026-06-19-servicestack-never-re-declare-base-payload-fields-with-new-w.md
- confidence: high
- proposed_target: engine/rules/backend
- scope: backend

## Slot-DB EF migration-history drift: apply additive migration surgically, not via database update
- path: second-brain/2026-06-19-slot-db-ef-migration-history-drift-apply-additive-migration.md
- confidence: high
- proposed_target: engine/rules/backend.md
- scope: backend

## SQL seed scripts must not use T-SQL variables across GO batches
- path: second-brain/2026-06-19-sql-seed-scripts-must-not-use-t-sql-variables-across-go-batc.md
- confidence: high
- proposed_target: engine/rules/backend
- scope: backend

## UI deep audit must require semantic reuse matrix
- path: second-brain/2026-06-19-ui-deep-audit-must-verify-live-widgets-and-layout-patterns.md
- confidence: high
- proposed_target: deep-review/checklist
- scope: frontend

## Diagnosing a capture-proof synchronous UI freeze: localStorage-gated block bisect (profiler/trace are useless)
- path: second-brain/2026-06-20-capture-proof-sync-freeze-bisect-with-localstorage-gated-blocks.md
- confidence: high
- proposed_target: engine/rules/frontend.md
- scope: frontend

## Directory.Build.props local SDK workaround must stay out of git
- path: second-brain/2026-06-20-directorybuildprops-local-sdk-workaround-must-stay-out-of-gi.md
- confidence: high
- proposed_target: main-brain
- scope: backend

## E2E browser tester subagents should not capture screenshots by default
- path: second-brain/2026-06-20-e2e-browser-tester-subagents-should-not-capture-screenshots.md
- confidence: high
- proposed_target: skill
- scope: workflow:super-test

## E2E browser testers produce false-positive bugs from form/auth-state gaps
- path: second-brain/2026-06-20-e2e-browser-testers-produce-false-positive-bugs-from-formaut.md
- confidence: high
- proposed_target: deep-review/checklist
- scope: workflow:super-test

## New worktree DB setup defaults to make migrate-data
- path: second-brain/2026-06-20-new-worktree-db-setup-defaults-to-make-migrate-data.md
- confidence: high
- proposed_target: main-brain
- scope: workflow:worktree

## Worktree slot recovery after a host crash: start SQL + Redis BEFORE BE; 'resolve master instance' timeout = Redis down
- path: second-brain/2026-06-20-slot-infra-recovery-after-crash-sql-redis-be-and-resolve-master-instance.md
- confidence: high
- proposed_target: docs/guides/worktree-zellij-manual or engine/rules
- scope: infra

## staging-test-bug-investigation-uses-slot3-code
- path: second-brain/2026-06-20-staging-test-bug-investigation-uses-slot3-code.md
- confidence: high
- proposed_target: engine/rules/frontend.md
- scope: workflow:staging-test

## TanStack Table autoReset* + a new-ref-every-render `data` array → infinite re-render loop (page 'slowing down')
- path: second-brain/2026-06-20-tanstack-table-autoreset-plus-unstable-data-ref-infinite-rerender-loop.md
- confidence: high
- proposed_target: engine/rules/frontend.md
- scope: frontend

## Worktree node_modules drift when master adds FE deps
- path: second-brain/2026-06-21-worktree-node-modules-drift-when-master-adds-fe-deps.md
- confidence: high
- proposed_target: engine/rules/frontend
- scope: frontend
