---
name: ui-spec
description: Owner-invoked. From a business DOCX + PNG mockups + the owner's specs/<module>/requirements, produce a DETAILED specs/<module>/03-ui.md that maps every UI element to REUSE / EXTEND / CREATE-NEW — maximizing reuse of existing FE components/UI/logic/patterns. READ-ONLY on source code; the foundation/input of the FE dev workflow. Trigger "/ui-spec", "ui spec", "reuse audit", "from mockup/docx".
---

# ui-spec (W6-FE) — into specs/<module>/03-ui.md (the FE-discovery keystone)

> Full runbook. `SKILL.md` is the token-light discovery stub for this skill.

Owner-invoked. **Input:** the business DOCX + PNG mockups + the owner's `specs/<module>/{02-requirements,07-schema}`. **Output:** a detailed `specs/<module>/03-ui.md` (the EXISTING SDD UI file) + a reuse map + envelope. You NEVER author schema or business rules — the owner owns those; you map the **UI** onto what the FE codebase already has. Full contract: `engine/workflows/ui-spec/README.md`.

## STEP 0 — input gate (deterministic; run BEFORE viewing mockups)
```bash
python engine/workflows/_shared/gate-check.py <module> --require 02-requirements --no-blocking 05-open-questions
```
Exit `2` = **STOP**: `02-requirements` missing/stub → `REQUIRES_SPEC_DISCOVERY` (the owner authors requirements first); a blocking `05` line → `REQUIRES_BA_DECISION`. Also STOP if no mockup images were provided (`BLOCKED_NO_MOCKUPS`) — there is nothing to inventory. No UI-spec on a stub requirement or without evidence.

## Steps (write INTO `specs/<module>/03-ui.md`; envelope under `engine/workflows/ui-spec/rounds/<id>/` — get `<id>` via `python engine/workflows/_shared/run-init.py ui-spec` → run-NNN + `00-run-meta` + `logs/`, per `_shared/run-memory.md`)
1. **Intake** — read the DOCX (use `rga` for `.docx/.pdf`) + the owner's `02-requirements`/`07-schema`. List the screens in scope.
2. **View mockups (MULTIMODAL)** — open each PNG with the **Read tool** (it renders images) and extract a **UI-needs inventory**: every screen / region / component / state / field / table / form / modal / filter / status / action / permission-gated element.
3. **Deep FE reuse-audit** — for each UI-need search the FE: **CodeGraph first** (`cd myhospital-fe && codegraph explore "<need>"` / `codegraph node <symbol>`), then the warehouse exemplar (**GOOD parts only** — see `engine/rules/frontend.md`) + shadcn `src/components/ui/*`. **Fan out** `Explore`/`general-purpose` subagents **by UI region** for a large module (depth + speed); the parent owns the merge.
4. **Reuse map** — classify each UI-need REUSE / EXTEND / CREATE-NEW with the rubric below, citing `file:line` evidence + the props/variants to pass.
5. **Output `03-ui.md`** — routes/screens/states · forms (field → component → validation display) · loading/error/empty · testid strategy · **FE STATE PLAN** (which adapter hooks, which `useMasterData` entities, the `invalidateQueries` + `invalidateMasterDataEntity` pair) · PLUS the reuse map. Detailed enough that the FE dev workflow implements **without guessing**.

## REUSE-classification rubric (default to the cheapest tier that fits)
- **REUSE** — an existing component/hook/pattern does the job as-is → cite `file:line` + props. (Prefer `src/components/ui/*` → `src/modules/common/*` → `src/lib/*` → warehouse.)
- **EXTEND** — an existing thing is 80% right; add a prop/variant/wrap. Cite the base + the exact delta. Never fork-and-edit a copy.
- **CREATE-NEW** — only after CodeGraph + shadcn + warehouse show no match. State why nothing fits.

## Mockup-vs-business flag (NEVER a silent assumption)
A mockup implying a business rule **absent from the DOCX**, or **contradicting** it (a `*` required marker, a computed badge, a hidden total), → an Open Question in `specs/<module>/05-open-questions.md` (tag `BLOCKING` if it gates the contract). Mockups are UI **evidence**, not business authority.

## Boundaries
UI mapping only — never author schema/business rules, never implement/edit source, never touch `myhospital-fe|be`/`worktrees`/`main-brain`. READ-ONLY on code; writes only `specs/`. Honor the guard.

## Close-out (envelope + state + learning)
1. Write `rounds/<id>/ui-spec.envelope.json` (shared schema, `artifact_type: ui-spec`, `next_recommended_workflow: mh-implement` = FE-dev mode) → validate: `python engine/workflows/_shared/validate-envelope.py rounds/<id>/ui-spec.envelope.json --payload specs/<module>/03-ui.md`.
2. `python engine/workflows/_shared/module-state.py <module> --set DESIGN --by ui-spec` (UI contract is part of design).
3. **Learning loop:** a recurring reuse-miss (a component CodeGraph/catalogs keep failing to surface, so it gets re-created) → note it in `second-brain/` for `/promote` (or a catalog-refresh fix).

## Status
Scaffold + wiring + contract; the **multimodal mockup-read + CodeGraph reuse-audit are REAL**; reuse-map quality is **UNPROVEN** → first real run = owner gate. **Input-dependency: the owner's `specs/<module>/02-requirements` + mockup PNGs provided first.**
