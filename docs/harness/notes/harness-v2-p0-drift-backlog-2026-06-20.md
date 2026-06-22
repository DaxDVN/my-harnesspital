# Harness v2 P0 Drift Backlog - 2026-06-20

Scope: only stale or drift issues relevant to lifecycle, router, manifest, public/internal/advisory classification, envelope/runtime boundary, and doctor governance.

## DRIFT-001 - Graphify availability docs disagree with current trust state

- Area: router/docs design-intent tooling
- Evidence: `CLAUDE.md` and `engine/rules/source-discovery.md` still describe graphify as currently absent in places, while `scripts/harness_doctor.py` can detect `graphify-out/graph.json` present but untrusted.
- Why it matters: future router/design flows could either skip a useful graph or trust an unverified graph.
- Risk: medium
- Recommended later phase: P2
- P0 action: documented only
- P2 action: root and source-discovery docs now point to doctor trust checks and `engine/rules/graphify.md`; remaining graph data cleanup is still separate.
- P4/P5 action: no lifecycle promotion depends on graphify; existing doctor warnings remain the source of truth.

## DRIFT-002 - Technical-design docs still have broad historical scope

- Area: manifest/router workflow classification
- Evidence: `engine/workflows/technical-design/README.md` still describes a broader BE+FE+API/schema/UI design flow, while `engine/skills/technical-design/SKILL.md` and the P0 manifest classify it as API-contract focused with schema owner-authored and UI from `ui-spec`.
- Why it matters: router `files_to_load` and allowed writes could become too broad if it follows the old README.
- Risk: high
- Recommended later phase: P1
- P0 action: manifest description narrowed; README drift documented only
- P1/P2 action: still open; workflow README should be reconciled in a focused technical-design doc cleanup.

## DRIFT-003 - Audit path references predate current audit round helper

- Area: artifact governance
- Evidence: some skill/docs references still mention flat `docs/audit/<module>-review-v<n>-<date>.md` paths, while the current root rule and `scripts/audit_path.py` use date folders and `.round-<N>.md`.
- Why it matters: review agents can write findings to inconsistent paths, weakening handoff and eval traceability.
- Risk: medium
- Recommended later phase: P1
- P0 action: documented only

## DRIFT-004 - Progressive-test envelope schema is separate from shared envelope schema

- Area: envelope/runtime boundary
- Evidence: `engine/workflows/_shared/envelope.schema.json` and `engine/workflows/progressive-test/.agentflow/schemas/envelope.schema.json` both exist with different required fields.
- Why it matters: an "envelope everywhere" migration could break progressive-test if it assumes one schema.
- Risk: high
- Recommended later phase: P3
- P0 action: documented only; do adapter-first, not breaking migration
- P2 action: still open; no runtime schema behavior changed.
- P3 action: added `engine/workflows/_shared/validate-compatible-envelope.py` to validate shared v1 and legacy progressive envelopes through one read-only adapter; added `runtime-boundary.md`. No schema migration or runtime behavior change.

## DRIFT-005 - Super-test status wording differs across files

- Area: lifecycle/public workflow status
- Evidence: `engine/workflows/super-test/manifest.json`, `engine/workflows/super-test/README.md`, and `engine/skills/super-test/SKILL.md` describe similar but not identical maturity/status wording.
- Why it matters: router/lifecycle governance needs one conservative source for auto-route decisions.
- Risk: medium
- Recommended later phase: P1
- P0 action: lifecycle set to `LAB`, `auto_route_allowed=false`; wording cleanup documented only
- P5 action: `engine/workflows/LIFECYCLE.md` and `docs/harness/plans/harness-v2-p5-consolidation-plan-2026-06-20.md` keep `super-test` as LAB/public explicit, not DEFAULT.

## DRIFT-006 - `clinical-ui-design` skill is not classified in workflow registry

- Area: public/internal/advisory classification
- Evidence: `engine/skills/clinical-ui-design/SKILL.md` exists, but `engine/REGISTRY.md` does not list it in the skills table.
- Why it matters: a router cannot know whether this is public, internal, advisory, deprecated, or folded into `ui-spec`.
- Risk: medium
- Recommended later phase: P1
- P0 action: documented only
- P5 action: still documented only; no workflow deprecation/consolidation without eval evidence.

## DRIFT-007 - Prose shortcut routing still predates lifecycle governance

- Area: router/public workflow surface
- Evidence: `engine/agent-shortcuts.md` maps intents directly to skills and fast-path prose without lifecycle checks.
- Why it matters: later adaptive routing should use lifecycle/manifest evidence before auto-suggesting a workflow.
- Risk: medium
- Recommended later phase: P1
- P0 action: router decision format added; shortcut behavior unchanged
- P1/P2 action: `scripts/harness_router.py` added as dry-run router, and `engine/agent-shortcuts.md` changed to lazy reference.
- P4/P5 action: router auto-route now also requires eval evidence for PROVEN/DEFAULT; workflow governance scanner prevents deprecation without replacement.
