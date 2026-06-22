# Spec-Driven Development Policy

This file is lazy-loaded for requirement analysis, design, UI spec, API design, task slicing, implementation discovery, or spec change-control work.

## Module Layout

Use `specs/_TEMPLATE/` for new modules.

```text
specs/<module>/
  00-module-state.md
  00-session-handoff.md
  01-source-audit.md
  02-requirements.md
  03-ui.md
  04-traceability.md
  05-open-questions.md
  06-decision-log.md
  07-schema.md
  08-api.md
  09-test-cases.md
  10-plan.md
  11-review-checklist.md
  12-change-log.md
  assets/manifest.md
```

Always read `00-module-state.md` and `00-session-handoff.md` first.

## Source Precedence

Business truth:

```text
BA DOCX / official business document
> confirmed owner/BA answer logged in 06-decision-log.md
> mockup/Figma/screenshot
> draft notes
> agent inference flagged as Assumption
```

Technical truth:

```text
existing BE APIs/services + FE generated client/DTO/codebase facts cited as file:line
```

When business truth and technical truth conflict, do not let code silently win. File an open question and record the chosen path once the owner/BA decides.

Mockups are UI evidence, not business-rule authority.

## Requirement States

```text
Candidate -> Confirmed
Candidate -> Open Question -> Confirmed|Deferred
Confirmed -> Assumption
Confirmed -> Deferred
Confirmed -> Superseded
```

## Three-Session Workflow

1. Requirement discovery and source mapping: primary files `01`, `02`, `03`, `05`, `assets/manifest`.
2. Design contract and baseline: primary files `07`, `08`, `03`, `06`.
3. Delivery plan and review: primary files `10`, `09`, `11`, `12`.

Each session updates `00-module-state.md`, `00-session-handoff.md`, and `12-change-log.md` when changed.

## Change Control

Stop only the affected task; continue unrelated tasks if safe.

Agents must not invent business/design rules. When a gap appears:

- Add to `05-open-questions.md` if human/BA answer is required.
- Add/update `06-decision-log.md` after a path is chosen.
- Append chronology to `12-change-log.md`.
- Update requirements/schema/api/ui/test/plan only after the question is answered or decision logged.

## Implementation Discovery Report

Use this template when an implementer discovers a blocking spec gap:

```text
# Implementation Discovery Report
Module / affected slice / type (missing-requirement | codebase-constraint | contradiction | infeasible-design)
What I found (evidence: file:line or DOCX section)
Why it blocks/changes the spec
Options (cost/impact) - do NOT pick a business/design rule
Technical recommendation only
Requested routing: open-question? decision from owner/BA? tasks to PAUSE vs CONTINUE
```

## Worktrees and Specs

Do not require a worktree for requirement/design-only sessions. Use worktrees later for development that consumes a finished spec.

Editing a frozen baseline without a decision-log entry is WARN. An implementer changing a confirmed business rule is WARN and should be reported before proceeding.
