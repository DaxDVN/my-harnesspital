# Plan: Biến BE-audit thành bộ skill / agent / rule / scanner cho agentic coding

> **Loại:** Implementation plan (harness engineering)
> **Ngày:** 2026-06-15
> **Nguồn audit (tham chiếu xuyên suốt):** `/home/dax/Documents/arabica/velvet/notes/myhospital-be-conventions-audit-2026-06-15.md`
>   — ký hiệu finding: **Vx** (violation), **Dx** (doc-error) theo đúng file đó.
> **Mục tiêu:** dev/fix an toàn + mượt, và audit/review hiệu quả + hội tụ — bằng cách **nạp audit vào learning-loop mà harness ĐÃ thiết kế sẵn để ăn** (`mh-review/protocol.md §7`, memo `review-harness-feasibility-2026-06-16.md §10.3`) nhưng chưa được cho ăn.
> **Phạm vi sửa:** chỉ harness ở workspace root (`.claude/`, `scripts/`, `harness/rules/`, `specs/`, `justfile`) + một thay đổi nhỏ trong BE repo (`CONVENTIONS.md`) BẮT BUỘC qua worktree. KHÔNG sửa source FE/BE.

---

## 0. Verdict

**CÓ — xây được, và ~85% hạ tầng đã có.** Đây KHÔNG phải dựng harness mới. Review layer đã chín (`mh-review` D1–D10 + `mh-reviewer` + findings-schema + coverage ledger + adversarial verify + learning-loop). Cái thiếu đúng 3 thứ, và cả 3 chính là nguyên liệu mà audit vừa sản xuất:

1. **Sàn deterministic (scanner) — lỗ hổng #1 do chính inventory harness nêu.** Mọi check convention hiện chạy bằng *agent-instruction* hoặc *mh-review*; không có scanner/analyzer/pre-commit cơ học. Memo `§11` tự gọi tên năng lực còn thiếu để bảo đảm hội tụ ≤3 vòng: *"công cụ phủ xác định (Semgrep/CodeQL/test thật)"*. Audit đẻ ra ~12 bug-class cơ học → seed scanner hoàn hảo.
2. **Doc-truth.** `myhospital-be/CONVENTIONS.md` sai 5 chỗ (D1–D6). Nguy hiểm vì **checklist D2 lấy `CONVENTIONS.md` làm nguồn chân lý** (`harness/review/checklist.md:25`) → reviewer sẽ lan truyền lỗi doc (báo `CanInsert` là sai, trích prefix `LK`). Sửa doc-truth là **tiền đề** để review đáng tin.
3. **Prevention ở worktree.** Heuristic BE/FE trong `myhospital_guard.py` chỉ bắn ở **main repo** (`.claude/hooks/myhospital_guard.py:153-157`) — mà main repo cấm sửa → heuristic **chết ở worktree**, nơi dev thật xảy ra.

Tin tốt phát hiện khi khảo sát: **`harness/rules/backend-rules-conventions-patterns.md` là bản song sinh chính xác** của `CONVENTIONS.md` — nó ĐÚNG ở đúng những chỗ `CONVENTIONS.md` sai (action names `:134-135`, prefix `:220`, settingkeys `:219`, transaction-nuance `:198-208`). Vậy phần lớn việc doc-truth là **đồng bộ `CONVENTIONS.md` LÊN theo agent-rules doc**, không phải viết lại.

---

## 1. Cái đã có (build-on, không dựng trùng)

| Lớp | Artifact | Trạng thái |
|---|---|---|
| Review orchestrator | `.claude/skills/mh-review/` (SKILL+protocol+checklist D1–D10+findings-schema+workflow.js) | Chín. ≤3-vòng, partition, adversarial verify, coverage ledger, learning-loop §7 |
| Per-dimension reviewer | `.claude/agents/mh-reviewer.md` (sonnet, read-only) | Chín. Con của mh-review |
| Quick-check agent | `.claude/agents/myhospital-rule-auditor.md` (haiku, standalone, BLOCK/WARN/OK) | Chín. Tách khỏi mh-review |
| Enforcement runtime | `.claude/hooks/myhospital_guard.py` (25 rule, fail-open, payload-tolerant) | Chín. Wired: Claude `settings.json` (Bash\|Write\|Edit), Codex `.codex/hooks.json` (Bash), opencode (symlink tay) |
| Rule fabric | `harness/rules/backend\|frontend-rules-conventions-patterns.md` (398/538 dòng, BLOCK/WARN, §316 "Automated Review Guardrails", §348 "Known Legacy Exceptions") | Chín + **chính xác hơn `CONVENTIONS.md`** |
| Dev-convention (BE repo) | `myhospital-be/CONVENTIONS.md` | **Drift — 5 lỗi (D1–D6)** |
| Health/ops | `scripts/harness_doctor.py`, `harness_backup.py`, `migrate_harness.py`, `worktree.py` | Chín |
| Spec scaffolding | `specs/_TEMPLATE/` (16 file) + 4 module sống | Có; **spec-session skills chưa build** |

**Lỗ hổng (inventory tự nêu):** (1) không scanner/analyzer cơ học, (2) không CI build/test gate, (3) không convention-truth/drift detector, (4) reuse-catalog không ở harness, (5) spec-session skills chưa có, (6) opencode guard chưa auto-install, (7) `worktree.py` chưa có `rebase`.

---

## 2. Chiến lược — 3 trụ (map thẳng vào lỗ hổng)

```
         AUDIT (velvet/notes/...-2026-06-15.md)
                       │  mỗi finding → lớp rẻ nhất (memo §10.3)
   ┌───────────────────┼───────────────────────┐
   ▼                   ▼                         ▼
TRỤ A Doc-truth   TRỤ B Sàn deterministic   TRỤ C Prevention
(gap 3 + D1-D6)   (gap 1+2 — KEYSTONE)      (guard worktree + scaffold)
   │                   │                         │
   └──────────► TRỤ D Learning-loop wiring ◄──────┘
        (checklist Known-bug-classes += audit; protocol §7)
```

**Nguyên tắc routing (memo §10.3):** mỗi finding đẩy xuống lớp RẺ NHẤT bắt được nó: **deterministic (scanner/guard) > convention doc > checklist dimension > memory.** Deterministic = bắt miễn phí mãi mãi + nâng recall mh-review (đưa scanner-hit làm *candidate list* cho reviewer thay vì grep mù) → đây chính là đòn hội tụ ≤3 vòng memo `§9/§11` đòi.

**Cross-tool:** mọi scanner là Python thuần + `rg`/`ast-grep` (giống guard) → Claude/Codex/opencode dùng chung, không phụ thuộc tool.

---

## 3. TRỤ A — Doc-truth (P0, rẻ nhất, ROI cao nhất)

Sửa lỗi doc + chặn drift tái diễn. Vì D2 review tin `CONVENTIONS.md`, đây là tiền đề.

**A1 — Sửa `myhospital-be/CONVENTIONS.md` (5 lỗi).** Map từ audit:
- §5 prefix table (audit **D1/V5**): LK/CL/CDHA/TT/BL/TU/PC → **MV/CS/DI/BI/IV/RC/AP/RF**; ghi prefix sống ở `static CodePrefix` trên entity + `CodePrefixRegistry.cs`, KHÔNG ở `CodePrefixes.cs`.
- §4 SettingKeys (audit **D2**): `Commons/SettingKeys.cs` → `Constants/Commons.cs` (class `SettingKeys`) + `*SettingKeys.cs` per-module.
- §8 endpoint (audit **D3**): `/types/typescript` = DTO (NativeTypes); `/types/typescript-types` = `Utilities.Types`; `/types/typescript-const` = constants+ErrorCodes.
- §7.2 action (audit **D4**): `CanView/CanInsert/CanUpdate/CanDelete/CanImport/CanExport/CanShare`; bỏ `CanCreate`/`CanApprove`.
- §1.5 helper (audit **D5**): `GetByIdInTenantAndHospital` → `GetByIdAsync`.
- §1.1 transaction (audit **D6/V6**): đổi "tuyệt đối cấm" → khớp agent-rules `:198-208` ("cấm transaction MỚI; legacy inventory/prescription được phép; warn khi đụng").
> ⚠️ `CONVENTIONS.md` ở **trong BE repo** → sửa qua **worktree docs-only** rồi PR (đúng kỷ luật "no direct edit myhospital-be"). KHÔNG sửa thẳng.

**A2 — Gộp precedence (khuyến nghị mạnh).** `harness/rules/backend-rules-conventions-patterns.md` đã là canon chính xác + có Source-of-Truth Hierarchy `§23`. Rút gọn `myhospital-be/CONVENTIONS.md` thành **con trỏ mỏng** ("quickref; nguồn chân lý đầy đủ = harness agent-rules; file này có thể lag") → diệt vĩnh viễn drift hai-doc, tránh sửa BE repo lặp lại. Sửa `checklist.md:25` để D2 nguồn = agent-rules doc (canon) trước, `CONVENTIONS.md` chỉ tham khảo.

**A3 — `convention_truth.py` (gap 3, chống drift tái diễn).** Script đối chiếu *claim trong doc* vs *code sống*: prefix table, action constants (`Functions.cs:312-318`), settingkeys path, `/types/*` route (`Configure.AppHost.cs`), `.NET` version. Xuất PASS/FAIL như `harness_doctor`. Đây là biến **audit-finding #1 thành check định kỳ**. Wire vào `harness_doctor.check_convention_truth`.

**A4 — Memory.** `type: project` — "CONVENTIONS.md drifted; agent-rules doc là canon; prefix=MV/CS/DI/..." → mọi phiên sau không bị doc dẫn sai.

---

## 4. TRỤ B — Sàn deterministic (P1, KEYSTONE)

**`scripts/mh_scan/`** — bộ scanner cơ học, mỗi cái = 1 bug-class audit. Python + `rg`/`ast-grep`. Xuất **findings-schema JSON** (khớp `harness/review/findings-schema.md`).

### 4.1 Bộ scanner (map thẳng audit Vx)

| Scanner | Audit ref | Mẫu phát hiện (đã verify trong pre-scan audit) | Severity | FP-note |
|---|---|---|---|---|
| `scan_auth_coverage` | **V1** 🔴 | mọi DTO `IReturn<>`/`[Route]` thiếu `[RequireAuth]`/`[Authenticate]` & ngoài whitelist (IPN/LIS/health) | BLOCK | whitelist file |
| `scan_error_code_literal` | **V3** | `new BusinessException("…"` (literal, không `ErrorCodes.`) | HIGH | — |
| `scan_legacy_listing` | **V4** | caller `ParseStringEquality\|ParseBooleanEquality\|ParseNumericEquality\|ParseContains\|ParseInOperator\|ExtractDateFilter` | WARN | reference Cashier/Invoice = clean |
| `scan_new_transaction` | **V6** | `BeginTransactionAsync\|TransactionScope` ngoài allowlist legacy (PrescriptionHold/BatchAdjustment/Transfer/LisResult/PrescriptionMgmt) | WARN→BLOCK(new) | allowlist 5 file |
| `scan_hard_delete` | **V10** | `Db.Remove(`/`.RemoveRange(` | INFO | mitigated bởi SaveChangesAsync; chỉ flag |
| `scan_raw_exception` | **V12** | `throw new Exception(` | HIGH | bỏ comment |
| `scan_swallow` | **V11** | `catch{}` rỗng / `catch(){return null}` (ast-grep) | WARN | parse-fallback = OK |
| `scan_contract_dict` | **V13** | `Dictionary<string,object>`/`dynamic` trong field DTO `*Request/*Response` (MyHospital.Apis) | WARN | internal = OK |
| `scan_redundant_softdelete` | **V9** | `.Where(...DeletedAt == null)` trừ file filter-def | INFO | nhiễu; auto-INFO |
| `scan_manual_codegen` | **V15** | `Code = $"…"`/`Guid.NewGuid` trong field code (ngoài `CreateUniqueCodeAsync`) | WARN | — |
| `scan_magic_status` | **V16** | `== "Xxx"`/`!= "Xxx"` so status/type literal trong `*Service.cs` | INFO | noisy |
| `scan_fat_api` | **V8** | `Db.` access trong `MyHospital.Apis/*Api.cs` | WARN | — |
| `scan_missing_hospital_scope` | **V2** 🔴 | `Db.<Set>.Where(...TenantId...)` thiếu `HospitalId` (candidate, agent xác nhận) | HIGH | cần biết :Base → agent verify |

### 4.2 IO contract + runner
- `scripts/mh_scan/run.py --scope <files|worktree|module> --format json|md` → một JSON list findings (severity, dimension, location, title, evidence=`scanner:<id>`, rule-ref).
- `just mh-scan` (target mới) chạy toàn bộ, in summary + exit-code (gate-able).

### 4.3 Ba consumer (vì sao keystone)
1. **mh-review (recall↑ → hội tụ):** patch `protocol.md Step 2` — orchestrator chạy `mh-scan` TRƯỚC fan-out, inject **candidate-list theo dimension** vào prompt mỗi `mh-reviewer` ("scanner đã thấy N hit ở D2 đây — confirm/refute + tìm thêm cái scanner bỏ sót"). Reviewer khởi động từ sàn cơ học thay vì grep mù → đúng đòn nâng recall memo `§9`.
2. **Guard/quick-check (shift-left):** `myhospital-rule-auditor` gọi `mh-scan --scope <diff>` → quick-check có sàn deterministic, không đoán.
3. **Gate (P3):** `just mh-scan` trong CI/pre-merge.

### 4.4 `harness_doctor.check_convention_scan`
Thêm check: scanner pack import được + self-test (mỗi scanner có ≥1 fixture block + ≥1 fixture allow, giống guard `--self-test`). Giữ scanner khỏi tự mục.

---

## 5. TRỤ C — Prevention (P2, dev/fix-time)

**C1 — Guard sống ở worktree.** Hiện `edit_rule` heuristic BE/FE chỉ main-repo (`myhospital_guard.py:147-157`) = chết. Thêm tầng **WARN (không block)** cho `worktrees/*/be|fe`: khi Write/Edit khớp mẫu audit (raw Exception, literal error code, new transaction, Db.Remove, Dictionary<string,object> DTO, legacy Parse*) → in nudge "pattern X vi phạm Vx; pattern chuẩn: …; xem agent-rules §". Block-vs-warn: chỉ những cái deterministic-an-toàn (auth-missing, generated-file) mới BLOCK; phần còn lại WARN (tránh false-positive trên legacy hợp lệ — memo R2). Giữ fail-open.

**C2 — Skill `mh-scaffold`.** Emit pattern CHUẨN để chặn V3/V4/V8 từ gốc: `listing-endpoint` (Cashier/Invoice-style: `[FilterField]`+`ODataRequest`+`ParseAllFilters`+`PagingDataSource`+`ApplyPaginationAsync`), `service` (`: BaseService<T>` + `I<Name>` + DI line), `error-path` (`BusinessException`+`ErrorCodes.<Module>` mới), `dto` (typed + DataAnnotations + `[RequireAuth]`). Mỗi scaffold trích đúng exemplar `file:line` từ code sống.

**C3 — Skill `mh-fix`.** Companion an toàn cho bug-fix (protocol §Round2 có nhắc nhưng chưa có skill riêng): đọc 1 finding/bug → research fix trong worktree → **tự-review-diff bằng `mh-scan` + checklist liên quan** trước khi đóng (diệt regression — memo §9 FIX). Route câu hỏi nghiệp vụ → `05-open-questions.md` (không tự quyết).

**C4 — Roslyn analyzer auth (tùy chọn, mạnh nhất).** `RequireAuthCoverageAnalyzer` báo compile-warning mọi DTO `IReturn<>` thiếu `[RequireAuth]` ngoài whitelist — biến V1 thành lỗi build-time. Đắt hơn scanner; chỉ làm nếu BE team muốn gate ở `dotnet build`. Scanner `scan_auth_coverage` đủ cho review/CI trước.

---

## 6. TRỤ D — Learning-loop wiring (P0, gần như free)

Đẩy audit vào `checklist.md` "Known bug-classes" (file tự mời — mục cuối). Mỗi dòng kèm exemplar `file:line` từ audit:
- **D2 be-conventions** += literal error code (`PrescriptionHoldService.cs:186`), legacy Parse* (`CTApi/MRIApi/...`), fat-Api (`CashierApi.cs:140`), service thiếu interface (`BedService`).
- **D4 correctness** += swallow `SaveChangesAsync` (`RetailOrderLifecycleService.cs:1108`), Console+return null (`TemplateService.cs:55`).
- **D5 data-access** += thiếu HospitalId (`DoctorService.cs:92`, `ProductService.cs:249`).
- **D6 security-pii** += endpoint không auth (`DiagnosticsApi.cs`, `PaymentMerchantConfigApi.cs`).
- Ghi rõ cái nào ĐÃ có scanner (deterministic) để reviewer khỏi tốn attention.

---

## 7. Catalog artifact (master)

| ID | Artifact | Loại | Audit ref | Consumer | Nơi đặt | Effort | Risk |
|---|---|---|---|---|---|---|---|
| A1 | Sửa CONVENTIONS.md 5 lỗi | doc | D1-D6 | dev+D2 | **BE worktree→PR** | S | thấp |
| A2 | Gộp precedence (CONVENTIONS→pointer) | doc | D1-D6 | mọi agent | harness+BE | S | thấp |
| A3 | checklist Known-bug-classes += audit | doc | V1-V16 | mh-reviewer | harness | S | thấp |
| A4 | memory doc-drift | memory | D1-D6 | mọi phiên | memory | XS | thấp |
| B1 | `scripts/mh_scan/` (~13 scanner) | code | V1-V16 | review+guard+CI | harness | **L** | TB (FP tuning) |
| B2 | runner + `just mh-scan` | code | — | CLI/CI | harness | M | thấp |
| B3 | `convention_truth.py` | code | D1-D6 | doctor | harness | M | thấp |
| B4 | doctor checks (scan+truth) | code | — | doctor | harness | S | thấp |
| B5 | protocol Step2 inject scanner candidate-list | doc | — | mh-review | harness | S | thấp |
| B6 | rule-auditor gọi mh-scan | doc/code | — | quick-check | harness | S | thấp |
| C1 | guard worktree WARN | code | V3/4/6/10/12/13 | dev-time | harness | M | TB (FP) |
| C2 | skill `mh-scaffold` | skill | V3/V4/V8 | implementer | harness | M | thấp |
| C3 | skill `mh-fix` | skill | — | fix-session | harness | M | thấp |
| C4 | Roslyn auth analyzer | code | V1 | dotnet build | BE (opt) | L | TB |
| D1 | CI/just build+test+scan gate | ci | — | pre-merge | harness/CI | M | thấp |
| D2 | ESLint FE rule pack | code | (FE-eq) | dev-time | FE (opt) | M | TB |
| D3 | doctor check opencode-guard install | code | — | doctor | harness | S | thấp |

---

## 8. Phasing + thứ tự cắt

| Pha | Gồm | Hạ tầng mới | Tại sao trước |
|---|---|---|---|
| **P0 — Now (doc + loop)** | A1 A2 A3 A4 D-wiring | 0 | Gỡ coupling "D2 tin doc sai"; gần-free; chặn lan lỗi ngay |
| **P1 — Sàn deterministic** | B1 B2 B3 B4 B5 B6 | 0 (Python+rg sẵn) | KEYSTONE: bắt free + nâng recall review = đòn hội tụ |
| **P2 — Prevention** | C1 C2 C3 (C4 opt) | Roslyn nếu C4 | Shift-left: chặn từ gốc, giảm finding tương lai |
| **P3 — Gate/cross-tool** | D1 D2 D3 | CI (chưa có) | Tự động hóa cuối; FE parity; opencode install |

**Thứ tự cắt nếu hẹp:** bỏ P3 → C4 → D2 trước. **KHÔNG bao giờ cắt P0 + B1/B3** (doc-truth + sàn deterministic = thứ trực tiếp tạo an toàn & hội tụ — khớp memo §12 "không bao giờ bỏ coverage ledger + provenance").

**Hiệu lực kỳ vọng:** P0 xong → review hết tin doc sai. P1 xong → ~12 bug-class audit thành deterministic (bắt mỗi lần, free) + recall mh-review tăng → số vòng giảm (memo §9). P2 → implementer ít đẻ vi phạm. P3 → gate.

---

## 9. Scope, an toàn, nơi-đặt-edit

- **Harness root** (`.claude/`, `scripts/`, `harness/rules/`, `specs/`, `justfile`): sửa trực tiếp — KHÔNG phải main repo, không cần worktree.
- **`myhospital-be/CONVENTIONS.md`** (A1/A2): **trong BE repo** → BẮT BUỘC worktree docs-only + PR. Không sửa thẳng (kỷ luật AGENTS.md).
- **C4 Roslyn / D2 ESLint**: source FE/BE → worktree + PR.
- Forbidden Actions vẫn áp: không git commit/push tự ý, không rm -r, không sửa generated. Scanner/skill là **read-only/advisory** — không auto-fix, không auto-merge (khớp mh-review Safety + memo §8).
- Mọi scanner **fail-open** như guard: lỗi scanner không được wedge session.

---

## 10. Quyết định mở (cần chủ harness chọn)

1. **A2 precedence:** gộp `CONVENTIONS.md` → pointer (khuyến nghị) HAY giữ 2 doc đồng bộ tay? (gộp = hết drift vĩnh viễn nhưng đổi thói quen dev đọc file trong BE repo).
2. **C1 guard worktree:** WARN-only (khuyến nghị, tránh FP trên legacy) HAY BLOCK cứng vài pattern (auth-missing)?
3. **C4 Roslyn:** làm build-time analyzer (mạnh, đắt) hay scanner+CI đủ?
4. **D1 CI:** dựng GitHub Actions build/test/scan gate (hiện `.github/workflows` = none) hay chỉ `just` local?
5. **Thứ tự bắt tay:** bắt đầu P0 ngay (doc + checklist, rẻ) hay P1 trước (scanner, ROI cao nhất)?

> Khuyến nghị mặc định nếu không chỉ định khác: **P0 → P1**, A2 = gộp, C1 = WARN, C4 = hoãn, D1 = `just` local trước.

---

### TL;DR
Harness đã có review-engine chín + rule fabric + guard. Thiếu **sàn deterministic** (lỗ #1) + **doc-truth** (CONVENTIONS.md sai 5 chỗ, mà D2 lại tin nó) + **guard sống ở worktree**. Plan = **nạp 16 finding audit vào learning-loop sẵn có**: P0 sửa doc + bồi checklist (free), P1 dựng `scripts/mh_scan/` (12 scanner = 12 bug-class audit) làm sàn cho cả review-recall lẫn shift-left guard, P2 scaffold/fix-skill chặn từ gốc, P3 gate. Mọi thứ ở harness root (sửa trực tiếp) trừ `CONVENTIONS.md` (worktree+PR). Không auto-fix, không sửa main repo.
