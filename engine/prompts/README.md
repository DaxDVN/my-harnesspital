# engine/prompts — reusable system prompts (copy-paste, hand to an agent)

Standalone **system prompts** the owner hands to an external/fresh agent (a high-capability audit agent, or
an Opus xhigh fixer). Not skills, not auto-invoked — durable copy-paste templates so the owner re-runs the
same audit→fix loop continuously without rewriting the prompt each time. Tool-neutral (any agent reads them
by path).

## Files

| File | Hand to | Purpose |
|---|---|---|
| `deep-audit-orchestrator.md` | a high-capability **audit** agent | **Self-contained.** Hand it + just a **slug/tên module** → it resolves the preset from its built-in **§11 MODULE REGISTRY** and starts immediately. Read-only-on-code deep audit; static **+ dynamic** (build/test/scanner/e2e) for max bug recall in **1 round**. Emits one **fix-ready** findings `.md` (every BLOCK/HIGH carries a FIX PACKET) into `docs/audit/<today>/`. |
| `bugfix-from-report.md` | an **Opus xhigh** fixer | Reads a findings `.md` path, investigates each bug on LIVE code, fixes via existing harness procedures (`/bug-fix` · `mh-rca` · `/mh-fix` · `/impact-analysis`) in a worktree, verifies. No scope-creep, no invented business rules. |

## The loop

```
deep-audit-orchestrator.md + <slug>  ──▶  docs/audit/<YYYY-MM-DD>/full-audit-<scope>.md   ──▶  bugfix-from-report.md + report-path(.md)
        (find + detail)                          + .vi.md (bản dịch cho owner)                     (Opus xhigh: triage → fix)
```

## Ngôn ngữ (cả 2 prompt)

- Prompt agent nhận + suy nghĩ + report cho-agent-đọc = **English**. Response chat cho owner = **tiếng Việt**.
- Mỗi report ra **2 file**: `<name>.md` (EN, canonical — agent/handoff đọc) + `<name>.vi.md` (VN — owner đọc).
  Gen EN trước, rồi 1 subagent rẻ (haiku/sonnet) clone bản VN. Mọi handoff/automation trỏ bản `.md` EN.

## Run an audit — 1 prompt + a slug

Hand the audit agent `engine/prompts/deep-audit-orchestrator.md` and name the target:
```
Đọc engine/prompts/deep-audit-orchestrator.md làm system prompt. Audit module: vital-signs. Chạy ngay.
```
Built-in registry targets (slug or Vietnamese name both resolve):
- `noi-tru-3modules` — bed / shift / reception (worktree `fix-bug-noi-tru`; carries the 42-item BA-FINAL list).
- `ipd-consultation` — Hội chẩn (merge-gate).
- `vital-signs` — Sinh hiệu nội trú (merge-gate, regression-heavy).

**New module not in the registry?** The agent asks you to fill the **MODULE BLOCK contract (§10)** once (or
auto-discovers baseline/scope via `worktree.py list` + `git diff --stat`), runs, then you append its preset to
§11 so next time it's just a slug.

Output → `docs/audit/<today>/full-audit-<scope>.md` (folder auto-created).

## Run the fix — Opus xhigh + report path

```
Đọc engine/prompts/bugfix-from-report.md làm system prompt.
Report: docs/audit/2026-06-19/full-audit-vital-signs.md   Worktree: worktrees/vital-signs   Bắt đầu.
```
Opus → trích OPEN findings theo severity+cluster → re-verify gốc LIVE → (mh-rca nếu phức tạp) → fix-plan
(+impact-analysis/Codex nếu rủi ro) → `/mh-fix` trong worktree → verify → cập nhật `status` trong report.

## Why this shape

The shared 90% (non-negotiables, harness workflows, dynamic floor, D1–D10, bug-classes, finding schema,
guardrails, DoD) + all per-module presets live **inside `deep-audit-orchestrator.md`** — one file, no external
instance files. Edit it once → every future audit inherits the upgrade. Output always lands in a
per-day folder (`docs/audit/<YYYY-MM-DD>/`), matching the workspace artifact convention.
