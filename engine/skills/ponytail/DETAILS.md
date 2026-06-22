# ponytail

Primary rule: `engine/rules/ponytail.md`.

## Use

- small fixes;
- scoped implementation;
- review comments about over-engineering;
- scaffold requests where an existing pattern/helper may already cover the need;
- owner asks for "ponytail", "minimal", "YAGNI", "đơn giản", "làm ít thôi", or "đừng over-engineer".

## Behavior

1. Check whether code is needed.
2. Reuse existing project pattern/helper before generic invention.
3. Prefer platform/stdlib/current dependency before new code.
4. Keep the diff as small as safely possible.
5. Run the same validation the task would require without Ponytail.

## Output

Say what heavier thing was skipped only if useful:

```text
Ponytail choice: reused <existing thing> instead of adding <new thing>.
```

Do not produce long philosophy notes unless the owner asks for a design explanation.
