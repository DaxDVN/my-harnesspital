# Workflow run-memory — per-run isolation + the 3 data classes

How a workflow RUN organizes its files so (a) every agent that joins the run knows exactly which files are
theirs, and (b) three different kinds of data are kept SEPARATE and never cross-read by mistake. This
formalizes the run-isolation pattern for all workflows.

## 1. The named run folder (isolation — so agents don't read each other's runs)
A **run** = one execution of a workflow. It gets a UNIQUE, NAMED folder; an agent joining the run is handed
that folder path and reads/writes **ONLY there**.
- browser/test: `engine/workflows/robust-test/runs/<scope>/run-NNN/`
- SDLC: `engine/workflows/<wf>/rounds/<run-id>/` for the run's receipts; the DURABLE output is the `specs/<module>/` SDD files.
- **run-id is deterministic + unique** — `run-NNN` (incrementing), `<module>-run-NNN`, or `<scenario>-NNN`. Never reuse an id.
- A root **`00-*-state` / `00-*-meta`** file makes the run self-describing (workflow · run-id · module · phase · who). Read it first on re-entry.
- **Rule: never read another run's folder.** One run = one memory scope.

## 2. The THREE data classes (keep them separate)
| Class | Where | Who reads it | Rule |
|---|---|---|---|
| **A. Agent↔agent interchange** (the contract) | numbered payloads `01-…`, `02-…` (.md/.json) + a short `*.envelope.json` each | the next agent / the router | the **router/orchestrator reads the ENVELOPE** (status·verdict·summary·next·`content_sha256`), **NOT the long payload** (context-rot guard); the step's specialist reads the payload it owns, by path |
| **B. Per-session logs** (debug, write-mostly) | `<run>/logs/` — stdout/stderr, executor transcripts, screenshots, `<run>/evidence/` | the owning step / a human debugging | NOT part of the contract; other agents do NOT read another step's logs by default |
| **C. Human-readable report** (the one a person reads) | exactly ONE per run | the human | one final report; don't make humans read the IO artifacts or logs |

Envelopes use `engine/workflows/_shared/envelope.schema.json` (+ `validate-envelope.py`). `content_sha256` binds
envelope↔payload so a stale receipt pointing at a changed payload is caught.

## 3. Read discipline (the anti-cross-reading rules)
- Join a run → you get ONE folder path; that folder is your whole world for the run.
- **Orchestrator/router**: read `00-*state` + the latest `*.envelope.json` + validator exit codes. Do NOT read payloads or `logs/`.
- **Specialist** (RCA/batch-RCA/reviewer/implementer): read the specific payload(s) you need by path — not the whole tree.
- Never: read another run's folder · treat `logs/` as a contract · paste a long payload into chat (pass the PATH).

## 4. Per-workflow conformance (current)
| workflow | run folder | A. agent IO | B. logs | C. human report |
|---|---|---|---|---|
| **robust-test** | `runs/<scope>/run-NNN/` | bug dossiers + review-ready bundle | `<run>/logs/` + `bugs/*/evidence/` | `05-final-report.md` |
| **bug-fix · impact-analysis · technical-design · task-slicing · incremental-impl · ui-spec** | `rounds/<run-id>/` (receipts+envelopes); durable → `specs/<module>/` | numbered payload+envelope | Claude-orchestrated → the envelope trail IS the log (no wrapper stdout) | the `specs/<module>/` files + the round envelope summary |
| **deep-review** | (fan-out — no per-run folder) | reviewers return findings IN-CONTEXT (Agent tool), merged by the orchestrator | n/a | `docs/audit/<module>-review-v<round>-<date>.md` + coverage ledger |

## 5. Gaps + alignment (what's not yet uniform)
- **SDLC `rounds/<id>/`**: now use `run-init.py <wf>` → a real `run-NNN/` + `00-run-meta.json` + `logs/` (no more ad-hoc ids). Wired into all 6 SDLC skills.
- **deep-review** is intentionally in-context (fan-out→merge→one audit file), so it has no run folder — keep it, but note it as the documented EXCEPTION (not a per-run pipeline).
- **fuzz-ledger** (step-fuzzing): robust-test `<run-dir>/fuzz-ledger.md` when in-step fuzzing is used.

## When adding a workflow
Use a unique run-id folder + a `00-*meta`; separate the 3 classes (A artifacts+envelopes · B `logs/` · C one report);
reuse the shared envelope; the router reads envelopes not payloads; never cross-read another run.
