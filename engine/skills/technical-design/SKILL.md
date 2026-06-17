---
name: technical-design
description: Owner-invoked. API-CONTRACT step (narrowed from full technical-design). DRAFTS specs/<module>/08-api.md from the owner's requirements + the owner's schema, for owner approval. Schema (07) is OWNER-OWNED — this skill READS/validates/cites it, NEVER authors it. UI (03) comes from /ui-spec. Writes 08-api + 06-decision-log + 04-traceability. Gated. Trigger "/technical-design", "api contract", "design api for module X".
---

# technical-design (W7) — API-contract only (schema = owner, UI = /ui-spec)

Owner-invoked. **Narrowed by owner decision (2026-06-16):** no longer designs schema or UI. It drafts the **API contract** (`08-api.md`) from `02-requirements` + the owner's `07-schema`, for owner approval. **Schema is OWNER-OWNED** — read/validate/cite it, **never write `07-schema`** (an agent must not invent a DB schema). **UI is produced by `/ui-spec`** (→ `03-ui.md`). **Input:** `specs/<module>/{02-requirements, 07-schema (owner-authored), 05-open-questions, 06-decision-log, 01-source-audit}` + CodeGraph. **Output:** `08-api.md` (DRAFT for approval) + `06-decision-log` + `04-traceability`. Full contract: `engine/workflows/technical-design/README.md`.

## STEP 0 — input gate (deterministic; run BEFORE drafting the API)
```bash
python engine/workflows/_shared/gate-check.py <module> --require 02-requirements,07-schema --no-blocking 05-open-questions
```
Exit `2` = **STOP** — do not draft:
- `02-requirements` missing/stub → `REQUIRES_SPEC_DISCOVERY` (owner authors requirements first).
- `07-schema` missing/stub → `REQUIRES_OWNER_SCHEMA` (**the owner must author the DB schema — this skill never invents it**).
- an unresolved `BLOCKING` / `BLOCKING_SCHEMA` / `BLOCKING_API` line in `05-open-questions` → `REQUIRES_BA_DECISION`.

Gate open → set state: `python engine/workflows/_shared/module-state.py <module> --set DESIGN --by technical-design`.

## Steps (write INTO `specs/<module>/`; envelope under `engine/workflows/technical-design/rounds/<id>/` — get `<id>` via `python engine/workflows/_shared/run-init.py technical-design` → run-NNN + `00-run-meta` + `logs/`, per `_shared/run-memory.md`)
1. **Read the owner's `07-schema`** + `02-requirements` → restate domain model + invariants (map BA terminology; do NOT invent lifecycle). **Validate** the schema against `engine/rules/backend.md` + `01-source-audit`; flag mismatches as questions — but **never edit `07-schema`** (owner-owned).
2. **DRAFT `08-api.md`** from requirements + the owner's schema — endpoints (method/path), request/response/error DTOs, validation, permission, pagination/filter/sort, back-compat. **Enough for FE to implement without guessing.** Mark it **DRAFT — needs owner approval**. This is the **FE↔BE contract lock** (contract-first): once the owner approves `08`, BE *and* FE implement against it; a later change needs a new `DL-00x`, not a silent edit.
3. Permission/validation map: functional rule → BE validation → FE display → API error.
4. **`06-decision-log.md`** — non-obvious API choices as `DL-00x`; technical risks LOW/MED/HIGH/BLOCKING.
5. Update **`04-traceability.md`**: each Confirmed requirement → API element.

> NOT this skill's job: `07-schema` (owner authors) · `03-ui` (produced by `/ui-spec`).

## API review gate (before owner approval / task-slicing)
If the API touches a shared contract · cross-module consumers · permission/validation rules · back-compat → spawn `mh-rule-auditor` (convention check) + optional Codex. HIGH-risk → run `/impact-analysis` first. The **owner approves `08-api`** before task-slicing.

## Boundaries
API-contract only — **never author `07-schema` (owner-owned) or `03-ui` (`/ui-spec`)**, never implement, never finalize `08-api` on an unresolved `05` question or without owner approval, never hide questions, never create tasks.

## Close-out (envelope + state + learning)
1. Write `rounds/<id>/api-contract.envelope.json` (shared schema, `artifact_type: api-contract`, `next_recommended_workflow: task-slicing`) → validate: `python engine/workflows/_shared/validate-envelope.py rounds/<id>/api-contract.envelope.json --payload specs/<module>/08-api.md`.
2. State: leave at `DESIGN`; after owner approval + the API review gate advance with `module-state.py <module> --set DESIGN_REVIEW`.
3. **Learning loop:** a recurring API gap (a convention the rules don't cover, a BA ambiguity) → note in `second-brain/` for later `/promote` — do NOT silently bake it into the contract.

## Status
Narrowed to API-contract (owner decision 2026-06-16): schema = owner-authored, UI = `/ui-spec`. **Input-dependency: `specs/<module>/02-requirements` + `07-schema` (owner-authored) must exist first.** API-draft quality unproven → owner approval is the gate.
