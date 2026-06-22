# Ponytail Rule — minimal correct diff

Adapted for this harness from Dietrich Gebert's Ponytail project (`DietrichGebert/ponytail`, MIT): the goal is
to make agents stop over-building. This is a coding discipline, not a license to skip safety.

## Default Status

Always on. The owner does not need to say `ponytail`.

This rule applies before source edits, scaffolds, design/spec planning, fix plans, and diff reviews.

Use it especially when the request is small, local, repetitive, or likely to trigger unnecessary abstraction, but
do not turn it off for larger work. Larger work still starts from reuse and the smallest safe vertical slice.

## The Ladder

Stop at the first rung that safely solves the task:

1. Does this need code at all? If not, skip the code.
2. Can existing project behavior, component, helper, adapter, service, endpoint, schema, or pattern do it?
3. Can the standard library or platform feature do it?
4. Can an already-installed dependency do it without new ownership?
5. Can it be one line or one small localized change?
6. Only then write the minimum new code that works.

For this codebase, reuse ranks above invention. "Existing project pattern" ranks above generic stdlib/platform
when it preserves MyHospital conventions such as FE adapters, `useMasterData`, generated DTOs, backend service
patterns, permission checks, scanner-clean shapes, UI components, form guards, table shells, and status badges.

## Rules

- Deletion beats addition when behavior stays correct.
- Prefer one changed file over many; prefer one local branch over a new abstraction.
- Search for and cite reuse evidence before creating a new pattern in FE/BE code.
- When `engine/rules/quality-gates.md` applies, treat reuse evidence, fix-plan boundary, and regression map as
  the proof that Ponytail was followed.
- Do not add a dependency for something already covered by the platform, stdlib, or current dependencies.
- Do not add factories, interfaces, config layers, hooks, wrappers, or "future-ready" scaffolding unless the
  current task requires them.
- If a deliberate shortcut has a ceiling, mark it with a short `ponytail:` comment naming the ceiling and the
  upgrade trigger.
- For non-trivial logic, leave the smallest useful check behind: a scoped unit test, scanner, typecheck, or
  runnable repro that would fail if the logic breaks.

## Never Simplify Away

Do not use Ponytail to remove or skip:

- trust-boundary validation;
- error handling that prevents data loss;
- auth, permission, tenancy, security, privacy, or audit behavior;
- clinical, billing, insurance, business-rule, or state-machine correctness;
- accessibility basics;
- required generated-client/DTO regeneration;
- owner-required artifact contracts, including `robust-test` per-bug folders and review bundles;
- validation commands required by the task's risk tier.

## How To Report

Keep the final report compact:

```text
Changed: <files>
Ponytail choice: reused/deleted/minimal diff instead of <skipped heavier option>
Validation: <commands/results>
Risk: <remaining risk or none>
```

If the owner explicitly asks for the heavier design, build it after stating the simpler option and its tradeoff.
