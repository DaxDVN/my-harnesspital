# Combined Realistic PACS Mocks (Mức 1 + Mức 2)

Bạn có **hai công cụ** để test HIS gần với PACS thật nhất:

## 1. Node REST Mock (Mức 1) — `tools/pacs-mock`

- Nhận order (REST) từ HIS
- Trả ACK giàu thông tin (studyInstanceUid, accession)
- Fire result callback (có delay, custom payload)
- Admin UI mạnh tại `/fire.html`
- Rất nhanh để giả lập nhiều vendor khác nhau

Chạy:
```bash
cd tools/pacs-mock
npm start   # (cần set env trước hoặc .env)
```

## 2. Python DICOM Mock (Mức 2) — `tools/pacs-dicom-mock`

- Nhận **ảnh DICOM thật** qua C-STORE (storescu, modality giả)
- Tạo study từ metadata thật trong file .dcm
- REST + trigger callback
- Có thể chain với Node mock

Chạy:
```bash
cd tools/pacs-dicom-mock
./run.sh
```

## Cách dùng kết hợp tốt nhất (khuyến nghị)

1. Chạy **cả hai** song song.
2. HIS → gửi order vào Node mock (port 9080)
3. (Optional) Gửi ảnh DICOM vào Python mock (port 4242)
4. Dùng `/admin/fire-callback` (Node) hoặc `/trigger-callback` (Python) để đẩy KQ về HIS.
5. Khi có spec vendor thật → chỉnh `custom_result` hoặc fixture để match gần như 1-1.

Điều này đảm bảo:
- I/O ổn định
- Study UID có nguồn gốc (hoặc từ order, hoặc từ ảnh DICOM thật)
- Dễ test lỗi, delay, format khác nhau

## Khi vendor thật về

- Dùng mock để **replay + validate** contract trước khi connect thật.
- Sau khi ổn → thay URL trong HIS config sang vendor thật.

Cả hai mock đều là throwaway, log rất rõ, và dễ xóa sau khi xong.
