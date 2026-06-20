---
title: "E2E browser testers produce false-positive bugs from form/auth-state gaps"
date: "2026-06-20"
status: provisional
source: review-closeout
scope: workflow:super-test
confidence: high
owner_confirmed: false
proposed_target: deep-review/checklist
tags: [super-test, e2e, agent-browser, triage, false-positive, consultation]
applies_tasks: [test, review, fix]
applies_globs: [docs/testing/**, engine/workflows/super-test/**]
applies_keywords: [e2e, agent-browser, super-test, signer, validation, Lưu và gửi ký]
expires: ""
---

# What

An agent-browser E2E sweep flags false BLOCK/HIGH bugs when the tester (a) does not fill ALL required content before a send/sign/submit action (gets silently/validation-blocked → 'no API call'), or (b) is not the gated actor (signer-gated buttons only render when detail.ChairmanUserId/SecretaryUserId === currentUserId, so a non-signer sees no Ký button). Triage must re-verify each browser bug against live code + an API replay with a correctly-filled payload and the current user as the gated actor BEFORE treating it as a real defect.

# Evidence

- docs/testing/2026-06-20/consultation-e2e-bugs.round-1.md: BUG-001/002/003/007 all NOT-A-BUG after API re-verify

# Why It Matters

Prevents wasting fix cycles on test-methodology artifacts; ~4 of 7 round-1 consultation bugs were non-bugs. Real bug yield was 1/7.

# How To Apply

_See # What above._

# Boundaries

Does not apply to deterministic errors (a 500 stack, a hard crash) which are real regardless of form state. Applies to 'no API call / no feedback / button missing' style observations.

# Promotion Recommendation

Promote to: deep-review/checklist
Reason: (fill in before promoting)
