---
name: promote
description: Owner-invoked ONLY — the agent must NEVER self-invoke this. Promote a second-brain/ learning into main-brain/ (distill into a lean source-of-truth entry) OR graduate it into a new .claude/skills skill. Use only when the OWNER types /promote. Trigger "/promote".
---

# promote — second-brain → main-brain (owner-gated)

**Owner-invoked ONLY.** Like `/mh-review`, this is explicit: do NOT trigger it autonomously, after
implement/fix, or because a learning "seems ready". Run it ONLY when the owner types `/promote`.

`main-brain/` is the gated source of truth — the guard hook blocks all agent writes to it. The owner's
`! touch main-brain/.promote-unlock` is the authorization act (the guard cannot see the owner's shell, so
only the owner can create the marker).

## Flow
1. **Confirm owner intent + target.** Which `second-brain/` entry (or entries)? Promote-to-brain or
   graduate-to-skill? If unclear, ask. If you reached here without the owner explicitly asking — STOP.
2. **Read** the `second-brain/` entry + the relevant `main-brain/knowledge.md` section (or existing skills).
3. **Decide & draft (show the owner before applying):**
   - **Promote → main-brain:** distill the learning into the SHORTEST clear durable statement. main-brain
     is loaded every session — no bloat. Link down to `engine/rules` / a skill instead of copying detail.
   - **Graduate → skill:** if it is a repeatable *procedure*, draft a new `.claude/skills/<slug>/SKILL.md`
     instead (skip the main-brain write). Skills are the "recipes"; main-brain holds the "lessons".
4. **Authorize (brain promotion only):** ask the owner to type in their prompt
   `! touch main-brain/.promote-unlock` (this unlocks the guard for the write). Wait for it.
5. **Apply** the `main-brain/knowledge.md` edit (now allowed). Keep it lean.
6. **Re-lock:** `rm main-brain/.promote-unlock`.
7. **Retire the source:** remove the promoted entry from `second-brain/` and leave a tombstone line in
   `second-brain/INDEX.md` (`~~slug~~ → promoted to main-brain` / `→ graduated to skill <x>`).
8. **Verify:** `python scripts/harness_doctor.py` (expect 0 FAIL); self-review the diff.

## Safety
Never write `main-brain/` except in step 5 within an owner-authorized run. Never create the unlock marker
yourself — only the owner does (step 4). Honor the guard (no git mutation, no editing generated files).
A graduated skill must follow existing skill conventions (model a sibling `.claude/skills/*/SKILL.md`).
