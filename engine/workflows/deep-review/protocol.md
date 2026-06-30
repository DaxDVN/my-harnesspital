# Review Protocol — `mh-review` (cross-tool, ≤3 vòng)

> Runbook vận hành cho **mọi** tool review (Claude `/mh-review`, Codex, opencode). Mục tiêu: bắt **tối đa** issue mỗi lần audit để hội tụ trong **≤3 vòng**, không phải 17. Nền tảng lý thuyết: `docs/harness/notes/review-harness-feasibility-2026-06-16.md`.
> Liên quan: [checklist.md](./checklist.md) (7 chiều) · [findings-schema.md](./findings-schema.md) (định dạng output).

## 0. Đơn vị & mục tiêu

- **1 vòng = audit → fix → verify** (trọn). Mục tiêu **≤3 vòng** = ≤3 audit, ≤3 fix, ≤3 verify. ≤3 là **trần**, không phải quota — thường 1–2 là xong.
- Nguyên nhân không hội tụ (cũ): audit lặp lại với recall thấp + ngẫu nhiên + không trí nhớ xuyên vòng → đuôi bug vô tận.
- Ba cơ chế đóng nó: **(M1) audit phân vùng** (recall cao mỗi lần, KHÔNG lặp) · **(M2) verify đối kháng + provenance** (diệt false-positive/churn) · **(M3) fix tự-review-diff** (diệt hồi quy).

## 1. M1 — Audit phân vùng + multi-pass convergence + exemplar anchors

Một reviewer đơn lẻ trải attention trên *(toàn diff × mọi loại lỗi)* → chỉ ra ~10 cái nổi nhất, phần còn lại **chìm dưới ngưỡng**. Phân vùng gỡ nút: mỗi reviewer giữ **1 lát code × 1 chiều** trong full-focus → không cái nào chìm.

- **Phân vùng mặc định = theo chiều** (7 chiều trong [checklist.md](./checklist.md)). Mỗi chiều **nhiều pass** (P1–P5), mỗi pass góc nhìn khác → union findings. Recall tăng đáng kể so với single-pass.
- **Pass mặc định:** `P1 rule/convention`, `P2 regression/caller/cross-file`, `P3 reuse/edge-case/null/state`. `P4 business/spec contradiction` cho D1 (so code vs Tài liệu Nội trú.md). `P5 reuse matrix` cho D3/D7.
- **Exemplar-first review:** trước khi review, reviewer **tìm 1–2 pattern đúng** trong code sống (exemplar) làm anchor. "Code này có match exemplar pattern không?" — giúp model mid-tier có reference concrete thay vì chỉ abstract rules.
- **Scanner pre-scan:** `mh_scan` chạy trước, inject hits vào reviewer prompt như candidate list. Scanner = deterministic floor (free recall), reviewer = semantic ceiling.
- Ô **nghiệp vụ rủi ro cao** → thêm 2–3 reviewer độc lập (chỉ ô đó), hợp nhất.
- **KHÔNG re-audit toàn bộ nhiều lần.** Phủ thiếu thì mót bằng *completeness check có chặn* (mục 4.5).

### 1.1 Multi-pass convergence + self-adversarial pre-filter

Deep-review runs **multiple passes per dimension** (P1–P5) and **unions** findings. A finding seen by any pass
is kept as a candidate. This maximizes recall at the cost of noise — noise is handled downstream.

**Self-adversarial pre-filter (before expensive verify):** every BLOCK/HIGH finding is challenged by a skeptic
agent that reads the actual code and tries to refute it. Findings with weak/doc-only evidence are DOWNGRADED
to MED or DROPPED before the stronger adversarial verify step. This reduces wasted verify cycles on obvious
false positives while keeping genuinely strong findings.

**Convergence voting:** a finding that appears in ≥2 independent passes gets a confidence boost. A finding
from only 1 pass is still kept but flagged for extra scrutiny during verify.

Every real finding must carry `bug_class` and `scanner_candidate` metadata from
[findings-schema.md](./findings-schema.md). This keeps aggressive weak-model passes useful even when noisy:
false positives are retained as learning data, while repeated true bug classes can be promoted to deterministic
checks.

## 2. Scope freeze (đầu mỗi vòng — read-only)

Cố định phạm vi, chống "review trôi":

1. **Dirty set:** `git -C <repo> diff --name-only <base>` (guard hook cho phép `git diff`/`status`). Với worktree: base = branch gốc. **Lưu ý**: Bắt buộc lọc và bỏ qua (ignore) các file tự sinh (FE generated-dtos.ts, Constants.ts, generated-api-client.ts) và các file BE EF migrations (thư mục `Migrations/`) ra khỏi scope review để tránh sinh cảnh báo nhiễu.
2. **Blast radius:** CodeGraph `impact`/`affected` trên symbol đã đổi → file phụ thuộc bị kéo theo (đưa vào scope nếu rủi ro).
3. **Nghiệp vụ source:** `specs/Tài liệu Nội trú.md` (hoặc `.docx`) — **nguồn sự thật duy nhất** cho rule nghiệp vụ. **KHÔNG** dùng `specs/<module>/02-requirements.md` làm nguồn rule nghiệp vụ (chỉ dùng cho MVP dev: schema, API, UI).
4. **Spec set (design/contract):** `specs/<module>/{03-ui,07-schema,08-api,04-traceability}.md` (nguồn rule thiết kế & contract, không phải nguồn rule nghiệp vụ).

Output scope = `{file-group}` × `{requirement Confirmed}`.

**Nguồn spec duy nhất cho review:** `specs/Tài liệu Nội trú.md` hoặc `.docx` — đây là nguồn sự thật duy nhất cho business logic review (D1). Các chiều khác dựa trên code sống + convention rules.

## 3. AUDIT (mỗi vòng — maximum recall)

1. Scope freeze (mục 2).
2. **Step 2.0 — Deterministic pre-scan (chạy TRƯỚC khi spawn reviewers):**
   ```
   python scripts/mh_scan --scope <frozen-scope-paths> --format json
   ```
   Group the output by dimension (scanner id → dimension mapping in checklist §Known bug-classes). For each dimension that has scanner hits, inject those hits into that reviewer's prompt as a **CANDIDATE LIST**:
   > "The deterministic scanner already found N hits in D2 — confirm or refute each with live evidence, then find what the scanner cannot catch (semantic / business-logic / cross-file). Do NOT just re-list scanner hits."

   **Rationale:** the scanner provides the deterministic floor — mechanical findings (auth missing, raw throw, dict DTO) are surfaced for free, raising first-pass recall (the M1 convergence lever) and stopping reviewers from re-deriving what a regex already caught. Scanner hits still need the reviewer's adversarial verify for HIGH/BLOCK (e.g. `missing_hospital_scope` flags *candidate* tenancy gaps — the reviewer must confirm the entity is `:Base` and the filter is genuinely absent).

3. Với mỗi chiều áp dụng (checklist) → spawn `mh-reviewer` theo **multi-pass** (P1–P5). Mỗi pass dùng cùng scope nhưng prompt khác góc nhìn. **Exemplar-first:** reviewer tìm 1–2 pattern đúng trong code sống làm anchor trước khi review. Reviewer ghi report dài ra artifact theo schema + coverage attestation; trả về parent **bản compact**: artifact path, counts, top BLOCK/HIGH, coverage gaps, blockers. Không paste full report vào parent chat vì các turn sau sẽ re-read toàn bộ.
4. **(M2a) Self-adversarial pre-filter:** trước khi verify đắt tiền, mỗi BLOCK/HIGH → 1 skeptic cố bác bằng evidence sống. Finding yếu → DOWNGRADE hoặc DROP. Giảm load cho verify downstream.
5. **(M2b) Verify/adjudicate đối kháng:** mỗi BLOCK/HIGH còn sống → 1 stronger skeptic/adjudicator cố **bác bỏ** (mặc định "bác nếu không chắc"). Không xóa khỏi report; mark `CONFIRMED` hoặc `REJECTED` để học false-positive.
6. **Dedup** theo `(file, line-range, dimension)`; xếp severity (BLOCK/HIGH/MED/LOW/NIT — mục 6).
7. **Completeness check CÓ CHẶN:** dựng Coverage ledger `(file × chiều)`. Ô nào **không** có finding **và** **không** có attestation → re-run **chỉ ô đó** (thường 0–1 mini-wave). Lặp tối đa K=2; quá K mà vẫn trống thì ghi `UNATTESTED` (không giả vờ sạch). Mọi Confirmed requirement phải có finding **hoặc** `verified-present`.
8. Ghi **một** file findings (mục 5 schema) + Coverage ledger vào `docs/audit/<YYYY-MM-DD>/<base>.round-<N>.md`.

> Chi phí: ≈ một pass kĩ + overhead vừa. KHÔNG ×N. Mỗi reviewer chỉ nạp context của chiều nó.

## 4. FIX (mỗi vòng — phiên người chỉ đạo, trong worktree)

Đầu vào **duy nhất** = file findings. Không đi săn thêm ở phiên fix.

1. Mỗi finding `OPEN` (ưu tiên BLOCK→HIGH→MED): nghiên cứu fix, sửa **trong worktree** (không đụng `myhospital-fe|be` chính), cập nhật `status: OPEN→FIXED` + ghi commit/diff.
2. **(M3) Tự-review-diff:** chạy checklist **chỉ trên diff-fix** trước khi đóng — bắt lỗi do chính fix đẻ ra. **Không để dành** cho vòng sau.
3. Finding thực ra là **câu hỏi nghiệp vụ** (không fix bằng code) → `specs/<module>/05-open-questions.md` + Implementation Discovery Report (template trong AGENTS.md), `status: DEFERRED-Q`. **Không** tính là review-miss; cần người/BA quyết.

## 5. VERIFY (mỗi vòng — read-only)

1. Mỗi `FIXED` → kiểm đã đóng thật → `VERIFIED`; nếu hồi quy → `REOPENED`.
2. Soi **diff-fix** bằng checklist đầy đủ (code mới = bề mặt mới).
3. Còn `OPEN`/`REOPENED`/finding mới → **vào vòng sau**. Vòng sau audit **warm-start** từ Coverage ledger + findings (không roll lại ngẫu nhiên).

Đóng module khi: 0 BLOCK/HIGH `OPEN|REOPENED`; mọi DEFERRED-Q đã route; nit còn lại → backlog.

## 6. Severity (khớp AGENTS.md)

- **BLOCK** — vi phạm rule cứng / lỗi nghiệp vụ sai / mất an toàn dữ liệu. Phải fix trước khi đóng.
- **HIGH** — bug thật, sai hành vi, nhưng không phá rule cứng. Fix trong cycle.
- **MED** — đúng nhưng rủi ro/khó bảo trì. Fix nếu rẻ; nếu không → backlog có lý do.
- **LOW / NIT** — style/cosmetic. **Không** tốn vòng; gom backlog.

**Kỷ luật provenance (bắt buộc cho BLOCK/HIGH):** mỗi finding phải có ≥1 bằng chứng **sống**: `rule-hit:<tool>` (ESLint/guard/CodeGraph) · `ba-source:<trang/mục trong Tài liệu BA>` · `exemplar:<file:line>` (mẫu đúng trong code sống). **Chỉ-dựa-doc→tối đa WARN/MED**, gắn cờ "verify vs live code" — vì một số convention docs đã **stale** (xem checklist §Staleness). Finding D1 PHẢI trích dẫn **trang/mục cụ thể** trong `specs/Tài liệu Nội trú.md`, không chỉ nói "đúng spec".

**Quality gate (áp dụng trước khi finding được ghi vào report):**
- BLOCK/HIGH: PHẢI có exemplar hoặc rule-hit evidence. Doc-only → auto-downgrade MED.
- Mọi finding: location phải trỏ đúng file:line tồn tại. Nếu reviewer cite sai location → REJECTED.
- Confidence scoring: ≥2 passes đồng ý → HIGH. 1 pass + exemplar → MEDIUM. 1 pass, no exemplar → LOW.

## 7. Vòng học (giảm vòng dần theo module — sau khi đóng)

Mỗi bug-class **mới/tái diễn** → promote theo mức rẻ nhất:
1. **Deterministic được?** → guard-hook rule / ESLint rule ⇒ bắt miễn phí mãi.
2. **Convention?** → `engine/rules/frontend|backend.md` ⇒ implementer sai ít hơn (shift-left).
3. **Chiều/pattern mới?** → thêm vào [checklist.md](./checklist.md) mục "Known bug-classes" của chiều ⇒ recall/pass ↑.
4. **Lỗi agent lặp?** → auto-memory (`type: feedback`).

Checklist chín dần ⇒ recall vòng-1 ↑ ⇒ số vòng ↓ theo thời gian.

## 8. Khi >3 vòng (không tránh được — trung thực)

Scope quá lớn cho 1 audit phủ-kín → **chẻ module nhỏ**, mỗi mảnh một chu kỳ ≤3 · fix kiến trúc lan tỏa = **thay đổi mới**, không phải miss · nghiệp vụ mơ hồ = open-question cần BA · checklist non (module đầu) → recall leo dần. Đây là giới hạn thật của recall, không phải lỗi quy trình — ghi nhận, đừng giả vờ đã phủ kín.
