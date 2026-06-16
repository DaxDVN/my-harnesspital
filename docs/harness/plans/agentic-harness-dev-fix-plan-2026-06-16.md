# PLAN: Bộ harness agentic cho Dev + Fix + Review — MyHospital

> **Ngày:** 2026-06-16 · **Trạng thái:** PLAN (chưa build — chờ go-ahead) · **Tác giả:** Claude (Opus, max effort)
> **Nguồn audit (refer trực tiếp):** `[AUDIT] = /home/dax/Documents/arabica/velvet/notes/myhospital-fe-convention-audit-2026-06-15.md` (V1–V16 + Mục 7 "canonical rules" + convention spine).
> **Nền lý thuyết hội tụ:** `harness/notes/review-harness-feasibility-2026-06-16.md`.
> **Nguyên tắc:** shift-left (chặn lỗi lúc VIẾT) + đóng vòng học (mỗi finding → tầng rẻ nhất).

---

## Quyết định đã chốt (2026-06-16)

1. **Phạm vi build hiện tại:** *chỉ lưu plan này*, chưa build artifact nào. Chờ duyệt P0/P1.
2. **`mh-fix` = skill TÁCH RIÊNG** khỏi `mh-implement` (không gộp `--mode=fix`). Lý do: repro-first vs reuse-first, trigger rõ ràng hơn.
3. **Thay đổi file repo main** (`myhospital-fe/eslint.config.js`, banner stale-doc trên `ARCHITECTURE-OVERVIEW.md` + `BEST-PRACTICES-NEW-PAGE.md`, `components.json rsc`) = **agent soạn diff, user tự apply** (tôn trọng rule cấm sửa main repo). Mọi artifact agent tạo nằm trong `roast/.claude/`, `roast/docs/`, `roast/scripts/`.

---

## 0. TL;DR

Đã có xương sống review: `mh-review` skill (≤3 vòng, fan-out D1–D10, verify đối kháng, coverage ledger), `mh-reviewer` agent, `frontend-rules-conventions-patterns.md` (538 dòng — chứa ~90% Mục 7 `[AUDIT]`), guard hook deterministic. **Không dựng lại.**

Thiếu 3 mảnh, suy trực tiếp từ `[AUDIT]`:
1. **Dev/Fix chưa đóng gói** — chỉ là văn xuôi trong `protocol.md §4`. → `mh-implement` + `mh-fix` skill + `mh-implementer` agent.
2. **Tầng deterministic FE không chạy trong worktree** — guard chặn `fetch(` nhưng chỉ ở repo main (mà main thì cấm sửa ⇒ rule không bao giờ bắn lúc dev thật). → ESLint pack + ast-grep rule chạy trong worktree.
3. **Một số finding `[AUDIT]` chưa promote** (V1 dead-import, V3 hardcode master-data, V4 form thiếu resolver, warehouse "partial-exemplar" caveat). → vá guard/ESLint/checklist/rules-doc.

---

## 1. Hiện trạng (KHÔNG dựng lại)

| Tầng | Artifact đã có | Trạng thái |
|---|---|---|
| Review orchestrator | `.claude/skills/mh-review/{SKILL,protocol,checklist,findings-schema}.md` + `workflow.js` | ✅ Mature |
| Review agent | `.claude/agents/mh-reviewer.md` | ✅ |
| Review dimensions | `checklist.md` D1–D10 (D3 đã encode spine FE + cite memory `[AUDIT]`) | ✅ |
| Convention FE | `harness/rules/frontend-rules-conventions-patterns.md` | ✅ ~90% trùng Mục 7 `[AUDIT]` |
| Convention BE | `harness/rules/backend-rules-conventions-patterns.md` | ✅ |
| Deterministic guard | `.claude/hooks/myhospital_guard.py` (git/rm/deps/generated + FE/BE heuristic, self-test) | ✅ nhưng FE-heuristic chỉ repo main |
| Cross-tool + discovery | `harness/rules/{cross-tool-enforcement,source-discovery,worktree-workflow}.md` | ✅ |
| Older auditor | `.claude/agents/myhospital-rule-auditor.md` | ✅ giữ |

---

## 2. Khoảng trống chính xác

| Gap | Bằng chứng | Hệ quả |
|---|---|---|
| G1 — Không skill dev/fix | `.claude/skills/` chỉ có `mh-review` | Implementer vào việc không có pre-flight → tái tạo V2/V3/V4 |
| G2 — Deterministic FE không chạy lúc dev | guard `edit_rule` dùng `FE_MAIN`; dev thật ở `worktrees/<slug>/fe` | `fetch(`/`axios`/`@/lib/dtos/dtos` lọt trong worktree (V1/V2/V5) |
| G3 — Finding `[AUDIT]` chưa promote | V1,V3,V4,warehouse-caveat chưa có ở guard/ESLint/checklist | Review bắt lại thủ công mỗi vòng |
| G4 — Rules-doc thiếu caveat warehouse | `frontend-rules…md:109-135` liệt warehouse canonical, không cảnh báo phần xấu (`[AUDIT] §4`) | Copy page 637 dòng / context useState / inline schema |
| G5 — Tooling vỡ | V9: `npm run create:page` thiếu script | Scaffold không chạy |

---

## 3. Nguyên tắc thiết kế (kế thừa memo hội tụ)

1. **Shift-left mạnh nhất** (`protocol.md §7.2`): chặn lúc viết = review không phải tìm = vòng giảm.
2. **Tầng rẻ nhất trước** (`protocol.md §7`): deterministic > convention doc > checklist bug-class > memory.
3. **Provenance + anti-stale** (`checklist §Staleness`): code sống thắng doc; không tin `ARCHITECTURE-OVERVIEW.md`/`BEST-PRACTICES-NEW-PAGE.md` (V10).
4. **An toàn bất biến**: read-only review; sửa chỉ trong worktree; guard fail-open; không auto-merge.
5. **0 hạ tầng mới**: chỉ skill/agent markdown + ESLint/ast-grep + vá guard.

---

## 4. Bộ artifact đề xuất

### 4.1 — Skill `mh-implement` (DEV) ⭐
`.claude/skills/mh-implement/SKILL.md` (+ `preflight.md`, `definition-of-done.md`):
- **B0 Scope & worktree** — Session Start Protocol; sửa trong worktree; đọc `specs/<module>/{02,03,06,08}` nếu có.
- **B1 Pre-flight discovery** (chống reinvent — `frontend-rules…md §Reuse`): `component-inventory.generated.md` + `reuse-catalog.generated.md` + CodeGraph/`rg` + exemplar warehouse phần TỐT (4.4).
- **B2 Convention contract (shift-left)**: trích rule áp dụng từ `frontend-rules…md` + spine `[AUDIT] §3.A/B` (RQ-adapter, `useMasterData`, id-only, invalidation pair, no FE money/stock, RHF+zod factory, EnhancedDataGrid). In trước khi code.
- **B3 Implement** theo contract; delegate bounded subtask cho `mh-implementer` (4.6).
- **B4 Definition-of-Done gate** (trong worktree): `npx tsc --noEmit` (bắt V1) · `npx eslint <changed>` (pack 4.3, KHÔNG `npm run lint`) · `ast-grep scan` (4.3) · regen DTO nếu chạm contract (D7) · `npm run components:index` nếu thêm UI.
- **B5 Self-review-diff** bằng `mh-review` round-1 trên chỉ diff (M3) trước khi giao.

### 4.2 — Skill `mh-fix` (BUG-FIX) — **TÁCH RIÊNG (đã chốt)**
`.claude/skills/mh-fix/SKILL.md` — repro-first + minimal blast radius:
- **F0** Repro + `git diff` base. **F1** Root-cause qua CodeGraph `callers/callees`/`impact`. **F2** Fix tối thiểu trong worktree, không refactor kèm. **F3** DoD gate (như B4). **F4** Self-review-diff + regression check trên blast-radius (`affected`). **F5** Nếu là câu hỏi nghiệp vụ → `05-open-questions.md` + Implementation Discovery Report, không tự quyết.

### 4.3 — Tầng DETERMINISTIC (vá G2 + promote V1/V2/V3/V5) ⭐
| Lớp | Chạy ở | Thêm gì | Bắt |
|---|---|---|---|
| **Guard hook** (roast/, sửa trực tiếp) | PreToolUse mọi tool | mở `edit_rule` FE heuristic `FE_MAIN`→`FE` (gồm worktree) cho `@/lib/dtos/dtos` + `fetch(`/`axios`; giữ fail-open; chỉ pattern ~0 false-positive | V1,V2,V5 |
| **ESLint pack** (myhospital-fe — **soạn diff, user apply**) | DoD B4 + review D3 | `no-restricted-imports`: axios, zustand/jotai/redux/mobx, react-icons, react-modal, **`@/lib/dtos/dtos`** (V1), ưu tiên `react-router-dom` (V14); `no-restricted-syntax`: `fetch(` trong `*.tsx` (V2/V5), `useForm` không `resolver` (V4 best-effort) | V1,V2,V4,V5,V14 |
| **ast-grep rule** (`roast/scripts/sgconfig/*.yml`, sửa trực tiếp) | DoD + review | `masterData.$X.find(e => e.$Name === '$LIT')` (V3) · `serviceStackClient.$M(` trong component (V2) · `.bak` committed (V12) | V2,V3,V12 |

### 4.4 — Tầng CONVENTION (vá G3/G4)
Sửa `harness/rules/frontend-rules-conventions-patterns.md` (roast/, sửa trực tiếp):
- Box **"Warehouse: COPY cái này, KHÔNG cái kia"** (`[AUDIT] §4`): copy routing/mutation-hook/table/UI/RHF-zod; KHÔNG copy page nguyên khối 637 dòng / context `useState`-only / schema inline / `models.ts` chỉ re-export.
- Rule **master-data flag** (V3): cấm so name/code (`=== 'kinh'`); dùng `IsDefault`/`Requires*`/`*Option`/`Id` (`[AUDIT] §3.B`).
- DoD note: `tsc --noEmit` bắt buộc (V1).
- Stale-doc banner (V10) trên `ARCHITECTURE-OVERVIEW.md` + `BEST-PRACTICES-NEW-PAGE.md` → trỏ rules-doc. **(repo main → soạn diff, user apply.)**

### 4.5 — Tầng CHECKLIST (review recall, G3) — sửa `harness/review/checklist.md`
- **D3** thêm: master-data name/code hardcode (V3, `patient-admin-info-block.tsx:225`); `useForm` thiếu `zodResolver` (V4, `ct-page.tsx:189`); import `@/lib/dtos/dtos` (V1).
- **D7** thêm: dead generated import path (V1).
- **D10** thêm: copy page warehouse nguyên khối / context useState-only (G4).

### 4.6 — Agent `mh-implementer` (đối xứng `mh-reviewer`)
`.claude/agents/mh-implementer.md` — `tools: Read,Edit,Write,Grep,Glob,Bash`, sonnet (opus cho nghiệp vụ). Hard rules: sửa chỉ trong worktree + chỉ scope được giao + không revert người khác + nạp convention contract + chạy DoD trước khi trả + báo files-changed + validation. Bản Claude của Codex-worker mà AGENTS.md đã cho phép.

---

## 5. Ma trận finding `[AUDIT]` → artifact → tầng

| Finding | Tầng | Artifact |
|---|---|---|
| **V1** dead `@/lib/dtos/dtos` | Deterministic | ESLint no-restricted-imports + guard worktree + DoD `tsc --noEmit` |
| **V2** retail bespoke fetch | Deterministic | ESLint no-restricted-syntax `fetch(` + ast-grep `serviceStackClient` in component + guard FE→worktree |
| **V3** hardcode `'kinh'` | Det.+Conv.+Checklist | ast-grep master-data name-compare + rule rules-doc (4.4) + D3 bug-class |
| **V4** form thiếu resolver | Checklist + ESLint | D3 bug-class + ESLint useForm-no-resolver |
| **V5** payment raw fetch | Convention (ngoại lệ duyệt) | rules-doc Legacy Exceptions thêm payment, "không mở rộng" |
| **V6** no global ErrorBoundary | Convention + backlog | rules-doc note + task docs/tasks/ |
| **V9** create:page vỡ | Tooling | sửa/khôi phục `scripts/create-page.js` hoặc gỡ script (propose) |
| **V10** doc stale | Convention | banner deprecation 2 doc (propose) |
| **V11** ContentLoader rỗng | Checklist D10 NIT + backlog | bug-class + task nhỏ |
| **V12** 14 `.v2.bak` | Deterministic/cleanup | ast-grep/`fd` "no .bak committed" trong DoD + task dọn |
| **V13/V16** lệch tên/lạm dụng lib | Checklist D3/D10 | bug-class |
| **V14** react-router mix/no ROUTES | Convention | rules-doc note + ESLint ưu tiên `-dom` |
| **V15** `components.json rsc:true` | Tooling (propose) | sửa 1 dòng (propose) |
| **Spine §3.A/B** | Dev-skill | convention contract B2 (shift-left) |
| **§4 warehouse partial** | Convention | box copy/không-copy (4.4) |

---

## 6. Lộ trình theo pha (ngày/tuần)

| Pha | Việc | Hạ tầng | Cắt nếu hẹp |
|---|---|---|---|
| **P0** | `mh-implement` + `mh-fix` SKILL + `mh-implementer` agent + convention-contract/DoD (markdown, roast/) | 0 | giữ |
| **P1** | ESLint pack diff + ast-grep rule file + vá guard hook (worktree FE) + self-test | 0 | giữ ESLint pack |
| **P2** | Vá rules-doc (4.4) + checklist bug-classes (4.5); propose banner stale-doc + config fix | 0 | giữ checklist |
| **P3** | Nối DoD self-review-diff vào `mh-review`; dual-run thử 1 module đo recall | 0 | cắt dual-run |

**Thứ tự cắt:** bỏ P3 + V11/V15 trước; không bao giờ bỏ P1 deterministic + convention-contract.

---

## 7. Rủi ro & an toàn

- **Chủ quyền main repo:** ESLint/`ARCHITECTURE-OVERVIEW.md`/`components.json` ở `myhospital-fe` ⇒ agent KHÔNG tự sửa → **soạn diff, user apply** (đã chốt). Artifact agent tạo nằm trong `roast/`.
- **Guard fail-open giữ nguyên:** pattern mới phải qua `--self-test` mở rộng; chỉ thêm khi ~0 false-positive.
- **ESLint false-positive:** ngoại lệ hợp lệ (`[AUDIT] §6`: blob fetch, sub-form FormProvider, dynamic-form) → `eslint-disable` có comment lý do, KHÔNG nới rule.
- **Review read-only; fix chỉ worktree; không auto-merge** (bất biến cũ).

---

## 8. Definition-of-Done của plan

- [ ] `/mh-implement` + `/mh-fix` chạy end-to-end 1 task thật trong worktree (contract + DoD gate).
- [ ] `npx eslint` (pack mới) bắt V1/V2 trên file test lỗi cố ý; ast-grep bắt V3.
- [ ] `python .claude/hooks/myhospital_guard.py --self-test` pass sau khi mở worktree-FE.
- [ ] checklist + rules-doc có bug-class/box mới (V1,V3,V4,warehouse) với `file:line`.
- [ ] Diff ESLint/config/doc main repo soạn xong, chờ user duyệt (không tự apply).

---

## 9. Bước tiếp (chờ go-ahead)
Plan đã lưu, chưa build. Khi go-ahead, đề xuất P0 trước (skill dev/fix — mảnh thiếu lớn nhất, toàn bộ trong roast/), rồi P1 (deterministic, bắt lỗi miễn phí).
