---
slug: test-data-done-rule
scope: workspace
applies_when: fix,implement,test,browser,e2e · test-data,seed,done,complete,data,view
confidence: high
created: 2026-06-25
---

# Rule: Never report done without real data in place

**Rule:** Không được báo "done" / "hoàn thành" / "xong" cho bất kỳ task nào liên quan đến UI
feature khi chưa có data thật để nhìn thấy trên UI. Nếu feature cần data để render thì data
phải có MẶT trước khi báo xong.

**Append-only:** Test data đã seed không được xóa đi. Nếu cần update thì chỉ được thêm mới
(UPSERT hoặc INSERT thêm row). Không DELETE, không TRUNCATE, không seed-reset. Owner sẽ dùng
data đó để view và test.

**Priority:** Ưu tiên thêm data qua UI/luồng thật (browser E2E, form, API call) — đây là smoke
test luôn. Chỉ dùng SQL trực tiếp khi luồng UI chưa ready hoặc không thể thao tác được.

**Why:** Tình huống xảy ra 2026-06-25: các dialog "Thêm thông tin diễn biến" (sinh hiệu, hội chẩn,
CLS, chuyên khoa) đã được implement nhưng không có data → owner nhìn vào chỉ thấy empty state,
không verify được gì. Phải seed data mới test được thật sự.

**Apply:** Trước khi báo done bất kỳ FE feature nào, hỏi: "có data để render không?" Nếu không →
seed data trước. Nếu là browser subagent → check data count trước khi close task.
