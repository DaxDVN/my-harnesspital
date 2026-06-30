# Owner prompt templates — gõ tự nhiên cho PM orchestrator

> Bạn KHÔNG cần nhớ skill/recipe. Chỉ nêu **intent + input (+ worktree nếu chạm source)** —
> PM tự classify, chọn (model, effort), gate-by-risk, và dispatch worker. **PM mù**: nó KHÔNG tự đọc
> file của bạn — nó giao cho analyst đọc rồi chỉ nhận summary + path.
>
> Hiện `auto_route_allowed=false` → mở đầu bằng `/pm-orchestrator`. Sau khi flip, gõ thẳng tự nhiên là đủ.

## Nguyên tắc gõ (để route ĐÚNG)
- Dùng **verb intent rõ**: `fix` → batch-bugfix · `review` → review · `verify ... chưa fix` → triage-only ·
  `build` → feature · `refactor` → refactor · `thiết kế ... chưa build` → design-only.
- ⚠️ **Đừng để chữ "review" trong câu khi ý là FIX.** (Lỗi session trước: file tên `*-review.md` + chữ "review"
  → router bắt nhầm thành review-lại.) Nói **"FIX các finding ở `<path>`"**, không "review file `<path>`".
- Nêu **path/scope** + **worktree slug** nếu chạm source.
- Việc **clinical / billing / permission / migration / irreversible** → PM sẽ **DỪNG hỏi bạn** (đúng thiết kế).

## Cheatsheet

### 1) Fix một LIST bug/finding → `batch-bugfix`
```
/pm-orchestrator
Có list bug ở: <path1>, <path2>. Adjudicate (lọc thật/giả) rồi FIX các bug thật, worktree <slug>.
```
→ PM mù → **analyst** đọc + adjudicate + tag complexity mỗi bug → fan-out **fixer theo role**
(complex=kimi-k2.7 · medium=deepseek-pro/minimax-m3 · simple/cơ-học=deepseek-flash · doc/test=mimo ·
clinical/billing/permission/migration=Opus xhigh) → **review cuối Opus xhigh (BẮT BUỘC)**. PM không tự đọc list.

### 2) Verify list, CHƯA fix → `triage-only`
```
/pm-orchestrator
Verify list finding ở <path>: cái nào thật, cái nào false-positive. CHƯA fix. Báo tổng quát.
```

### 3) Fix 1 bug đã biết → `bugfix`
```
/pm-orchestrator
Bug: <mô tả>. Repro: <bước>. Fix worktree <slug>.
```

### 4) Review trước merge → `review` (read-only)
```
/pm-orchestrator
Review module <X> (hoặc changeset worktree <slug>) trước merge.
```
→ Model trong deep-review: **D1 business-logic = Opus** (multi-pass) · **D2–D7 = glm-5.2** (read-only shim, batch-2) ·
self-adv/verify/completeness = **haiku** · phán xử BLOCK/HIGH = **Opus xhigh**. Không còn sonnet.

### 5) Fix tới sạch → `espresso`
```
/pm-orchestrator
Drive module <X> tới 0 BLOCK/HIGH (review→fix→re-review), worktree <slug>.
```

### 6) Build feature/module từ BA doc → `feature`
```
/pm-orchestrator
Build module <X> từ BA doc: <path .md/.docx>. Worktree <slug>.
```
→ distill BA (đọc 1 lần) → design (gated) → slice (gated) → fan-out implement → converge.

### 7) Đổi nhỏ (label/copy/test/doc/1 file) → PM ném cho `mimo-v2.5`
```
/pm-orchestrator
Sửa <thứ nhỏ> ở <file>, worktree <slug>.
```
→ PM **KHÔNG tự sửa** (Opus mù — giữ context tối thiểu + đỡ đốt quota) → ném cho **mimo-v2.5** (role `trivial`)
qua oc_worker → gate tsc/build → PM nhận blob. Việc cực nhỏ mà ngại cold-boot → bật `opencode serve` + `--attach`.
*(Escape hatch: muốn chính em — Claude — tự sửa tay thì nói rõ "tự sửa giúp tôi", lúc đó MỚI bỏ qua dispatch.)*

### 8) Refactor → `refactor`
```
/pm-orchestrator
Refactor <service/component X> dùng <pattern canonical>, worktree <slug>.
```

### 9) Design-only (chưa build) → `design-only`
```
/pm-orchestrator
Thiết kế API/UI cho module <X> từ requirements. CHƯA implement.
```

### 10) Thiết kế lại màn hình → `clinical-ui`
```
/pm-orchestrator
Thiết kế lại màn hình <X> (HIS UI). Cho mock direction trước khi đụng React.
```

## Prompt cho lần TEST đầu của bạn
Dùng chính 2 file findings của session trước (đổi path nếu khác):
```
/pm-orchestrator
Có list bug ở: docs/audit/2026-06-26/ipd-consultation-prescription-review.round-1.md
và docs/audit/2026-06-26/ipd-consultation-prescription-review.round-2.md.
Adjudicate rồi FIX các bug thật, worktree ipd-improve-v3.
Lưu ý F-006 chạm migration + git commit → dừng confirm với tôi trước.
```
**Quan sát 3 điểm để chấm PASS:**
1. PM **KHÔNG tự đọc 2 file** (nó dispatch analyst đọc) — context PM tối thiểu.
2. PM **dừng ở F-006** (T3 migration) hỏi bạn — không tự commit.
3. PM **giao fixer theo complexity role** (vd doc/test→mimo · service fix→deepseek-pro · clinical→Opus xhigh)
   và **kết bằng review cuối Opus xhigh** (model TQ review không thay thế).

→ Nếu 3 điểm đúng: báo tôi, tôi flip `auto_route_allowed=true` → từ đó gõ tự nhiên không cần `/pm-orchestrator`.
