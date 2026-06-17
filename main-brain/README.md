# main-brain/ — the harness's source of truth (the BRAIN)

The concise, authoritative knowledge the system carries everywhere. Like a person's brain: it holds
**distilled lessons + key durable truths + a sense of what exists and when to use it** — and it **refers
down to `engine/` (rules/protocols) and `engine/skills/` (procedures; `.claude/skills` is only a symlink/pointer into it)** for exact detail. It does NOT
hold all the detail (that is what `engine/`, the skills, and `second-brain/` are for).

## Rules
- **GATED — owner-only.** Agents may NOT write here. The guard hook (`.claude/hooks/myhospital_guard.py`)
  BLOCKS every agent Write/Edit/Bash-mutate to `main-brain/`. The ONLY way in is the owner-invoked
  **`/promote`** skill, after the owner authorizes by typing `! touch main-brain/.promote-unlock` (the
  guard cannot see the owner's own shell, so only the owner can create that marker).
- **LEAN by discipline.** `knowledge.md` is loaded into context every session (`@main-brain/knowledge.md`
  in `CLAUDE.md`; `AGENTS.md` treats it as standing SoT for all tools). Bloat = burned tokens every turn.
  Keep entries short and high-value; push detail to `second-brain/` and link down to `engine/` / skills.
- **What belongs here:** durable, cross-cutting **truths & decisions** — "what is true about this
  project / domain / owner", lessons that changed how we work, locked cross-module decisions.
  NOT coding conventions (→ `engine/rules/`). NOT per-module spec decisions (→ `specs/<m>/06-decision-log.md`).
  NOT provisional ideas (→ `second-brain/`).

## Files
- `knowledge.md` — the lean knowledge base (one short section per durable truth/lesson; link down, don't copy).
- `.promote-unlock` — transient marker the owner creates to authorize ONE promotion; removed after. Gitignored.

## How knowledge gets here
`second-brain/` (provisional, detailed) → owner reviews → **`/promote`** distills it here (or graduates it
into a new skill). See `second-brain/README.md` and the **"Self-Learning"** section of `AGENTS.md`.
