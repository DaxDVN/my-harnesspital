# Memory and Learning Policy

This file is lazy-loaded when work involves learning capture, recall, promotion, or harness memory maintenance.

## Tiers

| Tier | Role | Loaded by default | Writer |
|---|---|---:|---|
| `main-brain/` | Lean source of truth for durable cross-cutting truths and owner decisions | yes, lean only | owner via `/promote` only |
| `engine/` | Canonical rules, workflows, skills, agents, hooks, and reusable recipes | on demand | maintenance |
| `second-brain/` | Provisional learning buffer | no | agents may append |
| `.claude/`, `.codex/`, `.opencode/` | Tool pointers/config | on invocation | pointer/config only |

## Write Rules

- Never write `main-brain/` directly.
- `main-brain/` changes only through the owner-invoked `/promote` flow.
- Capture provisional learnings in `second-brain/` when the owner says "remember", "nhớ", "từ giờ", "always", "never", or a recurring bug class/convention gap appears.
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
