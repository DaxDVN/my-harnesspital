# Đánh giá khả thi: Harness review cho MyHospital — học từ deep-research-report, hội tụ ≤ 3 vòng

> Phân tích read-only. Nguồn: `velvet/research/deep-research-report.md` (284 dòng) đối chiếu với hệ thống hiện tại (`AGENTS.md`, `CLAUDE.md`, `harness/rules/*`, `specs/_TEMPLATE/*`, `.claude/hooks/myhospital_guard.py`, `.claude/agents/myhospital-rule-auditor.md`, `docs/audit/*`). Không sửa code, không chạy build, không đụng git.
> Quy ước: **[FACT]** = kiểm chứng được trong workspace · **[INFER]** = suy luận · **[REC]** = khuyến nghị · **[UNCERTAIN]** = chưa kiểm chứng.

---

## 1. Phán quyết (Verdict)

**Không sao chép báo cáo. Mượn nguyên tắc, bỏ hạ tầng. Vấn đề hội tụ ≤ 3 vòng KHÔNG nằm trong báo cáo — phải tự thiết kế.**

- Báo cáo mô tả một **review SaaS production**: single-agent + vector DB + Semgrep/CodeQL + replay buffer + LoRA/fine-tuning + CI webhook + đội 4 người + lộ trình 6–12 tháng. **[FACT]** Sai tầm (scale) để bê nguyên về một người dùng điều phối agent (Claude/Codex) trên một monorepo.
- Báo cáo tối ưu **chất lượng finding trong production**, **không** tối ưu **số vòng review**. Nỗi đau 17 vòng / `ipd-bed-round7` của bạn là bài toán khác — báo cáo cho nguyên liệu, lời giải hội tụ là phần tôi thiết kế ở §9.
- Tin tốt: hệ thống hiện tại **đã có ~80% các lớp** mà báo cáo đề xuất, dưới dạng markdown thay vì YAML/vector DB. Việc cần làm là **kỷ luật hóa + tự động hóa quy trình**, gần như **không thêm hạ tầng mới**.

Mức độ khả thi tổng: **CAO** cho phiên bản tối giản (§8) — vì nó dựa trên primitive sẵn có (Workflow, subagent, spec files, CodeGraph, convention docs, guard hook, auto-memory). **THẤP** nếu cố dựng đúng báo cáo (vector DB/fine-tuning/CI) — không cần và không đáng ở scale này.

---

## 2. Tóm tắt điều hành

Bạn đã làm đúng bản năng: review bằng reviewer mạnh (Codex 5.5) bắt > 10 bug/lần, gom vào `.md`, phiên khác (Opus) xử lý. Cái hỏng **không phải reviewer yếu** — mà là **kiến trúc vòng lặp**:

1. **Coverage roulette [INFER, bằng chứng mạnh].** Mỗi lệnh "tìm bug" = một lần lấy mẫu LLM ngẫu nhiên từ một túi bug chưa biết kích thước, theo thứ tự **độ nổi bật (importance-first)**. Vòng 1 rút A,B,C; vòng 2 rút D,E,F (vốn đã tồn tại, chưa nổi lên). Không freeze phạm vi, không có **lưới (file × chiều kiểm tra) cố định**, không có **sổ đăng ký xuyên vòng** → đuôi bug không bao giờ cạn. Bằng chứng trong chính repo: `docs/session-notes/ipd-bed-round6-be-fixes-report.md`, `…round7-fe-report.md` **[FACT]**, và hai audit độc lập cùng một module `docs/audit/vital-sign-codebase-audit-{claude-code,codex}.md` **[FACT]** — hai reviewer mạnh quét cùng module ra tập finding khác nhau, đó vừa là **bằng chứng roulette** vừa là **thuốc chữa** (fan-out nhiều góc nhìn nâng recall).
2. **Fix gây hồi quy.** Vòng 2 sửa lỗi lại đẻ lỗi mới, vòng 3 mới thấy — vì phiên fix không tự review lại diff của chính nó theo cùng checklist.
3. **False positive gây churn.** Sửa cái-không-phải-bug làm nhiễu, đôi khi đẻ bug thật → tốn nguyên một vòng. Rủi ro này tăng vì **một số convention docs đã stale** (memory: `ARCHITECTURE-OVERVIEW.md`, `BEST-PRACTICES-NEW-PAGE.md` stale; graphify stale) — reviewer chấm theo luật cũ sẽ báo nhầm.

**Lời giải hội tụ = nâng recall MỖI lần audit bằng cấu trúc, không bằng "review kỹ hơn" hay lặp nhiều lần.** Đơn vị: **1 vòng = audit + fix + verify**; mục tiêu **≤3 vòng** (≤3 audit, ≤3 fix, ≤3 verify). 17-vòng-cũ = 17 chu kỳ trọn, không phải 17 phase rời.
- **Audit phân vùng** — mỗi lần audit chạy ~10 agent theo (chiều × lát code), song song, mù lẫn nhau → gỡ **nút cổ chai *attention*** khiến một reviewer đơn lẻ chỉ ra ~10 cái nổi nhất. **Recall vọt mà KHÔNG cần lặp.** Mót bằng *completeness check có chặn* (0–1 mini-wave, chỉ ô mỏng), không re-audit chục lần.
- **Verify đối kháng** + **kỷ luật provenance** (BLOCK/HIGH phải có bằng chứng sống: tool-hit / spec-decision / exemplar `file:line`) → diệt false positive + churn.
- **Fix tự-review-diff** — mỗi lần fix tự soi diff của chính nó bằng checklist → diệt hồi quy, không đẩy lỗi sang vòng sau.

Khi cả 3 đóng bằng cấu trúc, recall mỗi audit cao ⇒ residual rớt ε→ε²→~0 ⇒ **hội tụ ≤3 vòng cho module phạm vi gọn + checklist trưởng thành** (thường 1–2). §11 nói thẳng những lớp thay đổi mà ≤3 **không** giữ được, và tại sao đó không phải "review sót".

---

## 3. Bản đồ luận điểm báo cáo (Deep report claim map)

| # | Luận điểm báo cáo | Vị trí | Đánh giá cho hệ của bạn |
|---|---|---|---|
| C1 | "Học nhanh ở rule/memory; học chậm vào weights" — multi-layer learning | §Tóm tắt, §Bộ kỹ năng | **Đúng và là xương sống.** Ở scale bạn: weights **không bao giờ** học; 100% học ở rule/memory/checklist. |
| C2 | Single orchestrator agent > multi-agent (latency/cost/governance) | §Kiến trúc | **Đúng cho production CI; sai cho audit offline.** Audit cần recall → fan-out. Xem §6 (divergence có lý do). |
| C3 | Rule store YAML có version + path-instructions (kiểu `.coderabbit.yaml`) | §Thu nhận tri thức | **Đã có** dưới dạng markdown: `harness/rules/frontend|backend-rules-conventions-patterns.md` + convention canon. |
| C4 | AST/static: tree-sitter + Semgrep + CodeQL + linter hiện hữu | §Thu nhận tri thức | **Một phần đã có:** CodeGraph (AST/semantic) + ESLint (FE). Semgrep/CodeQL = defer. |
| C5 | 4 lớp memory: episodic / semantic / parametric / replay buffer | §Bộ nhớ | Adopt 3/4: episodic = findings `.md` + `docs/audit/*`; semantic = spec + CodeGraph; replay = checklist curation. Bỏ parametric. |
| C6 | Confidence gating + human gate cho critical finding | §Bộ kỹ năng, §Đánh giá | **Đã có mô hình** BLOCK/WARN/INFO. Thêm verify đối kháng. |
| C7 | "Continuous learning nhưng human-curated" (đề xuất rule, người duyệt) | §Thu nhận tri thức | **Đúng và khả thi ngay:** bạn promote finding tái diễn → checklist/convention docs/guard hook. |
| C8 | Một file Markdown finding duy nhất, có provenance | §Đánh giá, §Bảo mật | **Chính xác cái bạn muốn.** §10 cho schema + vòng đời status. |
| C9 | Eval harness riêng: golden PRs, negative controls, seeded defects, shadow, A/B | §Đánh giá | Defer phần nặng; adopt bản nhẹ: dual-audit (đã làm) + canary bug-class. |
| C10 | Vector DB (Qdrant/Milvus/Weaviate/Pinecone) | §Bộ nhớ | **Reject.** Một monorepo; CodeGraph + markdown + rg đủ. |
| C11 | LoRA/QLoRA/SFT/RFT/online weight update | §Continual learning | **Reject.** Không hạ tầng train, không dataset nhãn, governance đắt. |
| C12 | CI/CD webhook (GitHub App, Check Runs, required checks) | §Tích hợp | **Reject/Defer.** Không có CI (`.github/workflows` = none **[FACT]**). "PR event" thay bằng "bạn xong module → gọi review". |
| C13 | Đội 4 người, roadmap 6–12 tháng, NATS/K8s/Postgres | §Lộ trình | **Reject.** Một người; roadmap của bạn tính bằng ngày/tuần (§12). |
| C14 | PII/PHI routing: on-prem/ZDR/BYOC/CMEK | §Bảo mật | Hạ tầng = N/A (bạn chạy agent local). Nhưng **chiều review PII** (không log thẻ BHYT/CCCD/mã BN) = adopt thành 1 mục checklist. |
| C15 | Vendor specifics (OpenAI giữ data 30 ngày, Llama 2 deprecated, OpenAI đóng Evals 2026…) | rải rác | **[UNCERTAIN]** — báo cáo trích bằng marker `turnNsearchM` không mở được; không kiểm chứng được, **không** dùng làm điểm tựa thiết kế. |

---

## 4. Ma trận khả thi (Feasibility matrix)

Phân loại: **Adopt now** · **Adapt** · **Defer** · **Reject** · **UNCERTAIN**. Cột tác động đo theo *recall vòng 1* và *giảm số vòng*.

| Thành phần báo cáo | Đã có gì trong hệ | Fit | Độ phức tạp thêm | Tác động recall | Tác động số vòng | Rủi ro vận hành | Phân loại |
|---|---|---|---|---|---|---|---|
| Single orchestrator | Claude main loop + Workflow | điều phối: cao; *cho audit*: thấp | thấp | thấp | thấp | thấp | **Adapt → fan-out** (§6) |
| External memory / retrieval | CodeGraph (code) + spec + graphify (stale) | cao | thấp | trung bình | trung bình | stale-doc | **Adopt (CodeGraph) / Adapt** |
| Rule store + path-instructions | `agent-rules/*-rules-conventions-patterns.md` (538+398 dòng) + canon | rất cao | thấp | **cao** | **cao** | stale-doc | **Adopt now** |
| AST / static analysis | CodeGraph + ESLint(FE) | cao | trung bình (nếu thêm Semgrep) | trung bình | trung bình | thấp | **Adopt (sẵn) / Defer (Semgrep)** |
| Confidence gating + human gate | BLOCK/WARN/INFO model | cao | thấp | trung bình | **cao** (giảm churn) | thấp | **Adopt + verify đối kháng** |
| Replay buffer / human-curated rules | checklist curation thủ công | cao | thấp | **cao** (dài hạn) | **cao** (dài hạn) | drift checklist | **Adopt now** |
| Eval harness + seeded defects | dual-audit (`vital-sign-*`) | trung bình | trung bình | trung bình | thấp | thấp | **Adapt (nhẹ) / Defer (nặng)** |
| Single Markdown findings file | bạn đã làm tay; `docs/audit/*` | rất cao | thấp | — | **cao** (registry xuyên vòng) | schema drift | **Adopt now (cần schema)** |
| 3-round loop | chưa có cấu trúc (đang 6–7+ vòng) | — | thấp | — | **cao** | — | **Thiết kế mới (§9)** |
| Vector DB | — | thấp | cao | thấp | thấp | ops | **Reject** |
| LoRA/SFT/online weights | — | thấp | rất cao | ? | ? | governance | **Reject** |
| CI/CD webhook gate | none | thấp | cao | — | — | — | **Reject/Defer** |
| Đội 4 người / 6–12 tháng | 1 người | — | — | — | — | — | **Reject** |
| PII/PHI infra routing | local agents | N/A | — | — | — | compliance | **Reject (infra) / Adopt (1 chiều checklist)** |

---

## 5. Mượn ngay (What to borrow now)

1. **"Một file findings duy nhất, mỗi finding có ≥ 1 bằng chứng."** [C8] → schema cố định ở §10. Đây là **bộ nhớ episodic + sổ đăng ký xuyên vòng** — round 2/3 đọc nó nên không tái-khám-phá.
2. **Rule fabric phân lớp + path-instructions.** [C3] Bạn đã có `frontend/backend-rules-conventions-patterns.md` (BLOCK/WARN/INFO, pattern chuẩn). Dùng **làm context bắt buộc** nạp vào từng reviewer theo layer.
3. **"Học human-curated, không vào weights."** [C7] Sau mỗi module, promote finding tái diễn → checklist (recall ↑) / convention docs (implementer sai ít hơn = shift-left) / guard hook / ESLint (bắt miễn phí mãi mãi).
4. **Bằng chứng-bắt-buộc cho mọi finding** (rule-hit | tool-result | retrieved precedent có provenance). [C6/C8] Ở đây thành **kỷ luật provenance** (§8.E) — chống đúng lớp false-positive sinh ra do stale docs.
5. **Severity gating + human gate.** [C6] "Done" = đóng hết BLOCK/HIGH đã verify, **không** phải "0 finding". Nit → backlog, không tốn vòng.

## 6. Thích nghi (What to adapt)

1. **Single-agent → fan-out + 1 synthesizer (divergence có chủ đích).** Báo cáo chọn single-agent vì **production** (latency/cost/governance). Audit của bạn **offline**, không bị ràng latency/cost ở scale này, mục tiêu là **recall** → chạy **N reviewer độc lập** (mỗi người một chiều/layer, mù lẫn nhau) rồi **1 synthesizer** gộp. Lợi ích governance của báo cáo **vẫn giữ** vì synthesizer/Workflow là **policy loop duy nhất** quyết định cái gì vào `.md`. → Đây chính là pattern review của công cụ **Workflow** (fan-out → verify → dedup → synthesize).
2. **"Rule store YAML" → markdown sẵn có + tài liệu BA làm rule nghiệp vụ.** Rule **convention** = `agent-rules/*`. Rule **nghiệp vụ** (BHYT/BHTM/admission/bed-day) = **`specs/Tài liệu Nội trú.md`** (nguồn sự thật duy nhất). `specs/<module>/` chỉ dùng cho MVP dev (schema, API, UI), KHÔNG phải nguồn rule nghiệp vụ.
3. **Confidence gating → verify đối kháng.** Trước khi finding vào `.md`, một agent thứ hai cố **bác bỏ** nó (mặc định "bác bỏ nếu không chắc"). Sống thì giữ. Rẻ, diệt false positive.
4. **Eval nặng → eval nhẹ.** Dual-audit (bạn đã làm với `vital-sign`) = inter-rater check sẵn. Giữ cho module rủi ro cao: chạy 2 harness độc lập (Claude-workflow + Codex), diff hai tập finding; cái chỉ một bên bắt = tín hiệu lỗ hổng recall → nuôi checklist.

## 7. Loại bỏ (What to reject)

| Bỏ | Lý do |
|---|---|
| Vector DB | Một monorepo; CodeGraph + markdown + `rg` đủ; thêm DB = nợ vận hành vô ích. |
| LoRA/SFT/RFT/online weights | Không hạ tầng train, không dataset nhãn sạch, rollback khó, governance đắt. Báo cáo cũng xếp online-weight "không khuyến nghị". |
| CI/CD webhook / GitHub App / Check Runs gate | `.github/workflows` = none **[FACT]**. Trigger là "bạn xong module → gọi review", không phải PR event. |
| Multi-tenant / K8s / NATS / Postgres metadata | Hạ tầng SaaS. Bạn không vận hành dịch vụ. |
| On-prem/ZDR/BYOC routing | Bạn chạy agent local; data-routing không phải lớp bài toán này. (Giữ riêng **1 chiều review PII**.) |
| Đội 4 người, roadmap 6–12 tháng | Một người; quy mô tính bằng ngày/tuần. |

---

## 8. Harness tối giản đề xuất (Proposed minimal harness)

Tên gọi tạm: **`mh-review`** — một quy trình + một workflow, dựa hoàn toàn trên primitive sẵn có. Năm thành phần:

**A. Scope freezer (read-only).**
Đầu vào của mọi vòng. Cố định phạm vi để chống "review trôi":
- Dirty set: `git -C worktrees/<slug>/<fe|be> diff --name-only <base>` (guard hook **cho phép** `git diff`/`status` **[FACT]**).
- Blast radius: CodeGraph `impact`/`affected` trên symbol đổi → file phụ thuộc bị kéo theo.
- Spec set: `specs/<module>/{02,03,06,07,08,04}` của module.
Output: danh sách **file-group** + con trỏ requirement Confirmed.

**B. Dimension checklist (rule fabric).**
~10 chiều cho hệ này (nguồn: `agent-rules/*` + `CONVENTIONS.md` + guard hook):
1. **Nghiệp vụ** — đúng mô tả trong **`specs/Tài liệu Nội trú.md`** (BHYT/BHTM/admission/inpatient/bed-day). KHÔNG dùng `specs/<module>/02-requirements.md` làm nguồn rule nghiệp vụ.
2. **Contract/DTO/client** — không sửa tay file generated; FE client khớp BE (guard rule **[FACT]**).
3. **Convention FE** — `frontend-rules-conventions-patterns.md` (adapter, EnhancedDataGrid, không network ở UI, không global state, không tự tính tiền/tồn FE…).
4. **Convention BE** — `backend-rules-conventions-patterns.md` (BaseService, không transaction/lock, **không N+1**, 1 query/bảng/API, multi-tenant scope, soft-delete/audit auto).
5. **Đúng logic** — null/biên/race/off-by-one/error-handling.
6. **Truy cập dữ liệu** — query pattern, transaction boundary, filter declarative.
7. **Bảo mật/PII** — không log thẻ BHYT/CCCD/mã BN/payload hồ sơ (= `his.no-phi-in-logs` của báo cáo, thành 1 mục).
8. **Provider hierarchy / tái dùng component** — `component-inventory.generated.md`.
9. **Test/traceability** — mỗi Confirmed requirement có TC trong `09` + map trong `04`.
10. **Migration/schema** — không sửa tay EF migration; schema khớp `07`.

**C. Fan-out reviewer pool (Workflow).**
Phân vùng **mặc định theo chiều**: ~10 agent, mỗi agent quét **toàn diff qua 1 lăng kính**, chỉ load đúng mục convention + requirement Confirmed của chiều đó (token bounded — đây là cách giữ chi phí ≈ một pass kĩ, không ×N). Ô **nghiệp vụ rủi ro cao** → tách thêm theo file + N=2–3 reviewer (chỉ ô đó). Trả finding **có cấu trúc** (schema §10). Tier: Haiku cho chiều cơ học (style/format), Sonnet cho convention/logic, Opus cho nghiệp vụ. (Khớp "Subagents v1.0" trong CLAUDE.md.) **Recall đến từ phân vùng (gỡ nút attention), KHÔNG từ lặp lại.**

**D. Verifier + synthesizer (policy loop duy nhất).**
- Verify đối kháng từng finding (refute).
- Dedup theo `(file, line-range, dimension)`; xếp severity.
- **Completeness critic**: liệt kê ô `(file × dimension)` **không** ra finding **và** **không** có "clean attestation" → ép thêm một pass nhắm vào ô trống. **Chỉ khi mọi ô được attest** vòng 1 mới đóng. *Đây là cơ chế chống roulette.*
- Ghi **một** `.md` + Coverage ledger.

**E. Kỷ luật provenance (chống stale-doc).**
Vì có convention docs đã stale (memory `[[fe-live-conventions-vs-stale-docs]]`; graphify stale): **BLOCK/HIGH bắt buộc bằng chứng sống** — tool-hit (ESLint/guard/CodeGraph), spec-decision (`06`), hoặc **exemplar `file:line`** của pattern đúng trong code sống. Chỉ-dựa-doc → tối đa **WARN**, gắn cờ "verify vs live code". Diệt đúng lớp false-positive sinh churn.

**An toàn (không phá hệ):** Vòng 1 & 3 **read-only**, không sửa code. Fix chỉ ở vòng 2, do người chỉ đạo, trong worktree (không đụng `myhospital-fe|be` chính). Không auto-merge, không auto-fix. Guard hook đã chặn lệnh nguy hiểm cross-tool **[FACT]**. Khớp nguyên tắc "no auto-merge/no auto-fix" của báo cáo.

---

## 9. Giao thức ≤3 vòng — "vòng" = audit + fix + verify

### Đơn vị (chốt vocab với chủ harness)
- **1 vòng = audit → fix → verify** (trọn). **≤3 vòng = ≤3 audit, ≤3 fix, ≤3 verify.**
- ≤3 là **trần an toàn, KHÔNG phải quota** — thường 1–2 vòng là xong; không độn cho đủ 3.
- Cũ 17 vòng vì **recall mỗi audit thấp + ngẫu nhiên** → residual mỗi vòng lớn → lặp mãi. Mới: **nâng recall mỗi audit** → residual rớt nhanh → ≤3.

### Hai loại vòng lặp — đừng lẫn
| | Vòng NGOÀI | Vòng TRONG của 1 audit |
|---|---|---|
| Là gì | audit+fix+verify | cách 1 audit đạt recall cao |
| Chi phí | **đắt** (có người, fix thật) | **rẻ** (agent song song) |
| Mục tiêu | **giảm tối đa → ≤3** | đủ phủ, **có chặn** |
| KHÔNG phải | — | KHÔNG phải "audit lại chục lần" |

"17 lần lặp đắt ở ngoài" → gói vào **một đợt rẻ bên trong** audit. Không nhân chi phí.

### Recall đến từ PHÂN VÙNG, không từ LẶP LẠI (cốt tử)
- Audit-kĩ-một-lần kiểu cũ chỉ ra ~10 vì **nút cổ chai = attention**: một reviewer trải attention trên *(toàn diff × mọi loại lỗi)* cùng lúc → chỉ ~10 cái **nổi bật nhất** vượt ngưỡng, phần còn lại **chìm dưới ngưỡng** (không phải lười — attention hữu hạn).
- **Phân vùng** (chiều × lát code) gỡ nút: mỗi agent giữ *1 lát × 1 lăng kính* trong full-focus → không cái nào chìm → recall vọt. **Cùng lượng đọc, attention không loãng.**
- ⇒ **Lặp lại = brute-force qua nút (phí token + thời gian). Phân vùng = gỡ nút (hiệu quả).** Đây là lý do **KHÔNG cần audit chục lần**.

### AUDIT (mỗi vòng) — "1 audit thật kĩ", bên trong là MỘT đợt phân vùng
1. **Scope freeze** (§8.A): dirty set + blast radius + spec set.
2. **Một đợt fan-out theo chiều** (~10 agent, mỗi agent quét **toàn diff** qua **1 lăng kính**, chỉ load đúng mục convention + spec của chiều đó → **token bounded**). Ô **nghiệp vụ rủi ro cao** → thêm N=2–3 reviewer **chỉ cho ô đó** (không phải mọi ô).
3. **Verify đối kháng** → bỏ false positive.
4. **Dedup + severity.**
5. **Completeness check CÓ CHẶN**: critic soi ô mỏng/chưa-attest → re-run **chỉ ô đó** (thường **0–1 mini-wave**, K=1–2). **KHÔNG** re-run toàn bộ.
6. Ghi **một** `docs/audit/<module>-review-v<n>-<date>.md` + Coverage ledger.

→ Từ phía bạn: **một lần gọi audit**, trả **gần-tối-đa issue**. Chi phí ≈ *một pass kĩ + overhead vừa*, **KHÔNG ×12**.

### FIX (mỗi vòng)
1. Mỗi finding OPEN: phiên Opus effort cao nghiên cứu fix (đúng cái bạn làm), sửa trong worktree, cập nhật `status: OPEN→FIXED`.
2. **Tự-review-diff**: chạy checklist **chỉ trên diff-fix** trước khi đóng — bắt lỗi do chính fix đẻ ra, **không để dành** cho vòng sau.
3. Finding là **câu hỏi nghiệp vụ** (không fix bằng code) → `05-open-questions.md` + Implementation Discovery Report (template đã có **[FACT]**), đánh dấu `DEFERRED-Q`, **không** tính là review-miss.

### VERIFY (mỗi vòng)
1. Mỗi FIXED → kiểm đã đóng thật (`→VERIFIED`); hồi quy → `REOPENED`.
2. Soi **diff-fix** bằng checklist đầy đủ (code mới = bề mặt mới).
3. Còn OPEN/REOPENED → **vào vòng sau** (đó là lý do tồn tại vòng 2, 3 — không phải audit lại từ đầu một cách mù).

### Trí nhớ xuyên vòng (mảnh 17-vòng-cũ THIẾU)
Coverage ledger + findings.md **mang sang vòng sau**. Audit vòng 2 **warm-start**: biết vòng 1 mỏng chỗ nào → soi đúng đó + diff-fix, **không roll ngẫu nhiên**. Loop cũ không có trí nhớ → mỗi audit roll mới từ đầu → batch ngẫu nhiên mãi → 17.

### Vì sao ≤3 + chi phí bounded
audit#1 phân vùng ⇒ recall cao ⇒ residual vào vòng 2 **bé**. fix tự-review ⇒ ít regression ⇒ audit#2 không bận lỗi-do-fix. ⇒ residual **ε → ε² → ~0** ⇒ **thường 1–2 vòng, trần 3**. Tổng chi phí ≈ *(≤3) × (một audit phân vùng)*, **không phải** *17 × (audit ngẫu nhiên lặp)*.

### Sơ đồ
```
VÒNG NGOÀI (≤3 · đắt · có người)
┌─ Vòng 1 ───────────────────────────────────────────────┐
│ AUDIT#1  = MỘT đợt phân vùng (rẻ · song song · có chặn)  │
│   scope freeze                                          │
│   ├ ~10 agent ∥  (1 chiều × toàn diff)        ┐        │
│   ├ +N=2-3 reviewer cho ô nghiệp vụ rủi ro    │ 1 đợt  │
│   ├ verify đối kháng (refute → bỏ false-pos)  │ fan-out│
│   ├ dedup + severity                          ┘        │
│   └ completeness check (K=1-2 mini-wave · CHỈ ô mỏng)  │
│   → findings.md + coverage ledger                      │
│ FIX#1     sửa + TỰ-REVIEW-DIFF                          │
│ VERIFY#1  đóng? + soi diff-fix                          │
└──────────────────────────────────────────────────────────┘
        ↓ residual bé  (ledger + findings.md mang sang)
┌─ Vòng 2 ─ audit#2 warm-start → fix → verify ──┐  ra RẤT ít
└─ Vòng 3 ─ lưới an toàn ───────────────────────┘  ≈ 0 → đóng module
```

### Khi >3 vòng (trung thực — không tránh được)
Scope quá lớn cho 1 audit phủ-kín → **chẻ module nhỏ**, mỗi mảnh một chu kỳ ≤3 · fix kiến trúc lan tỏa = **thay đổi mới**, không phải miss · nghiệp vụ mơ hồ = open-question cần BA · checklist non (module đầu) → recall leo dần. Giới hạn thật, không phải lỗi quy trình.

---

## 10. Thiết kế Memory / Rule / Eval

### 10.1 Schema file findings (interchange, tool-agnostic — Claude & Codex dùng chung)
Đóng băng schema này trong `AGENTS.md` (cross-tool source of truth) để Codex và Claude không lệch định dạng.

```markdown
# Review — <module> — Round <n> — <YYYY-MM-DD>
scope_base: <sha>          dirty_files: [<path>...]      checklist_version: <vX>
reviewer_runs: [claude-workflow | codex | ...]

## Coverage ledger
| file-group | dim1 | dim2 | ... | dim10 |   (mỗi ô: F-id | CLEAN | N/A)

## Findings
### F-001
severity: BLOCK|HIGH|MED|LOW|NIT
dimension: <1..10>
location: <file:line>
title: <1 dòng>
evidence: rule-hit:<tool> | spec:<DL-00x/REQ-id> | exemplar:<file:line>   # bắt buộc ≥1 cho BLOCK/HIGH
root_cause: <...>
fix: <khuyến nghị, KHÔNG quyết định nghiệp vụ>
status: OPEN|FIXED|VERIFIED|REJECTED|DEFERRED-Q|REOPENED
round_found: <n>   verified_by: <run>
```

File này = **episodic memory** (báo cáo C5) + **registry xuyên vòng**. Coverage ledger = bằng chứng chống roulette: ô trống nhìn thấy được.

### 10.2 Rule layer (ổn định, sống lâu)
- **Convention:** `agent-rules/frontend|backend-rules-conventions-patterns.md` + `myhospital-fe/CLAUDE.md` + `myhospital-be/CONVENTIONS.md`.
- **Nghiệp vụ:** spec `02/06/04` của module.
- **Deterministic (free):** guard hook (25 rule **[FACT]**) + ESLint(FE).
- **[REC → ĐÃ DỰNG]** `checklist.md` = danh sách 10 chiều (B) + bug-class tích lũy — đã build trong bundle **`.claude/skills/mh-review/`** (KHÔNG ở `harness/rules/` — review tách thành tầng riêng). "rule store có version" dạng markdown, version bằng git.

### 10.3 Vòng học human-curated (làm số vòng giảm dần theo thời gian — C7)
Sau mỗi module, với mỗi finding **mới/tái diễn**, route theo mức rẻ nhất:
1. **Deterministic được?** → thêm guard-hook rule / ESLint rule ⇒ bắt miễn phí, **không bao giờ** thành finding nữa.
2. **Convention?** → thêm vào `agent-rules/*` ⇒ implementer sai ít hơn (**shift-left** = đòn giảm vòng mạnh nhất dài hạn).
3. **Chiều kiểm tra mới?** → thêm vào `review-checklist.md` ⇒ recall/pass ↑.
4. **Lỗi agent lặp?** → auto-memory (`type: feedback`).
Theo module, checklist trưởng thành ⇒ recall vòng-1 ↑ ⇒ số vòng ↓. **Đây là câu trả lời cho "giảm vòng toàn dự án, không chỉ một module".**

### 10.4 Eval (nhẹ)
- **Dual-harness** cho module rủi ro cao: Claude-workflow ⟂ Codex, diff 2 tập finding (bạn đã làm với `vital-sign` **[FACT]**). Finding một-bên = lỗ hổng recall → nuôi checklist.
- **[REC, defer]** Canary: giữ list nhỏ bug-class quá khứ (từ `docs/audit/*`); thỉnh thoảng tiêm 1 vào nhánh test, xác nhận harness còn bắt. Bỏ được nếu bận — dual-audit đã cho phần lớn giá trị.

---

## 11. Rủi ro / Blocker — và khi nào ≤ 3 KHÔNG giữ được

| # | Rủi ro | Tác động | Giảm thiểu |
|---|---|---|---|
| R1 | **Trần context/token**: lưới `(file×dim)` của module lớn vượt 1 workflow | audit vòng 1 không phủ kín | **Chia theo module/layer**; mỗi sub-scope một chu kỳ ≤3 riêng. Đây là lý do #1 vẫn > 3 vòng — **scope to, không phải review sót**. |
| R2 | **Convention docs stale** → finding nhầm → churn | đẻ vòng thừa | Kỷ luật provenance §8.E; trust-mark docs; ưu tiên exemplar code sống. **[FACT]** stale: `[[fe-live-conventions-vs-stale-docs]]`, graphify. |
| R3 | **Spec mơ hồ**: "finding" thật ra là câu hỏi nghiệp vụ BHYT | không sửa được bằng code | Route `05-open-questions` + Discovery Report, `DEFERRED-Q`, **không** tính vòng. Cần người/BA quyết. |
| R4 | **Trần recall** với logic mới/tinh vi | sót dù fan-out | Fan-out + checklist *giảm* không *triệt*. Rủi ro tồn dư — chấp nhận, ghi nhận. |
| R5 | **Schema findings lệch giữa tool** | `.md` hỏng vai trò interchange | Đóng băng schema §10.1 trong `AGENTS.md`. |

**Khi > 3 vòng là KHÔNG TRÁNH ĐƯỢC (trả lời thẳng yêu cầu):**
1. **Thay đổi quá lớn** cho một audit phủ-kín → chẻ nhỏ (mỗi mảnh ≤3).
2. **Fix vòng 2 mang tính kiến trúc/lan tỏa** → tạo bề mặt *thực sự mới* = một thay đổi mới = chu kỳ mới, **không phải bug sót**.
3. **Nghiệp vụ mơ hồ** → open question, cần BA/người quyết, không "fix" trong vòng được.
4. **Checklist còn non** (vài module đầu) → recall leo dần khi checklist chín; module đầu có thể cần 1 pass thêm.
5. **Logic mới lạ vượt trần recall** → tồn dư, giảm không triệt.

**Năng lực còn thiếu để kéo các case trên xuống ≤ 3:** công cụ phủ **xác định** (Semgrep/CodeQL/test thật) cho recall-guarantee theo lớp cụ thể, **và** một checklist trưởng thành. Tới khi có: **≤ 3 giữ vững cho module gọn + checklist chín; việc lớn/mới-lạ/mơ-hồ thì không** — và đó là giới hạn trung thực, không phải lỗi quy trình.

---

## 12. Lộ trình theo pha (ngày/tuần, không phải 6–12 tháng)

| Pha | Việc | Hạ tầng mới | Cắt nếu hẹp |
|---|---|---|---|
| **0 — Now** | Viết `review-checklist.md` (10 chiều) + đóng băng schema findings (§10.1) vào `AGENTS.md`. Viết giao thức 3 vòng thành SOP/skill. | 0 | giữ |
| **1 — Workflow** | Mã hóa vòng 1 thành Workflow script: fan-out → verify đối kháng → dedup → ghi `.md` + Coverage ledger + completeness critic. Nạp `agent-rules/*` + spec + CodeGraph làm context reviewer. | 0 (dùng Workflow sẵn) | giữ coverage ledger + provenance |
| **2 — Learning loop** | Sau mỗi module: promote finding → checklist/convention/guard/ESLint. Thêm kỷ luật trust/freshness cho docs. | 0 | giữ |
| **3 — Optional** | Semgrep/ast-grep cho vài pattern xác định giá trị cao mà guard không biểu diễn được; dual-harness eval cho module rủi ro cao. | Semgrep (nhẹ) | **cắt trước tiên** |

**Thứ tự cắt nếu phải thu hẹp:** bỏ Semgrep + eval trước; **không bao giờ** bỏ Coverage ledger + provenance — đó là hai thứ trực tiếp tạo hội tụ.

---

## 13. Bằng chứng (Evidence)

- **[FACT]** Báo cáo 284 dòng, kiến trúc production: `velvet/research/deep-research-report.md:5-11` (multi-layer learning, single orchestrator, stack vector DB + Semgrep/CodeQL + PEFT), `:226-237` (đội 4 người, K8s/NATS), `:239-257` (Gantt 6–12 tháng).
- **[FACT]** Bằng chứng đa vòng trong repo: `docs/session-notes/ipd-bed-round6-be-fixes-report.md`, `…round7-fe-report.md` (round 6, 7).
- **[FACT]** Bằng chứng roulette + cure (dual reviewer cùng module): `docs/audit/vital-sign-codebase-audit-claude-code.md` (63.5KB), `…-codex.md` (61.1KB), `…-dirty-changeset-audit-2026-06-15.md`.
- **[FACT]** Rule fabric đã tồn tại: `harness/rules/frontend-rules-conventions-patterns.md` (538 dòng), `backend-rules-conventions-patterns.md` (398 dòng), `myhospital-be/CONVENTIONS.md` (260 dòng), `myhospital-fe/CLAUDE.md` (37 dòng).
- **[FACT]** Checklist + traceability skeleton: `specs/_TEMPLATE/11-review-checklist.md`, `04-traceability.md`, `09-test-cases.md`, `06-decision-log.md`.
- **[FACT]** Reviewer agent: `.claude/agents/myhospital-rule-auditor.md` (Haiku, read-only, BLOCK/WARN/OK). Guard hook: `.claude/hooks/myhospital_guard.py` (283 dòng, 25 rule, cho phép `git diff`, chặn `git commit/push/reset`, `rm -r`, sửa file generated). Self-test 38 case.
- **[FACT]** Không có CI: `.github/workflows` = none. ESLint chỉ FE: `myhospital-fe/eslint.config.js`. Không coverage tooling.
- **[FACT]** Stale knowledge: memory `[[fe-live-conventions-vs-stale-docs]]` (ARCHITECTURE-OVERVIEW.md, BEST-PRACTICES-NEW-PAGE.md stale); graphify Windows-stale (CLAUDE.md, harness_doctor).
- **[INFER]** Cơ chế 17-vòng = coverage roulette + thiếu registry + fix-regression + false-positive churn (§2). Suy từ pattern round6/7 + dual-audit khác tập finding.
- **[REC]** Toàn bộ §8–§12.

## 14. Điều chưa chắc (Uncertainties)

- **[UNCERTAIN]** Mọi vendor-claim trong báo cáo (OpenAI giữ data 30 ngày, ZDR, Llama 2 "deprecated", OpenAI đóng Evals 2026, đặc tả Qdrant/Milvus/Weaviate/Pinecone) — trích bằng marker `turnNsearchM` **không mở được**. Không kiểm chứng, **không** dùng làm điểm tựa thiết kế. Nếu sau này cần fine-tuning/vendor thì phải verify lại bằng doc chính thức.
- **[UNCERTAIN]** Recall thực tế của fan-out + checklist trên *module mới lạ* (R4) — chỉ đo được sau vài module chạy thật + dual-harness. Không có con số phần trăm hứa trước.
- **[UNCERTAIN]** Trần token chính xác cho module lớn nhất (R1) — phụ thuộc kích thước diff; cần thử để biết ngưỡng chẻ scope.
- **[UNCERTAIN]** ESLint hiện cấu hình "recommended" tới đâu (chỉ thấy `eslint.config.js` 29 dòng); mức phủ rule deterministic FE chưa rõ — ảnh hưởng bao nhiêu chiều "bắt được miễn phí".
- **[UNCERTAIN]** `careflow_ba_fixes_smoke.py` có còn dùng không (inventory ghi "appears unused") — không ảnh hưởng thiết kế.

---

### TL;DR
Đừng xây lại báo cáo. Bạn đã có rule fabric + checklist + reviewer agent + CodeGraph + Workflow + guard hook. Thiếu **một thứ**: **kỷ luật vòng lặp**. 1 vòng = audit+fix+verify; mục tiêu ≤3 vòng. Lắp 3 cơ chế — *audit phân vùng (recall cao mỗi lần, KHÔNG lặp — gỡ nút attention)* · *verify đối kháng + provenance* · *fix tự-review-diff* — và **promote finding vào checklist/convention sau mỗi module**. Đường từ 17 vòng xuống ≤3 = **nâng recall mỗi audit bằng phân vùng**, cộng đường giảm vòng dần theo module.
