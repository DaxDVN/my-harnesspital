# Current Harness Review — 2026-06-17

## Executive Summary

Verdict: harness hiện tại có kiến trúc đúng hướng và mạnh hơn mức “agent prompt” thông thường, nhưng chưa nên coi là một hệ tự vận hành hoàn chỉnh. Phần nền tảng tốt nhất là: worktree isolation, CodeGraph-first discovery, rule canon trong `engine/`, deterministic scanners, guard tripwire, review protocol có coverage ledger, và memory tier `main-brain`/`second-brain`. Điểm yếu chính không nằm ở ý tưởng mà nằm ở drift giữa policy và wiring thực tế: một số tài liệu còn chỉ sang nguồn cũ, một số workflow tự nhận `UNPROVEN`, Codex/opencode parity chưa thật sự ngang Claude, và learning loop hiện là thủ công.

Mức đánh giá khách quan:

- Kiến trúc / design: 8/10.
- Guardrail an toàn: 7/10 nếu agent làm ở workspace root; 5/10 khi chạy từ worktree hoặc tool/subagent không được hook.
- Cross-tool parity: 5/10.
- Review harness concept: 8/10; proof thực chiến: 5/10.
- Self-learning: 4/10 hiện tại; có khung đúng nhưng chưa có intake tự động.
- Maintainability: 6/10 do nhiều doc lịch sử và path cũ còn tồn tại.

## What Is Working Well

### 1. Có phân tầng rõ: dispatcher, engine, brain, tool adapters

`AGENTS.md` định nghĩa root dispatcher và không cố nhồi toàn bộ convention vào một file duy nhất. `engine/README.md` xác định `engine/` là nơi chứa rules, skills, agents, hooks, workflows; `.claude`, `.codex`, `.opencode` chỉ nên là pointer/config. Đây là hướng đúng vì giảm duplicate giữa tools.

Bằng chứng:

- `AGENTS.md:47-75` định nghĩa `main-brain`, `engine`, `second-brain`.
- `engine/README.md:1-16` định nghĩa `engine/` là canonical home.
- `.claude/{skills,agents,hooks,workflows}` là symlink sang `engine/`.

### 2. Worktree isolation là đúng cho repo FE/BE

Rule “không edit `myhospital-fe/` và `myhospital-be/` trực tiếp” là hợp lý vì workspace chứa main repos, task worktrees, DB slots và ports riêng. Đây là một guardrail thực tế, nhất là khi agent chạy nhiều phiên.

Bằng chứng:

- `AGENTS.md:25`, `AGENTS.md:91-93`, `AGENTS.md:153-156`.
- `docs/guides/worktree-zellij-manual.md:7-15`.

### 3. CodeGraph-first discovery là điểm mạnh

Policy đã chuyển từ grep-first sang CodeGraph-first cho source code. `just codegraph-status` xác nhận cả BE và FE index đang up-to-date:

- BE: 1,402 files, 31,975 nodes, 76,945 edges.
- FE: 1,732 files, 34,592 nodes, 104,658 edges.

Điều này giảm token waste và giảm rủi ro agent đọc nhầm pattern do search quá rộng.

### 4. Deterministic floor có thật

Các self-test pass:

- `python engine/hooks/myhospital_guard.py --self-test` → `all 64 cases passed`.
- `python scripts/mh_scan --self-test` → `all 31 cases passed`.
- `_shared` validators pass: `validate-envelope`, `gate-check`, `module-state`, `allowlist-check`.
- `python scripts/harness_doctor.py` → `60 OK, 0 WARN, 0 FAIL, 2 INFO`.

Đây là nền tốt. Những thứ có thể kiểm bằng script thì không nên để LLM tự nhớ.

### 5. Review protocol có cơ chế chống roulette

`engine/workflows/deep-review/protocol.md` có các phần đúng: scope freeze, deterministic pre-scan, partitioned audit theo D1-D10, adversarial verify, coverage ledger, bounded completeness check, status lifecycle. Đây là cách review hợp lý hơn so với “một agent đọc hết rồi báo vài issue nổi bật”.

## Major Issues

### H1 — Source-of-truth conflict: BE docs route vẫn trỏ vào `CONVENTIONS.md` cũ

Severity: HIGH.

`engine/rules/README.md` nói `engine/rules/backend.md` là canon và `myhospital-be/CONVENTIONS.md` có drift đã biết. `just convention-truth` cũng xác nhận `CONVENTIONS.md` là superseded/advisory. Nhưng `AGENTS.md` và `engine/rules/backend.md` vẫn route BE work sang `myhospital-be/CONVENTIONS.md` như canonical source.

Bằng chứng:

- `AGENTS.md:122-124`: BE work đọc và obey `myhospital-be/CONVENTIONS.md`.
- `engine/rules/README.md:14-18`: `engine/rules/*` là canon; `CONVENTIONS.md` drift.
- `engine/rules/backend.md:21-32`: vẫn gọi `CONVENTIONS.md` là backend convention source/canonical.
- `just convention-truth`: 4 INFO drift trong `CONVENTIONS.md`, gồm code prefixes, SettingKeys, action names, TypeScript endpoint.

Risk:

Agent mới có thể nạp `CONVENTIONS.md` trước, gặp rule cũ, rồi implement/review sai. Đây là lỗi “harness tự mâu thuẫn”, nguy hiểm hơn lỗi code lẻ vì nó dẫn sai nhiều phiên.

Recommended fix:

1. Sửa `AGENTS.md` Scope Routing: BE work đọc `engine/rules/backend.md` trước, `myhospital-be/CONVENTIONS.md` chỉ là package-local legacy pointer.
2. Sửa `engine/rules/backend.md` Source-of-Truth Hierarchy.
3. Sửa checklist D2 sources để `engine/rules/backend.md` đứng trước, `CONVENTIONS.md` chỉ tham khảo legacy.
4. Khi được owner cho phép qua BE worktree, thay `myhospital-be/CONVENTIONS.md` bằng thin pointer hoặc apply `docs/harness/pending/CONVENTIONS.fixed.md`.

### H2 — Backend canon hiện còn một drift thật về TypeScript endpoints

Severity: HIGH.

`engine/rules/backend.md` dòng `BE-FE Contract Sync and Type Export` nói `/types/typescript-types` export C# DTO/utility interfaces. Code sống và `convention_truth.py` cho thấy DTO chính đến từ ServiceStack NativeTypes endpoint `/types/typescript`; `/types/typescript-types` là custom handler cho utility types từ `MyHospital.Utilities`.

Bằng chứng code sống:

- `MyHospital/Services/TypeScriptGeneratorHostedService.cs`: fetch `/types/typescript`, `/types/typescript-types`, `/types/typescript-const`.
- `MyHospital/Configure.AppHost.cs:300-311`: custom raw handlers chỉ cho `typescript-const` và `typescript-types`.
- CodeGraph confirmed `NativeTypesFeature` controls `/types/typescript`.
- `scripts/convention_truth.py` explicitly flags old claim.

Risk:

Đây là canon-level bug. Agent có thể diagnose sai khi DTO missing hoặc regenerate sai endpoint.

Recommended fix:

Sửa `engine/rules/backend.md`:

- `/types/typescript` = ServiceStack NativeTypes DTO export.
- `/types/typescript-types` = custom utility/shared types.
- `/types/typescript-const` = constants, ErrorCodes, entity stores, query schema.

Sau đó thêm `convention_truth.py` check cho chính `engine/rules/backend.md`, không chỉ legacy `CONVENTIONS.md`.

### H3 — Codex skill parity chưa thực tế

Severity: HIGH.

Harness nói Codex reach engine skills qua `[[skills.config]] / symlink`, nhưng project `.codex/config.toml` chỉ có model config. Global `~/.codex/config.toml` có trust, hook state, CodeGraph MCP, nhưng không thấy project skill config cho `engine/skills`. Trong phiên Codex này, danh sách available skills không có `mh-implement`, `mh-review`, `mh-fix`, `mh-scaffold`, `agentflow`, `ui-spec`, v.v.

Bằng chứng:

- `engine/README.md:38-42` claim Codex có `[[skills.config]] / symlink`.
- `.codex/config.toml` chỉ có:
  - `model = "gpt-5.4-mini"`
  - `model_reasoning_effort = "xhigh"`
- Current Codex session skills list không expose `mh-*`.

Risk:

Với Codex, nhiều “skill” hiện chỉ là Markdown policy phải đọc thủ công, không phải tool/skill callable. Điều này làm giảm khả năng proactive routing đúng như `agent-shortcuts.md` mô tả.

Recommended fix:

1. Wire project skills thật sự cho Codex bằng cơ chế current Codex supports, hoặc tạo `.agents/skills` symlink/pointers tới `engine/skills` nếu đó là loader đang hoạt động.
2. Thêm `harness_doctor` check: “Codex session can see `mh-implement`, `mh-review`, `promote`”.
3. Nếu Codex không có project skill loader tương đương Claude, hạ wording từ “skill” xuống “workflow docs” trong Codex path và cung cấp wrapper command/scripts thay vì giả định slash-skill.

### H4 — Codex guard dùng relative `.claude/...`, fail-open khi chạy từ worktree

Severity: HIGH.

`.codex/hooks.json` chạy:

```sh
if test -f .claude/hooks/myhospital_guard.py; then exec python3 .claude/hooks/myhospital_guard.py; fi
```

Khi Codex chạy từ workspace root thì được. Nhưng thực tế implementer thường chạy trong `worktrees/<slug>/fe` hoặc `worktrees/<slug>/be`. Ở đó không có `.claude/hooks/myhospital_guard.py`, nên hook no-op/fail-open. Đây là đúng chỗ cần guard nhất.

Bằng chứng:

- `.codex/hooks.json:7-12` chỉ matcher `Bash`, command dùng relative path.
- `engine/rules/cross-tool-enforcement.md:177-180` tự ghi là no-op khi Codex runs from worktree subdir.
- Guard cũng không cover Codex `apply_patch`/file edit shapes; doc đã thừa nhận ở `cross-tool-enforcement.md:206-207`.

Risk:

Worktree edits, generated files, migrations, dangerous shell command có thể lọt nếu tool shape không phải `Bash` hoặc cwd không phải root.

Recommended fix:

1. Đổi Codex hook sang absolute path hoặc wrapper tự walk-up tới workspace root như opencode plugin.
2. Thêm doctor check mô phỏng hook từ:
   - root
   - `worktrees/<slug>/fe`
   - `worktrees/<slug>/be`
3. Nếu Codex không hook `apply_patch`, thêm validation bắt buộc sau edit: `git diff --name-only` + generated/migration path check + `mh_scan`.
4. Không claim “Codex guard wired” nếu chỉ wired cho root Bash.

### H5 — opencode project config chưa thể hiện đầy đủ rule/instruction wiring

Severity: MEDIUM-HIGH.

Global opencode guard plugin có symlink đúng ở `~/.config/opencode/plugin/myhospital-guard.js`. Nhưng project `.opencode/opencode.json` chỉ load graphify plugin, không thể hiện `instructions: ["engine/rules/*", ...]` như `engine/README.md` claim. `opencode agent list` cho thấy permissions cho `.claude/skills/*`, nhưng đó là quyền đọc external dir, không chứng minh model sẽ tự nạp đúng rules/workflows.

Bằng chứng:

- `.opencode/opencode.json` chỉ có graphify plugin.
- `engine/README.md:41` claim `instructions: ["engine/rules/*", …] + guard plugin`.
- `cross-tool-enforcement.md:203-205` tự thừa nhận opencode subagent tool calls không bị intercept.

Risk:

OpenCode/MiMo flows có thể chạy với thiếu instruction context hoặc guard không cover subagent calls.

Recommended fix:

1. Add explicit opencode project instructions/pointers nếu supported.
2. Doctor should verify opencode sees:
   - guard plugin active
   - CodeGraph MCP active
   - engine rules in instruction context or a documented fallback prompt wrapper.
3. Mọi OpenCode wrapper (`test-with-opencode`, `implement-with-opencode`) phải inject a compact harness preamble + allowed files + forbidden actions, không rely vào global config.

### H6 — Graphify state in docs is stale/contradictory: graph absent, not merely Windows-stale

Severity: MEDIUM.

`AGENTS.md` và `CLAUDE.md` nói current graph is STALE Windows-built. Nhưng `python scripts/harness_doctor.py` hiện báo `no graph.json`; `graphify-out/` không tồn tại. `docs/graphify-agent-guide.md` vẫn nói graph nằm ở `graphify-out/graph.json`.

Bằng chứng:

- `graphify-out missing`.
- Doctor: `[INFO] graphify no graph.json`.
- `AGENTS.md:231-240` mô tả graph Windows-stale.
- `docs/graphify-agent-guide.md` assume graph exists.

Risk:

Agent có thể mất thời gian chạy graphify hoặc báo stale warning không đúng trạng thái. Trạng thái thật là “absent until rebuilt”.

Recommended fix:

1. Update root docs: “graph may be absent; if absent, skip graphify and read source docs”.
2. Update `docs/graphify-agent-guide.md`.
3. Doctor output already correct; propagate it to docs.

### H7 — Workspace artifact policy mâu thuẫn `.gitignore`

Severity: MEDIUM.

`AGENTS.md` yêu cầu session notes, audit reports, tasks, testing artifacts lưu ở `docs/session-notes`, `docs/audit`, `docs/tasks`, `docs/testing`. Nhưng `.gitignore` ignore `/docs/*` và chỉ unignore `docs/graphify-agent-guide.md` + `docs/harness/`. Nghĩa là artifacts theo policy sẽ không được version-control trong root harness repo.

Bằng chứng:

- `AGENTS.md:360-374` artifact table.
- `.gitignore:21-24` ignore `/docs/*`, chỉ unignore `docs/graphify-agent-guide.md` và `docs/harness/`.
- `git check-ignore -v docs/session-notes/probe.md` → ignored by `.gitignore:22`.

Risk:

Agent tưởng đã lưu artifact bền vững, nhưng artifact không tracked. Với harness reports, điều này gây mất lịch sử hoặc lệch giữa docs và git.

Recommended fix:

Chọn một trong hai:

1. Nếu muốn version-control artifacts: unignore các dirs listed trong `AGENTS.md`.
2. Nếu chỉ muốn track harness history: update `AGENTS.md` table, nói harness review/research đi vào `docs/harness/notes/`, session runtime artifacts có thể ignored.

Tôi chọn ghi báo cáo này vào `docs/harness/notes/` vì đây là harness history và hiện đang tracked.

### H8 — Worktree manual guide có path cũ và câu “quick single-agent tasks” mơ hồ

Severity: MEDIUM.

`docs/guides/worktree-zellij-manual.md:5` trỏ `harness/rules/worktree-workflow.md`, path cũ sau restructure. Ngoài ra dòng 13-15 nói skip worktree cho “quick single-agent tasks”; nếu hiểu là quick code edits thì mâu thuẫn với hard rule “normal code changes go in worktree”.

Bằng chứng:

- `docs/guides/worktree-zellij-manual.md:5`.
- `AGENTS.md:25`, `AGENTS.md:91-93`, `AGENTS.md:153-156`.

Recommended fix:

- Path đúng: `engine/rules/worktree-workflow.md`.
- Clarify: skip worktree only for read-only review/spec/docs-only harness work; any FE/BE code edit still needs worktree unless owner bypass.

### H9 — `AGENTS.md` vẫn bắt FE component inventory script đã bị loại bỏ

Severity: MEDIUM.

`AGENTS.md:179` nói FE UI/component work phải run/read `myhospital-fe/docs/components/component-inventory.generated.md` và update bằng `npm run components:index`. Nhưng `engine/rules/frontend.md` và `mh-implement/fe-flow.md` nói catalogs và `components:index` đã bị removed, không tồn tại; reuse source mới là CodeGraph + `/ui-spec` reuse-map.

Bằng chứng:

- `AGENTS.md:179`.
- `engine/rules/frontend.md:56`, `engine/rules/frontend.md:439`.
- `engine/skills/mh-implement/preflight.md:69-72`.

Risk:

Agent có thể dừng vì script không tồn tại hoặc cố sửa FE main repo để tạo catalog, trái với owner decision mới.

Recommended fix:

Update `AGENTS.md` Mandatory Discovery FE bullet:

- FE UI work: CodeGraph first from FE repo; if spec exists, consume `specs/<module>/03-ui.md` reuse-map; bounded `rg` only after that.
- Remove `components:index` from root mandatory rule or mark legacy only.

### H10 — Một số active docs còn stale path/name từ restructure

Severity: MEDIUM.

Search tìm thấy nhiều path cũ: `harness/rules/*`, `agent-rules/*`, `.claude/skills/<x>` as skill graduation target. Một phần nằm trong archived notes, không cần fix. Nhưng một số nằm trong active docs:

- `engine/skills/mh-review/SKILL.md:201-202` còn `agent-rules/*-rules-conventions-patterns.md`.
- `engine/skills/promote/SKILL.md` nói graduate vào `.claude/skills/<slug>/SKILL.md`, trong khi canonical home mới là `engine/skills`.
- `docs/guides/worktree-zellij-manual.md:5` path cũ.

Risk:

Agent tạo asset vào sai tier hoặc dẫn người dùng đến path không tồn tại.

Recommended fix:

1. Run stale-ref scan in doctor for active files only (`AGENTS.md`, `CLAUDE.md`, `engine/**`, `docs/guides/**`).
2. Allow stale paths in `docs/harness/notes` and old audit artifacts as historical records.
3. Fix active refs to `engine/rules`, `engine/skills`, `engine/workflows`.

### H11 — Multi-agent story chưa nhất quán giữa tools

Severity: MEDIUM.

Harness định nghĩa Claude-style agents (`engine/agents/*.md`) và review skill nói spawn Agent tool. `AGENTS.md` lại cho Codex dùng `gpt-5.3-codex-spark` workers. Nhưng không thấy một neutral runner contract đủ rõ để cùng chạy trên Claude/Codex/opencode, ngoại trừ workflow docs và một số wrappers. Với Codex hiện tại, multi-agent tools có thể tồn tại qua deferred tools, nhưng không được harness doctor kiểm.

Bằng chứng:

- `AGENTS.md:341-350`.
- `engine/agents/*.md` là Claude agent format (`tools`, `model` frontmatter).
- `engine/skills/mh-review/SKILL.md:173-182` assume Agent tool fan-out.

Risk:

Review/implementation partition có thể chỉ hoạt động đầy đủ trong Claude, còn Codex/opencode phải làm thủ công. Nếu docs claim cross-tool ngang nhau, đây là overclaim.

Recommended fix:

- Tạo `engine/workflows/_shared/worker-task.md` hoặc JSON schema cho worker prompt/result.
- Tạo adapter docs/scripts:
  - Claude Agent call.
  - Codex worker call.
  - OpenCode run wrapper.
- Doctor/probe kiểm “current tool can spawn workers” hoặc downgrade mode to single-agent with explicit coverage limits.

### H12 — Nhiều workflow đã scaffold nhưng tự nhận UNPROVEN

Severity: MEDIUM.

Đây không phải lỗi nếu được ghi rõ, nhưng là rủi ro nếu agent/user tưởng chúng production-ready.

Bằng chứng:

- `engine/skills/bug-fix/SKILL.md`: full investigate→fix→verify `UNPROVEN`.
- `engine/skills/impact-analysis/SKILL.md`: CodeGraph step real, risk-framing `UNPROVEN`.
- `engine/skills/incremental-impl/SKILL.md`: wrapper `UNPROVEN`.
- `engine/skills/ui-spec/SKILL.md`: reuse-map quality `UNPROVEN`.
- `engine/workflows/super-test/manifest.json`: M1 built; M2/M3 next; E2E unproven.

Risk:

Workflow complexity có thể tạo cảm giác automation hoàn chỉnh, trong khi acceptance chưa có real run.

Recommended fix:

Add a `maturity` field to every workflow manifest:

- `concept`
- `scaffolded`
- `self-tested`
- `smoke-tested`
- `real-run-proven`
- `production-default`

Doctor should summarize maturity and block auto-use of workflows below a configured level unless owner explicitly invokes.

### H13 — Learning loop hiện mostly manual; `main-brain` và `second-brain` đang empty

Severity: MEDIUM.

Harness có model `main-brain`/`second-brain` và `/promote`, nhưng chưa có learning intake tự động từ conversation. `second-brain/INDEX.md` empty; `main-brain/knowledge.md` empty.

Bằng chứng:

- `AGENTS.md:60-75` describes learning lifecycle.
- `second-brain/INDEX.md`: empty.
- `main-brain/knowledge.md`: empty.
- `engine/workflows/deep-review/protocol.md:75-83` says bug-class should be promoted, but no automatic capture mechanism.

Risk:

Harness “có khả năng tự học” ở mức policy, không phải system behavior. Nếu agent quên capture, tri thức từ thảo luận vẫn mất.

Recommended fix:

See separate file: `docs/harness/notes/harness-self-learning-solution-2026-06-17.md`.

## Minor Issues

### M1 — Cross-tool doc self-test count stale

`engine/rules/cross-tool-enforcement.md:154-156` nói guard self-test 55 cases; actual output là 64 cases. Minor but indicates docs drift.

### M2 — `mh-fix` and `mh-review` Markdown links are relative-wrong from skill folder

Examples:

- `engine/skills/mh-fix/SKILL.md:10` links `(engine/workflows/...)` from a file already under `engine/skills/mh-fix/`, so Markdown resolution is wrong unless rendered from root.
- `engine/skills/mh-review/SKILL.md:8` same issue.

Fix: use root-relative text paths or correct relative links (`../../workflows/...`).

### M3 — Some docs still say graphify is “current graph stale” rather than “graph absent”

Covered in H6, but easy to fix.

### M4 — `docs/graphify-agent-guide.md` likely needs a full pass

It assumes `graphify-out/graph.json` exists and gives MCP setup commands. Current state says no graph. Add a top warning.

## Optimal Remediation Plan

### Phase 0 — Freeze current harness state

Goal: avoid reviewing moving target.

Steps:

1. Run `git status --short` and decide whether current dirty harness changes are intended.
2. Run `just harness-backup` before broad edits.
3. Create a tracked “harness repair plan” in `docs/harness/plans/`.

Acceptance:

- Backup exists.
- Dirty files understood: owner changes vs agent changes.

### Phase 1 — Fix active documentation truth

Goal: remove policy contradictions that mislead agents.

Files likely affected:

- `AGENTS.md`
- `CLAUDE.md`
- `engine/rules/backend.md`
- `engine/rules/frontend.md`
- `engine/rules/README.md`
- `engine/skills/promote/SKILL.md`
- `engine/skills/mh-review/SKILL.md`
- `engine/skills/mh-fix/SKILL.md`
- `docs/guides/worktree-zellij-manual.md`
- `docs/graphify-agent-guide.md`

Specific fixes:

1. BE source-of-truth: `engine/rules/backend.md` first; `CONVENTIONS.md` legacy pointer.
2. TypeScript endpoints: `/types/typescript` DTO, `/types/typescript-types` utility, `/types/typescript-const` constants.
3. FE reuse: remove `components:index` from active mandatory root rule.
4. Graphify: graph absent unless rebuilt.
5. Path references: `engine/rules`, `engine/skills`, `engine/workflows`.
6. Artifact destination: reconcile `AGENTS.md` with `.gitignore`.

Acceptance:

- `rg` over active docs shows no stale `harness/rules`, `agent-rules`, or `components:index` except archived docs.
- `just convention-truth` has no contradiction with `engine/rules/backend.md`.

### Phase 2 — Make cross-tool wiring factual

Goal: if docs say a tool can use a capability, prove it.

Actions:

1. Codex:
   - Wire `engine/skills` into the actual Codex skill loader, or explicitly document “Codex reads workflow docs manually”.
   - Replace `.codex/hooks.json` relative guard path with absolute/walk-up wrapper.
   - Add doctor checks for root and worktree cwd.
2. opencode:
   - Make project instructions explicit or inject harness preamble in wrappers.
   - Doctor verifies guard plugin, CodeGraph MCP, model availability, agent-browser capability.
3. Claude:
   - Keep symlinks; add stale-ref check.

Acceptance:

- `harness_doctor.py` can answer: “which tools can see which skills/rules/guards”.
- Codex guard works from `worktrees/<slug>/fe`.

### Phase 3 — Add maturity gates to workflows

Goal: stop over-trusting scaffolded workflows.

Actions:

1. Add `maturity` to each `manifest.json`.
2. Add `doctor` summary:
   - `proven`: safe default.
   - `unproven`: explicit owner invocation only.
3. Run one real pilot per workflow before promotion:
   - `mh-review`: one actual dirty worktree review with findings file.
   - `bug-fix`: one reproduced bug → RCA → fix → verify.
   - `ui-spec`: one DOCX+mockup → `03-ui.md`, then FE consume it.
   - `agentflow/super-test`: one bounded browser run on a disposable worktree.

Acceptance:

- Each workflow has a real-run artifact or remains marked unproven.

### Phase 4 — Implement learning intake

Goal: make “self-learning” reliable but not unsafe.

Actions:

1. Add `scripts/learning_capture.py`.
2. Add `just learning-capture`, `just learning-list`, `just learning-doctor`.
3. Update `agent-shortcuts.md`: `nhớ cái này`, `để ý cái này`, `from now on`, review close-out bug-class → capture to `second-brain`.
4. Keep `/promote` owner-gated.

Acceptance:

- A user statement “nhớ cái này...” creates a structured provisional second-brain entry.
- Promotion preview can distill into `main-brain` or graduate to `engine/skills`.

### Phase 5 — Continuous health checks

Goal: keep harness from drifting again.

Add to `just doctor` or separate `just harness-lint`:

- stale path scan for active docs.
- `git check-ignore` check for artifact policy.
- Codex/opencode/Claude wiring probes.
- graphify absent/stale clarity.
- backend endpoint canon check.
- markdown link check for active docs.
- workflow maturity summary.

## Answer To “Is There Any Issue?”

Yes. The harness is strong, but there are real issues:

1. Canon conflict around BE docs is the highest priority.
2. Backend canon has a concrete TypeScript endpoint drift.
3. Codex/opencode parity is overclaimed.
4. Guard enforcement has cwd/tool-shape gaps.
5. Graphify docs do not match current absent graph state.
6. Artifact storage policy conflicts with `.gitignore`.
7. FE component inventory rule is stale in `AGENTS.md`.
8. Self-learning is mostly manual.
9. Several workflows are scaffolded/unproven and should be maturity-gated.

## Commands Run

```text
python scripts/worktree.py list
python scripts/harness_doctor.py
just convention-truth
git status --short
just codegraph-status
python engine/hooks/myhospital_guard.py --self-test
python scripts/mh_scan --self-test
python engine/workflows/_shared/validate-envelope.py --self-test
python engine/workflows/_shared/gate-check.py --self-test
python engine/workflows/_shared/module-state.py --self-test
python engine/workflows/_shared/allowlist-check.py --self-test
codegraph explore "TypeScript export endpoints in Configure.AppHost TypeScriptTypesHandler NativeTypes /types/typescript /types/typescript-types"
rg ... focused stale-reference checks
git check-ignore -v docs/session-notes/probe.md docs/harness/notes/probe.md docs/audit/probe.md docs/tasks/probe.md docs/testing/probe.md
```

## Residual Risk

This review is read-only against the harness working tree except for writing this report. The workspace is dirty with many harness changes; conclusions reflect the current working tree, not a committed stable baseline. I did not run a real `mh-review` multi-agent workflow, `agentflow`, `super-test`, or actual browser E2E loop; where workflow maturity is discussed, it is based on docs, scripts, self-tests, and existing notes, not a fresh full real-run.

