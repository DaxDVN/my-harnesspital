# Backend Migrations, Schema, Seed, And Backfill

- Agent must not manually edit generated EF migrations unless the owner explicitly authorizes that exact task.
- Additive schema changes consumed by new code need data/backfill/default safety before the new query path depends on them.
- Worktree slot DBs can drift from main; verify migration history/schema before diagnosing source bugs.
- Seed scripts must respect SQL batch boundaries and existing non-empty table semantics.
- Restart the slot backend before regenerating FE DTO/client after BE contract changes.
- If migration/data mutation is needed, use the approved worktree-slot workflow and report exact commands.
