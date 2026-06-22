# second-brain/ — the learning buffer (SCRATCH NOTEBOOKS)

Where the harness **learns**. Provisional knowledge accumulates here — "remember this", "pay attention to
this", ideas, observations. **May be right or wrong.** Detailed and allowed to grow; it is NOT loaded into
context by default, so size here is fine (unlike `main-brain/`, which must stay lean).

**Cross-tool + in-repo:** every agent (Claude, Codex, opencode) reads/appends here — unlike
`~/.claude/.../memory/` (Claude-only, session-scoped, ephemeral). Knowledge that must **survive and be
shared across tools and fresh sessions** lives HERE, versioned in the repo.

## Grouped View

Use `grouped/` first for management/review/recall. It compresses related raw notes into generalized rule gates,
for example freshness-before-diagnosis and canonical-reuse gates.

Raw `YYYY-MM-DD-*.md` notes that have already been compressed live in `_archive/`. Open them only when a grouped
rule needs verification or promotion detail. This keeps second-brain manageable without losing provenance.

## Rules
- **OPEN.** Any agent may APPEND a new entry freely (no gate) when the owner says "nhớ cái này / để ý cái
  này", or when a durable cross-cutting fact is discovered worth keeping. One file per learning.
- **Lifecycle.** An entry lives until either (1) the owner says delete it, or (2) it is **promoted**.
- **Promotion (owner-gated, via `/promote`).** The owner reviews and runs `/promote`, which either:
  - **distills** the entry into `main-brain/knowledge.md` (a lean durable truth/lesson), or
  - **graduates** it into a new reusable **skill** in `engine/skills/<slug>/SKILL.md` (a repeatable procedure; `.claude/skills` is a symlink → `engine/skills`, the canonical home).
  On promotion the source entry is removed and a tombstone line is left in `INDEX.md`.

## Files
- `INDEX.md` — the **applicability MAP**: a table `slug · scope · applies-when (tasks·keywords) · conf · target`.
  Read THIS to know what's here + WHEN each note may apply; promoted entries become tombstones. Regenerate from
  entry frontmatter with `python scripts/learning_recall.py --rebuild-map` (canonical — no drift).
- `grouped/*.md` — compressed provisional memory, grouped by related rule families. Read this before archive.
- `_archive/YYYY-MM-DD-<slug>.md` — raw evidence already compressed into grouped files; open only for provenance.
- `YYYY-MM-DD-<slug>.md` — new, uncompressed learning: frontmatter (`title`, `date`, `status: provisional`, `source`,
  `scope`, `confidence`, `owner_confirmed`, `proposed_target`, `tags`, **`applies_tasks`**, **`applies_globs`**,
  **`applies_keywords`**, `expires`) + **What** / **Evidence** / **Why** / **How To Apply** / **Boundaries** /
  **Promotion Recommendation**. Create via `scripts/learning_capture.py` (enforces enums; recurrence appends
  "Seen again" to the existing provisional entry, any date). Periodically compress these into `grouped/`, then
  move the raw source to `_archive/`.

## Recall — how a note gets USED (not just written)
second-brain is on-demand (NOT auto-loaded — saves tokens). To stop notes rotting unread, each note declares
`applies_when`, and you QUERY the map instead of reading the whole buffer:
- `python scripts/learning_recall.py --context "<your task>"` → only the notes whose scope/tasks/keywords fit.
- `--all` prints the map; `--rebuild-map` regenerates it from frontmatter.
- The `learning_trigger` UserPromptSubmit hook NUDGES recall when a work prompt arrives **and** notes exist.

A match MAY apply (or not, or several) — apply if it fits, but **verify** (provisional). Never read the full
second-brain when the map + a query suffice. Promote proven notes with `/promote`.
