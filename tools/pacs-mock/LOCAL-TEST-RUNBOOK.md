# Hướng dẫn kiểm thử E2E HIS ↔ PACS Mock (Loopback localhost)

> Tài liệu này là push-button runbook để owner chạy E2E HIS↔mock ngay lập tức.
> Phase E1 của `docs/business/pacs/PACS-self-test-and-connectivity-plan.md`.
> Chỉ dùng trên môi trường local dev (localhost loopback); không push lên prod.

---

## 1. Checklist sẵn sàng

Trước khi chạy bất kỳ test nào, xác nhận tất cả mục sau:

| # | Mục | Cách kiểm tra | Đạt khi |
|---|---|---|---|
| R1 | HIS BE đã build thành công và đang chạy trên `:5003` | `curl -s http://localhost:5003/health` hoặc xem log terminal BE | HTTP 200 hoặc redirect |
| R2 | Mock PACS đang chạy trên `:9080` | `curl -s http://localhost:9080/admin/state` | JSON `{"status":true,...}` |
| R3 | Bảng `PacsConnection` đã seed đúng (sibling subagent tạo) | Query DB: `SELECT * FROM PacsConnections WHERE HospitalId=7` | `Enabled=1`, `BaseUrl='http://localhost:9080'`, `InboundApiKey='pacs-local-test-key'`, `CallbackIpAllowlist=NULL/empty` |
| R4 | `Encryption__Key` set trong môi trường BE | Xem `.env` hoặc `appsettings.Development.json` của BE | Key tồn tại, không rỗng |
| R5 | `CallbackIpAllowlist` để trống | Xem row `PacsConnection` | NULL hoặc empty string |

---

## 2. Cấu hình chia sẻ

| Tham số | Giá trị |
|---|---|
| HIS base URL | `http://localhost:5003` |
| PACS callback inbound path | `POST http://localhost:5003/pacs/callback` |
| Catalog paths (HIS serve, PACS pull) | `GET http://localhost:5003/pacs/GetListUser` / `GetListService` / `GetListModality` |
| Mock PACS URL | `http://localhost:9080` |
| Auth inbound (mock→HIS callback) | `X-Api-Key: pacs-local-test-key` |
| Auth outbound (HIS→mock) | `Basic hisuser:hislocaltest` → `Authorization: Basic aGlzdXNlcjpoaXNsb2NhbHRlc3Q=` |
| Test tenant | `bvtest3` — tenant6 / hosp7 |
| Browser login | bvtest3 (never admin; per harness memory) |

---

## 3. Khởi động dịch vụ

### 3.1 Khởi động HIS BE

```bash
cd worktrees/combine-his-pacs/be
ASPNETCORE_URLS=http://localhost:5003 make server
```

Hoặc nếu `.env` đã có `ASPNETCORE_URLS=http://localhost:5003`:

```bash
cd worktrees/combine-his-pacs/be
make server
```

Xác nhận đang lắng nghe:

```bash
curl -s http://localhost:5003/health
# Hoặc kiểm tra log: "Now listening on: http://localhost:5003"
```

### 3.2 Khởi động Mock PACS

```bash
cd tools/pacs-mock
# .env đã cấu hình sẵn (không cần sửa cho loopback):
# PORT=9080, EXPECTED_BASIC_USER=hisuser, EXPECTED_BASIC_PASS=hislocaltest
# HIS_CALLBACK_URL=http://localhost:5003/pacs/callback
# HIS_INBOUND_APIKEY=pacs-local-test-key, HIS_BASE_URL=http://localhost:5003
npm start
```

Xác nhận đang chạy:

```bash
curl -s http://localhost:9080/admin/state
# Kết quả mong đợi: {"status":true,"data":{"studiesCount":0,"faultMode":"none",...}}
```

---

## 4. Kịch bản kiểm thử

### T1 — Inbound callback happy path (mock bắn kết quả → HIS nhận + lưu)

**Mục đích:** Xác nhận cả pipeline callback hoạt động: mock gửi FHIR Bundle → HIS 200 + ghi `DiagnosticImagingResults`.

**Điều kiện trước:** HIS có 1 chỉ định CĐHA (MedicalVisitDiagnosticImagingService) đã tạo, với:
- `AccessionNumber` (trên ParaclinicalGroup) = `"354365"`
- `PacsServiceRequestId` = `"66677141097"` (hoặc `Code` = `"66677141097"` nếu chưa có PacsServiceRequestId)

**Bước 1 — Gửi order lên mock** (để mock tạo study, dùng cho fire-callback):

```bash
curl -X POST http://localhost:9080/his/json/request \
  -u hisuser:hislocaltest \
  -H "Content-Type: application/json" \
  -d @fixtures/order-fhir.json
```

Kết quả mong đợi: HTTP `201`, body JSON với `accessionNumber` và `studyInstanceUid`.

**Bước 2 — Mock bắn result callback về HIS**:

```bash
curl -s -X POST \
  "http://localhost:9080/admin/fire-callback?orderNumber=354365&serviceId=66677141097&fixture=result-callback-fhir.json"
```

Mock sẽ POST đến `http://localhost:5003/pacs/callback` với `X-Api-Key: pacs-local-test-key`.

**Kết quả mong đợi:** Mock log hiển thị `HIS response: 200`. HIS log không có exception.

**Xác minh:**

```sql
-- DB: kiểm tra DiagnosticImagingResults được ghi
SELECT * FROM DiagnosticImagingResults
WHERE MedicalVisitDiagnosticImagingServiceId = <mvdis_id>
ORDER BY Id DESC LIMIT 1;

-- PacsIntegrationLog: phải có row AckStatus='Ok', Direction='Inbound'
SELECT OrderNumber, ServiceRequestId, AckStatus, HttpStatus, ErrorMessage
FROM PacsIntegrationLogs
WHERE Direction='Inbound' ORDER BY Id DESC LIMIT 5;
```

---

### T2 — Auth: thiếu/sai X-Api-Key → HIS 401

**Mục đích:** Xác nhận HIS trả `401` thật (không phải `200` always hoặc `403`).

```bash
# Thiếu key
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:5003/pacs/callback \
  -H "Content-Type: application/json" \
  -d '{"resourceType":"Bundle","type":"collection","entry":[]}'
# Mong đợi: 401

# Sai key
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:5003/pacs/callback \
  -H "X-Api-Key: wrong-key" \
  -H "Content-Type: application/json" \
  -d '{"resourceType":"Bundle","type":"collection","entry":[]}'
# Mong đợi: 401
```

**Lưu ý:** KHÔNG dùng `Authorization: Basic` cho callback — đây là lỗi #1 hay gặp. Inbound dùng `X-Api-Key`, Basic chỉ dành cho chiều HIS→PACS outbound.

---

### T3 — Malformed body → HIS 400

**Mục đích:** Xác nhận HIS không 500 khi body rác.

```bash
# Body không parse được
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:5003/pacs/callback \
  -H "X-Api-Key: pacs-local-test-key" \
  -H "Content-Type: application/json" \
  -d 'NOT JSON'
# Mong đợi: 400

# Body thiếu OrderNumber (FHIR bundle không có SO_PHIEU)
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:5003/pacs/callback \
  -H "X-Api-Key: pacs-local-test-key" \
  -H "Content-Type: application/json" \
  -d '{"resourceType":"Bundle","type":"collection","entry":[{"resource":{"resourceType":"DiagnosticReport","status":"final"}}]}'
# Mong đợi: 400 (thiếu OrderNumber)
```

Kiểm tra `PacsIntegrationLogs` có row `AckStatus='Error'`.

---

### T4 — Idempotency / Amendment: callback thứ 2 với signedDate mới hơn → UPDATE

**Mục đích:** Fix BLOCK-1 — null signedDate không bị drop; bản mới hơn đè bản cũ.

**Bước 1 — Fire callback lần 1** (dùng fixture gốc `effectiveDateTime = 2024-07-24T15:16:20+07:00`):

```bash
curl -s -X POST \
  "http://localhost:9080/admin/fire-callback?orderNumber=354365&serviceId=66677141097"
# Ghi nhận DiagnosticImagingResults.ConcludedAt = 2024-07-24T08:16:20Z (UTC)
```

**Bước 2 — Fire callback lần 2 với signedDate cũ hơn** (phải bị bỏ qua — idempotent):

```bash
curl -s -X POST http://localhost:5003/pacs/callback \
  -H "X-Api-Key: pacs-local-test-key" \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType":"Bundle","type":"collection",
    "entry":[
      {"resource":{"resourceType":"ServiceRequest","id":"66677141097","status":"completed","intent":"order",
        "note":[{"extension":[{"valueCodeableConcept":{"coding":[{"code":"SO_PHIEU"}],"text":"354365"}}]}]}},
      {"resource":{"resourceType":"DiagnosticReport","status":"final",
        "identifier":{"value":"354365"},
        "effectiveDateTime":"2024-07-24T14:00:00+07:00",
        "conclusion":"Old result — should be ignored"}}
    ]}'
# Mong đợi: 200 (idempotent, không update vì effectiveDateTime cũ hơn)
```

**Bước 3 — Fire callback lần 3 với issued mới hơn** (phải UPDATE):

```bash
curl -s -X POST http://localhost:5003/pacs/callback \
  -H "X-Api-Key: pacs-local-test-key" \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType":"Bundle","type":"collection",
    "entry":[
      {"resource":{"resourceType":"ServiceRequest","id":"66677141097","status":"completed","intent":"order",
        "note":[{"extension":[{"valueCodeableConcept":{"coding":[{"code":"SO_PHIEU"}],"text":"354365"}}]}]}},
      {"resource":{"resourceType":"DiagnosticReport","status":"final",
        "identifier":{"value":"354365"},
        "issued":"2024-07-25T10:00:00+07:00",
        "conclusion":"Amendment — newer than original, must overwrite"}}
    ]}'
# Mong đợi: 200 + DiagnosticImagingResults.Conclusion updated
```

Xác minh: `SELECT Conclusion, ConcludedAt FROM DiagnosticImagingResults WHERE ...` — phải thấy "Amendment" và ConcludedAt = 2024-07-25T03:00:00Z.

---

### T5 — Catalog pull: HIS phục vụ GetListUser / GetListService / GetListModality

**Mục đích:** Xác nhận 3 catalog endpoint trả 200 và dữ liệu (Code-not-Id per D5 crit#5).

```bash
# GetListUser (authenticated bằng X-Api-Key)
curl -s -H "X-Api-Key: pacs-local-test-key" \
  http://localhost:5003/pacs/GetListUser | head -c 500

# GetListService
curl -s -H "X-Api-Key: pacs-local-test-key" \
  http://localhost:5003/pacs/GetListService | head -c 500

# GetListModality
curl -s -H "X-Api-Key: pacs-local-test-key" \
  http://localhost:5003/pacs/GetListModality | head -c 500
```

Kết quả mong đợi: HTTP 200, JSON array với các object chứa `UserID` (= Code bác sĩ, không phải DB id), `UserName`.

**Lưu ý:** Mock's `/admin/pull-catalog` sẽ báo `shapeOk=false` vì HIS trả bare JSON array thay vì `{"userInfor":[...]}` theo vendor spec — xem §6 Fixture Gaps. Dùng direct curl ở trên để verify.

---

### T6 — Outbound: tạo chỉ định CĐHA trong HIS → HIS POST Bundle lên mock → verify log

**Mục đích:** Xác nhận toàn bộ chiều outbound: doctor nhập chỉ định → HIS POST FHIR Bundle lên mock (Basic auth) → mock ghi log → `PacsIntegrationLog` ghi `Pending→Ok` + `AccessionNumber ≤ 10 ký tự`.

**Bước 1 — Đăng nhập FE bằng bvtest3:**

Mở `http://localhost:5173` (hoặc FE port), đăng nhập tài khoản `bvtest3`.

**Bước 2 — Tạo phiếu CĐHA:**

Vào module chỉ định CĐHA (XQ/CT/MRI), tạo chỉ định cho bệnh nhân bất kỳ trong hosp7. Lưu lại.

**Bước 3 — Xem mock nhận gì:**

Mock log (stdout) sẽ in:
```
[timestamp] POST /his/json/request
Headers: { authorization: "Basic aGlzdXNlcjpoaXNsb2NhbHRlc3Q=", ... }
Body: { "resourceType": "Bundle", ... }
[PACS-MOCK] Order received → study created/updated: order=<N> studyIUID=1.2.840...
```

**Bước 4 — Kiểm tra study registry mock:**

```bash
curl -s http://localhost:9080/admin/studies | python3 -m json.tool | grep -E "orderNumber|accessionNumber|status"
```

**Bước 5 — Xác minh HIS log:**

```sql
-- PacsIntegrationLog chiều outbound: Pending sau khi tạo, Ok sau khi mock ACK
SELECT OrderNumber, Direction, AckStatus, AccessionNumber, HttpStatus, CreatedAt
FROM PacsIntegrationLogs
WHERE Direction='Outbound'
ORDER BY Id DESC LIMIT 5;

-- AccessionNumber phải <= 10 ký tự
SELECT OrderNumber, AccessionNumber, LEN(AccessionNumber) AS Len
FROM PacsIntegrationLogs
WHERE Direction='Outbound' AND AccessionNumber IS NOT NULL;
```

---

### T7 — Disabled noop: PacsConnection.Enabled=0 → chỉ định vẫn tạo được, không có traffic PACS

**Mục đích:** Xác nhận HIS không throw khi PACS disabled (order-entry non-throw per D17).

```sql
-- Disable PacsConnection
UPDATE PacsConnections SET Enabled=0 WHERE HospitalId=7;
```

Tạo chỉ định CĐHA mới qua FE (bvtest3). Xác nhận:
- Chỉ định tạo thành công (không error popup)
- Mock stdout KHÔNG có request mới
- `PacsIntegrationLogs` KHÔNG có row mới

```sql
-- Re-enable sau khi test xong
UPDATE PacsConnections SET Enabled=1 WHERE HospitalId=7;
```

---

## 5. Nơi cần xem để xác minh

| Mục cần xem | Cách truy cập |
|---|---|
| `PacsIntegrationLogs` | DB query (xem các bước trên); cột quan trọng: `Direction`, `AckStatus`, `OrderNumber`, `ServiceRequestId`, `ErrorMessage` |
| `DiagnosticImagingResults` | DB query theo `MedicalVisitDiagnosticImagingServiceId` |
| Mock request log | Stdout của `npm start` trong `tools/pacs-mock/` |
| Mock study registry | `curl -s http://localhost:9080/admin/studies` |
| FE imaging list — PACS badge | Sau callback thành công T1/T4, vào trang kết quả CĐHA của bệnh nhân bvtest3; phiếu tương ứng phải hiện trạng thái "Có kết quả" / PACS badge |

---

## 6. Fixture Gaps — Các điểm cần lưu ý (mock subagent xử lý)

Những khoảng trống sau đây được phát hiện khi đối chiếu fixtures với hành vi HIS post-fix. Không cần chặn test ngay nhưng nên fix trước khi test amendment (T4) một cách rõ ràng.

### Gap 1 — `result-callback-fhir.json`: thiếu trường `issued` (ADVISORY, không block T1–T3)

- **Hiện trạng:** `DiagnosticReport` trong fixture chỉ có `"effectiveDateTime":"2024-07-24T15:16:20+07:00"`, không có `"issued"`.
- **Hành vi post-fix:** HIS `FhirPacsSerializer.ParseDiagnosticReport` đọc `issued` → `SignedDate` (primary); nếu vắng → fallback `effectiveDateTime`. Fixture dùng fallback — hoạt động được.
- **Rủi ro T4:** Khi test amendment với 2 lần callback, cần 2 fixture khác nhau `issued` hoặc `effectiveDateTime`. T4 trong runbook này dùng inline payload để tránh phụ thuộc vào fixture; fixture gốc không bị ảnh hưởng.
- **Khuyến nghị:** Mock subagent thêm `"issued":"2024-07-24T15:16:20+07:00"` vào `DiagnosticReport` của fixture để primary path luôn được tập luyện.

### Gap 2 — Catalog shape mismatch: mock validator vs HIS response (BLOCK cho `/admin/pull-catalog`, không block T5)

- **Hiện trạng:** Mock's `/admin/pull-catalog` gọi `/pacs/GetListUser|GetListService|GetListModality` và kiểm tra xem response có field `userInfor[]` / `serviceInfor[]` / `modalityInfor[]` hay không (vendor spec shape).
- **Hành vi thực tế:** HIS trả bare JSON array `[{UserID, UserName}]`, không phải `{userInfor:[{account, hisID, ...}]}`. Vì vậy mock validator sẽ báo `shapeOk=false` cho cả 3 endpoints.
- **Tác động:** `POST http://localhost:9080/admin/pull-catalog` cho kết quả `ok=false` mặc dù HIS thực sự trả 200. Đây là false-negative trong mock's shape validator, không phải lỗi HIS.
- **Workaround (T5):** Dùng direct curl với `X-Api-Key` như hướng dẫn ở T5 thay vì `/admin/pull-catalog`.
- **Khuyến nghị:** Mock subagent cập nhật validator để xử lý cả bare array response, hoặc ghi chú rõ `shapeOk=false` là expected khi HIS trả array thuần.

### Gap 3 — Catalog field names khác vendor spec (ADVISORY — cần xác nhận với VIETRAD)

- HIS trả `UserID` (= Code bác sĩ), `UserName`; vendor fixture (catalog-users.json) dùng `account`, `hisID`, `name`, `jobTitle`.
- HIS trả `Servicecode`, `Servicename`, `CategoryID`, `CategoryName`; fixture dùng `serviceID`, `serviceName`, `group`.
- HIS trả `ModalityID`, `ModalityName`; fixture dùng `hisCode`, `modalityName`, `group`.
- Đây là giả định chưa được vendor xác nhận (DECISIONS.md §D). Ghi lại là pending vendor confirmation.

---

## 7. Xử lý sự cố thường gặp

| Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|
| HIS callback trả `401` khi dùng `Authorization: Basic` | Sai auth direction — callback dùng `X-Api-Key`, không phải Basic | Chuyển sang `-H "X-Api-Key: pacs-local-test-key"` |
| HIS callback trả `403` | `CallbackIpAllowlist` không rỗng, IP `127.0.0.1` bị chặn | Set `CallbackIpAllowlist = NULL` trong `PacsConnections` |
| HIS callback trả `404` | Sai path (ví dụ `/pacs/Callback` thay vì `/pacs/callback`) | Dùng đúng path: `POST /pacs/callback` |
| Outbound — mock nhận request nhưng HIS log `AckStatus='Error'` hoặc retry | Mock trả format ACK không đúng hoặc HTTP status không phải 2xx | Kiểm tra mock stdout; xem `ErrorMessage` trong `PacsIntegrationLogs`; đảm bảo `FAULT_MODE=none` trong `.env` |
| T4 amendment không update — lần 2 vẫn bị `DuplicateNoOp` | `issued`/`effectiveDateTime` của payload lần 2 nhỏ hơn hoặc bằng lần 1 | Dùng `issued` timestamp lớn hơn (mới hơn) trong payload T4 bước 3 |
| Catalog trả `401` | Endpoint `/pacs/GetListUser` etc. đòi `X-Api-Key` | Thêm `-H "X-Api-Key: pacs-local-test-key"` vào curl |
| `/admin/pull-catalog` báo `shapeOk=false` | HIS trả bare array; mock validator tìm `userInfor[]` field | Xem Gap 2 ở trên; dùng direct curl cho T5 |
| HIS không gửi order lên PACS sau khi tạo chỉ định | `PacsConnection.Enabled=0` hoặc không có row | Kiểm tra T7 reverse: `SELECT Enabled FROM PacsConnections WHERE HospitalId=7` |
