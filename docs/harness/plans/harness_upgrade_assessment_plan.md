# Assessment & Upgrade Plan: Aligning MyHospital Harness with Latest Anthropic Guidelines

This document provides a detailed evaluation of whether and how to upgrade the MyHospital harness tools, agent prompts, and workflows to align with the latest Anthropic documentation (covering **Claude Sonnet 4.6** and **Claude Opus 4.8**).

---

## 1. Executive Summary: Should We Upgrade?

**Recommendation: YES, an upgrade is highly recommended.**

Since you primarily use **Claude Code** with **Sonnet** and **Opus** models, upgrading the harness prompts and configurations will solve several common friction points:
1. **Preventing "AI Slop" in Frontend UI:** Opus 4.8 defaults to a warm cream/serif editorial aesthetic that is unsuitable for a professional clinical healthcare dashboard like MyHospital. Explicit theme injection is required.
2. **Mitigating Overthinking & Token Waste:** Newer models (especially Opus 4.6/4.8) can over-think, over-explore, and over-delegate to subagents when given vague or overly defensive prompts. Scoping their autonomy is critical for efficiency.
3. **Handling Literalism in Code Reviews:** Opus 4.8's literal instruction-following means that qualitative filters (e.g., "only report high severity") cause it to discard valid findings. Review prompts must be adjusted to prioritize coverage.
4. **Transitioning to Adaptive Thinking:** Any manual `budget_tokens` and prefill-based prompts need migration to `adaptive thinking` configurations using the `effort` parameter.

Below is a detailed plan grouped by impact areas.

---

## 2. Key Alignment Areas & Technical Decisions

### A. Thinking & Cost Calibration (Adaptive Thinking)
*   **The Issue:** Previous models used manual extended thinking with `budget_tokens`. Claude Sonnet 4.6 and Claude Opus 4.8 use **Adaptive Thinking** (`thinking: {type: "adaptive"}`) driven by the `effort` parameter (`xhigh` / `high`).
*   **Impact on Harness:** Workflows like `espresso-test` (blind coordinator routing fixer/reviewer tiers) and skills like `/bug-fix` must pass correct `effort` values rather than fixed token budgets.
*   **Action Plan:**
    *   Update model invocation configurations (e.g., in providers or coordinator wrappers) to set `thinking: {type: "adaptive"}`.
    *   Map `xhigh` effort to implementation/fixer roles (`mh-implementer`, `mh-rca`) and `high` to reviewer roles (`mh-reviewer`).

### B. Frontend Design (Overriding Opus 4.8 Defaults)
*   **The Issue:** Opus 4.8 has a strong, persistent cream/serif/terracotta default style. If left unguided, it will convert clinical pages into looking like hospitality blogs.
*   **Impact on Harness:** `ui-spec` (spec-driven FE design) and `/mh-implement` (FE-mode) need explicit aesthetic constraints.
*   **Action Plan:**
    *   Inject a specific CSS/theme specification block into `engine/prompts/clinical-ui-design.md` and `engine/rules/frontend.md`.
    *   Force a concrete visual palette matching the MyHospital design system (e.g. cold gray backgrounds, sharp 4px border-radius, sans-serif typography like Outfit/Inter, clinical blue/teal accents).

### C. Autonomy, Proactivity & Subagent Scoping
*   **The Issue:** Opus 4.8/Sonnet 4.6 can overengineer, add unnecessary defensive code, or spawn too many subagents for simple lookups.
*   **Impact on Harness:** Prompts for `mh-implementer` and `mh-rca` can trigger excessive round trips.
*   **Action Plan:**
    *   Insert a `<default_to_action>` block to force implementations over suggestions when intent is clear.
    *   Insert the `<investigate_before_answering>` directive to eliminate guess-work.
    *   Provide explicit limits on subagent spawning: only spawn subagents when tasks run in parallel or require isolated contexts. For single-file edits or simple CodeGraph queries, work directly.

### D. Code Review Coverage (`mh-reviewer`)
*   **The Issue:** Claude Opus 4.8 is very literal. If instructed to "be conservative," it will spend tokens finding bugs but refuse to list them.
*   **Impact on Harness:** `deep-review` workflow yields fewer reported bugs.
*   **Action Plan:**
    *   Modify `engine/agents/mh-reviewer.md` and review prompts to emphasize **finding coverage first, filtering second**. Tell the model explicitly that its goal is to surface all potential issues, leaving filtering and confidence sorting to downstream stages.

---

## 3. Step-by-Step Implementation Plan (No Code Edits)

### Phase 1: Audit & Foundation
1.  **Audit Invocation Configurations:** Search for any backend model-calling wrappers or mock APIs (e.g. `promptfoo_harness_router_provider.py`) to verify they don't use deprecated prefill configurations (which cause 400 errors in Claude 4.6+).
2.  **Verify XML & Data Ordering:** Ensure inputs from CodeGraph and workspace metadata are injected at the *top* of prompt templates, leaving queries and task instructions at the *bottom* (improves long-context performance by up to 30%).

### Phase 2: Agent Prompt Upgrades
1.  **Update `mh-implementer.md` & `mh-rca.md`:**
    *   Add `<investigate_before_answering>` tag to ensure source files are read before logic is written.
    *   Add anti-overengineering rules (minimizing net-new files, avoiding helper script workarounds, implementing general solutions instead of hardcoded test-passing code).
2.  **Update `mh-reviewer.md`:**
    *   Apply the "coverage over self-filtering" directive to capture low-severity and high-severity findings alike, ranking confidence explicitly.

### Phase 3: Guidelines & Rules Alignment
1.  **Update `engine/rules/frontend.md`:**
    *   Incorporate the `<frontend_aesthetics>` block specifying cold monochrome/clinical theme overrides.
2.  **Update `engine/rules/ponytail.md`:**
    *   Align the minimalist/correctness principles with the official Antigravity/Anthropic "Anti-laziness" and "Anti-overengineering" guidelines.

### Phase 4: Validation & Evaluation
1.  **Run Evaluation Suite:** Use `scripts/harness_quality_eval.py` to baseline current prompt metrics (tokens/elapsed/results).
2.  **Compare Costs:** Monitor token usage on the new `adaptive thinking` setup versus the old model setup using the updated `scripts/harness_eval.py`.
