# PACS DICOM Mock (Mức 2)

**Mục tiêu**: Làm cho test integration **gần thực tế nhất có thể** khi bạn cần:

- Nhận ảnh DICOM thật từ `storescu`, modality simulator, hoặc công cụ khác.
- Tạo Study với StudyInstanceUID thật từ file DICOM.
- Kích hoạt result callback sang HIS (có study refs).
- Dùng song song hoặc độc lập với Node REST mock (Mức 1).

## Quick Start

```bash
cd tools/pacs-dicom-mock
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env (HIS_CALLBACK_URL, keys, ports...)

python app.py
```

Server sẽ chạy:
- DICOM SCP: port 4242 (AE MOCKPACS)
- REST API: port 9081

## Test với dcmtk (rất khuyến khích)

```bash
# 1. Ping
echoscu -aec MOCKPACS localhost 4242

# 2. Gửi ảnh thật (dùng file .dcm bất kỳ)
storescu -aec MOCKPACS localhost 4242 /path/to/study/image.dcm

# 3. Xem studies đã nhận
curl http://localhost:9081/studies

# 4. Trigger result callback (hoặc để AUTO_FIRE_DELAY_MS tự động bắn)
curl -X POST http://localhost:9081/trigger-callback \
  -H "Content-Type: application/json" \
  -d '{"order_number": "ACC123456", "delay_ms": 2000}'
```

Callback sẽ được gửi tới `HIS_CALLBACK_URL` (có thể trỏ thẳng vào HIS hoặc vào Node mock `/admin/fire-callback`).

## Tích hợp với Node REST Mock (Mức 1)

Trong `.env` của DICOM mock:

```env
HIS_CALLBACK_URL=http://localhost:9080/admin/fire-callback
HIS_INBOUND_APIKEY=
```

Khi bạn gửi ảnh qua DICOM → study được tạo → fire callback sang Node mock → Node sẽ enrich thêm và forward sang HIS.

## API chính

- `GET /studies`
- `GET /studies/{order_number}`
- `POST /studies` (seed thủ công)
- `POST /trigger-callback` (body: `{order_number, delay_ms, custom_result}`)
- `GET /health`

## Cấu hình quan trọng

- `AUTO_FIRE_DELAY_MS`: Sau khi nhận C-STORE xong, tự động bắn result sau X ms (0 = tắt).
- `STORAGE_DIR`: nơi lưu file .dcm thật.
- `DB_PATH`: SQLite metadata.

## Sử dụng thực tế khi test vendor khác

1. Gửi order từ HIS → Node mock (Mức 1) nhận và trả studyIUID.
2. (Tùy chọn) Gửi ảnh thật qua DICOM vào mock này → nó tạo study với UID từ ảnh.
3. Trigger callback (hoặc auto) với `custom_result` hoặc fixture để match đúng contract của vendor thật.

## Lưu ý

- Đây là **throwaway mock**, không production.
- Dùng thư viện chuẩn `pynetdicom` (không tự viết protocol).
- Kết hợp với Mức 1 (Node) cho trải nghiệm đầy đủ nhất.

Chạy cả hai mock cùng lúc là cách tốt nhất để test toàn bộ flow gần với PACS thật.
