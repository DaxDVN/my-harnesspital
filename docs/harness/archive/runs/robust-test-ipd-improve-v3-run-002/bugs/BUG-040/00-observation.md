# BUG-040 — TASK-328: Form "Sản phụ khoa" hiển thị ngay khi chọn NB

## Metadata

- status: **BLOCKED** (0 NB today, không có NB sản phụ khoa)
- severity: MED
- bug_class: examination-form-not-respecting-config
- flow: /examination → chọn NB cấu hình form "Sản phụ khoa"
- worktree: ipd-improve-v3 slot 3
- observed_at: 2026-06-26T13:10Z

## 00 Observation (drill)

`/examination` loaded with:
- "Danh sách bệnh nhân" filter: "Chờ khám / Đang khám / Khám xong", "Hôm nay"
- "1 - 0 of 0" — không có NB nào hôm nay
- Bệnh Án section có: Lý do khám, Tiền sử gia đình/bản thân, Toàn thân, Hỏi bệnh, Từng bộ phận, Chẩn đoán (Chẩn đoán ban đầu, Chính, Kèm theo)

→ 0 NB hôm nay → không thể test form Sản phụ khoa. Cần NB có cấu hình form sản phụ khoa.

## 02 Triage

Verdict: **BLOCKED** — no data to test. Owner manual test cần thiết.
