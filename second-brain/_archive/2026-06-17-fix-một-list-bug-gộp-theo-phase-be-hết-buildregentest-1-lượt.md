---
title: "Fix một LIST bug: gộp theo PHASE (BE hết → build/regen/test 1 lượt → FE hết → typecheck 1 lượt), không chạy nhiều chu kỳ nhỏ"
date: "2026-06-17"
status: provisional
source: conversation
scope: workspace
confidence: high
owner_confirmed: false
proposed_target: main-brain
tags: [harness, orchestration, cost, batch, multi-agent, build-test]
applies_tasks: [fix, implement, review]
applies_globs: []
applies_keywords: [batch, build once, test once, phase, orchestration, list bug, list of bugs, subagent, wave, round]
expires: ""
---

# What

Khi fix một LIST bug bằng subagent, batch theo PHASE chứ đừng chia nhiều round nhỏ. Cụ thể: (0) MỘT lượt RCA trước — tìm gốc, loại bug đã-fix-sẵn, và gom HẾT câu hỏi quyết định của owner vào 1 batch (đừng dừng giữa chừng để hỏi từng cái). (1) Phase BE: fan-out TẤT CẢ fix BE trong 1 đợt, chia theo FILE rời nhau (bug cùng file -> 1 agent; agent không tự sửa migration), rồi chạy MỘT build + MỘT migration/regen DTO + MỘT lượt test; lỗi gì fix bù trong 1 follow-up nhỏ. (2) Phase FE: TẤT CẢ fix FE 1 đợt (trang rời nhau), rồi MỘT lượt typecheck. Phase BE phải trước FE vì đổi contract BE cần regen trước khi FE dùng. Đúng ý owner 'code 1 lượt, build 1 lượt, test 1 lượt, lỗi thì fix tiếp' — kèm ràng buộc file-rời + thứ-tự-BE-trước-FE + gom-quyết-định-đầu để an toàn.

# Evidence

- Run đầu trên 39 bug tốn ~2h, phần lớn do ~6 chu kỳ launch->build->test + 3 vòng hỏi quyết định riêng lẻ

# Why It Matters

Gộp về 2 phase (BE hết, rồi FE hết) với 1 build/test mỗi phase + 1 batch quyết định đầu sẽ bỏ phần lớn thời gian chờ mà không mất recall.

# How To Apply

_See # What above._

# Boundaries

KHÔNG bỏ review tay diff lâm sàng/tài chính/viện phí và adversarial-verify các finding HIGH (giữ nguyên). Bug thật sự dùng chung 1 file hoặc có phụ thuộc contract BE->FE vẫn phải tuần tự trong phase của nó. Vẫn RCA trước — đó là cái giúp bỏ qua bug đã fix sẵn.

# Promotion Recommendation

Promote to: main-brain
Reason: (fill in before promoting)
