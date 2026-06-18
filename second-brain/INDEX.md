# second-brain index — the APPLICABILITY MAP

Read THIS file to know what second-brain holds + WHEN each note may apply. Do **NOT** read the full
second-brain. To pull only the notes that fit your task:
`python scripts/learning_recall.py --context "<your task>"`. A match MAY apply (or not, or several) —
apply if it fits, but **verify** (second-brain is provisional). Promote a proven note with `/promote`.

| slug | scope | applies when (tasks · keywords) | conf | → target |
|---|---|---|---|---|
| [clone-real-server-data-to-local-dev-dbs](2026-06-17-clone-real-server-data-to-local-dev-dbs.md) | backend / dev-data | any · — | high | engine/skills (a `clone-server-data` recipe) or main-brain |
| [fix-một-list-bug-gộp-theo-phase-be-hết-buildregentest-1-lượt](2026-06-17-fix-một-list-bug-gộp-theo-phase-be-hết-buildregentest-1-lượt.md) | workspace | fix,implement,review · batch,build once,test once,phase,orchestration | high | main-brain |
| [mimo-executor-retries-provider-400](2026-06-17-mimo-executor-retries-provider-400.md) | workflow:super-test | test,implement,review · opencode,mimo,retry,400,non-retryable | medium | skill |
| [multi-round-fixreview-harness-batch-reporting-per-phase-vali](2026-06-17-multi-round-fixreview-harness-batch-reporting-per-phase-vali.md) | workspace | fix,review,implement · harness,orchestration,cost,batch,multi-round | medium | main-brain |
| [shift-on-duty-enforcement-binds-at-the-service-order-path-no](2026-06-17-shift-on-duty-enforcement-binds-at-the-service-order-path-no.md) | backend | fix,implement · shift,shiftassignment,useshiftassignment,reception,admission | high | engine/rules/backend |
| [worktree-slot-dbs-are-sync-from-main-not-ef-migration-manage](2026-06-17-worktree-slot-dbs-are-sync-from-main-not-ef-migration-manage.md) | backend | fix,implement · migration,ef database update,schema,column,slot db | high | engine/rules/backend |
| [in-memory-batch-dedup-must-match-the-tables-real-unique-inde](2026-06-17-in-memory-batch-dedup-must-match-the-tables-real-unique-inde.md) | backend | review,implement,fix · dedup,HashSet,batch,unique,index,skip,SkippedCodes,continue | high | deep-review/checklist |
| [fe-custom-onerror-must-route-through-handleapierror-not-raw](2026-06-17-fe-custom-onerror-must-route-through-handleapierror-not-raw.md) | frontend | review,implement,fix · onError,showErrorToast,error.message,handleApiError,FORCE_I18N_CODES,i18n,toast | high | engine/rules/frontend |
| [fabricated-dl-fix-decision-ids-in-code-invented-authority](2026-06-17-fabricated-dl-fix-decision-ids-in-code-invented-authority.md) | workspace | review,fix,implement · DL-FIX,decision-log,engine,NFR-11,calc | high | deep-review/checklist |
| [additive-not-null-default-column-consumed-by-a-new-query-nee](2026-06-17-additive-not-null-default-column-consumed-by-a-new-query-nee.md) | backend | review,fix,implement · migration,defaultValue,NOT NULL,backfill,IsClinicalOccupancy | high | deep-review/checklist |
| [servicestack-re-declaring-an-inherited-dto-property-with-new](2026-06-17-servicestack-re-declaring-an-inherited-dto-property-with-new.md) | backend | fix,implement,review · servicestack,DTO,new,shadow,base,property,confirm flag,deserialize | high | engine/rules/backend |
| [guard-blocks-all-migrationscs-edits-additive-data-backfill-n](2026-06-17-guard-blocks-all-migrationscs-edits-additive-data-backfill-n.md) | backend | fix,implement · migration,backfill,data-migration,guard,bypass,migrationBuilder.Sql | high | engine/rules/backend |
| [be-full-test-suite-needs-live-sql-validate-batches-via-the-i](2026-06-17-be-full-test-suite-needs-live-sql-validate-batches-via-the-i.md) | backend | test,fix,review · dotnet test,full-suite,SQL Server,OneTimeSetUp,InMemory,proc_CodeGenerator,baseline-failures | high | engine/rules/backend |
| [seed-table-command-skips-non-empty-tables-and-gitignore-can](2026-06-18-seed-table-command-skips-non-empty-tables-and-gitignore-can.md) | backend | fix,implement,test · seed,csv,slot,db,table-specific,non-empty,gitignore | high | engine/rules/backend |
| [validate-fe-fixes-with-viteesbuild-not-bare-npx-tsc-noemit](2026-06-18-validate-fe-fixes-with-viteesbuild-not-bare-npx-tsc-noemit.md) | frontend | fix,implement,test · tsc,vite,esbuild,typecheck,syntax,frontend | high | engine/rules/frontend |
| [frontend-design-skill-bias-marketing-cần-clinical-variant-ch](2026-06-18-frontend-design-skill-bias-marketing-cần-clinical-variant-ch.md) | frontend | implement,scaffold,design · ui,design,shadcn,skill,frontend | medium | skill |
| [fe-ui-quality-harnessskill-quyết-định-chứ-không-phải-model-đ](2026-06-18-fe-ui-quality-harnessskill-quyết-định-chứ-không-phải-model-đ.md) | workspace | implement,design,review,any · model,opus,gpt,gemini,harness,ui,committer | medium | main-brain |
