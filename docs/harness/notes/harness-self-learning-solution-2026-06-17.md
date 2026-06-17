# Harness Self-Learning Assessment And Proposed Solution — 2026-06-17

## Short Answer

Harness hiện tại có kiến trúc memory đúng hướng nhưng chưa có khả năng tự học tự động qua các đoạn thảo luận với user theo nghĩa mạnh.

Nó có:

- `second-brain/` làm buffer tri thức provisional.
- `main-brain/` làm source-of-truth lean, owner-gated.
- `/promote` để owner review rồi distill/promote.
- Review protocol có “learning loop” sau khi đóng module.

Nó chưa có:

- Cơ chế tự phát hiện câu user kiểu “từ giờ”, “nhớ”, “đừng làm X”, “rule này đúng” và tạo entry đều đặn.
- Script/schema chuẩn để capture learning.
- Queue trạng thái học: captured → verified → promoted/graduated/rejected.
- Doctor check cho learning health.
- Session-close learning audit.
- Cơ chế cập nhật `engine/rules`/checklist/skills một cách có kiểm soát sau review/bug-fix.

Kết luận khách quan: harness hiện có “memory architecture”, không có “learning intake system”.

## Current State

### Existing learning model

`AGENTS.md` định nghĩa ba tier:

- `main-brain/`: source of truth, lean, owner-only via `/promote`.
- `engine/`: canonical rules/skills/hooks/workflows.
- `second-brain/`: scratch notebooks, agent được append freely.

`second-brain/README.md` nói agent có thể append entry khi owner nói “nhớ cái này / để ý cái này” hoặc khi phát hiện durable cross-cutting fact. `engine/skills/promote/SKILL.md` định nghĩa flow promote owner-gated.

### Practical gap

`second-brain/INDEX.md` đang empty. `main-brain/knowledge.md` cũng empty. Điều này không chứng minh cơ chế sai, nhưng chứng minh chưa có intake loop vận hành thường xuyên trong các phiên trước.

Nhiều workflow nói “learning loop” nhưng không có script bắt agent tạo structured entry. Nếu agent nhớ thì có, nếu agent quên thì mất.

## Design Principle

Self-learning phải chia làm hai mức:

1. Auto-capture provisional knowledge: agent được phép tự tạo entry trong `second-brain/` khi có trigger rõ hoặc sau review/bug-fix có bug-class mới.
2. Canonization/promotion: không tự động. Chỉ owner-gated qua `/promote`, vì canon sai nguy hiểm hơn không học.

Nói cách khác: agent có thể tự ghi nháp, không được tự sửa não chính.

## Proposed Solution: Learning Intake Loop

### Overview

Thêm một workflow nhẹ: `learning-intake`.

Mục tiêu:

- Bắt tri thức từ hội thoại/user feedback thành file có schema.
- Giữ mọi thứ provisional trong `second-brain/`.
- Cho owner một queue dễ review.
- Promote lên `main-brain` hoặc graduate thành `engine/rules`/`engine/skills` khi owner explicit.

Không cần LLM database, vector store, hay service ngoài. Chỉ cần Markdown + script Python nhỏ + doctor checks.

## Proposed Files

```text
engine/workflows/learning-intake/
  README.md
  manifest.json
  schema.md

engine/skills/learning-intake/SKILL.md

scripts/learning_capture.py
scripts/learning_list.py
scripts/learning_check.py

second-brain/
  INDEX.md
  YYYY-MM-DD-<slug>.md
```

Nếu muốn tránh thêm skill cho Codex/opencode ngay, bắt đầu chỉ với scripts và update `agent-shortcuts.md`.

## Capture Triggers

### Explicit user triggers

Agent tự capture vào `second-brain/` khi user nói các pattern rõ:

- `nhớ cái này`
- `để ý cái này`
- `từ giờ`
- `lần sau`
- `đừng bao giờ`
- `always`
- `never`
- `remember this`
- `make this a rule`
- `promote this later`

### Review/fix close-out triggers

Sau khi review/fix/bug-fix xong, agent chạy learning audit:

- Có bug-class mới không?
- Có lỗi agent lặp lại không?
- Có convention gap không?
- Có deterministic rule nên thêm vào scanner/guard không?
- Có owner decision cross-cutting không?

Nếu có, tạo entry provisional.

### Conversation contradiction triggers

Nếu user sửa agent:

- “Không, cái đó sai”
- “Không được làm thế”
- “Ở project này phải làm X”

Agent phải capture nếu correction có tính cross-cutting. Nếu chỉ là scoped-to-task, ghi vào task/spec, không vào brain.

## Learning Entry Schema

Mỗi file `second-brain/YYYY-MM-DD-<slug>.md`:

```markdown
---
title: "<short>"
date: "2026-06-17"
status: provisional
source: conversation | review-closeout | bug-fix | user-correction | implementation-discovery
scope: workspace | backend | frontend | module:<name> | workflow:<name>
confidence: low | medium | high
owner_confirmed: false
proposed_target: main-brain | engine/rules/backend | engine/rules/frontend | deep-review/checklist | skill | spec-decision | reject
tags: [harness, convention]
expires: "" # optional, e.g. "revalidate after FE eslint pack"
---

# What

One clear statement of the learning.

# Evidence

- User said: "<short paraphrase, not full private transcript>"
- Code/doc evidence: `path:line`
- Validation command, if any: `...`

# Why It Matters

What failure this prevents.

# How To Apply

Concrete behavior for future agents.

# Boundaries

Where this does NOT apply.

# Promotion Recommendation

Promote to: ...
Reason: ...
```

Rationale:

- `status: provisional` prevents accidental canon.
- `scope` avoids overgeneralizing module-specific decisions.
- `confidence` tells future agents how strongly to trust.
- `proposed_target` routes owner review.
- `boundaries` prevents bad global rules.

## Script Behavior

### `scripts/learning_capture.py`

Responsibilities:

- Takes fields via CLI flags or stdin.
- Creates a slugged file in `second-brain/`.
- Appends one line to `second-brain/INDEX.md`.
- Refuses to write `main-brain/`.
- If an existing similar slug exists, appends a “seen again” section instead of duplicating.

Example:

```fish
python scripts/learning_capture.py \
  --title "Codex guard must work from worktree cwd" \
  --source review-closeout \
  --scope workspace \
  --confidence high \
  --proposed-target engine/rules/cross-tool-enforcement \
  --evidence ".codex/hooks.json:11 uses relative .claude path" \
  --what "Codex guard wiring must use absolute or walk-up root discovery, not cwd-relative .claude path." \
  --why "Implementation sessions run from worktrees; cwd-relative hook fails open there."
```

### `scripts/learning_list.py`

Shows queue:

```text
OPEN provisional:
- 2026-06-17-codex-guard-worktree-cwd.md — target engine/rules/cross-tool-enforcement — high
```

Filters:

- `--target main-brain`
- `--target rules`
- `--confidence high`
- `--stale`

### `scripts/learning_check.py`

Doctor-like checks:

- Every `second-brain/*.md` has frontmatter.
- Every `INDEX.md` entry points to an existing file.
- No entry with `status: provisional` is referenced by `main-brain` as canon.
- `main-brain/knowledge.md` stays below a size budget.
- No agent-created `.promote-unlock`.

## Promotion Flow

Keep existing `/promote`, but update it to consume the new schema.

Promotion paths:

### 1. Promote to `main-brain`

Use for durable cross-cutting truths/owner preferences.

Rules:

- One or two sentences.
- Link to detailed `second-brain` entry or `engine` file.
- Owner must create `main-brain/.promote-unlock`.
- Agent removes unlock after edit.

### 2. Graduate to `engine/rules`

Use for coding convention.

Example:

- “Always use `BaseService<T>` helper for tenant-scoped query.”

Flow:

1. Owner approves.
2. Agent edits `engine/rules/backend.md` or `frontend.md`.
3. Add scanner/guard if deterministic.
4. Tombstone second-brain entry.

### 3. Graduate to `engine/workflows/deep-review/checklist.md`

Use for review bug-class.

Example:

- “FE mutation updates master data but misses `invalidateMasterDataEntity`.”

Flow:

1. Add to D3 or D10 Known bug-classes.
2. If deterministic, add `mh_scan` rule first.
3. Tombstone second-brain entry.

### 4. Graduate to a skill/workflow

Use for repeatable procedure.

Important correction:

Current `promote` skill says create `.claude/skills/<slug>`. New canonical home should be `engine/skills/<slug>/SKILL.md`, because `.claude/skills` is a symlink to `engine/skills`.

## Safety Rules

### What agent may do autonomously

- Create `second-brain/*.md`.
- Append to `second-brain/INDEX.md`.
- Suggest promotion target.
- Suggest exact diff for `engine/rules` or checklist.

### What agent must not do autonomously

- Write `main-brain/`.
- Create `.promote-unlock`.
- Promote a provisional entry into canon.
- Turn a one-off module decision into global rule.
- Add new scanner/guard that blocks without owner approval, unless task explicitly asks.

## Integration Points

### `AGENTS.md`

Add a short operational rule:

```text
When the owner says "nhớ cái này", "để ý cái này", "từ giờ", "always/never", or corrects a repeated agent behavior, create a structured provisional learning in second-brain via scripts/learning_capture.py. Do not write main-brain. At session end, if new cross-cutting facts were discovered, capture them or state "no durable learning captured".
```

### `engine/agent-shortcuts.md`

Current shortcut already maps `nhớ cái này` to second-brain. Make it executable:

```text
nhớ cái này / remember this -> python scripts/learning_capture.py ...
```

### `harness_doctor.py`

Add:

- `learning:index`
- `learning:schema`
- `learning:main-brain-size`
- `learning:pending-count`

### Review protocol

Update protocol §7:

- New bug-class → call `learning_capture.py` unless immediately promoted by owner.
- Deterministic candidate → capture with `proposed_target: mh_scan|guard|eslint`.

### Bug-fix workflow

After `VERIFIED_FIXED`:

- RCA root cause recurrent? Capture.
- Fix had PLAN_MISMATCH? Capture agent-process learning.
- User correction? Capture.

## Minimal MVP

Do not overbuild. MVP can be done with 3 small changes:

1. Add `scripts/learning_capture.py`.
2. Update `agent-shortcuts.md` and `AGENTS.md` to require using it.
3. Add `learning_check.py` into `harness_doctor.py`.

MVP acceptance test:

1. User says: “nhớ cái này: với Codex hook không được dùng cwd-relative `.claude`, vì implementer chạy từ worktree”.
2. Agent runs `learning_capture.py`.
3. A file appears in `second-brain/`.
4. `second-brain/INDEX.md` gets one entry.
5. `python scripts/harness_doctor.py` reports learning schema OK.
6. `/promote` later can distill it into `main-brain` or `engine/rules/cross-tool-enforcement.md`.

## Better V2

After MVP works:

1. Add duplicate detection:
   - slug similarity.
   - tags + proposed target.
2. Add `review-needed` queue:
   - high-confidence, repeated entries rise to top.
3. Add `learning promote-preview`:
   - produce proposed `main-brain` text or rule/checklist diff, but do not apply.
4. Add stale expiry:
   - entries with `expires` are surfaced by doctor after date/condition.
5. Add cross-tool wrappers:
   - Claude skill.
   - Codex workflow doc/script.
   - OpenCode wrapper prompt.

## Anti-Patterns To Avoid

### 1. Do not auto-write `main-brain`

Bad because a misunderstood user correction becomes permanent instruction loaded every session.

### 2. Do not use raw chat transcript as memory

Store paraphrased evidence, not entire discussion. It keeps memory lean and avoids leaking unrelated content.

### 3. Do not promote every preference

Only cross-cutting durable knowledge belongs in `main-brain`. Module-specific decisions belong in `specs/<module>/06-decision-log.md`. Coding conventions belong in `engine/rules`.

### 4. Do not make `second-brain` auto-loaded

It is allowed to grow and may contain wrong ideas. Auto-loading it would pollute context. Load only index/target entry when needed.

### 5. Do not let learning bypass source precedence

If a learning conflicts with live code, specs, or owner decision, mark conflict and ask. Provisional memory must not silently override source truth.

## Example Learning Entries

### Example 1 — Tooling convention

```markdown
---
title: "Codex guard must resolve root from worktree cwd"
date: "2026-06-17"
status: provisional
source: harness-review
scope: workspace
confidence: high
owner_confirmed: false
proposed_target: engine/rules/cross-tool-enforcement
tags: [codex, guard, worktree]
---

# What

Codex guard wiring should not rely on cwd-relative `.claude/hooks/...`; implementation sessions run from `worktrees/<slug>/fe|be`.

# Evidence

- `.codex/hooks.json` uses `test -f .claude/hooks/myhospital_guard.py`.
- `engine/rules/cross-tool-enforcement.md` says this no-ops from worktree subdir.

# Why It Matters

The guard is weakest where code edits actually happen.

# How To Apply

Use absolute root path or walk-up root discovery in Codex hook.
```

### Example 2 — Owner preference

```markdown
---
title: "Owner wants manual worktree/Zellij control"
date: "2026-06-17"
status: provisional
source: user-correction
scope: workspace
confidence: high
owner_confirmed: true
proposed_target: main-brain
tags: [workflow, worktree, zellij]
---

# What

Owner wants agents to print worktree/Zellij commands unless explicitly told to run them.

# Boundaries

Read-only root harness docs do not need worktree selection.
```

## Final Recommendation

Implement the MVP learning intake, not a heavy autonomous memory system.

Best near-term architecture:

- `second-brain` = append-only provisional queue.
- `scripts/learning_capture.py` = one reliable intake path for all tools.
- `/promote` = owner-gated canonization.
- `engine/rules`/`checklist` = where reusable technical learnings graduate.
- `harness_doctor` = verifies memory health.

This gives the harness practical self-learning without letting an agent silently rewrite the project’s source of truth.

