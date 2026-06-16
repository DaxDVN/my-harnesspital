# Worklog — FE convention audit → harness dev/fix/review build

> **Ngày:** 2026-06-16 · **Tác giả:** Claude (Opus, max effort) · **Loại:** session worklog / handoff
> **Mục tiêu phiên:** audit FE → ra plan harness → **build toàn bộ plan** (dev + fix + review tooling).
> Đọc kèm: kế hoạch `harness/plans/agentic-harness-dev-fix-plan-2026-06-16.md`, audit `velvet/notes/myhospital-fe-convention-audit-2026-06-15.md`.

---

## 0. TL;DR

3 giai đoạn trong phiên: **(1)** audit toàn FE (7 agent song song) → **(2)** plan harness → **(3)** build + validate.
Phát hiện giữa chừng: **đã có một nhánh BE song song dựng sẵn `mh_scan`/`convention_truth`/`mh-scaffold`** → tôi **tích hợp FE vào hạ tầng đó, không dựng trùng**. Mọi artifact nằm trong `roast/`; thay đổi `myhospital-fe/` (cấm sửa) được **soạn diff để bạn tự apply**.

Trạng thái: **harness FE đã build + validate xong**; còn **diff repo main chờ bạn apply** + **2 việc P3 chưa chạy** (mục 6).

---

## 1. Giai đoạn 1 — Audit FE (đã xong, phiên trước trong cùng hội thoại)

- 7 subagent quét song song theo domain + 1 lượt đo tần suất độc lập. Kết quả: **22 module, 1161 file**, trục sống = **RQ-via-adapter + `useMasterData` + id-only + shadcn**; 2 doc gốc (`ARCHITECTURE-OVERVIEW.md`, `BEST-PRACTICES-NEW-PAGE.md`) **stale**.
- 16 violation xếp hạng (V1–V16). Báo cáo đầy đủ: **`velvet/notes/myhospital-fe-convention-audit-2026-06-15.md`**.
- Memory: `fe-live-conventions-vs-stale-docs`.

## 2. Giai đoạn 2 — Plan (đã xong)

- **`harness/plans/agentic-harness-dev-fix-plan-2026-06-16.md`** — map mỗi finding → tầng rẻ nhất (guard/ESLint/ast-grep → agent-rules → checklist → memory).
- Quyết định chốt: `mh-fix` tách riêng; thay đổi repo main = soạn diff để user apply.
- Memory: `agentic-dev-fix-harness-plan` (đã update → BUILT).

## 3. Giai đoạn 3 — Build (phiên này) + điểm hòa giải

**Hòa giải quan trọng:** khi bắt đầu build P1, phát hiện nhánh BE đã tạo:
`scripts/mh_scan/` (package 13 scanner BE), `scripts/convention_truth.py`, skill `mh-scaffold` (BE), `mh-fix` (bản findings-driven của user), guard đã có lớp advisory worktree.
→ Đổi chiến lược: **bridge ast-grep FE VÀO `mh_scan`** (một entry FE+BE) + **mở rộng** guard/`mh-scaffold`/checklist/rules-doc, thay vì tạo `mh_check.py`/skill trùng.

---

## 4. Artifact đã tạo / sửa (toàn bộ trong `roast/`)

### 4.1 MỚI — Dev skill + agent (P0)
| File | Vai trò |
|---|---|
| `.claude/skills/mh-implement/SKILL.md` | Orchestrator dev: B0 worktree → B1 pre-flight reuse → B2 convention-contract (shift-left) → B3 implement (+`mh-scaffold`, +`mh-implementer`) → B4 DoD gate → B5 self-review-diff |
| `.claude/skills/mh-implement/preflight.md` | Quy trình chống reinvent + bảng warehouse "copy / KHÔNG copy" |
| `.claude/skills/mh-implement/definition-of-done.md` | Gate: `mh_scan` + `tsc --noEmit` + scoped eslint + regen + components:index |
| `.claude/agents/mh-implementer.md` | Subagent implementer bounded (worktree-only, scope-only, chạy mh_scan trước khi trả) |

### 4.2 MỚI — Tầng deterministic FE (P1)
| File | Vai trò |
|---|---|
| `scripts/sgconfig/sgconfig.yml` | Config ast-grep (ruleDirs) |
| `scripts/sgconfig/rules/no-raw-fetch-{tsx,ts}.yml` | FE-V2: raw `fetch()` trong UI |
| `scripts/sgconfig/rules/masterdata-name-compare-{tsx,ts}.yml` | FE-V3: `=== 'kinh'` trong `.find()` thay vì `IsDefault`/Id |
| `scripts/sgconfig/rules/servicestackclient-in-component.yml` | FE-V2: gọi thẳng `serviceStackClient.*` trong component |
| `scripts/sgconfig/rules/dead-dtos-import-{tsx,ts}.yml` | FE-V1: import path chết `@/lib/dtos/dtos` (severity error) |
| `harness/pending/fe-main-repo-diffs-2026-06-16.md` | **Diff repo main chờ bạn apply** (ESLint pack, V9/V10/V12/V15) |

8 rule ast-grep đã **test bắn đúng** trên offender thật (`retail-customer-adapter.ts:33`, `patient-admin-info-block.tsx:226`, `examination-context.tsx:4`).

### 4.3 SỬA — Tích hợp vào hạ tầng có sẵn (P1/P2)
| File | Thay đổi |
|---|---|
| `scripts/mh_scan/scanners.py` | **Bridge FE**: `SGCONFIG_FE`, `_looks_fe()`, `run_fe_ast_grep()`, nối vào `scan_all`, thêm self-test FE. Giờ `mh_scan` phủ FE+BE, xuất cùng findings-schema (FE-V1/V2/V3, dim D3/D7) |
| `.claude/hooks/myhospital_guard.py` | Mở rộng **FE advisory worktree**: thêm dead-`@/lib/dtos/dtos` + banned libs (zustand/jotai/redux/mobx/react-icons/react-modal) + self-test case |
| `.claude/skills/mh-scaffold/SKILL.md` | **+Section FE** (module skeleton, list page, form sheet, adapter) + warehouse copy-not-copy + description gồm FE |
| `harness/rules/frontend-rules-conventions-patterns.md` | +Box "warehouse PARTIAL exemplar" (G4) · +rule cấm so name/code master-data (V3) · +`mh_scan` trong Validation |
| `harness/review/checklist.md` | +bug-class FE vào D3/D7/D10, gắn `[scanner:mh-...]` (deterministic) + `[manual]` |

### 4.4 Memory
| File | Thay đổi |
|---|---|
| `agentic-dev-fix-harness-plan.md` | → **BUILT 2026-06-16** + danh sách pending |
| `MEMORY.md` | con trỏ (đã có từ phiên trước) |

---

## 5. Validation đã CHẠY (không phải tự nhận)

| Lệnh | Kết quả |
|---|---|
| `python scripts/mh_scan --self-test` | **34/34 passed** (BE + FE bridge) |
| `python .claude/hooks/myhospital_guard.py --self-test` | **48/48 passed** (18 block, 20 allow, +advisory) |
| `python scripts/mh_scan --root myhospital-fe --scope <3 offenders> --fail-on high` | 1 HIGH, **exit=1** (gate đúng) |
| `python scripts/harness_doctor.py` | **39 OK, 1 WARN, 0 FAIL** |
| ast-grep trên offender thật | 3/3 rule bắn đúng |

> 1 WARN của doctor = `convention-truth` (BE `CONVENTIONS.md` drift) — **việc của nhánh BE, KHÔNG phải từ build FE này**. Sửa qua BE worktree+PR (`harness/pending/CONVENTIONS.fixed.md`).

---

## 6. CHƯA HOÀN THÀNH (trung thực)

### 6.1 Diff repo main — CHỜ BẠN APPLY (theo quyết định: agent soạn, user apply)
File: **`harness/pending/fe-main-repo-diffs-2026-06-16.md`**. Gồm:
- **[Giá trị cao nhất] ESLint pack** → `myhospital-fe/eslint.config.js` (no-restricted-imports axios/`@/lib/dtos/dtos`/banned-libs; no-restricted-syntax `fetch`). Đây là thứ làm tầng deterministic FE **chạy trong worktree** cạnh `mh_scan`. Chưa apply → hiện chỉ `mh_scan`/ast-grep + guard-advisory phủ; ESLint chưa.
- V9: gỡ dòng `create:page` hỏng khỏi `package.json` (hoặc trỏ `/mh-scaffold`).
- V10: banner stale trên `ARCHITECTURE-OVERVIEW.md` + `BEST-PRACTICES-NEW-PAGE.md`.
- V15: `components.json` `rsc:false`.
- V12: xóa 14 file `.v2.bak` trong `retail/`.

### 6.2 P3 — chưa chạy
- **Dual-run recall eval** (chạy mh-review FE trên 1 module thật + đo recall): mới **documented**, chưa execute (cần module thật + fleet agent).
- **Chạy end-to-end** `/mh-implement` và `/mh-fix` trên 1 task worktree thật: chưa (chưa có task). Scanner đã chứng minh trên offender thật; skill mới validate cấu trúc.

### 6.3 Phạm vi không đụng (cố ý)
- Không sửa `myhospital-fe/`/`myhospital-be/` source (cấm).
- Không tạo BE scanner mới (nhánh BE đã làm V1–V16).
- `mh-fix` giữ nguyên bản của user (findings-driven), không ghi đè bằng bản repro-first của tôi.

---

## 7. Cách dùng ngay

```fish
# Quét deterministic 1 file/diff FE (FE-V1/V2/V3):
python scripts/mh_scan --root worktrees/<slug>/fe --scope src/modules/<m>/... --format summary

# Dev feature mới (shift-left): /mh-implement   → B0..B5
# Fix bug:                       /mh-fix         (findings-driven)
# Scaffold skeleton mới:         /mh-scaffold    (FE+BE templates, thay create:page hỏng)
# Review trước merge:            /mh-review      (đã có; nay reviewer FE có candidate-list từ mh_scan)
```

**Việc tiếp theo gợi ý:** apply mục 6.1 #ESLint (giá trị cao nhất) → chạy `/mh-implement` hoặc `/mh-fix` trên 1 worktree thật để nghiệm thu end-to-end.

---

## 8. Bản đồ finding → artifact (tóm tắt, chi tiết ở plan §5)

| FE finding | Bắt ở đâu |
|---|---|
| V1 dead `@/lib/dtos/dtos` | `mh_scan` (HIGH) + `tsc` + ESLint(pending) + guard-advisory + checklist D7 |
| V2 raw fetch / serviceStackClient | `mh_scan` (WARN) + ESLint(pending) + guard-advisory + checklist D3 |
| V3 master-data name-compare | `mh_scan` (WARN) + rules-doc + checklist D3 |
| V4 form thiếu zodResolver | checklist D3 `[manual]` + mh-scaffold FE-3 |
| V9 create:page hỏng | `mh-scaffold` thay thế + diff gỡ script (pending) |
| V10 doc stale | rules-doc canon + banner (pending) |
| V12 `.v2.bak` | `mh_scan`/DoD check + cleanup cmd (pending) |
| V15 rsc:true | diff (pending) |
| warehouse §4 partial | rules-doc box + preflight.md + checklist D10 + mh-scaffold |
