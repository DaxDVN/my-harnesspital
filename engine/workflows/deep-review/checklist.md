# Review Checklist — 10 chiều (cross-tool, maturing)

> Đăng ký các **chiều review** cho `mh-review`. Mỗi audit phân vùng theo file này (1 chiều = 1 reviewer). Đây là **rule fabric sống**: mỗi vòng học (protocol §7) bồi thêm vào "Known bug-classes" → recall tăng dần. Dùng cùng [protocol.md](./protocol.md) + [findings-schema.md](./findings-schema.md).
>
> **Deterministic floor:** `python scripts/mh_scan --scope <paths> --format json` (hoặc `--format md|summary`) chạy trước mỗi audit (protocol §3 Step 2.0) và nạp hits vào reviewer prompt. Các `[scanner:<id>]` dưới đây là những gì scanner bắt được tự động.

## Cách dùng

- Reviewer mỗi chiều: chỉ nạp **Sources** của chiều mình + lát scope → giữ token bounded.
- **Tier** = model khuyến nghị (Haiku/Sonnet/Opus) theo độ cần suy luận. Orchestrator override khi cần.
- **Applies-to** quyết định chiều có chạy trên scope không (FE/BE/both + glob). Không áp dụng → đánh `N/A` trong ledger.

## ⚠️ Staleness — đọc trước khi tin Sources

Một số convention docs đã **stale** (memory `fe-live-conventions-vs-stale-docs`: `ARCHITECTURE-OVERVIEW.md`, `BEST-PRACTICES-NEW-PAGE.md` lỗi thời; graphify Windows-stale). **Quy tắc:** finding BLOCK/HIGH phải neo vào **bằng chứng sống** — tool-hit, spec-decision, hoặc **exemplar `file:line`** trong code đang chạy. Convention doc mâu thuẫn code sống → tin code sống, mở finding "doc stale" mức INFO. Spine FE thật: RQ-via-adapter + useMasterData + id-only + shadcn.

---

## D1 — business-logic · Tier: **Opus**
- **Applies-to:** both (mọi thay đổi chạm luồng nghiệp vụ).
- **Sources:** `specs/<module>/02-requirements.md` (Confirmed), `06-decision-log.md`, `04-traceability.md`, `03-ui.md`.
- **Check:** mỗi Confirmed requirement có implement đúng & đủ? Acceptance criteria thỏa? Logic BHYT/BHTM, admission/inpatient, bed-day, quyết toán, rounding/retry đúng decision đã chốt? Edge nghiệp vụ (chuyển khoa, hủy, trùng) xử lý? Mâu thuẫn spec↔code → finding (không tự quyết nghiệp vụ — route open-question).
- **Known bug-classes:** requirement Confirmed bị implement thiếu nhánh; mockup-implied rule không có trong DOCX (phải thành open-question); tính sai bed-day ranh giới ngày; thiếu idempotency cho create/update quyết toán.

## D2 — be-conventions · Tier: **Sonnet**
- **Applies-to:** BE (`*.cs`, `worktrees/*/be/**`).
- **Sources:** `engine/rules/backend.md` (**CANON** — use this first); `myhospital-be/CONVENTIONS.md` (legacy/superseded — advisory only; known drift in prefixes, SettingKeys, action names, TypeScript endpoints — see `engine/rules/README.md`).
- **Check:** BaseService\<T\> + helper (GetAllByTenant…)? **Không transaction/lock** (write-order + idempotent + derived)? **Không N+1** (load-all + Dictionary lookup)? 1 query/bảng/API? Multi-tenant scope (TenantId+HospitalId)? Soft-delete + audit auto (không set tay)? Listing API declarative (`[FilterField]`, ODataRequest, PagingDataSource\<T\>)? Request DTO `\<Verb\>\<Resource\>Request` + IReturn? `[RequireAuth(...)]` + `[Tag]`? ValidationHelper + BusinessException(ErrorCodes)?
- **Known bug-classes:** N+1 trong loop; `BeginTransactionAsync`/`IProcessLockService` lén; thiếu tenant scope → rò dữ liệu viện khác; set CreatedAt/UpdatedBy tay; endpoint thiếu RequireAuth; `throw Exception` thay BusinessException; `ErrorCodes` string-literal thay vì hằng số `[scanner:error_code_literal]` (ClaudeAnalyzeService.cs:30, PrescriptionHoldService.cs:186); listing API dùng `GetAll`/vòng lặp thay declarative `[scanner:legacy_listing]` (CTApi, MRIApi, XRayApi); API controller quá béo — business logic inline thay service `[scanner:fat_api]` (CashierApi.cs:140); service không có interface (không thể mock/swap) `[manual]` (BedService, Configure.AppHost.cs:94).

## D3 — fe-conventions · Tier: **Sonnet**
- **Applies-to:** FE (`*.ts/*.tsx`, `worktrees/*/fe/**`).
- **Sources:** `engine/rules/frontend.md`, `myhospital-fe/CLAUDE.md`.
- **Check:** server-state qua React Query **adapter** (không `fetch`/`axios` trong UI)? mutation kèm invalidation? dùng EnhancedDataGrid (không tự dựng grid)? **không global state** (Zustand/Jotai/Redux) khi chưa duyệt? **không tính tiền/tồn ở FE**? không permission-fallback logic? form/routing/permission theo rule? id-only props + useMasterData? every visible field/action/surface reuses the existing component or pattern for its semantic role?
- **Known bug-classes:** gọi `fetch`/`axios` trực tiếp `[scanner:mh-no-raw-fetch]` (legacy §6: result-viewers/query-provider/retail-log OK); mutation không invalidate query → UI stale; FE tự cộng tiền/tồn; bypass EnhancedDataGrid; thêm Zustand không xin phép; hard-code chuỗi tiếng Việt (i18n); so master-data theo name/code `=== 'kinh'` thay vì `IsDefault`/flag/Id `[scanner:mh-masterdata-name-compare]` (FE-V3, patient-admin-info-block.tsx:225); form `useForm` thiếu `zodResolver` dù schema tồn tại `[manual]` (FE-V4, ct-page.tsx:189); `serviceStackClient.*` gọi thẳng trong component `[scanner:mh-servicestackclient-in-component]` (ngoại lệ duyệt: inventory-form-sheet.tsx:306); visible UI element implemented with raw HTML/generic `Input`/hand-rolled local logic while a shared or module-local semantic component already exists (examples include date/time, master-data selector, user/product/diagnosis selector, status badge, attachment uploader, confirmation dialog); **CSS grid N-cột cố định + `cell()` trả `null` khi value falsy → cell bị skip, layout xô lệch** — cell helper phải luôn render với fallback `'—'` (exemplar: `bed-context-card.tsx:27-34`, bug-fix 2026-06-20); **checkbox filter group all-unchecked xử lý thiếu** — khi tất cả options unchecked cần nhánh tường minh (show-none hoặc show-all); không được mặc nhiên fall-through như cả-checked (exemplar: `ward-map-page.tsx:192-197`, bug-fix 2026-06-20).

## D4 — correctness · Tier: **Sonnet** (Opus nếu logic rối)
- **Applies-to:** both.
- **Sources:** code sống (đọc kĩ), CodeGraph callers/callees để hiểu invariant.
- **Check:** null/undefined; biên (mảng rỗng, 0, âm, off-by-one); switch/enum đủ nhánh; async/await đúng (race, await sót, promise nuốt lỗi); error-handling (nuốt exception, `return null` che lỗi); rounding tiền; timezone/ngày.
- **Known bug-classes:** `return null` nuốt lỗi (BE pattern flag); await thiếu → race; nhánh enum mới không xử lý; off-by-one ranh giới ngày bed-day; `throw new Exception(...)` thay BusinessException — stack trace lộ internals `[scanner:raw_exception]` (ActiveIngredientService.cs:120); catch block nuốt lỗi hoặc chỉ log mà không rethrow `[scanner:swallow_catch]` (RetailOrderLifecycleService.cs:1108, TemplateService.cs:55).

## D5 — data-access · Tier: **Sonnet**
- **Applies-to:** BE (+ FE nếu query phức tạp).
- **Sources:** `backend.md` (DB&Query), code service quanh entity.
- **Check:** N+1 (chéo D2); transaction boundary (đúng là KHÔNG dùng — kiểm có lén không); GlobalQueryFilter soft-delete không bị bypass (`IgnoreQueryFilters`?); tenant filter không rò; số query/API hợp lý; index/scan lớn.
- **Known bug-classes:** `IgnoreQueryFilters` làm lộ bản ghi đã xóa; query trong vòng lặp; thiếu HospitalId trong filter; query lọc thiếu HospitalId/TenantId trên entity kế thừa Base — data rò giữa các viện `[scanner:missing_hospital_scope]` (DoctorService.cs:92, ProductService.cs:249); `BeginTransactionAsync`/`IProcessLockService` lén `[scanner:new_transaction]`; hard-delete bằng `Remove()`/`ExecuteDeleteAsync` thay soft-delete `[scanner:hard_delete]` (mitigated nếu entity không có DeletedAt — xác nhận); `DeletedAt` set tay thay vì để BaseService/interceptor xử lý `[scanner:redundant_softdelete]`.

## D6 — security-pii · Tier: **Sonnet**
- **Applies-to:** both.
- **Sources:** `backend.md` (auth), code logging.
- **Check:** **không log** số thẻ BHYT / CCCD / mã bệnh nhân / payload hồ sơ (HIS PHI); endpoint không `[AllowAnonymous]` nhầm; authz đúng function/action; không injection (SQL string-concat, dynamic); không lộ secret/connection string; không trả field nhạy cảm thừa trong DTO.
- **Known bug-classes:** `Console.WriteLine`/logger in mã BN; `[AllowAnonymous]` sót; nối chuỗi SQL; trả cả entity thay vì DTO; endpoint thiếu `[RequireAuth(...)]` hoàn toàn (không có cả `[AllowAnonymous]` — có thể là quên, không phải chủ ý) `[scanner:auth_coverage]` (DiagnosticsApi.cs, PaymentMerchantConfigApi.cs).

## D7 — contract-dto · Tier: **Haiku→Sonnet**
- **Applies-to:** both (ranh giới FE↔BE).
- **Sources:** `08-api.md`, generated files list (guard hook), `myhospital-fe/CLAUDE.md`.
- **Check:** **không sửa tay** file generated (`generated-dtos.ts`, `generated-api-client.ts`, `Constants.ts`, EF migrations) — phải regen (`npm run dtos:update`/`client:generate`); FE client khớp BE DTO sau đổi contract; shape request/response khớp `08-api`; breaking change có cập nhật cả 2 phía.
- **Known bug-classes:** hand-edit generated DTO (guard chặn nhưng vẫn kiểm); đổi BE DTO mà quên regen FE; FE gọi field BE đã đổi tên; dùng `Dictionary<string, object>` trong DTO/request/response thay typed property — phá contract type-safety `[scanner:contract_dict]` (SettingApi.cs:50, PortalPublishResult.cs:17); codegen file bị sửa tay dù không phải generated path `[scanner:manual_codegen]`; import path chết `@/lib/dtos/dtos` (đúng: `@/lib/dtos/generated-dtos`, vỡ build) `[scanner:mh-dead-dtos-import]` (FE-V1, HIGH, examination-context.tsx:4).

## D8 — tests-traceability · Tier: **Sonnet**
- **Applies-to:** both.
- **Sources:** `09-test-cases.md`, `04-traceability.md`, `10-plan.md`.
- **Check:** mỗi Confirmed requirement có TC (09) + map trong 04? Code mới có test tương ứng (e2e Playwright nếu FE flow)? Coverage gaps trong 04 đã đóng? T→TC link đủ?
- **Known bug-classes:** requirement Confirmed không có TC; flow mới không e2e; traceability có orphan (design không gắn requirement).

## D9 — migration-schema · Tier: **Sonnet**
- **Applies-to:** BE (migrations, entities).
- **Sources:** `07-schema.md`, EF migrations dir.
- **Check:** **không sửa tay** migration đã sinh (regen `dotnet ef migrations add`); schema khớp `07`; migration không destructive vô ý (drop column/table mất dữ liệu); cột mới nullable/default an toàn; soft-delete/audit cột chuẩn TrackingBase.
- **Known bug-classes:** hand-edit migration; drop column còn dữ liệu; cột NOT NULL không default trên bảng có data.

## D10 — component-reuse-state · Tier: **Haiku→Sonnet**
- **Applies-to:** FE.
- **Sources:** **CodeGraph** (`codegraph explore` trong `myhospital-fe`) + `frontend.md`. *(catalog `*.generated.md` + `components:index` đã bỏ — không tồn tại trong fe.)*
- **Check:** component đã có trong inventory chưa (tránh trùng lặp)? provider hierarchy đúng? dùng design-system default (shadcn) thay vì tự chế? state đặt đúng tầng? page/sheet/dialog layout follows an existing live-code pattern for the same surface class? CTA-specific create flows preserve the selected document/entity type instead of reintroducing a generic selector?
- **Known bug-classes:** dựng lại component đã có; provider đặt sai tầng; tự style thay vì shadcn default; copy nguyên page warehouse nguyên khối (600+ dòng) thay vì split wrapper+content / context `useState`-only làm data layer `[manual]` (FE audit §4); page/sheet/dialog/list/filter/tab surface copies arbitrary classes instead of matching a live surface-class exemplar; typed CTA opens a form that allows switching to another type even though the module exposes separate create actions; hand-rolled local widget/control instead of existing `src/components/ui/*`, `src/modules/common/*`, or module-local pattern; coverage marked CLEAN without citing at least one live exemplar for each non-trivial widget/layout/action semantic role.

**D3/D10 UI-pattern attestation rule:** for every visible create/edit/filter form in scope, reviewers must include a compact reuse table:
`UI element/surface/action → semantic role → existing exemplar component/pattern (file:line) → actual implementation (file:line) → CLEAN/FINDING`.
If no exemplar was searched or cited, the coverage ledger cell is `UNATTESTED`, not `CLEAN`.

---

## Thêm bug-class mới (vòng học — protocol §7)

Khi đóng module, bug-class mới/tái diễn → thêm 1 dòng vào "Known bug-classes" của chiều đúng (kèm `file:line` exemplar nếu có). Nếu deterministic → ưu tiên đẩy thành guard/ESLint rule trước. Commit thay đổi checklist như code (versioned). Đây là cách harness **vét cạn hơn theo thời gian**.
