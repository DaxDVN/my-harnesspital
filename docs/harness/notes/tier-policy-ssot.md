# Tier Policy — Single Source of Truth

`scripts/tier_policy.json` is the canonical model/effort routing table. It contains TWO parallel systems by design. This note explains why both exist and how to audit them. Owner decision 2026-06-26; superseded any prior anthropic-only routing.

## The two systems

| System | Keys | Read by | Used for | Models |
|---|---|---|---|---|
| **Actual dispatch** | `roles` + `agentic_ladder` | `select_worker_routing()` | REAL worker dispatch today | OpenCode Go paid models (deepseek / glm / minimax / kimi / mimo) + Anthropic Opus for floors/danger |
| **Safety baseline** | `tiers` + `escalation_ladder` + `coordinator` + `verifier` | `select_model_effort()` | Anthropic-equivalent risk-tier floor (audit/sanity) | haiku / sonnet / opus (Anthropic ladder) |

They are NOT redundant. The baseline exists so that an anthropic-only reader (auditor, fresh agent, external wrapper) can still reason about risk-tier safety without learning the OpenCode role ladder. The actual dispatch is what the harness uses to spare Claude quota by routing cheap implementation/audit work to OpenCode paid models.

## Why two coexist

- Owner runs OpenCode Go (paid, dollar-capped seat) for cheap-but-capable implementation/audit models → `roles`/`agentic_ladder` route to them.
- Claude/Anthropic is the safety floor for clinical/billing/permission/migration/danger classes + the mandatory final review (`mandatory_final_review.role = final_review` → Opus 4.8 xhigh, non-skippable).
- An anthropic-only consumer can ignore `roles`/`agentic_ladder` and use `tiers`/`escalation_ladder` to get a conservative-but-correct tier. Both systems agree on the safety floor.

## How to audit

1. **Read `_comment` at the top of `tier_policy.json`** — owner-locked summary of the policy.
2. **For dispatch truth**: trace `scripts/harness_router.py` → `select_worker_routing()` → reads `roles[<role>]` + walks `agentic_ladder` for escalation.
3. **For safety-baseline truth**: trace `select_model_effort()` → reads `tiers[<risk_tier>]` + `escalation_ladder`.
4. **Mandatory final review** (`mandatory_final_review`): every code-mutating workflow ends with `final_review` role = Opus 4.8 xhigh. `applies_to` lists the recipes. This is additive — non-Anthropic review never substitutes.
5. **Risk-class floor** (`risk_class_floor`): `clinical` / `billing` / `permission` / `migration` always lift to Opus xhigh, regardless of role.
6. **Orchestrator** (`orchestrator`): always Opus 4.8 low — it is the blind coordinator, cheap to run, never does domain work.

## Owner invariants

- 2026-06-26: orchestrator ALWAYS Opus 4.8 low; mandatory Opus 4.8 xhigh final review on every code-mutating workflow (non-skippable, additive).
- Sonnet dropped from dispatch (kept only as emergency manual fallback in `tiers`).
- OpenCode paid models only (no `-free` variants — rate-limit risk); single dollar-capped seat `$12/5h $30/wk $60/mo`.

## Plan reference

`docs/harness/plans/opencode-multimodel-integration-plan-2026-06-26.md` — the integration plan that introduced the dual-system design.
