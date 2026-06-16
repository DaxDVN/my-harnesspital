# Hướng dẫn sử dụng harness sau nâng cấp (Tiếng Việt)

> Tài liệu này: (a) hướng dẫn dùng những gì vừa làm, và (b) **note kỹ mọi thay đổi hành vi**
> trong harness để bạn nắm, tránh behavior ngoài ý muốn.
> Kiểm tra trạng thái bất cứ lúc nào: `python scripts/harness_doctor.py` (hoặc `just doctor`).

---

## 0. Cần làm NGAY (2 việc thủ công)

```fish
# 1) Bật các helper fish (zorch/zimpl/wtlist...). Chạy 1 lần.
echo 'source /home/dax/Documents/arabica/roast/scripts/fish/myhospital-zellij.fish' >> ~/.config/fish/config.fish
exec fish

# 2) Commit harness repo (root giờ đã là git repo, nhưng agent BỊ CHẶN commit — bạn tự commit)
cd /home/dax/Documents/arabica/roast
git add -A
git status        # xem lại: chỉ nên có file harness
git commit -m "Harness upgrade: safety, helpers, doctor, graph demotion, VCS"
```

Không cần cài package nào — mọi tool `doctor` cần đều đã có trên PATH.

---

## 1. ⚠️ NHỮNG THAY ĐỔI HÀNH VI quan trọng (đọc kỹ phần này)

### 1.1. Guard hook giờ NGHIÊM hơn — nhưng chỉ áp dụng cho **agent Claude Code**
File `.claude/hooks/myhospital_guard.py` chạy như PreToolUse hook của **Claude Code**. Nó **chỉ chặn lệnh do agent Claude gọi** (Bash/Write/Edit/MultiEdit). Nó **KHÔNG** ảnh hưởng:
- Terminal fish của bạn (bạn gõ tay → chạy bình thường).
- `opencode` / `codex` / tool khác (chúng không đọc `settings.json` của Claude).
- Lệnh bên trong `worktree.py` (đó là subprocess Python, không phải agent Bash).

**Agent Claude giờ bị chặn** (trước đây lọt):
- `git push`, `git commit`, `git reset --hard`, `git clean -f`, `git checkout -- <file>` — **kể cả khi có `git -C <path>`** (trước đây `git -C ... push` lọt).
- `rm` đệ quy: `rm -r`, `-rf`, `-fr`, `--recursive` (trước đây chỉ chặn đúng chuỗi `rm -rf`).
- Cài package mới: `npm/pnpm/yarn/bun install <pkg>`, `dotnet add package`.
- Sửa file generated FE / migration BE — **giờ chặn cả trong `worktrees/<slug>/...`** (trước chỉ chặn ở repo chính).

**Agent Claude KHÔNG bị chặn** (cố tình để implementer làm việc): `npm run dev`, `dotnet run/build/test`, `kill`/`pkill` (tắt/khởi động lại dev server), `git pull`, `git status`, `git add`, `git worktree ...`, `git branch -D`, `rm file` (xoá 1 file), `npm install` (không kèm tên package).

**Nếu agent thực sự cần chạy 1 lệnh bị chặn:** bạn tự chạy trong terminal fish của bạn (guard không đụng tới), hoặc tạm sửa `.claude/settings.json`. Guard là "tripwire hợp tác", không phải sandbox — nó **fail-open** (nếu lỗi thì cho qua, không bao giờ làm kẹt session).

### 1.2. Không còn nhắc "MANDATORY graphify" nữa
Đã **gỡ** 2 hook ép "phải chạy graphify trước khi đọc/grep code". Lý do: graph **không chứa code**, lời nhắc đó sai và gây nhiễu. Giờ:
- Đọc/tìm **code** → dùng `rg`/`fd`/`bat`; đọc `.docx`/`.pdf` → `rga`.
- graphify chỉ là **tuỳ chọn** cho câu hỏi **thiết kế docs/specs**.

### 1.3. Mỗi lần mở session sẽ thấy dòng "[graphify] ... STALE ..."
Đây là **đúng**, không phải lỗi. Graph hiện tại được build trên **Windows** (`graphify-out/.graphify_root` = đường dẫn ổ Windows), nên đường dẫn `src=` của nó **không tồn tại trên Linux** và nó từng **lẫn cả `session-auth`/`cookie`/`token`** vào graph. Hook SessionStart giờ cảnh báo điều này. **Đừng tin path từ graph** cho tới khi rebuild trên Linux (xem §4).

### 1.4. `sync-main` giờ BỎ QUA repo không đứng đúng branch
Hiện tại cả `myhospital-fe` và `myhospital-be` đang ở branch `chore/linux-cachyos-tooling-migration`, **không phải** `master`/`main`. Nên:
- `python scripts/worktree.py sync-main` sẽ **SKIP cả 2 repo** kèm thông báo + lệnh khắc phục.
- Muốn nó thực sự pull: chuyển repo về đúng branch trước, hoặc thêm `--checkout` để tự chuyển.

> Vì sao đổi: trước đây nó chạy `git restore .` + `git pull origin master` ngay trên branch hiện tại → sẽ **merge master vào nhầm branch và xoá thay đổi**. Giờ chặn tình huống đó.

### 1.5. Root (`/home/dax/Documents/arabica/roast`) GIỜ LÀ git repo
- `git status` ở root giờ chạy được và hiện file harness. Đây là chủ đích (để harness có version control).
- Chỉ track file harness; đã loại `myhospital-fe/`, `myhospital-be/`, `worktrees/`, `_db-backups/`, secrets, file `.docx` lớn, output generated qua `.gitignore`.
- **Chưa commit** (agent bị chặn commit) — bạn tự commit (xem §0).
- Không ảnh hưởng repo FE/BE (chúng có `.git` riêng; `worktree.py` luôn dùng `git -C myhospital-fe/be`).

### 1.6. `create` mặc định VẪN sync DB (phá/dựng lại slot DB), nhưng có "light mode" thật
- `python scripts/worktree.py create --slug bed --slot 1` → vẫn sync DB slot (destructive, không hỏi thêm).
- Muốn nhẹ, **không đụng Docker/SQL**: thêm `--skip-db-sync --skip-db-init` (cờ `--skip-db-init` là **mới**).

### 1.7. Một số thay đổi nhỏ khác
- **Slug** giờ ép về kebab-case `[a-z0-9-]`: `my_feature` → `my-feature`, `v1.2` → `v1-2`; loại `..`/`.`/rỗng (chống path traversal).
- **Log của `worktree.py` che mật khẩu**: bạn sẽ thấy `Password=***`, `-P ***` thay vì mật khẩu thật.
- **`graphifyignore` (không có chấm) giờ là symlink** trỏ tới `.graphifyignore`. Sửa file nào cũng như nhau, không lệch nữa.
- **`cleanup` không tự xoá branch** trừ khi thêm `--delete-branch`; nếu không, nó in sẵn lệnh `git branch -D` để bạn xoá (giúp tái dùng lại slug).

---

## 2. Cách dùng hằng ngày

### 2.1. Bật helper (1 lần) — xem §0.
Sau khi source, bạn có: `wtlist`, `wtcreate`, `zorch`, `zimpl`, `zls`, `zkillwt`, `wtjoin`.
Các helper tự tìm root từ vị trí file (không hardcode), tự trỏ tới layout Zellij trong repo (không cần cài vào `~/.config`), và báo lỗi rõ nếu thiếu worktree/zellij.

### 2.2. Bảng lệnh

| Việc cần làm | Lệnh (fish) |
|---|---|
| Tạo worktree đầy đủ (FE+BE+DB) | `wtcreate bed 1` |
| Tạo worktree nhẹ (không DB/không cài FE) | `wtcreate bed 1 --skip-db-sync --skip-db-init --skip-fe-install` |
| Xem trước (không tạo gì) | `just wt-create-preview bed 1` |
| Liệt kê worktree | `wtlist` (hoặc `just wt-list`) |
| Mở session orchestrator | `zorch bed claude` |
| Mở session implementer | `zimpl bed opencode` (vd `zimpl bed composer`) |
| Join worktree đang có | `wtlist` → `zorch bed claude` → `zimpl bed opencode` |
| Xem session Zellij của workspace | `zls` |
| Kill mọi session của 1 worktree | `zkillwt bed` |
| Sync main branches | `python scripts/worktree.py sync-main` (thêm `--checkout` nếu đang sai branch) |
| Reset DB 1 slot | `python scripts/worktree.py sync-db --slot 1 --be-path worktrees/bed/be` (thêm `--dry-run` để xem trước) |
| Dọn worktree | `python scripts/worktree.py cleanup --slug bed` (thêm `--delete-branch` để giải phóng slug) |
| Kiểm tra sức khoẻ harness | `python scripts/harness_doctor.py` (hoặc `just doctor`) |
| Backup harness | `just harness-backup` |

`just` có sẵn: `wt-list`, `wt-create`, `wt-create-lite`, `wt-create-preview`, `wt-sync-main`, `wt-sync-db`, `wt-cleanup`, `z-sessions`, `z-install-layouts`, `doctor`, `harness-backup`, `agent-audit`.

### 2.3. Quy ước
- **1 worktree = 2 session**: orchestrator (`mh-<slug>-orch-<tool>`) + implementer (`mh-<slug>-impl-<tool>`).
- Layout chỉ **mở shell + in gợi ý**, **không tự chạy dev server**. Agent tự chạy khi cần.
- Map intent→lệnh đầy đủ: `harness/rules/worktree-workflow.md`.

---

## 3. Guard hook chặn gì / không chặn gì (tham chiếu nhanh)

Tự kiểm chứng: `python .claude/hooks/myhospital_guard.py --self-test` (hiện pass 38/38).

| Loại lệnh (do **agent Claude** gọi) | Kết quả |
|---|---|
| `git push` / `git commit` / `git -C x push` | ❌ Chặn |
| `git reset --hard` / `git clean -fdx` / `git checkout -- file` | ❌ Chặn |
| `rm -rf` / `rm -fr` / `rm -r` / `cmd && rm -r x` | ❌ Chặn |
| `npm install lodash` / `yarn add x` / `dotnet add package X` | ❌ Chặn |
| Sửa generated DTO/client/Constants, migration `.cs` (main **hoặc** worktree) | ❌ Chặn |
| `npm run dev` / `dotnet run` / `kill` / `pkill` (dev server) | ✅ Cho phép |
| `git pull` / `git status` / `git add` / `git worktree ...` / `git branch -D` | ✅ Cho phép |
| `npm install` (không tên package) / `rm file` (1 file) | ✅ Cho phép |

---

## 4. graphify — trạng thái & dùng sao cho an toàn

- **Hiện trạng:** graph build trên Windows → **stale**, path sai trên Linux, từng lẫn secrets. `doctor` báo WARN cho việc này.
- **Đã làm:** hạ graphify xuống "tuỳ chọn, chỉ docs/specs"; siết `.graphifyignore` để loại `*.har`/`session-auth.json`/legacy `.ps1`; sửa hook freshness để cảnh báo đúng.
- **Dùng tạm:** chỉ hỏi câu **thiết kế docs/specs**, và **luôn đối chiếu lại file gốc**. Đừng dùng path từ graph.
- **Khi nào nên rebuild (tuỳ chọn, do bạn quyết):** khi cần graph tươi & đáng tin. Rebuild đúng cách cần LLM/skill:
  ```fish
  /graphify .     # trong Claude Code; chọn lại scope docs+specs
  ```
  Sau rebuild, `.graphify_root` sẽ là path Linux và WARN biến mất.

---

## 5. Từng file đã thay đổi (để bạn nắm)

**File MỚI**
- `scripts/harness_doctor.py` — kiểm tra sức khoẻ harness (read-only).
- `scripts/harness_backup.py` — snapshot harness (không kèm secret/DB).
- `scripts/fish/myhospital-zellij.fish` — các helper fish.
- `scripts/zellij/myhospital-orch.kdl`, `myhospital-impl.kdl` — layout Zellij bản repo.
- `harness/rules/worktree-workflow.md` — bản đồ intent→lệnh chuẩn.
- `.gitignore` — phạm vi cho harness git repo.
- `.harness-backups/20260614-132135/` — snapshot trước khi sửa (đã gitignore).

**File SỬA**
- `CLAUDE.md`, `AGENTS.md` — sửa routing BE; hạ cấp graphify; trỏ tới doc workflow + helper.
- `.claude/settings.json` — **gỡ 2 hook graphify**; gộp guard về 1 matcher `Bash|Write|Edit|MultiEdit`.
- `.claude/hooks/myhospital_guard.py` — guard siết hơn + `--self-test`.
- `.claude/hooks/graphify_stale_check.py` — viết lại (phát hiện graph Windows/stale).
- `.codex/hooks.json` — bỏ hook `graphify hook-check` (vốn là no-op).
- `.graphifyignore` — loại secrets/HAR/legacy; `graphifyignore` → symlink.
- `justfile` — thêm recipe wt-*/z-*/doctor/harness-backup; `agent-audit` chính xác hơn.
- `scripts/worktree.py` — guard branch cho `sync-main`; sửa `sync-db --dry-run` không hỏi; rollback khi `create` lỗi; thêm `--skip-db-init`; siết `safe_slug`; che mật khẩu trong log; `cleanup --delete-branch`; bắt `OSError` cho port probe.
- `scripts/README.md`, `scripts/WORKTREE-TOOLING.md` — cập nhật helper + `--skip-db-init`.

> Bản gốc trước khi sửa nằm ở `.harness-backups/20260614-132135/` nếu cần đối chiếu/khôi phục.

---

## 6. Khôi phục nếu có gì ngoài ý muốn

- **Tắt guard tạm thời:** sửa `.claude/settings.json`, xoá block `PreToolUse`. (Hoặc cứ chạy lệnh bị chặn trong terminal fish của bạn — guard không đụng tới.)
- **Bỏ git repo ở root:** `rm -rf .git` (chạy trong terminal của bạn) — không ảnh hưởng FE/BE.
- **Khôi phục 1 file harness:** copy từ `.harness-backups/20260614-132135/<đường-dẫn-file>`.
- **Hoàn tác đổi graphify guidance:** các thay đổi nằm trong `AGENTS.md`/`CLAUDE.md`/`.graphifyignore` — có bản gốc trong snapshot.

---

## 7. Việc còn lại (chưa làm, có chủ đích)

- **Rebuild graph trên Linux** — cần `/graphify`/LLM, để bạn tự quyết (xem §4).
- **Wiring guard cho Codex** — cần xác minh schema hook của Codex (phải chạy Codex), nên tạm để trống `.codex/hooks.json`.
- **`cleanup --delete-branch`** — logic đã verify bằng code, nhưng chưa test end-to-end (cần 1 worktree thật = fetch mạng + mutation).
- **"sync worktree hiện tại với main" (rebase task branch lên main)** — chưa có lệnh `worktree.py`; tạm làm tay: `git -C worktrees/bed/be fetch origin && git -C worktrees/bed/be rebase origin/main`.
- **Commit harness repo** — bạn tự làm (xem §0).
