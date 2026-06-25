# Memory and Learning Policy

This file is lazy-loaded when work involves learning capture, recall, promotion, or harness memory maintenance.

## Tiers

| Tier | Role | Loaded by default | Writer |
|---|---|---:|---|
| `main-brain/` | Lean source of truth for durable cross-cutting truths and owner decisions | yes, lean only | owner via `/promote` only |
| `engine/` | Canonical rules, workflows, skills, agents, hooks, and reusable recipes | on demand | maintenance |
| `second-brain/` | Provisional learning buffer (lessons, patterns, reusable insights only) | no | agents (must ask owner first) |
| `.claude/`, `.codex/`, `.opencode/` | Tool pointers/config | on invocation | pointer/config only |

## Write Rules

- Never write `main-brain/` directly.
- `main-brain/` changes only through the owner-invoked `/promote` flow.
- **second-brain/ is strictly for distilled lessons**: reusable patterns, "always/never" rules, insights about why something works or fails, and learnings that can prevent future issues.
  - Do **not** put raw audit reports, full bug investigation dumps, detailed findings, repro logs, or large investigation artifacts here.
  - Suitable locations for those: `docs/audit/`, `docs/session-notes/`, worktree notes, or `specs/<module>/`.
- Agents **must ask the owner first** before creating any new file or significant content in `second-brain/`.
- Capture provisional learnings in `second-brain/` only when the owner explicitly wants to remember a lesson (e.g. "remember", "nhớ", "từ giờ", "always", "never", or a clear reusable pattern).
- Use `python scripts/learning_capture.py ...` for structured captures.
- A module-local business/design decision belongs in `specs/<module>/06-decision-log.md`, not in the brain.

## Recall Rule

Before fix, review, implement, design, or scaffold work:

```bash
python scripts/learning_recall.py --context "<task>"
```

Open only the matched notes. Treat them as provisional strong hints; verify before relying on them.

## Promotion Path

Provisional learning should graduate into the cheapest preventive layer that works:

```text
guard/scanner/ESLint/ast-grep
-> engine/rules
-> review checklist bug class
-> main-brain
```

Use `python scripts/learning_check.py` to verify learning health.
