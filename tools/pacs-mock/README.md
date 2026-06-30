# PACS Mock Server

Standalone Node.js/Express mock of the VIETRAD/MINERVA PACS endpoint. It is **completely independent** of the HIS codebase — delete `tools/pacs-mock/` when testing is done.

Use it to prove real two-way HTTP/TLS/auth/firewall integration before contacting the vendor.

## Quick start

```bash
cd tools/pacs-mock
cp .env.example .env
# edit .env with your test credentials / callback URL
npm install
npm start
```

## Configuration

All config is via environment variables (see `.env.example`):

| Variable | Meaning | Default |
|---|---|---|
| `PORT` | listener port | `9080` |
| `TLS_CERT` / `TLS_KEY` | enable HTTPS | (unset = HTTP) |
| `EXPECTED_BASIC_USER` / `EXPECTED_BASIC_PASS` | Basic Auth HIS must send | required |
| `HIS_CALLBACK_URL` | URL to push results back to HIS | required for fire-callback |
| `HIS_INBOUND_APIKEY` | `X-Api-Key` sent on callback | required for fire-callback |
| `HIS_BASE_URL` | HIS base for pull-catalog | required for pull-catalog |
| `FAULT_MODE` | `none` \| `http400` \| `http500` \| `timeout` | `none` |
| `FIXTURE_DIR` | payload fixtures directory | `./fixtures` |
| `AUTO_CALLBACK` | auto-push result to `HIS_CALLBACK_URL` after order receive (POST/PUT only) | `false` |
| `AUTO_CALLBACK_DELAY_MS` | simulated radiologist turnaround when `AUTO_CALLBACK=true` | `4000` |

## Realistic PACS-like behavior (for testing with different vendors / real PACS)

This mock is intentionally **stateful** to act more like a real PACS (not just echo fixed fixtures):

- Khi HIS gửi order → mock **tự tạo Study** với `studyInstanceUid` (DICOM-style), `accessionNumber`, list service IDs.
- ACK trả về các ID này (nhiều PACS thật làm vậy) → HIS lưu được `PacsStudyId` / accession.
- `/admin/fire-callback` với orderNumber đã nhận → tự động inject `studyIUID`, execution times vào result (nếu fixture trống).
- `AUTO_CALLBACK=true` → sau khi nhận order (POST/PUT), mock tự schedule result callback sau `AUTO_CALLBACK_DELAY_MS` (giống PACS thật push kết quả về HIS). Manual `/admin/fire-callback` vẫn hoạt động như cũ.
- `GET /admin/studies` + `/admin/state` để inspect state.

Lợi ích lớn khi test vendor khác:
- Roundtrip có dữ liệu liên kết thật (order ACK ↔ callback).
- Dễ thay payload / format khi spec pacs thật về.
- Test late results, duplicate callbacks, study UID flow một cách ổn định.

## Mức 2 — DICOM layer (tools/pacs-dicom-mock)

Để gần thực tế **toàn diện** hơn (nhận ảnh DICOM thật từ storescu/modality):

```bash
cd tools/pacs-dicom-mock
./run.sh          # (sẽ tạo venv + cài + chạy)
```

- Nhận C-STORE thật → lưu file .dcm + tạo study với UID từ ảnh.
- REST + trigger callback (có thể trỏ thẳng vào HIS hoặc vào Node mock).
- Xem `tools/pacs-dicom-mock/README.md`.

**Khuyến nghị chạy cả hai**:
- Node (Mức 1) lo REST order/result + admin UI.
- Python DICOM (Mức 2) lo nhận ảnh thật.

Khi C-STORE xong → có thể fire callback có studyIUID thật từ DICOM file.

## Run modes

### Mode 1 — localhost loopback (fastest)

```bash
PORT=9080 \
EXPECTED_BASIC_USER=pacs_user EXPECTED_BASIC_PASS=pacs_pass \
HIS_CALLBACK_URL=http://localhost:9081/pacs/callback \
HIS_INBOUND_APIKEY=his-key \
npm start
```

HIS points outbound to `http://localhost:9080`; mock points callback to a local HIS listener on `9081`.

### Mode 2 — real network / TLS

```bash
# Generate a self-signed cert for testing
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 7 -nodes -subj '/CN=pacs-mock'

PORT=9443 TLS_CERT=./cert.pem TLS_KEY=./key.pem \
EXPECTED_BASIC_USER=pacs_user EXPECTED_BASIC_PASS=pacs_pass \
HIS_CALLBACK_URL=https://your-public-his.example.com/pacs/callback \
HIS_INBOUND_APIKEY=his-key \
HIS_BASE_URL=https://your-public-his.example.com \
npm start
```

This proves firewall egress, DNS, TLS termination, reverse-proxy routing, and header preservation.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `POST/PUT/DELETE *` | PACS receive — HIS pushes order/patient/cancel. **Now returns realistic `accessionNumber` + `studyInstanceUid`** (generated like a real PACS) |
| `POST /admin/fire-callback?orderNumber=&serviceId=&fixture=` | Push a result. If a study was previously received for that orderNumber, `studyIUID` + times are auto-injected |
| `GET  /admin/studies` | Inspect studies the mock has received (stateful registry) |
| `GET  /admin/state` | Quick view of mock state |
| `POST /admin/pull-catalog` | Pull `GetListUser/Service/Modality` from HIS |
| `GET /admin/verify-signature?user=&token=&expires=&signature=` | Verify signed URL MD5 independently |
| `GET /fire.html` | Manual fire-callback button page |

## Logging

Every inbound request is printed to stdout with method, real path, headers, and body. Use this to see exactly what HIS sends.

## Fixtures

Payloads are copied verbatim from the vendor analysis docs under `docs/business/pacs/analysis/`:

- `order-fhir.json` — FHIR Bundle order request (`analysis/01-hl7-fhir.md` §5.2)
- `result-callback-fhir.json` — FHIR Bundle result (`analysis/01-hl7-fhir.md` §9.2). Includes a minimal valid base64 PDF in `Media.content.data` (exercises HIS `MedicalVisitParaclinicalResultFile` save), `DiagnosticReport.performer[0].display` = `BS001|Nguyễn Văn A` (interpreter), and Device `Technicians` = `KTV01|Trần Thị B` (technician).
- `order-json-plain.json` — plain JSON order (`analysis/03-json-thuan.md` §5.1)
- `result-callback-json-plain.json` — plain JSON callback (`analysis/03-json-thuan.md` §5.4)
- `catalog-users.json` / `catalog-services.json` / `catalog-modality.json` — catalog shapes (`analysis/03-json-thuan.md` §5.7.1–3)

## Testing realistic flow (recommended for vendor / real PACS prep)

```bash
# 1. Start mock
PORT=9080 EXPECTED_BASIC_USER=... EXPECTED_BASIC_PASS=... HIS_CALLBACK_URL=... npm start

# 2. HIS gửi order (hoặc dùng curl để test)
curl -X POST http://localhost:9080/his/json/request \
  -u pacs_user:pacs_pass \
  -H "Content-Type: application/json" \
  -d @fixtures/order-json-plain.json

# 3. Xem study mock vừa tạo
curl http://localhost:9080/admin/studies

# 4. Bắn result (sẽ auto có studyIUID từ bước 2)
curl -X POST "http://localhost:9080/admin/fire-callback?orderNumber=579166468&serviceId=059483226"

# 5. Kiểm tra HIS đã nhận + xử lý study refs chưa

# Optional: push-driven mode (auto result after order)
AUTO_CALLBACK=true AUTO_CALLBACK_DELAY_MS=4000 PORT=9080 ... npm start
# POST order → wait ~4s → mock auto-POSTs result to HIS_CALLBACK_URL
```

## Assumptions

See `SIMULATOR-ASSUMPTIONS.md` for every baked-in simplification and pending vendor question.

**Mẹo khi pacs thật về:** Dùng `/admin/fire-callback` với custom JSON (hoặc POST body `customResult`) để replicate đúng format của vendor thật. Kết hợp delay + study registry để test flow gần thực tế nhất.

## Mức 1 Enhancements (Realistic PACS Simulator)

- Persistent studies (studies.json) — survives restart.
- On every order receive: auto-create study + return `studyInstanceUid` + `accessionNumber` + `serviceRequestIds` in ACK (very close to real PACS).
- `/admin/fire-callback` supports:
  - `?delay=15000` or in body (async simulation).
  - Full `customResult` override via POST JSON body (perfect for testing different vendors).
  - Auto-inject study data from registry.
- New powerful endpoints:
  - `GET /admin/studies?accession=...`
  - `POST /admin/studies` (manually seed studies)
  - `POST /admin/studies/{orderNumber}/complete`
  - `GET /admin/state`
- Enhanced fire.html with custom payload + delay + studies viewer.
- This gives stable I/O testing: order → rich ACK with IDs → (delayed) result callback with linked study data.
