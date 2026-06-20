---
title: "staging-test-bug-investigation-uses-slot3-code"
date: "2026-06-20"
status: provisional
source: conversation
scope: workflow:staging-test
confidence: high
owner_confirmed: false
proposed_target: engine/rules/frontend.md
tags: [staging-test, bug-fix, workflow]
applies_tasks: [staging-test, E2E test, browser test, test staging]
applies_globs: []
applies_keywords: [staging, E2E, bug list, test kết quả, điều tra bug]
expires: ""
---

# What

Sau khi staging/E2E test ra bug list → thực hiện đầy đủ 3 bước:

1. **Điều tra root cause** — code slot 3: FE = `worktrees/fix-bug-noi-tru/fe`, BE = `worktrees/fix-bug-noi-tru/be`. Cả hai, không chỉ FE.
2. **Đánh giá ảnh hưởng** — nếu cách fix ảnh hưởng diện rộng (cross-module, shared component, contract, migration) → chạy `/impact-analysis` trước khi fix.
3. **Fix** — dùng `/mh-fix` (FE bug) hoặc `/bug-fix` (cần RCA sâu hơn). Fix cả FE lẫn BE nếu lỗi từ BE.

# Evidence

- Owner instruction 2026-06-20: "nếu lỗi từ be cũng phải điều tra fix luôn cho tôi, nhờ áp dùng các workflow cần thiết nếu cần ví dụ điều tra, đánh giá ảnh hưởng (nếu cách fix ảnh hưởng diện rộng) và fix bug"

# Why It Matters

Code slot 3 là worktree mới nhất (chưa merge). Staging dùng code cũ → bug có thể đã fix, hoặc ngược lại root cause nằm ở code mới. Cần verify từ source thật. BE bug không fix thì FE fix vô nghĩa.

# How To Apply

Khi có bug list từ staging/E2E test:
- Với mỗi bug: đọc code slot 3 FE + BE để xác định root cause
- Nếu fix scope rộng (shared component toàn app, contract change, migration) → `/impact-analysis` trước
- Fix bằng `/mh-fix` hoặc `/bug-fix` (chọn tùy độ phức tạp RCA)
- Không bỏ qua BE bug dù đang làm session FE

# Boundaries

Áp dụng cho mọi staging/E2E test session trong workspace này.
Slot 3 path: `worktrees/fix-bug-noi-tru/{fe,be}`, port FE :3003, BE :5003.

# Promotion Recommendation

Promote to: engine/rules/frontend.md (và backend.md)
Reason: cross-cutting workflow rule cho mọi test session
