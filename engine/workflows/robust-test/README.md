# Robust-Test — owner-gated targeted/sweep testing

`robust-test` replaces the removed `progressive-test` and `super-test` runtimes.

It is not an autonomous multi-agent loop. It is a manual, artifact-backed testing protocol that a single
owner-approved agent/session can run. The workflow may use browser tools, logs, CodeGraph, and source reads,
but it must not call other agents, call external implementers, or edit source code.

## What It Is For

- `targeted` mode: reproduce and verify one known bug or one risky user flow.
- `sweep` mode: map a module/route bug surface before final fix/review.
- produce bug dossiers that a higher-reasoning reviewer can audit after the tester believes the bug set is done.

## Hard Boundary

The workflow writes only under:

```text
engine/workflows/robust-test/runs/**
```

It must not edit `worktrees/`, `myhospital-fe/`, `myhospital-be/`, `specs/`, generated files, or DB data.
Fix implementation is a separate owner-approved action, typically `/mh-fix` or direct bounded source work.

## Process

```text
0. Owner invokes robust-test and chooses targeted|sweep.
1. Gate environment: worktree, slot URLs, login actor, data preconditions, FE/BE running.
2. Build a test map: flow, action, expected result, required actor/permission/data.
3. Execute tests manually or with browser tooling.
4. For every bug candidate, create one bug folder immediately.
5. Triage each candidate to confirmed bug, not-a-bug, blocked, or needs-owner-decision.
6. RCA only confirmed bugs.
7. Write a fix plan per confirmed bug or cluster.
8. STOP for owner approval before any implementation.
9. After owner-approved fixes happen outside robust-test, record fix references and retest.
10. Build the final review-ready bundle for a higher-reasoning agent.
```

## Run Folder

```text
engine/workflows/robust-test/runs/<scope>/run-NNN/
  00-robust-test-state.md
  01-test-map.md
  02-bug-index.md
  03-fix-batch-plan.md
  04-review-ready-bundle.md
  05-final-report.md
  bugs/
    BUG-001/
      00-observation.md
      01-reproduction.md
      02-triage.md
      03-rca.md
      04-fix-plan.md
      05-fix-attempts.md
      06-retest.md
      07-review-brief.md
      evidence/
  templates/
```

## Per-Bug Folder Invariant

Every captured bug candidate gets its own folder before discussion continues:

```text
bugs/BUG-NNN/
```

Do not keep bug details only in chat or only in a long catalog. The folder is the review unit for the final
high-reasoning pass.

Minimum fields per bug:

- `status`: `CANDIDATE | CONFIRMED | NOT_A_BUG | BLOCKED | NEEDS_OWNER_DECISION | FIX_PROPOSED | FIXED_PENDING_RETEST | VERIFIED`
- `severity`: `BLOCK | HIGH | MED | LOW | NIT`
- `bug_class`: stable reusable key for real bugs, or `none` with reason for true one-off bugs
- `scanner_candidate`: `yes | no`, plus the cheapest future prevention tier when yes
- `flow`: route/user action where it was observed
- `actor`: logged-in role/user and permission assumptions
- `data_preconditions`: required records/state
- `expected`: expected result and source of expectation
- `actual`: observed result
- `repro_steps`: exact steps
- `triage`: why this is or is not a real product bug
- `rca`: root cause with file/symbol evidence when confirmed
- `fix_plan`: proposed fix, reuse evidence, regression map, files not touched, alternative considered, and why the fix is not broader
- `fix_reference`: changed files/commit/diff path if a separate fix workflow ran
- `retest`: command/browser steps and result
- `review_brief`: fix reasonableness, regression risk, and adjudication question for the final high-reasoning pass

Use `templates/bug-dossier-template.md` as the checklist when creating each bug folder. The template may be
copied into `bugs/BUG-NNN/README.md` or split across the numbered files above; the fields are mandatory either
way.

## False-Positive Guard

For browser/E2E observations, do not mark a candidate `CONFIRMED` until the triage checks common test-method
artifacts:

- required fields were fully filled before send/sign/submit;
- the current user is the gated actor when buttons/actions are actor-gated;
- missing API calls are checked against form validation and UI state, not assumed to be product bugs;
- API replay uses a valid payload when feasible;
- test data/state is verified before blaming code;
- network/browser evidence is captured for the specific failure, not as a generic screenshot dump;
- the same issue is reproduced or disproved outside the first observation when feasible;
- a button missing because of permission/state is classified as `NOT_A_BUG` unless the permission/state itself is wrong.

Do not capture screenshots by default. Use targeted screenshots only as evidence for a specific bug.

## Review-Ready Bundle

When the tester believes all bugs are fixed or routed, write:

```text
04-review-ready-bundle.md
```

This bundle is for the owner to hand to a higher-reasoning review agent. It must include:

- bug index with status/severity;
- bug class and scanner-candidate summary for every confirmed bug;
- one-line verdict for every bug folder;
- links to every `bugs/BUG-NNN/07-review-brief.md`;
- fix clusters and changed-file references, if fixes happened outside robust-test;
- reuse evidence and regression map for each confirmed fix cluster;
- unresolved owner decisions;
- retest coverage and gaps;
- explicit question: "Is each fix approach reasonable and low-regression?"

Use `templates/review-ready-bundle-template.md` as the minimum structure.

The reviewer should read the bundle first, then open only contested/high-risk bug folders.

## Relationship To Removed Legacy Workflows

- `progressive-test` was a fix-first autonomous E2E loop.
- `super-test` was a harvest-first autonomous multi-agent module sweep.
- `robust-test` keeps the useful testing artifacts from both, but removes autonomous agent handoff and source edits.
- Old names may still be understood by the router as aliases, but no legacy runtime folder or skill remains.
