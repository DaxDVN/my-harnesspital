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
review_mode: aggressive-weak-multipass | standard
reviewer_passes: <dimension:pass-count summary>

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
- bug_class: <stable-key | none>   # bắt buộc cho bug thật; dùng key ổn định để scanner-promotion phát hiện lặp lại
- scanner_candidate: yes | no      # yes nếu bug_class có thể bắt bằng guard/mh_scan/eslint/ast-grep
- location: <path:line[-line]>
- title: <một dòng>
- evidence: rule-hit:<tool> | ba-source:<trang/mục Tài liệu BA> | exemplar:<file:line>   # BẮT BUỘC ≥1 cho BLOCK/HIGH; D1 PHẢI dùng ba-source
- root_cause: <vì sao sai>
- fix: <khuyến nghị kỹ thuật — KHÔNG quyết định nghiệp vụ>
- fix_reasonableness: <vì sao fix đề xuất là tối thiểu/hợp lý, hoặc vì sao cần fix lớn hơn>
- regression_risk: <callers/flows/API/DTO/state/permission/business có thể bị ảnh hưởng>
- alternative_considered: <phương án khác đã cân nhắc | none>
- why_not_bigger_fix: <vì sao không refactor/mở rộng ngoài phạm vi | n/a nếu phải fix lớn>
- status: OPEN | FIXED | VERIFIED | REJECTED | DEFERRED-Q | REOPENED
- review_status: NEEDS_ADJUDICATION | CONFIRMED | REJECTED | DEFERRED-Q
- confidence: LOW | MEDIUM | HIGH
- found_by: [<dimension/pass/tool>]
- adjudicated_by: <tool/model/run | -->
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
- **review_status=NEEDS_ADJUDICATION** mặc định cho BLOCK/HIGH từ weak-model pass trước khi fix.
- **review_status=CONFIRMED** khi stronger reviewer/adjudicator hoặc deterministic evidence giữ finding.
- **FIXED** khi fix xong + đã tự-review-diff.
- **VERIFIED** khi verify xác nhận đóng thật.
- **REOPENED** khi verify thấy hồi quy hoặc fix không đóng.
- **REJECTED** khi verify đối kháng bác bỏ (false positive) — **không xóa**, giữ để vòng học biết pattern báo nhầm.
- **DEFERRED-Q** khi logic nghiệp vụ không rõ trong `specs/Tài liệu Nội trú.md` — route `specs/<module>/05-open-questions.md` + Implementation Discovery Report. Không tính là review-miss.

## Fix reasonableness gate

BLOCK/HIGH phải có `fix_reasonableness`, `regression_risk`, `alternative_considered`, và
`why_not_bigger_fix` trước khi được chuyển cho phiên fix. Mục tiêu là để model yếu có thể báo nhiều
ứng viên bug, nhưng model/reviewer mạnh hơn vẫn có đủ dữ kiện để bác hoặc giữ lại. Nếu trường này chỉ
ghi chung chung như "fix normally" hoặc không nêu boundary, finding vẫn là `NEEDS_ADJUDICATION`.

## Scanner promotion metadata

Mọi finding là bug thật (`OPEN`, `CONFIRMED`, `FIXED`, `VERIFIED`, hoặc `REOPENED`) phải có
`bug_class` khác `none`, trừ khi reviewer ghi rõ vì sao lỗi là one-off không tổng quát hóa được. Nếu
`scanner_candidate=yes`, phần `fix` hoặc `regression_risk` phải nêu tầng rẻ nhất có thể bắt lần sau:
`guard`, `mh_scan`, `eslint/ast-grep`, hoặc `review-checklist`.

## Quy tắc đọc cho phiên fix (vòng 2)

- Đầu vào **duy nhất** = file này. Không đi săn thêm.
- Xử lý theo severity: BLOCK → HIGH → MED. LOW/NIT → backlog, không tốn vòng.
- Cập nhật `status` + ghi commit/diff **tại chỗ** trong file (hoặc tạo file vòng kế trỏ ngược).

## Coverage ledger = chống roulette

Ledger làm **miss thành nhìn thấy được**. Ô `UNATTESTED` = nợ phủ, phải mót ở mini-wave (protocol §3.5) hoặc ghi rõ là nợ — **không** được để trống mà coi như sạch. Vòng sau audit warm-start từ ledger: ưu tiên ô `UNATTESTED` + diff-fix, không roll lại toàn bộ ngẫu nhiên.
