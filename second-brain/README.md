# second-brain/ — the learning buffer (SCRATCH NOTEBOOKS)

Where the harness **learns**. Provisional knowledge accumulates here — "remember this", "pay attention to
this", ideas, observations. **May be right or wrong.** Detailed and allowed to grow; it is NOT loaded into
context by default, so size here is fine (unlike `main-brain/`, which must stay lean).

**Cross-tool + in-repo:** every agent (Claude, Codex, opencode) reads/appends here — unlike
`~/.claude/.../memory/` (Claude-only, session-scoped, ephemeral). Knowledge that must **survive and be
shared across tools and fresh sessions** lives HERE, versioned in the repo.

## Rules
- **OPEN.** Any agent may APPEND a new entry freely (no gate) when the owner says "nhớ cái này / để ý cái
  này", or when a durable cross-cutting fact is discovered worth keeping. One file per learning.
- **Lifecycle.** An entry lives until either (1) the owner says delete it, or (2) it is **promoted**.
- **Promotion (owner-gated, via `/promote`).** The owner reviews and runs `/promote`, which either:
  - **distills** the entry into `main-brain/knowledge.md` (a lean durable truth/lesson), or
  - **graduates** it into a new reusable **skill** in `.claude/skills/<x>` (a repeatable procedure).
  On promotion the source entry is removed and a tombstone line is left in `INDEX.md`.

## Files
- `INDEX.md` — one line per entry (`slug — hook`); promoted/graduated entries become tombstones.
- `<slug>.md` — one learning: frontmatter (`title`, `date`, `status: provisional`, `source`, `tags`) +
  **What** / **Why** / **How to apply** / `[[links]]`.
