# BUG-NNN — <short title>

## Metadata

- status: CANDIDATE
- severity: HIGH
- bug_class:
- scanner_candidate: yes | no
- scanner_candidate_tier: guard | mh_scan | eslint/ast-grep | review-checklist | none
- flow:
- actor:
- route/url:
- worktree:
- observed_at:

## 00 Observation

Expected:

Actual:

Evidence:

## 01 Reproduction

Preconditions:

Steps:

Result:

Repro reliability:

## 02 Triage

False-positive checks:

- Required fields filled:
- Correct actor/permission:
- API replay or validation checked:
- Live code gate checked:
- Test data/state verified:
- Network/browser artifact captured:
- Same issue reproduced or disproved outside the first observation:

Verdict: CANDIDATE | CONFIRMED | NOT_A_BUG | BLOCKED | NEEDS_OWNER_DECISION

Reason:

Scanner promotion note:

## 03 RCA

Root cause:

Evidence:

- file/symbol:
- log/API/browser evidence:

Blast radius:

## 04 Fix Plan

Root cause boundary:

Reuse evidence:

Regression map:

Proposed fix:

Files likely touched:

Files explicitly not touched:

Alternative considered:

Why not bigger fix:

Risk:

Validation needed:

Owner approval needed:

## 05 Fix Attempts

Fix reference:

Changed files:

Notes:

## 06 Retest

Retest steps:

Result:

Remaining risk:

## 07 Review Brief

Question for high-reasoning reviewer:

Is the fix approach reasonable, minimal, and low-regression?

Should `bug_class` be promoted to a deterministic scanner/rule?

Fix reasonableness:

Regression risk:

Adjudication needed:

Reviewer should inspect:

- triage correctness
- RCA evidence
- proposed/actual fix
- reuse evidence
- regression map
- validation coverage
