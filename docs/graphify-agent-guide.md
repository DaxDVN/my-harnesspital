# Graphify — Hướng dẫn cho coding agent

> File này hướng dẫn **mọi agent** (Claude Code, Codex CLI/desktop, Grok, Antigravity, Cursor…)
> cách dùng knowledge graph mà graphify đã build cho workspace này.
> Trỏ tới từ `AGENTS.md` (mục *Knowledge Graph*) và `CLAUDE.md`.

---

## 0. TL;DR (đọc cái này trước)

- Graph đã build nằm ở **`graphify-out/graph.json`**.
- Đây là **knowledge graph của `docs/` + `specs/`** (133 file, ~250K từ) — tức là **bản đồ của tài
  liệu BA / spec / quyết định thiết kế / task slices / convention**, **KHÔNG phải graph của code FE/BE**.
- **Tìm/hiểu source code FE/BE → dùng CodeGraph, KHÔNG dùng graphify** (xem
  `engine/rules/source-discovery.md`). graphify chỉ cho design intent của docs/specs.
- Cách dùng nhanh nhất cho **bất kỳ agent nào có shell**:
  ```fish
  graphify query "<câu hỏi>"        # trả về vùng đồ thị liên quan, KHÔNG cần API key
  graphify explain "<tên node>"     # giải thích 1 node + hàng xóm
  graphify path "A" "B"             # đường đi ngắn nhất giữa 2 node
  graphify affected "<tên node>"    # cái gì bị ảnh hưởng nếu đổi node này
  ```
  Chạy từ thư mục `/home/dax/Documents/arabica/roast` (mặc định đọc `graphify-out/graph.json`).
- Cách dùng cho agent **không có shell / chỉ đọc file**: đọc **`graphify-out/GRAPH_REPORT.md`**.
- Lệnh `query/explain/path/affected` **không cần LLM, không cần API key** — chỉ là duyệt đồ thị.

---

## 1. Graph này chứa gì (và KHÔNG chứa gì)

| Có trong graph | KHÔNG có trong graph |
|---|---|
| Spec admission/inpatient (`specs/admission/**`) | Source code FE (`myhospital-fe/src`) |
| Spec bed-day billing (`specs/ipd_bed*/**`) | Source code BE (`myhospital-be/**`) |
| Task plan & audit (`docs/tasks`, `docs/session-notes`) | Test runtime, log, build artifact |
| Agent rules / convention (`engine/rules`, `AGENTS.md`, `CLAUDE.md`) | Hình ảnh / screenshot (đã loại) |
| Quyết định đã chốt (`_DECISIONS.md`), override của architect | `worktrees/`, `trash/`, `bin/`, `obj/`, `node_modules` (đã loại) |

> **Hệ quả quan trọng:** graph này giúp trả lời câu hỏi về **ý định thiết kế, quan hệ giữa các spec,
> quyết định đã chốt, task nào phụ thuộc task nào**. Nó **không** thay thế việc đọc/grep code thật.
> Khi cần biết "hàm X gọi hàm Y ở đâu trong code", vẫn phải dùng `rg` / đọc code, **không** dùng graph này.

### File trong `graphify-out/`

| File | Dùng để làm gì | Ai đọc được |
|---|---|---|
| `GRAPH_REPORT.md` | Báo cáo người-đọc: god nodes, communities, surprising connections, câu hỏi gợi ý | Mọi agent (chỉ cần đọc file) |
| `graph.json` | Dữ liệu đồ thị thô (node + edge) | CLI / MCP / code tự duyệt |
| `graph.html` | Đồ thị tương tác, mở bằng browser | Con người |
| `manifest.json` | Hash file để `graphify update` biết file nào đổi | CLI |
| `cost.json` | Theo dõi token đã tốn qua các lần build | Con người |

---

## 2. Bốn cách tiêu thụ graph (chọn theo khả năng của agent)

### Cách A — Đọc `GRAPH_REPORT.md` (mọi agent, kể cả không có shell)
Mở `graphify-out/GRAPH_REPORT.md`. Quan tâm các mục:
- **God Nodes** — các "trung tâm" của tài liệu (node nhiều liên kết nhất). Bắt đầu hiểu module từ đây.
- **Communities** — các cụm chủ đề đã được đặt tên (vd "Bed-Day Domain Model", "BHTM Multi-Card Guarantee").
- **Surprising Connections** — quan hệ chéo ít người ngờ tới (vd một override thay thế component cũ).
- **Suggested Questions** — câu hỏi mà graph trả lời tốt nhất.

### Cách B — CLI (mọi agent có shell; **không cần API key**)
`graphify` đã nằm trên PATH (`/home/dax/.local/bin/graphify`). Chạy từ `/home/dax/Documents/arabica/roast`:

```fish
# Hỏi tự nhiên → duyệt BFS quanh các node khớp câu hỏi
graphify query "Vì sao Admission Reception Requirements lại nối FE Reuse với Architect Overrides?"
graphify query "<câu hỏi>" --budget 1500     # giới hạn output ~1500 token
graphify query "<câu hỏi>" --dfs             # duyệt sâu thay vì rộng (lần theo 1 chuỗi)

# Giải thích 1 node + hàng xóm của nó
graphify explain "MedicalVisitBedStay (E6)"

# Đường đi ngắn nhất giữa 2 khái niệm (vd: spec A liên quan spec B qua đâu)
graphify path "Slice 06: Create Inpatient Admission" "InpatientService (BE)"

# Phân tích tác động ngược: nếu sửa node này thì cái gì bị ảnh hưởng
graphify affected "Locked Decisions File (_DECISIONS.md)" --depth 2
```
Output của `query` là một danh sách NODE kèm `src=<file> loc=<§mục> community=<id>`. Agent dùng các
`src`/`loc` này để **mở đúng file/đúng mục** rồi tự tổng hợp câu trả lời. Tên node lấy y hệt nhãn
trong `GRAPH_REPORT.md` hoặc cột NODE của `query`.

> Nếu chạy ở thư mục khác, thêm `--graph graphify-out/graph.json`.

### Cách C — MCP server (agent hỗ trợ MCP: Claude Code, Codex, Cursor, Antigravity…)
Có sẵn binary `graphify-mcp` (mặc định transport `stdio`):

```fish
graphify-mcp graphify-out/graph.json            # stdio cho agent local
# hoặc HTTP nếu agent ở xa:
graphify-mcp --transport http --port 8080 graphify-out/graph.json
```

Khai báo server stdio trong cấu hình MCP của agent (ví dụ chung):
```json
{
  "mcpServers": {
    "graphify-myhospital": {
      "command": "graphify-mcp",
      "args": ["graphify-out/graph.json"]
    }
  }
}
```
Sau đó agent gọi các tool MCP (query/explain/path…) như tool thường, không cần shell.

### Cách D — Đọc `graph.json` thô
Khi agent muốn tự duyệt (NetworkX, code riêng): load `graphify-out/graph.json`, mỗi node có
`id/label/file_type/source_file/community`, mỗi edge có `source/target/relation/confidence`.

---

## 3. Hướng dẫn theo từng agent

> Có **2 mức tích hợp**: (1) chỉ **dùng** graph (đọc report + chạy CLI) — luôn được; (2) **cài skill**
> `/graphify` vào agent để nó tự nhận lệnh và tự build/refresh. Graphify có sẵn lệnh cài:
> ```fish
> graphify codex install      # cài Codex integration cho project hiện tại
> graphify claude install     # cài Claude integration cho project hiện tại
> ```
> Platform được hỗ trợ: `claude, codex, opencode, kilo, aider, copilot, claw, droid, trae, trae-cn,`
> `hermes, kiro, pi, codebuddy, antigravity, antigravity-windows, windows, kimi, amp, devin, cursor`.
> (**Grok build** không có installer → dùng Cách A/B.)

### Claude Code
- Skill `/graphify` đã có sẵn ở `~/.claude/skills/graphify/`. Gõ `/graphify query "..."` để hỏi,
  hoặc `/graphify <path>` để build/cập nhật.
- Mô tả skill đã nói: *khi `graphify-out/` tồn tại, hãy coi câu hỏi về codebase là một graphify query trước*
  → Claude Code **tự** ưu tiên dùng graph (xem thêm mục 5).
- Không cần shell thủ công; có thể dùng trực tiếp lệnh `graphify query/explain/path/affected` qua Bash tool.

### Codex (CLI và Desktop)
- **Dùng ngay:** đọc `graphify-out/GRAPH_REPORT.md` + chạy `graphify query "..."` qua shell (Cách B).
- **Cài skill (khuyến nghị):** `graphify codex install` → Codex nhận lệnh `/graphify`.
- **MCP (tuỳ chọn):** thêm `graphify-mcp` vào cấu hình MCP của Codex (Cách C).
- Codex đọc `AGENTS.md` ở repo → đã có mục *Knowledge Graph* trỏ về file này.

### Antigravity
- `graphify antigravity install` để cài skill.
- Hoặc dùng MCP (Cách C) / CLI (Cách B). Antigravity cũng đọc `AGENTS.md`.

### Grok build
- Không có installer riêng → **Cách A** (đọc `GRAPH_REPORT.md`) + **Cách B** (chạy `graphify query`).
- Nếu Grok hỗ trợ MCP, dùng Cách C.

### Cursor
- `graphify cursor install`. Còn lại giống trên.

---

## 4. Khi nào NÊN dùng — và khi nào KHÔNG

### Nên dùng graph khi:
- Bắt đầu một task về **admission / inpatient reception / bed-day billing / BHYT-BHTM**: hỏi graph
  để biết spec liên quan, **quyết định đã chốt** (`_DECISIONS.md`), **override** của architect, ràng buộc BLOCK/WARN.
- Cần biết **component/DTO được tái sử dụng ở đâu, bị thay thế bởi gì** → `explain` / `affected`.
- Cần biết **slice/task nào phụ thuộc slice nào**, thứ tự thực thi → `path` / `query`.
- Onboard nhanh một module lạ: đọc God Nodes + Communities trong report.
- Trước khi sửa một tài liệu lớn: `affected` để xem tài liệu/quyết định nào trỏ tới nó.

### KHÔNG nên dùng graph khi:
- Cần điều hướng **code thật** (hàm gọi hàm, import, props component) → dùng `rg`/đọc code, **không** graph này.
- Cần chạy/sửa **test, build, runtime bug** → graph không chứa thông tin đó.
- Câu hỏi về file **không thuộc `docs/`+`specs/`** (vd file trong `myhospital-fe/src`) → ngoài phạm vi graph hiện tại.

---

## 5. Agent có TỰ ĐỘNG dùng được không?

Câu trả lời ngắn: **không mặc định, trừ khi được chỉ dẫn.** Graph chỉ là file tĩnh; agent không tự
"biết" nó tồn tại. Có 3 cơ chế để agent dùng (tự động hoặc bán tự động):

1. **Chỉ dẫn trong harness (`AGENTS.md`/`CLAUDE.md`)** — *cơ chế chính cho workspace này.*
   Mọi agent đều đọc `AGENTS.md`. Mục *Knowledge Graph* trong `AGENTS.md` ra lệnh: *trước khi trả lời
   câu hỏi về spec/quyết định trong `docs/`+`specs/`, hãy tham khảo graphify trước*. Đây là mức "tự động
   theo quy ước" — agent tuân theo vì nó là luật của harness.

2. **Skill được cài (`graphify <platform> install`)** — agent có lệnh `/graphify` với mô tả "dùng khi có câu hỏi
   về codebase". Với Claude Code, skill còn có *fast-path*: nếu `graphify-out/graph.json` tồn tại và
   người dùng hỏi câu hỏi tự nhiên về codebase, nó **tự** chạy `graphify query` thay vì build lại.

3. **MCP server** — sau khi khai báo, các tool query/explain/path xuất hiện như tool thường; agent tự
   chọn gọi khi thấy phù hợp.

> **Lưu ý trung thực:** "tự động" ở đây nghĩa là *agent được hướng dẫn để ưu tiên hỏi graph*, không phải
> graph tự cập nhật. Graph là **ảnh chụp** tại thời điểm build — xem mục 6 để giữ nó tươi mới.

---

## 6. Giữ graph tươi mới (đừng để stale)

Graph hiện tại được build với phạm vi **`docs/` + `specs/`, loại `trash/`+`worktrees/`+`bin/`+`obj/`+ảnh**.

- **Sau khi sửa code (không đụng docs/specs):** không cần làm gì — graph này không chứa code.
- **Sau khi thêm/sửa nhiều file trong `docs/` hoặc `specs/`:** build lại phần ngữ nghĩa. Cách đúng phạm vi:
  ```fish
  # Trong Claude Code (có skill + LLM để chạy subagent trích xuất):
  /graphify .          # rồi chọn lại scope docs+specs, loại noise như lần đầu
  ```
  hoặc dùng LLM key + CLI:
  ```fish
  set -x GEMINI_API_KEY "..."; graphify update .   # cập nhật, không cần subagent
  ```
- **Kiểm tra graph có cần build lại không:** `graphify check-update .`
- **Cảnh báo phạm vi:** lệnh `graphify update .` / `/graphify .` mặc định quét **toàn bộ root** (21K file).
  Phạm vi được cố định bằng `.graphifyignore` ở root; kiểm tra file này trước khi mở rộng graph scope.
- **Cạm bẫy:** edge `INFERRED` là suy luận của model (13% số edge, độ tin ~0.86) — **phải verify** trước khi
  coi là sự thật. Chỉ `EXTRACTED` mới là quan hệ ghi rõ trong tài liệu.

---

## 7. (Tuỳ chọn) Cố định phạm vi bằng `.graphifyignore`

Để mọi lần build/`update` sau này tự loại noise mà không phải gõ exclude, dùng `.graphifyignore`:
```gitignore
worktrees/
trash/
_db-backups/
graphify-out/cache/
.env
.env.*
node_modules/
bin/
obj/
```
> File `.graphifyignore` là **cấu hình tooling** (giống `.gitignore`), không phải "artifact" — đặt ở root được.

---

## 8. Tham chiếu nhanh các lệnh

| Mục đích | Lệnh |
|---|---|
| Hỏi tự nhiên | `graphify query "<q>"` |
| Hỏi + giới hạn token | `graphify query "<q>" --budget 1500` |
| Giải thích 1 node | `graphify explain "<label>"` |
| Đường đi A→B | `graphify path "<A>" "<B>"` |
| Tác động ngược của 1 node | `graphify affected "<label>" --depth 2` |
| Build lại (code, no LLM) | `graphify update .` |
| Kiểm tra cần build lại? | `graphify check-update .` |
| Đặt lại tên cluster (cần LLM) | `graphify label .` |
| Chạy MCP (stdio) | `graphify-mcp graphify-out/graph.json` |
| Cài skill vào Codex | `graphify codex install` |
| Cài skill vào Claude | `graphify claude install` |

Tất cả lệnh duyệt (`query/path/explain/affected`) **không cần API key**. Chỉ build ngữ nghĩa mới (semantic
extraction) và `label` mới cần LLM (API key phù hợp hoặc host LLM của Claude Code chạy subagent).
