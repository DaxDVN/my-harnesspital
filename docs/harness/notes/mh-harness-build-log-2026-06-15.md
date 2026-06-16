# Build log — Harness convention-enforcement từ BE audit

> **Loại:** Nhật ký thực thi + handoff (đọc để nắm đã làm gì, còn gì chưa).
> **Ngày:** 2026-06-15
> **Chuỗi việc:** BE audit → plan → build harness.
> **3 file gốc:**
> - Audit: `/home/dax/Documents/arabica/velvet/notes/myhospital-be-conventions-audit-2026-06-15.md` (finding V1–V16, doc-error D1–D6)
> - Plan: `harness/plans/mh-harness-from-be-audit-plan-2026-06-15.md`
> - Build log (file này): `harness/notes/mh-harness-build-log-2026-06-15.md`

---

## 0. TL;DR

Audit BE thấy 2 lớp hỏng: (a) `CONVENTIONS.md` sai 5 chỗ mà review lại tin nó, (b) không có tầng kiểm convention cơ học. Đã **xây xong sàn deterministic + doc-truth + prevention**, nạp thẳng vào harness `mh-review` sẵn có. Tất cả ở harness root, đã test. `harness_doctor`: **39 OK · 0 FAIL · 1 WARN (cố ý)**. **Chưa xong (cần BẠN):** áp `CONVENTIONS.fixed.md` vào BE qua PR; vá 38 endpoint thiếu auth; (optional) Roslyn/ESLint/CI.

---

## 1. Đã xây — artifact

### 1.1 File MỚI tạo

| Path | Là gì | Audit ref | Test |
|---|---|---|---|
| `scripts/mh_scan/scanners.py` | **Scanner pack** — engine + 13 scanner cơ học + self-test | V1–V16 | self-test 34/34 ✓ |
| `scripts/mh_scan/__main__.py`, `__init__.py` | CLI wrapper (`python scripts/mh_scan`) | — | chạy ✓ |
| `scripts/convention_truth.py` | **Doc-vs-code drift checker** (CONVENTIONS.md) | D1–D6 | phát hiện 4 FAIL = D1–D4 ✓ |
| `.claude/skills/mh-scaffold/SKILL.md` | Template chuẩn BE+FE (listing/service/error/detail + FE module/page/list/form). Thay `npm run create:module` đã hỏng | chặn V3/V4/V8 | exemplar `file:line` thật |
| `.claude/skills/mh-fix/SKILL.md` | Bug-fix an toàn, tự soi diff bằng mh_scan, route business-Q → open-questions | — | — |
| `.claude/skills/mh-implement/SKILL.md` | Feature-dev shift-left (nạp convention trước khi code) — *ngoài plan, bonus* | — | — |
| `.claude/agents/mh-implementer.md` | Implementer subagent (1 scope/worktree) cho mh-implement/mh-fix — *ngoài plan, bonus* | — | — |
| `harness/pending/CONVENTIONS.fixed.md` | **Staging** bản CONVENTIONS.md đã sửa 6 lỗi (chờ áp qua PR) | D1–D6 | — |
| `harness/plans/mh-harness-from-be-audit-plan-2026-06-15.md` | Plan đầy đủ | — | — |
| `~/.claude/.../memory/be-conventions-doc-drift.md` | Memory: CONVENTIONS.md sai, agent-rules là canon | D1–D6 | — |

### 1.2 File SỬA (chỉ thêm, giữ nội dung cũ)

| Path | Thêm gì |
|---|---|
| `.claude/hooks/myhospital_guard.py` | Tầng **advisory worktree** (WARN, không block — vá "guard chết ở worktree"). Refactor `_parse`/`_file_path`. Self-test 46/46 (18 block · 20 allow · 8 advisory) |
| `scripts/harness_doctor.py` | 3 check mới: `mh-scan:selftest`, `convention-truth`, `opencode-guard` + đăng ký vào `main()` |
| `justfile` | Target `mh-scan`, `convention-truth` |
| `harness/review/protocol.md` | **Step 2.0** — chạy `mh_scan` trước fan-out, inject candidate-list theo dimension cho reviewer (đòn nâng recall → hội tụ) |
| `harness/review/checklist.md` | Known-bug-classes += audit (D2/D4/D5/D6/D7), tag `[scanner:id]` vs `[manual]` + exemplar |
| `.claude/agents/myhospital-rule-auditor.md` | Bước đầu chạy `mh_scan` lấy baseline deterministic |
| `MEMORY.md` | Pointer tới memory mới |

### 1.3 13 scanner (mỗi cái = 1 bug-class audit)

`auth_coverage`(V1·BLOCK·D6) · `missing_hospital_scope`(V2·HIGH·D5) · `error_code_literal`(V3·HIGH·D2) · `legacy_listing`(V4·WARN·D2) · `new_transaction`(V6·WARN·D5, có allowlist legacy) · `hard_delete`(V10·INFO·D5) · `raw_exception`(V12·HIGH·D4) · `swallow_catch`(V11·WARN·D4) · `contract_dict`(V13·WARN·D7) · `redundant_softdelete`(V9·INFO·D5) · `manual_codegen`(V15·WARN·D2) · `magic_status`(V16·INFO·D2) · `fat_api`(V8·WARN·D2).

Live scan BE khớp audit: error_code_literal=12 (chính xác), auth BLOCK=38 (gồm DiagnosticsApi), raw_exception=5, redundant_softdelete=404, contract_dict=25, hard_delete=14.

---

## 2. Kiến trúc — các mảnh nối nhau thế nào

```
                    BE audit (V1–V16, D1–D6)
                            │
        ┌───────────────────┼────────────────────┐
        ▼                   ▼                     ▼
  scripts/mh_scan      convention_truth      CONVENTIONS.fixed.md
  (sàn deterministic)  (doc drift)           (staging → PR)
        │                   │                     │
   ┌────┼─────────┬─────────┴──────┐              │
   ▼    ▼         ▼                ▼              ▼
 mh-review    rule-auditor   guard(advisory)  harness_doctor
 (Step2.0     (baseline)     (worktree WARN)  (3 check mới)
  candidate)
        │
   recall↑ → hội tụ ≤3 vòng (memo review-harness-feasibility)

  Lifecycle skills: mh-scaffold (template) · mh-implement (feature)
                    · mh-fix (bug) · mh-review (audit)
                    ↳ mh-implementer (subagent thực thi)
```

Routing convention (memo §10.3): bug-class cơ học → **mh_scan** (free, mãi mãi) → feed review + auditor + guard. Doc sai → **convention_truth**. Cả hai vào `harness_doctor` để giám sát.

---

## 3. Kết quả validation (đã chạy thật)

```
harness_doctor:  39 OK · 1 WARN · 0 FAIL · 3 INFO
  mh-scan:selftest      OK — all 34 cases passed
  guard-selftest        OK — all 46 cases (18 block, 20 allow, 8 advisory)
  convention-truth      WARN — DOC DRIFT 4 FAIL (đúng: CONVENTIONS.md chưa vá)
  opencode-guard        OK — installed
convention_truth (standalone): 4 FAIL = prefix/settingkeys/actions/ts-endpoints (= audit D1–D4)
mh_scan live BE: 38 BLOCK, 38 HIGH, 364 WARN, 430 INFO
```

WARN duy nhất = `convention_truth` đang **đúng việc**: phát hiện CONVENTIONS.md chưa được vá (mục 4.1). Sẽ xanh sau khi áp staging patch.

---

## 4. CHƯA hoàn thành

### 4.1 Cần BẠN (đụng main repo — không tự làm được)

1. **Áp `harness/pending/CONVENTIONS.fixed.md` → `myhospital-be/CONVENTIONS.md`** qua worktree docs-only + PR (cấm sửa BE trực tiếp). 6 sửa: prefix MV/CS/DI/BI/IV/RC/AP/RF (D1), SettingKeys path (D2), endpoint /types (D3), action CanInsert bỏ CanCreate/CanApprove (D4), GetByIdAsync (D5), transaction nuance (D6). Sau đó `python scripts/convention_truth.py` → 0 FAIL.
2. **Vá auth (V1)** — mh_scan thấy **38 endpoint thiếu `[RequireAuth]`**; nặng nhất `DiagnosticsApi` (11, không auth tầng nào) + `PaymentMerchantConfigApi` (4, giữ credential cổng TT). Triage: whitelist bớt cái public-by-design (sửa `AUTH_WHITELIST` trong `scanners.py`), thêm `[RequireAuth]` cho phần còn lại trong BE worktree.

### 4.2 Deferred (plan đánh optional — cần FE/BE PR hoặc CI)

3. **C4 Roslyn auth analyzer** — biến V1 thành lỗi `dotnet build` (mạnh nhất). Chưa làm: cần project BE. Scanner `auth_coverage` + CI đủ tạm.
4. **D2 ESLint FE rule pack** — tương đương deterministic cho FE. Chưa làm: cần FE repo.
5. **D1 GitHub Actions gate** — `.github/workflows` hiện = none. Primitive đã sẵn: `python scripts/mh_scan --fail-on block` (exit 1). Chỉ cần thêm 1 workflow gọi nó — quyết định của bạn.

### 4.3 Cần review/dọn (phát sinh trong lúc build)

6. **`mh-implement` (skill) + `mh-implementer` (agent) + mở rộng FE của `mh-scaffold`** xuất hiện ngoài plan gốc (plan chỉ có mh-scaffold + mh-fix). Là bonus phủ lifecycle tốt, NHƯNG: `mh-scaffold` (template) và `mh-implement` (feature flow) **chồng nhau một phần** — nên đọc lại 2 file, quyết giữ cả hai (bổ trợ) hay gộp. Chưa kiểm sâu nội dung 2 file này.
7. **A2 gộp precedence** (CONVENTIONS.md → con trỏ mỏng, agent-rules = canon duy nhất): mới làm phần "sync up" (staging patch) + memory ghi canon. Việc **rút gọn CONVENTIONS.md thành pointer** = quyết định của bạn (mục 5).
8. **Tinh chỉnh false-positive scanner:** `fat_api`=182, `redundant_softdelete`=404, `magic_status`=12 là INFO/WARN hơi ồn. Dùng vài vòng `mh-review` rồi siết `classify`/allowlist nếu nhiễu. `missing_hospital_scope`=21 là *candidate* — reviewer D5 phải xác nhận entity là `:Base` (đã ghi rõ trong scanner + checklist).

---

## 5. Quyết định mở (chờ bạn chọn)

1. **CONVENTIONS.md:** gộp thành con trỏ (agent-rules = canon duy nhất) hay giữ 2 doc đồng bộ? (khuyến nghị: gộp — hết drift vĩnh viễn).
2. **CI:** thêm GitHub Actions chạy `mh-scan --fail-on block` + `convention_truth --strict` không? (hiện chưa có CI nào).
3. **mh-scaffold vs mh-implement:** giữ cả hai hay gộp?
4. **Guard worktree:** hiện WARN-only (an toàn). Có muốn nâng vài pattern (vd auth-missing) thành BLOCK cứng ở worktree không? (rủi ro false-positive trên legacy).

---

## 6. Cách dùng ngay

```fish
just mh-scan                                   # quét toàn BE
just mh-scan --only auth_coverage --format md  # chỉ lỗ hổng auth (V1)
python scripts/mh_scan --fail-on block         # CI gate (exit 1 nếu có BLOCK)
just convention-truth                          # drift doc↔code
just doctor                                    # health (gồm 3 check mới)
```
- `/mh-review` — giờ tự chạy mh_scan trước fan-out (recall↑).
- `/mh-implement` — build feature shift-left; `/mh-fix` — sửa bug, tự soi diff; `/mh-scaffold` — lấy template chuẩn.
- Guard tự nhắc (ADVISORY) khi edit worktree dính pattern audit; không chặn.

---

## 7. Index file liên quan

- Audit gốc: `velvet/notes/myhospital-be-conventions-audit-2026-06-15.md`
- Plan: `harness/plans/mh-harness-from-be-audit-plan-2026-06-15.md`
- Staging fix: `harness/pending/CONVENTIONS.fixed.md`
- Scanner: `scripts/mh_scan/scanners.py` · Doc-truth: `scripts/convention_truth.py`
- Memo hội tụ (nền tảng review): `harness/notes/review-harness-feasibility-2026-06-16.md`
- Canon convention: `harness/rules/backend|frontend-rules-conventions-patterns.md`
- Memory: `be-conventions-doc-drift`, `review-harness-convergence`
