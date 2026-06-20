# Findings Schema — file `.md` interchange (cross-tool)

> Định dạng **chuẩn** cho file findings mà mọi tool (Claude/Codex/opencode) sinh & tiêu thụ. Đóng băng schema này để `.md` làm cầu nối xuyên vòng & xuyên tool. Dùng cùng [protocol.md](./protocol.md) + [checklist.md](./checklist.md).

## Vị trí output

**Folder NGÀY + ROUND-VERSION (bắt buộc, theo rule canon AGENTS.md):** `docs/audit/<YYYY-MM-DD>/<base>.round-<N>.md`.
`<N>` = round, tự tăng theo `<base>` đã có dưới `docs/audit/` (lần đầu = 1). Resolve deterministic bằng
`python scripts/audit_path.py "<base>"` (tự `mkdir -p` folder ngày). Một file/round; round sau tham chiếu round
trước (warm-start từ ledger round trước). `<base>` = vd `<module>-review` (round thay cho hậu tố `-v<n>` cũ).
KHÔNG ghi phẳng vào `docs/audit/`. File cũ (`<module>-review-v<n>-<date>.md` phẳng) giữ nguyên; chỉ áp cho file mới.

## Template

```markdown
# Review — <module> — Vòng <n> — <YYYY-MM-DD> — <tool>
scope_base: <sha hoặc branch gốc>
dirty_files: [<path>, ...]
checklist_version: <git short-sha của checklist.md>
prev_round: <link file vòng trước | none>

## Tóm tắt
BLOCK: <k>  HIGH: <k>  MED: <k>  LOW/NIT: <k>  DEFERRED-Q: <k>
Verdict: <CHƯA ĐÓNG | ĐÓNG (0 BLOCK/HIGH open)>

## Coverage ledger
| file-group              | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|-------------------------|----|----|----|----|----|----|----|----|----|-----|
| <path/glob>             | F1 |CLEAN| N/A| ...                                  |
<!-- ô = finding-id | CLEAN (đã soi, sạch) | N/A (chiều không áp dụng) | UNATTESTED (chưa phủ — nợ) -->

## Findings

### F-001
- severity: BLOCK | HIGH | MED | LOW | NIT
- dimension: D<1..10>
- location: <path:line[-line]>
- title: <một dòng>
- evidence: rule-hit:<tool> | spec:<DL-00x|REQ-id> | exemplar:<file:line>   # BẮT BUỘC ≥1 cho BLOCK/HIGH
- root_cause: <vì sao sai>
- fix: <khuyến nghị kỹ thuật — KHÔNG quyết định nghiệp vụ>
- status: OPEN | FIXED | VERIFIED | REJECTED | DEFERRED-Q | REOPENED
- round_found: <n>
- verified_by: <tool/run | -->

### F-002
...
```

## Vòng đời status

```
OPEN ──fix──▶ FIXED ──verify──▶ VERIFIED            (đường chính)
  │                      └─hồi quy─▶ REOPENED ──▶ (vào vòng sau)
  ├─ verify đối kháng bác ─▶ REJECTED  (false positive, giữ lại để học)
  └─ không fix bằng code ─▶ DEFERRED-Q (→ 05-open-questions + Discovery Report)
```

- **OPEN** mặc định khi audit tạo.
- **FIXED** khi fix xong + đã tự-review-diff.
- **VERIFIED** khi verify xác nhận đóng thật.
- **REOPENED** khi verify thấy hồi quy hoặc fix không đóng.
- **REJECTED** khi verify đối kháng bác bỏ (false positive) — **không xóa**, giữ để vòng học biết pattern báo nhầm.
- **DEFERRED-Q** khi là câu hỏi nghiệp vụ — route `specs/<module>/05-open-questions.md` + Implementation Discovery Report. Không tính là review-miss.

## Quy tắc đọc cho phiên fix (vòng 2)

- Đầu vào **duy nhất** = file này. Không đi săn thêm.
- Xử lý theo severity: BLOCK → HIGH → MED. LOW/NIT → backlog, không tốn vòng.
- Cập nhật `status` + ghi commit/diff **tại chỗ** trong file (hoặc tạo file vòng kế trỏ ngược).

## Coverage ledger = chống roulette

Ledger làm **miss thành nhìn thấy được**. Ô `UNATTESTED` = nợ phủ, phải mót ở mini-wave (protocol §3.5) hoặc ghi rõ là nợ — **không** được để trống mà coi như sạch. Vòng sau audit warm-start từ ledger: ưu tiên ô `UNATTESTED` + diff-fix, không roll lại toàn bộ ngẫu nhiên.
