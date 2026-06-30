# Harness Restructure Plan — dọn dẹp + hợp nhất

> **Ngày:** 2026-06-16 · **Loại:** PLAN (chưa execute — chờ bạn duyệt) · **Tác giả:** Claude (Opus max).
> **Nguồn tổng hợp:** worklog BE `mh-harness-build-log-2026-06-15.md` + worklog FE `fe-harness-build-worklog-2026-06-16.md` + full inventory (read-only) + 2 lượt trao đổi taxonomy.
> **Mục tiêu:** dọn harness lộn xộn thành 1 cấu trúc rõ, KHÔNG gãy `harness_doctor`/scripts, theo đúng taxonomy bạn chốt.

---

## ✅ QUYẾT ĐỊNH ĐÃ CHỐT (2026-06-16) — phần này SUPERSEDE mọi đề xuất `.claude/rules/` bên dưới

1. **Nhà rule = vùng TRUNG LẬP `harness/` (top-level), KHÔNG phải `.claude/`** — vì bạn muốn MỌI agentic tool (Claude, Codex, opencode, Cursor…) đọc+apply được, không riêng Claude. `.claude/` chỉ là wiring Claude-specific.
2. Mở rộng nguyên tắc trung lập: **review knowledge** (`protocol.md`, `checklist.md`, `findings-schema.md`) cũng ra `harness/review/` cho mọi tool đọc native; chỉ giữ `SKILL.md`+`workflow.js` (driver Claude) trong `.claude/skills/mh-review/`.
3. Chạy **Stage 1–3 luôn**, backup+doctor gate. Stage 4 = bạn (PR repo main). Giữ **cả mh-scaffold + mh-implement** (ghi rõ ranh giới).

**Cấu trúc đích MỚI:**
```
roast/
├── harness/                 ← 🆕 TRUNG LẬP, mọi tool đọc theo path (AGENTS.md trỏ vào)
│   ├── rules/                 ← docs/agent-rules/* (convention canon + policy)
│   ├── review/                ← protocol/checklist/findings-schema (từ .claude/skills/mh-review/)
│   └── README.md              ← precedence + bản đồ wiring từng tool
├── .claude/ .codex/ .opencode/  ← wiring TỪNG tool (skill/agent/hook/plugin) → trỏ vào harness/
├── scripts/                  ← automation trung lập (mọi tool chạy python scripts/…)
├── docs/                     ← tham khảo (+ harness/{plans,pending,notes} gom tài liệu harness)
└── specs/                    ← nghiệp vụ
```

**Đính chính baseline (doctor xác nhận, inventory sai 3 điểm):** CLAUDE.md routing BE→CONVENTIONS.md **đúng** (không có ref gãy tới `myhospital-be/CLAUDE.md`); CodeGraph **đã index** cả 2 repo; opencode-guard **đã cài**. → Stage 5 phần lớn xong; Stage 2 chỉ làm rõ precedence (giữ CONVENTIONS.md được doctor `routing:claude-md` nhắc tới để không gãy check).

**Lưu ý Stage 3:** `harness_doctor.py` check `docs/agent-rules/source-discovery.md` (codegraph-policy) + AGENTS/CLAUDE refs → phải update path trong chính `harness_doctor.py` khi move.

---

## ✅ ĐÃ THỰC THI 2026-06-16 — Stage 1–3 XONG (doctor 39 OK · 1 WARN cố ý · 0 FAIL · ZERO ref gãy)

- **`harness/` tạo (TRUNG LẬP):** `rules/` = 5 file convention+policy (từ `docs/agent-rules/`) + `README.md` precedence; `review/` = protocol+checklist+findings-schema (từ `.claude/skills/mh-review/`); `harness/README.md` = bản đồ wiring từng tool. `.claude/skills/mh-review/` còn lại `SKILL.md`+`workflow.js` (driver Claude).
- **Dọn docs:** `harness/{plans,notes,pending}` gom 14 file harness khỏi `docs/tasks` + `docs/session-notes`. `docs/tasks/` giờ chỉ còn plan feature.
- **~25 ref cập nhật** (AGENTS/CLAUDE/4 skill/3 agent/scripts/memory) — `docs/agent-rules/`→`harness/rules/`, review-knowledge→`harness/review/`. Grep stale = **0**. `harness_backup.py` đã include `harness/`. `harness_doctor` `codegraph-policy` trỏ `harness/rules/source-discovery.md` ✓.
- **CÒN LẠI = Stage 4 (BẠN, repo main):** apply `harness/pending/CONVENTIONS.fixed.md` → BE; `harness/pending/fe-main-repo-diffs-2026-06-16.md` → FE; vá 38 endpoint thiếu auth. WARN doctor sẽ tắt sau khi vá CONVENTIONS.md.

> §3/§4 bên dưới là **kế hoạch gốc** (đề xuất `.claude/rules/`) — đã **SUPERSEDE** bởi quyết định `harness/` trung lập ở block trên; giữ làm lịch sử.

---

## 0. Nguyên tắc (taxonomy bạn chốt → 4 vùng)

| Vùng | Là gì | Folder |
|---|---|---|
| **Não harness** | thứ agent ĐỌC/CHẠY: skill, agent, hook, **rule/convention** | **`.claude/`** (Claude-discover; cross-tool đọc theo path) |
| **Cánh tay automation** | script harness | **`scripts/`** (giữ nguyên — đã gọn, move = gãy nhiều) |
| **Tham khảo** | tài liệu người đọc: worklog, memo, audit, guide | **`docs/`** |
| **Nghiệp vụ** | spec SDD | **`specs/`** |

Harness **xoay quanh** `myhospital-fe` + `myhospital-be`, **nằm trong** `roast/`. Ngoài roast = không phải harness.

**Lệch lớn nhất hiện tại:** rule/convention (canon) đang nằm trong `docs/agent-rules/` = vùng "tham khảo" → phải đưa vào "não harness".

---

## 1. Hiện trạng (đã build, validate thật — doctor 39 OK/1 WARN/0 FAIL)

Vòng đời harness đầy đủ, **đã chạy được**:

```
mh-scaffold ──▶ mh-implement ──▶ mh-fix ──▶ mh-review
(template)      (build feature)   (sửa bug)   (audit ≤3 vòng)
     └──────── chống lưng ────────┘
  mh_scan (quét FE+BE) · convention_truth (dò lệch doc) · guard (tripwire+advisory)
  · harness_doctor (sức khỏe) · agent-rules (convention canon)
```

**Đã có (BUILT):** 4 skill (`mh-review/implement/fix/scaffold`) · 3 agent (`mh-reviewer/implementer`, `myhospital-rule-auditor`) · `scripts/mh_scan/` (13 scanner BE + bridge FE) · `scripts/sgconfig/` (7 rule ast-grep FE) · `scripts/convention_truth.py` · guard hook (block+advisory) · `harness_doctor.py` (16 check) · agent-rules canon (BE 398 + FE 553 dòng).

**Chờ BẠN apply (đụng repo main — agent không tự làm):** `harness/pending/CONVENTIONS.fixed.md` → BE · `harness/pending/fe-main-repo-diffs-2026-06-16.md` → FE (gói ESLint) · vá 38 endpoint thiếu auth.

---

## 2. Vấn đề (ưu tiên giảm dần)

| # | Vấn đề | Bằng chứng | Mức |
|---|---|---|---|
| P1 | **Rule/convention canon nằm trong vùng "tham khảo"** `docs/agent-rules/` | bạn nêu 2 lần | 🔴 |
| P2 | **Canon trùng/lệch**: `agent-rules/*` (canon, đúng) vs `myhospital-be/CONVENTIONS.md` (lệch D1–D6) vs `myhospital-fe/CLAUDE.md` (stub 37 dòng). Root `CLAUDE.md` còn route "obey `myhospital-be/CLAUDE.md`" — **file này KHÔNG tồn tại** | inventory §7A, §7D | 🔴 |
| P3 | **`docs/tasks/` lẫn lộn**: 4 file harness (2 plan + CONVENTIONS.fixed + fe-diffs) trộn ~22 plan feature | `ls docs/tasks` | 🟠 |
| P4 | **Harness worklog/memo rải `docs/session-notes/`** lẫn report linh tinh | 9 file harness-* | 🟠 |
| P5 | **Pending-apply staging** (`CONVENTIONS.fixed.md`, `fe-main-repo-diffs`) nằm như "plan" — thực ra là patch chờ apply, không có nhà riêng | inventory §6 | 🟡 |
| P6 | **mh-scaffold vs mh-implement chồng nhau** một phần | worklog BE §4.3 #6 | 🟡 |
| P7 | **Wiring chưa xong**: opencode guard cần symlink tay · CodeGraph chưa init · graphify stale | inventory §7G,D | 🟡 |
| P8 | **FE doc stale** (`ARCHITECTURE-OVERVIEW.md`, `BEST-PRACTICES-NEW-PAGE.md`) chưa gắn banner | audit V10 | 🟡 |
| P9 | **Naming** `mh_scan` (snake) vs `mh-*` (kebab) | inventory §7B | ℹ️ |

---

## 3. Cấu trúc ĐÍCH (đề xuất — tôi quyết, bạn duyệt)

```
roast/                                    ← harness root, orbit fe+be
├── myhospital-fe/  myhospital-be/        ← 2 project (KHÔNG đụng)
│
├── .claude/                              ← 🧠 NÃO HARNESS (toàn bộ thứ agent đọc/chạy)
│   ├── skills/   mh-review/ mh-implement/ mh-fix/ mh-scaffold/
│   ├── agents/   mh-reviewer.md  mh-implementer.md  myhospital-rule-auditor.md
│   ├── hooks/    myhospital_guard.py  graphify_stale_check.py
│   ├── rules/    ← 🆕 NHÀ MỚI cho convention/policy (chuyển từ docs/agent-rules/)
│   │   ├── backend-rules-conventions-patterns.md     (CANON BE — giữ tên)
│   │   ├── frontend-rules-conventions-patterns.md    (CANON FE — giữ tên)
│   │   ├── source-discovery.md  cross-tool-enforcement.md  worktree-workflow.md
│   │   └── README.md   ← 🆕 chốt precedence: rules/ = sự thật duy nhất; repo doc = con trỏ
│   └── settings.json  settings.local.json
│
├── scripts/                              ← 🦾 AUTOMATION (GIỮ NGUYÊN — move = gãy nhiều)
│   ├── mh_scan/   sgconfig/   convention_truth.py
│   ├── harness_doctor.py  worktree.py  migrate_harness.py  harness_backup.py
│   └── opencode/  fish/  zellij/
│
├── docs/                                 ← 📚 THAM KHẢO (thuần)
│   ├── audit/         ← output review (mh-review ghi ra đây)
│   ├── session-notes/ ← report/notes KHÔNG phải harness
│   ├── tasks/         ← CHỈ còn plan FEATURE (ipd-*, bhtm-*, vital-*…)
│   └── harness/       ← 🆕 gom mọi tài liệu harness
│       ├── plans/     agentic-harness-dev-fix-plan · mh-harness-from-be-audit-plan · plan này
│       ├── worklogs/  mh-harness-build-log · fe-harness-build-worklog · review-harness-feasibility · *harness-review*
│       └── pending/   🆕 patch chờ bạn apply: CONVENTIONS.fixed.md · fe-main-repo-diffs.md
│
├── specs/                                ← 🏥 NGHIỆP VỤ SDD (KHÔNG đụng)
└── AGENTS.md  CLAUDE.md  justfile        ← dispatcher gốc + automation
```

### Quyết định đã chốt (lý do)
1. **Rule → `.claude/rules/`** (không phải top-level `rules/`): gom trọn não harness vào `.claude/` — nơi skill/agent/hook BẮT BUỘC ở (Claude mới discover). Cross-tool vẫn đọc theo path. `rules/` KHÔNG phải subdir reserved của Claude → an toàn, không bị tự diễn giải.
2. **`scripts/` giữ nguyên**: đã là 1 nhà gọn cho automation; move = sửa justfile + doctor self-check + migrate FIXUP + fish + README… rủi ro cao, lợi ích thấp.
3. **Giữ CẢ `mh-scaffold` + `mh-implement`** (không gộp): scaffold = phát template rời; implement = orchestrate feature đầy đủ và *gọi* scaffold ở B3. Bổ trợ, không trùng lõi. Sẽ ghi rõ ranh giới ở đầu mỗi SKILL.md.
4. **CONVENTIONS.md + FE CLAUDE.md → con trỏ mỏng** trỏ về `.claude/rules/` (hết drift vĩnh viễn) — NHƯNG cần PR (repo main), nên là **việc pending của bạn**, không phải tôi.
5. **Naming `mh_scan` snake giữ nguyên** (đúng chuẩn Python module); `mh-*` kebab cho skill/agent. Ghi chú trong `scripts/README.md`.

---

## 4. Migration theo STAGE (rủi ro thấp → cao; mỗi stage backup + validate)

> **Trước MỖI stage:** `python scripts/harness_backup.py` (snapshot rollback). **Sau MỖI stage:** `python scripts/harness_doctor.py` phải GIỮ 0 FAIL + `python scripts/mh_scan --self-test` pass + `grep` 0 ref gãy. FAIL → rollback từ snapshot.

### STAGE 1 — Dọn `docs/` (🟢 rủi ro thấp; không đụng code/scripts)
**Move:**
- `docs/tasks/{agentic-harness-dev-fix-plan,mh-harness-from-be-audit-plan}-*.md` + plan này → `harness/plans/`
- `docs/session-notes/{mh-harness-build-log,fe-harness-build-worklog,review-harness-feasibility,*harness-review*,harness-*,independent-harness-*,gemini*harness*}.md` → `harness/worklogs/`
- `harness/pending/CONVENTIONS.fixed.md` + `harness/pending/fe-main-repo-diffs-2026-06-16.md` → `harness/pending/`
- Giữ nguyên: plan feature trong `docs/tasks/`, `docs/audit/`, report không-harness trong `docs/session-notes/`.

**Update ref** (các file TRỎ tới file vừa move):
- Memory `~/.claude/.../memory/*.md` (review-harness-convergence, agentic-dev-fix-harness-plan, be-conventions-doc-drift) → sửa path.
- 2 worklog trỏ chéo nhau + trỏ feasibility memo + trỏ plan → sửa.
- `AGENTS.md` mục "Review Harness": path feasibility memo.
- `scripts/harness_doctor.py` / `migrate_harness.py` nếu hard-code path nào trong số này.

**Validate:** `grep -rn "docs/tasks/CONVENTIONS.fixed\|docs/tasks/.*harness\|session-notes/.*harness\|session-notes/review-harness"` → 0 (trừ trong chính file đã move). doctor xanh.

### STAGE 2 — Sửa canon precedence (🟡 trung bình; CHỈ file harness, không repo main)
**Tôi làm được ngay (không cần PR):**
- **Root `CLAUDE.md` §Routing:** bỏ "obey `myhospital-be/CLAUDE.md`" (file không tồn tại) → "BE canon = `.claude/rules/backend-rules-conventions-patterns.md`; `myhospital-be/CONVENTIONS.md` chỉ tham khảo, có drift". Sửa FE tương tự.
- **`mh-review/checklist.md` D2/D3 Sources:** ưu tiên `.claude/rules/*` lên đầu, hạ `CONVENTIONS.md`/`CLAUDE.md` xuống "tham khảo, verify vs live code".
- **Tạo `.claude/rules/README.md`:** chốt thứ tự sự thật: live code > `.claude/rules/*` (canon) > repo doc (con trỏ) > memo. Liệt kê 6 drift D1–D6 đã biết.

### STAGE 3 — Dời rule vào não harness (🔴 cao; ~20 ref — pass cẩn thận)
**Move:** cả 5 file `docs/agent-rules/*` → `.claude/rules/` (**giữ nguyên tên** → chỉ đổi prefix path, giảm churn).

**Update ref — thay prefix `docs/agent-rules/` → `.claude/rules/` ở:**
- `AGENTS.md`, `CLAUDE.md` (root) — nhiều chỗ.
- 4 skill: `mh-review/{checklist,protocol}.md`, `mh-fix/SKILL.md`, `mh-implement/SKILL.md`, `mh-scaffold/SKILL.md`.
- 3 agent: `mh-reviewer.md`, `mh-implementer.md`, `myhospital-rule-auditor.md`.
- scripts: `convention_truth.py` (đọc backend-rules doc), `harness_doctor.py` (check tồn tại source-discovery.md), `migrate_harness.py` (FIXUP_FILES list worktree-workflow.md), `scripts/README.md`, `scripts/WORKTREE-TOOLING.md`, `scripts/opencode/myhospital-guard.js`.
- Cross-ref nội bộ trong chính 5 file (vd worktree-workflow ↔ source-discovery).
- Lịch sử (`docs/.../worklog`, `docs/audit/*codex*`, `graphify-agent-guide.md`): cập nhật để link không gãy (đây là snapshot — chấp nhận sửa path cho liền mạch).

**Validate:** `grep -rn "docs/agent-rules" .` → **0**. `harness_doctor` 0 FAIL (đặc biệt check `convention-truth`, `mh-scan:selftest`, routing). `python scripts/convention_truth.py` chạy được (đường dẫn doc mới). `python scripts/mh_scan --self-test` pass.

### STAGE 4 — Pending repo main (⚠️ CHỈ BẠN làm — agent cấm đụng fe/be)
Để trong `harness/pending/`, làm qua worktree docs-only + PR:
1. Apply `CONVENTIONS.fixed.md` → `myhospital-be/CONVENTIONS.md` (6 sửa D1–D6) → rồi rút thành **con trỏ** trỏ `.claude/rules/`. Sau đó `python scripts/convention_truth.py` → 0 FAIL (doctor WARN biến mất).
2. Apply `fe-main-repo-diffs.md` → FE (gói **ESLint** = giá trị cao nhất; gỡ `create:page` hỏng; banner stale; xóa 14 `.v2.bak`; `rsc:false`).
3. Vá **38 endpoint thiếu `[RequireAuth]`** (whitelist cái public-by-design trong `scanners.py` trước, vá phần còn lại).

### STAGE 5 — Wiring follow-up (🟡 tùy chọn, không chặn)
- opencode guard: thêm recipe `just opencode-install` symlink `scripts/opencode/myhospital-guard.js` → `~/.config/opencode/plugin/`.
- CodeGraph: `just codegraph-init-main` (cả 2 repo) — bật lợi thế source-discovery.
- graphify: rebuild Linux bằng `/graphify` khi cần, hoặc ghi "deprecated nếu ít dùng".
- P8: gắn banner stale lên 2 FE doc (qua fe-diffs Stage 4).

---

## 5. Thứ tự thực thi đề xuất

```
backup → STAGE 1 (docs) → doctor✓ → STAGE 2 (canon fix) → doctor✓
       → STAGE 3 (rules→.claude/rules) → doctor✓ + grep 0 + selftest✓
       → [bàn giao Stage 4 cho bạn: PR repo main]
       → STAGE 5 (wiring, khi rảnh)
```

Stage 1–3 = tôi làm trong roast (an toàn, có backup + doctor gate). Stage 4 = bạn (repo main). Stage 5 = tùy.

## 6. Rủi ro + rollback

- **Rollback:** mỗi stage có snapshot `harness_backup.py` → khôi phục nếu doctor FAIL.
- **Rủi ro chính = Stage 3** (ref gãy). Giảm thiểu: đổi-prefix cơ học + `grep "docs/agent-rules"` phải về 0 + `harness_doctor`/`convention_truth`/`mh_scan --self-test` làm cổng nghiệm thu.
- **Không đụng** `myhospital-fe/`, `myhospital-be/`, `worktrees/`, `specs/` trong Stage 1–3.
- **Git:** không commit/push (theo guard) — bạn review rồi tự commit.

## 7. Quyết định cần bạn xác nhận trước khi tôi chạy

1. **Nhà rule = `.claude/rules/`?** (khuyến nghị) hay muốn top-level `rules/` / tên khác?
2. **Chạy Stage 1–3 luôn không** (có backup + doctor gate), hay làm từng stage chờ duyệt giữa chừng?
3. **mh-scaffold + mh-implement:** giữ cả hai (khuyến nghị) hay gộp?
4. Stage 4 (PR repo main) bạn tự làm — OK chứ?

Chốt 4 câu trên → tôi execute Stage 1–3.
