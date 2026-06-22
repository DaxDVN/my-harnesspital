---
title: "Rule Gate: Evidence and verification before claims"
date: "2026-06-22"
status: provisional
source: grouped-generalization
scope: workspace
confidence: high
owner_confirmed: true
proposed_target: engine/rules/quality-gates + deep-review/checklist + validation gates
tags: [grouped, evidence, verification, validation, audit, proof]
applies_tasks: [fix, implement, review, test, design, scaffold]
applies_globs: [worktrees/**, myhospital-fe/**, myhospital-be/**, docs/audit/**, docs/testing/**]
applies_keywords: [verified, evidence, proof, validation, test, typecheck, audit, migration, convention, assumption, edge-case, live-path]
expires: ""
---

# Evidence And Verification Gate

Do not convert assumptions, static inspection, or stale memory into claims of correctness. A claim needs the right
evidence for that claim.

## Use When

- Reporting `VERIFIED`, `fixed`, `safe`, `false positive`, `by design`, or `matches convention`.
- Accepting or rejecting audit findings.
- Validating FE/BE fixes, especially visible UI, save/persist paths, migrations, and generated code.

## Rule

- `VERIFIED` requires the real project gate plus the actual user path when behavior is user-visible.
- If the gate/user path did not run, say `NOT VERIFIED` and name residual risk.
- A fix must test both the original repro and new edge cases introduced by the chosen fix.
- Use the correct validator for the surface. Root-level green checks can be false green for app-level type/runtime
  failures.
- Convention exceptions require current empirical evidence across the relevant population, not stale memory or one
  exemplar.
- Audit findings need full evidence before acceptance; migration findings often require later migrations and
  snapshot checks.
- Cited authority such as decision IDs must exist.
- For hard-to-capture runtime hangs, use targeted bisection rather than over-trusting screenshots/profilers.

## Why It Generalizes

This is the anti-overclaim gate. It prevents agents from shipping "looks right" work that the owner discovers is
not actually proven.

## Archive Sources

- [`fabricated-decision-ids`](../_archive/2026-06-17-fabricated-dl-fix-decision-ids-in-code-invented-authority.md)
- [`validate-fe-vite-esbuild`](../_archive/2026-06-18-validate-fe-fixes-with-viteesbuild-not-bare-npx-tsc-noemit.md)
- [`audit-migration-full-chain`](../_archive/2026-06-19-audit-migration-drift-claim-check-all-migrations-not-just-ba.md)
- [`audit-migration-later-snapshot`](../_archive/2026-06-19-audit-migration-findings-must-check-later-migrations-and-sna.md)
- [`capture-proof-freeze-bisect`](../_archive/2026-06-20-capture-proof-sync-freeze-bisect-with-localstorage-gated-blocks.md)
- [`fe-gate-tsconfig-app`](../_archive/2026-06-20-fe-gate-tsc-p-tsconfigappjson-not-root-tsc-noemit.md)
- [`convention-skip-current-evidence`](../_archive/2026-06-21-a-convention-skip-needs-current-empirical-evidence-survey-nt.md)
- [`do-not-claim-verified`](../_archive/2026-06-21-do-not-claim-verified-without-running-the-real-gate-the-live.md)
- [`self-test-new-edge-cases`](../_archive/2026-06-21-self-test-the-fix-new-edge-cases-not-just-the-original-bug.md)
