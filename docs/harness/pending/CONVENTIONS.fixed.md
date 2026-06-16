```
> STAGING — corrected CONVENTIONS.md. Apply to myhospital-be via a docs-only worktree + PR
> (never edit myhospital-be directly). Source of corrections: BE audit 2026-06-15 (D1–D6).
> After applying, `python scripts/convention_truth.py` should report 0 FAIL.
```

# MyHospital Backend — Coding Conventions

> Tài liệu này tổng hợp các rule **bắt buộc tuân thủ** khi code trong project. PR vi phạm các mục **MUST** sẽ không được merge.

---

## 1. Database & Query — MUST

### 1.1 Hạn chế transaction và locking
Project **không tạo transaction mới** và **không tạo lock mới**. Thay vào đó phải thiết kế:
- **Write order strategy**: ghi cái quan trọng nhất trước (vd: `Billing` → `Service` → `BillingItem` → `VisitCount`)
- **Idempotent operations**: chạy lại nhiều lần kết quả không đổi
- **Derived/computed values**: tính tại query time, không lưu duplicate (vd: `TotalAmount` tính từ `BillingItem` thay vì lưu vào `Billing`)

> **Ngoại lệ legacy**: một số path inventory/prescription có `BeginTransactionAsync` có chủ đích và comment lý do atomicity (PrescriptionHoldService, BatchAdjustmentService, TransferService, LisResultService, PrescriptionManagementService). **BLOCK** thêm transaction/lock mới; **WARN** khi chạm vào các path legacy này.

### 1.2 No N+1 queries
**KHÔNG** được query trong vòng lặp. Pattern bắt buộc:
```csharp
// ❌ SAI
foreach (var id in ids)
{
    var item = await Db.Items.FirstOrDefaultAsync(x => x.Id == id);
    ...
}

// ✅ ĐÚNG
var items = await Db.Items.Where(x => ids.Contains(x.Id)).ToListAsync();
var byId = items.ToDictionary(x => x.Id);
foreach (var id in ids)
{
    var item = byId.GetValueOrDefault(id);
    ...
}
```

### 1.3 Mỗi bảng chỉ query 1 lần / API
Trong 1 endpoint, **mỗi bảng chỉ được hit 1 lần**. Load tất cả data cần thiết trong 1 query, dùng `Dictionary`/`HashSet` để lookup trong memory.

### 1.4 Soft-delete tự động — đừng filter thủ công
Global Query Filter trong `MyHospitalContext.OnModelCreating` đã tự lọc `DeletedAt == null` cho mọi entity kế thừa `TrackingBase`. **Không cần** viết:
```csharp
// ❌ DƯ THỪA — Global Filter đã handle
Db.Shifts.Where(s => s.DeletedAt == null)

// ✅ ĐỦ
Db.Shifts
```
Khi cần lấy cả record đã xoá, dùng `.IgnoreQueryFilters()`.

### 1.5 Multi-tenant scoping
Mọi entity kế thừa `TenantBase` **bắt buộc** scope theo `TenantId + HospitalId`. Dùng helper từ `BaseService<T>`:
```csharp
var query = GetAllByTenantAndHospital();          // IQueryable đã scope
var entity = await GetByIdAsync(id);              // single
```
**KHÔNG** query trực tiếp `Db.Shifts.Where(...)` mà bỏ qua tenant scope.

### 1.6 Audit trail tự động
`TrackingBase` đã tự handle `CreatedAt`, `UpdatedAt`, `CreatedBy`, `UpdatedBy`, `DeletedAt`. **Không tự viết** audit code.
- Soft-delete: dùng `DeleteAsync<T>(entity)` / `DeleteRangeAsync` từ `BaseService`
- Không xoá thật bằng `Db.Remove(...)` trừ khi entity không kế thừa `TrackingBase`

---

## 2. API Design — MUST

### 2.1 Listing API: pattern canonical (CashierApi/InvoiceApi)
Tất cả listing API **bắt buộc** theo pattern declarative:

```csharp
[FilterField(F.Q, FilterType.String)]
[FilterField(F.Status, FilterType.Enum, "EnumSourceName")]
[Route("/resource", "GET")]
[RequireAuth(Functions.FunctionNames.X, Functions.Actions.CanView)]
public class GetResourceListRequest : ODataRequest, IGet, IReturn<PagingDataSource<ResourceListItem>>
{
    public static class F
    {
        public const string Q = "q";
        public const string Status = "Status";
    }
}
```

Trong service:
```csharp
public async Task<PagingDataSource<ResourceListItem>> Get(GetResourceListRequest request)
{
    var f = request.ParseAllFilters();
    var q = f.GetString(F.Q);
    var status = f.GetString(F.Status);
    // ... build query, apply ApplyPaginationAsync
    return new PagingDataSource<ResourceListItem> { Count = total, ListOfObject = items };
}
```

**KHÔNG** dùng pattern manual `request.ParseStringEquality(...)` (legacy). Reference:
- `MyHospital.Apis/CashierApi.cs`
- `MyHospital.Apis/InvoiceApi.cs`

### 2.2 Pagination
- **Bắt buộc** trả `PagingDataSource<T>` với `Count` (tổng số record) + `ListOfObject` (page hiện tại)
- Dùng `request.Skip`, `request.Top` từ `ODataRequest`
- Giới hạn `Top` tối đa nên check ở base, không cho client request unbounded

### 2.3 Detail API
- Trả thẳng entity/DTO (không wrap `PagingDataSource`)
- Khi không tìm thấy → **throw** `BusinessException` với `ErrorCodes.X.NotFound`, **không** trả `null`/`404` thủ công

### 2.4 Response wrap
`StandardResponsePlugin` tự wrap mọi response thành `{ Code, Message, Data }`. **KHÔNG** wrap thủ công.

---

## 3. Error Handling — MUST

### 3.1 Dùng BusinessException + ErrorCodes
```csharp
// ❌ SAI
throw new Exception("Không tìm thấy bệnh nhân");
return null;

// ✅ ĐÚNG
throw new BusinessException(ErrorCodes.Patient.NotFound, "Không tìm thấy bệnh nhân");
```

### 3.2 ErrorCodes phải khai báo constant
Mọi error code đặt trong `MyHospital.Utilities/Constants/ErrorCodes.cs` theo nhóm (Cashier, Patient, Billing...). **Không** truyền string literal vào `BusinessException`.

### 3.3 Không nuốt exception
- Không `try { ... } catch { }` rỗng
- Không `catch (Exception) { return null; }` — để exception bubble lên global handler

---

## 4. Constants — No Magic Strings/Numbers — MUST

Tất cả giá trị cố định phải khai báo constant ở chỗ phù hợp:

| Loại | Vị trí |
|---|---|
| Function/Action permission | `Functions.cs` (`FunctionNames`, `Actions`) |
| Error code | `Constants/ErrorCodes.cs` |
| Setting key (chung) | `Constants/Commons.cs` (class `SettingKeys`) |
| Setting key (per-module) | `Constants/InventorySettingKeys.cs`, `Constants/PrescriptionSettingKeys.cs`, `Constants/PricingSettingKeys.cs` |
| Code prefix | `public static CodePrefix` trên từng entity (xem §5) |
| Status / Enum value | enum class hoặc `Constants/<Module>Status.cs` |
| Filter field name | `static class F` trong DTO request |

Ví dụ:
```csharp
// ❌ SAI
if (shift.Status == "APPROVED") { ... }
var setting = await GetSetting("AllowConflictOverride");

// ✅ ĐÚNG
if (shift.Status == ShiftStatus.Approved) { ... }
var setting = await GetSetting(SettingKeys.AllowConflictOverride);
```

---

## 5. Code Generation — Mã định danh

Dùng `BaseService.CreateUniqueCodeAsync(prefix, ...)` cho mọi mã sinh tự động.

**Prefix sống dưới dạng `public static CodePrefix` (hoặc `CodePrefixes`) trên từng entity class — KHÔNG tập trung trong `CodePrefixes.cs`** (file này chỉ giữ `PNV` cho `InpatientAdmissionOrder`). Toàn bộ bảng prefix được scan tự động bởi `CodeGeneration/CodePrefixRegistry.cs`.

| Entity | Prefix |
|---|---|
| MedicalVisit | `MV` |
| MedicalVisitClinicalService | `CS` |
| MedicalVisitDiagnosticImagingService | `DI` |
| Billing | `BI` |
| Invoice (default) | `IV` |
| Invoice – Receipt | `RC` |
| Invoice – AdvancePayment | `AP` |
| Invoice – RefundVoucher | `RF` |
| InpatientAdmissionOrder | `PNV` (via `Constants/CodePrefixes.cs`) |
| Patient | `PT` (auto, entity-level) |

> Các entity khác (Shift=`SH`, ScheduleRule=`SCH`, CorporatePartner=`CP`, v.v.) đặt prefix trực tiếp trên entity, không liệt kê hết ở đây — tra cứu qua `CodePrefixRegistry.GetAllPrefixes()`.

---

## 6. Service Layer

### 6.1 Kế thừa BaseService<T>
```csharp
public class ShiftService : BaseService<Shift>, IShiftService
{
    // Db, CurrentSession, GetAllByTenantAndHospital, CreateUniqueCodeAsync, ...
    // ApplyPaginationAsync, DeleteAsync<T>(...), DeleteRangeAsync(...) đã có sẵn
}
```

### 6.2 Service nào dùng cross-module → expose interface
- Service được service khác gọi: phải có `I<Name>` interface và register DI
- Service chỉ chứa endpoint handler riêng: không bắt buộc interface

### 6.3 Tách trách nhiệm
- API class (`*Api.cs`): mỏng, chỉ orchestrate request → service
- Service class (`*Service.cs`): chứa toàn bộ business logic
- Mapper riêng (`*Mapper.cs`) khi mapping phức tạp

---

## 7. Authentication & Authorization — MUST

### 7.1 Không tự viết lại auth/authz
- **Authentication**: dùng `MyHospitalCredentialsAuthProvider` + `[Authenticate]` của ServiceStack. **KHÔNG** viết custom auth provider, custom session, hay tự verify token.
- **Authorization**: dùng `[RequireAuth(FunctionNames.X, Actions.Y)]` ở mọi request DTO. **KHÔNG** viết custom attribute hay tự check role/permission trong handler.
- Lấy thông tin user qua `CurrentSession` (`TenantId`, `HospitalId`, `UserId`, `Roles`) — đã có sẵn trong `BaseService`.

### 7.2 Reuse permission có sẵn — đừng đẻ thêm
Trước khi thêm `Function` hay `Action` mới, **bắt buộc**:
1. Rà `Functions.cs` xem đã có function/action phù hợp chưa
2. Action chuẩn (`Functions.Actions`): `CanView`, `CanInsert`, `CanUpdate`, `CanDelete`, `CanImport`, `CanExport`, `CanShare` — **ưu tiên dùng lại**
   > **Lưu ý**: `CanInsert` (không phải `CanCreate`) là action thêm mới. `CanApprove` không tồn tại — approval reuse `CanUpdate` hoặc một `FunctionName` riêng biệt đặc thù nghiệp vụ.
3. Chỉ thêm action/function mới khi:
   - Có quyền nghiệp vụ thực sự khác biệt (vd review ≠ approve về luồng phê duyệt)
   - Đã giải thích trong PR description tại sao không reuse được
   - Đã update seed phân quyền tương ứng

### 7.3 Không bypass authorization
- Không `[AllowAnonymous]` cho endpoint nội bộ
- Không tự kiểm tra `if (session.Roles.Contains("admin"))` trong handler — đặt vào permission system

---

## 8. BE-FE Contract Sync (TypeScript) — MUST

BE và FE **đồng bộ contract** qua 3 endpoint:
- **`/types/typescript`** — ServiceStack NativeTypes: export **tất cả DTO/interface/request/response** (request, response, entity, sub-object). Đây là endpoint chính để FE consume DTO.
- **`/types/typescript-types`** — Custom handler: export utility types từ `MyHospital.Utilities.Types` (typed settings class, shared value objects).
- **`/types/typescript-const`** — Custom handler: export **constants + ErrorCodes** (enum, status, code prefix, setting key, error code).

Hệ quả: **mọi object FE cần biết phải được khai báo dưới dạng C# class/enum/const** ở project — KHÔNG dùng `dynamic`, `JObject`, `Dictionary<string, object>` ở contract layer.

### 8.1 DTO request/response
- Bắt buộc strong-typed class/record. Field optional → nullable (`string?`, `long?`).
- Không dùng `object` cho field trong DTO — define class cụ thể, kể cả khi chỉ có 1–2 field.

### 8.2 Settings dạng JSON
Khi 1 setting được lưu dạng JSON (vd `Setting.Value` chứa object cấu hình), **bắt buộc**:
- Define 1 class C# tương ứng (vd `WorkflowSettings`, `BillingSettings`, ...) ở `MyHospital.Utilities` hoặc module tương ứng
- Class này được expose qua `/types/typescript-types` để FE strong-type khi parse
- Class này dùng để **deserialize + validate** ở BE (không parse `JObject` raw)
- Mỗi key của setting JSON phải có constant trong `SettingKeys`

```csharp
// ✅ ĐÚNG
public class WorkflowSettings
{
    public bool AllowConflictOverride { get; set; }
    public bool RequireScheduleApproval { get; set; }
    public int MaxConcurrentShifts { get; set; }
}

var settings = JsonSerializer.Deserialize<WorkflowSettings>(setting.Value);
```

### 8.3 Enum / Constant cần FE biết
- Status, type, kind, mode... → khai báo dưới dạng `static class` hằng số hoặc enum trong `MyHospital.Utilities/Constants` để export qua `/types/typescript-const`
- KHÔNG hardcode chuỗi ở cả BE lẫn FE — chỉ define ở 1 chỗ trong BE rồi sync sang FE

### 8.4 Validation song song
Object đã define cho contract sync **kiêm luôn** validation:
- Dùng `DataAnnotations` (`[Required]`, `[Range]`, `[StringLength]`, ...) trên class
- ServiceStack tự validate request DTO; class settings tự validate khi deserialize
- FE tận dụng cùng định nghĩa cho client-side validation
