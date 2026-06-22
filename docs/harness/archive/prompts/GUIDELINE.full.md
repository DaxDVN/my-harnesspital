 # Hướng Dẫn Dùng engine/prompts

  ## 1. Bản Chất Của Các Prompt Này

  Các file trong engine/prompts là system prompt copy-paste, không phải command tự chạy.

  Bạn dùng chúng khi muốn mở một agent mới hoặc một session mới và ép agent đó làm đúng vai trò/runbook cụ thể.

  Mẫu dùng chung:

  Đọc engine/prompts/<file>.md làm system prompt.

  <Input cụ thể của task>

  Bắt đầu.

  Ví dụ:

  Đọc engine/prompts/bugfix-rca-single.md làm system prompt.

  Bug: khi lưu sinh hiệu nội trú, form báo thành công nhưng reload lại mất dữ liệu.
  Worktree: worktrees/vital-signs
  Expected: dữ liệu phải persist sau reload.

  Bắt đầu.

  Nói thẳng: mấy prompt này dùng để khỏi phải viết lại một prompt dài mỗi lần.

  ## 2. Cách Chọn Prompt Nhanh

  ### Nếu bạn muốn audit sâu

  Dùng engine/prompts/deep-audit-orchestrator.md

  Khi dùng:

  - Module gần merge.
  - Muốn tìm bug tối đa.
  - Muốn audit cả static + dynamic.
  - Muốn report fix-ready cho agent khác sửa.

  Ví dụ:

  Đọc engine/prompts/deep-audit-orchestrator.md làm system prompt.

  Audit module: vital-signs.
  Worktree: worktrees/vital-signs.
  Đây là merge-gate audit, cần recall tối đa.

  Bắt đầu.

  Không dùng khi:

  - Chỉ sửa 1 bug nhỏ.
  - Chỉ cần review diff vài file.
  - Chưa có module/worktree/scope rõ.

  ### Nếu bạn có report audit và muốn sửa bug

  Dùng engine/prompts/bugfix-from-report.md

  Khi dùng:

  - Đã có file audit report.
  - Muốn Opus/Codex đọc report, triage từng finding, RCA, fix, verify.
  - Muốn tránh fix bừa mọi finding.

  Ví dụ:

  Đọc engine/prompts/bugfix-from-report.md làm system prompt.

  Report: docs/audit/2026-06-20/full-audit-vital-signs.round-1.md
  Worktree: worktrees/vital-signs

  Triage toàn bộ BLOCK/HIGH trước, sau đó fix theo cluster root-cause.

  Bắt đầu.

  Không dùng khi:

  - Chưa có audit report.
  - Bug chỉ là một issue đơn lẻ từ user.

  ### Nếu chỉ có 1 bug cụ thể

  Dùng engine/prompts/bugfix-rca-single.md

  Khi dùng:

  - Một bug cụ thể.
  - Cần reproduce -> RCA -> fix -> verify.
  - Không cần đọc audit report dài.

  Ví dụ:

  Đọc engine/prompts/bugfix-rca-single.md làm system prompt.

  Bug: màn hình hội chẩn không load danh sách bác sĩ sau khi chọn khoa.
  Worktree: worktrees/ipd-consultation
  Expected: chọn khoa thì danh sách bác sĩ filter theo khoa.

  Bắt đầu.

  ### Nếu finding đã rõ và chỉ cần patch nhỏ

  Dùng engine/prompts/mh-fix-approved-finding.md

  Khi dùng:

  - Finding đã được xác nhận.
  - Scope nhỏ.
  - Root cause khá rõ.
  - Không cần audit lại.

  Ví dụ:

  Đọc engine/prompts/mh-fix-approved-finding.md làm system prompt.

  Finding: F-012, component gọi serviceStackClient trực tiếp trong page component.
  Worktree: worktrees/vital-signs
  Allowed writes:
  - worktrees/vital-signs/fe/src/features/vital-signs/**
  Validation:
  - npm run build
  - python scripts/mh_scan --root worktrees/vital-signs/fe --scope src/features/vital-signs --format summary

  Bắt đầu.

  Không dùng khi:

  - Finding chưa chắc đúng.
  - Dính API/schema/business/permission.
  - Cần điều tra sâu.

  ## 3. Nhóm Harness / Governance

  ### Read-only architecture audit

  Dùng engine/prompts/architecture-audit-readonly.md

  Khi dùng:

  - Bạn muốn audit lại harness.
  - Không muốn agent sửa gì.
  - Muốn đánh giá token burn, workflow overlap, router, manifest, envelope, doctor, lifecycle.

  Ví dụ:

  Đọc engine/prompts/architecture-audit-readonly.md làm system prompt.

  Audit toàn bộ harness hiện tại sau các phase tối ưu.
  Tập trung vào: prompt library, router, lifecycle, eval, runtime contract.
  Không edit file.

  Bắt đầu.

  ### Đánh giá triết lý quality-vs-cost

  Dùng engine/prompts/adaptive-harness-evaluation.md

  Khi dùng:

  - Bạn đang phân vân tối ưu có làm tụt quality không.
  - Muốn agent tranh luận/đánh giá roadmap.
  - Muốn phân biệt waste layer vs quality layer.

  Ví dụ:

  Đọc engine/prompts/adaptive-harness-evaluation.md làm system prompt.

  Đánh giá roadmap tối ưu harness hiện tại:
  thin root + router + manifest + envelope + eval.
  Tôi muốn biết phần nào nên làm tiếp, phần nào nên defer.

  Bắt đầu.

  ### Chạy một phase governance cụ thể

  Dùng engine/prompts/harness-governance-phase-runner.md

  Khi dùng:

  - Bạn muốn agent triển khai P0/P1/P2/P3/P4/P5 riêng lẻ.
  - Muốn agent không nhảy phase.
  - Muốn validation cuối phase.

  Ví dụ:

  Đọc engine/prompts/harness-governance-phase-runner.md làm system prompt.

  Phase cần triển khai: P4 eval/lifecycle enforcement.
  Không đụng FE/BE.
  Không deprecate workflow.
  Chạy validation đầy đủ.

  Bắt đầu.

  ### Chạy toàn bộ optimization còn lại

  Dùng engine/prompts/harness-full-optimization-runner.md

  Khi dùng:

  - Bạn đã quyết muốn agent tự chạy các phase còn lại.
  - Chấp nhận agent đi tuần tự và báo cáo một thể.
  - Dùng cho maintenance lớn.

  Ví dụ:

  Đọc engine/prompts/harness-full-optimization-runner.md làm system prompt.

  Tự kiểm tra phase nào đã xong, phase nào còn thiếu.
  Triển khai toàn bộ phase còn lại nhưng không làm giảm quality gate.
  Không edit myhospital-fe/myhospital-be.

  Bắt đầu.

  Không dùng cho task nhỏ.

  ### Kiểm tra harness đã sẵn sàng chưa

  Dùng engine/prompts/harness-readiness-check.md

  Khi dùng:

  - Sau khi tối ưu xong.
  - Trước khi bạn bắt đầu trial thực tế.
  - Muốn verdict READY, READY_WITH_WARNINGS, hoặc NOT_READY.

  Ví dụ:

  Đọc engine/prompts/harness-readiness-check.md làm system prompt.

  Kiểm tra harness hiện tại đã sẵn sàng để tôi bắt đầu test workflow thật chưa.
  Chạy doctor, readiness, learning, router/eval/runtime checks nếu có.

  Bắt đầu.

  ## 4. Nhóm Router / Discovery / Impact

  ### Classify prompt trước khi chạy workflow

  Dùng engine/prompts/router-dry-run-classifier.md

  Khi dùng:

  - Bạn chưa chắc task nên đi workflow nào.
  - Muốn biết T0/T1/T2/T3.
  - Muốn biết files_to_load, gates, validators.
  - Không muốn agent execute ngay.

  Ví dụ:

  Đọc engine/prompts/router-dry-run-classifier.md làm system prompt.

  Prompt cần classify:
  "Sửa lỗi form sinh hiệu không lưu được mạch và huyết áp sau khi reload."

  Chỉ dry-run, không sửa code.

  Bắt đầu.

  ### Tìm code / call path / impact bằng CodeGraph

  Dùng engine/prompts/codegraph-source-discovery.md

  Khi dùng:

  - “X nằm ở đâu?”
  - “API này ai gọi?”
  - “Đổi service này vỡ gì?”
  - “Pattern đúng để reuse là gì?”

  Ví dụ:

  Đọc engine/prompts/codegraph-source-discovery.md làm system prompt.

  Câu hỏi: trong worktrees/vital-signs, flow lưu vital signs đi qua API/service nào?
  Tôi cần call path FE -> BE và các file chính.

  Bắt đầu.

  ### Preflight blast-radius trước change rủi ro

  Dùng engine/prompts/impact-analysis-preflight.md

  Khi dùng:

  - Change chạm API/DTO/schema.
  - Chạm permission/security.
  - Chạm billing/insurance/BHYT/BHTM.
  - Chạm state machine.
  - Chạm shared service.

  Ví dụ:

  Đọc engine/prompts/impact-analysis-preflight.md làm system prompt.

  Proposed change: thêm field AdmissionId vào response API sinh hiệu và FE sẽ dùng field này để filter.
  Worktree: worktrees/vital-signs

  Chỉ phân tích impact, chưa sửa code.

  Bắt đầu.

  ## 5. Nhóm Implement / Fix

  ### Implement feature/module

  Dùng engine/prompts/mh-implement-feature.md

  Khi dùng:

  - Làm feature/page/module.
  - Có spec hoặc acceptance criteria.
  - Cần BE -> DTO -> FE đúng thứ tự.

  Ví dụ:

  Đọc engine/prompts/mh-implement-feature.md làm system prompt.

  Feature: thêm màn hình nhập sinh hiệu nội trú.
  Worktree: worktrees/vital-signs
  Spec: specs/vital-signs/
  Scope: chỉ implement phần list + form create/update.
  Không đổi schema nếu chưa cần.

  Bắt đầu.

  ### Worker làm một slice nhỏ

  Dùng engine/prompts/incremental-impl-worker.md

  Khi dùng:

  - Bạn chia việc cho subagent.
  - Một agent chỉ được sửa vài file.
  - Muốn tránh agent đụng scope của nhau.

  Ví dụ:

  Đọc engine/prompts/incremental-impl-worker.md làm system prompt.

  slice_id: VS-FE-02
  worktree: worktrees/vital-signs
  goal: implement vital-signs form sheet UI only
  allowed_writes:
  - worktrees/vital-signs/fe/src/features/vital-signs/components/vital-signs-form-sheet.tsx
  - worktrees/vital-signs/fe/src/features/vital-signs/hooks/**
  forbidden_writes:
  - worktrees/vital-signs/be/**
  - generated DTO/client files
  validation:
  - npm run build

  Bắt đầu.

  ### Fix từ report audit

  Dùng engine/prompts/bugfix-from-report.md

  Chuỗi điển hình:

  deep-audit-orchestrator.md
    -> sinh report docs/audit/...
  bugfix-from-report.md
    -> triage/fix/verify report đó

  Ví dụ thực tế:

  Đọc engine/prompts/bugfix-from-report.md làm system prompt.

  Report: docs/audit/2026-06-20/full-audit-ipd-consultation.round-1.md
  Worktree: worktrees/ipd-consultation

  Ưu tiên BLOCK/HIGH, bỏ LOW/NIT nếu không ảnh hưởng merge.
  Bắt đầu.

  ## 6. Nhóm Review / Audit / Test

  ### Full deep audit

  Dùng engine/prompts/deep-audit-orchestrator.md

  Khi dùng:

  - Muốn bắt bug nhiều nhất.
  - Không sợ tốn token/time.
  - Chuẩn bị merge.
  - Muốn report cho fixer đọc.

  Ví dụ:

  Đọc engine/prompts/deep-audit-orchestrator.md làm system prompt.

  Audit module: Hội chẩn.
  Worktree: worktrees/ipd-consultation.
  Merge gate: yes.
  Cần report canonical EN + bản VI.

  Bắt đầu.

  ### Review diff có scope, rẻ hơn deep audit

  Dùng engine/prompts/scope-aware-review.md

  Khi dùng:

  - Bạn chỉ muốn review diff hiện tại.
  - Không cần deep audit full module.
  - Muốn chọn dimension theo risk.

  Ví dụ:

  Đọc engine/prompts/scope-aware-review.md làm system prompt.

  Review diff hiện tại trong worktrees/vital-signs.
  Không sửa code.
  Tập trung API contract, FE generated DTO usage, visible UI reuse.

  Bắt đầu.

  ### Robust-test sweep

  Dùng engine/prompts/robust-test.md

  Khi dùng:

  - Module gần xong.
  - Muốn browser/E2E exploratory để gom bug.
  - Muốn mỗi bug có folder riêng để review lại.
  - Muốn dừng trước khi fix để owner approve.

  Ví dụ:

  Đọc engine/prompts/robust-test.md làm system prompt.

  Mode: sweep
  Module: vital-signs
  Worktree: worktrees/vital-signs
  Slot: 1
  Goal: harvest lỗi UI/E2E của luồng xem, tạo, sửa, xoá sinh hiệu.
  Không sửa code.

  Bắt đầu.

  ### Robust-test targeted flow

  Dùng engine/prompts/robust-test.md

  Khi dùng:

  - Có một flow E2E đang fail.
  - Muốn reproduce -> triage -> RCA -> fix-plan -> owner approve -> retest.
  - Không phải harvest toàn module.

  Ví dụ:

  Đọc engine/prompts/robust-test.md làm system prompt.

  Mode: targeted
  Flow fail: login -> nội trú -> sinh hiệu -> tạo mới -> reload -> record biến mất.
  Worktree: worktrees/vital-signs
  Slot: 1
  Expected: record vẫn còn sau reload.

  Bắt đầu.

  ### Browser smoke đơn giản

  Dùng engine/prompts/browser-e2e-smoke.md

  Khi dùng:

  - Chỉ muốn chạy một flow trên browser và lấy evidence.
  - Chưa muốn fix.
  - Muốn phân loại PASS/APP_BUG/ENVIRONMENT_ISSUE.

  Ví dụ:

  Đọc engine/prompts/browser-e2e-smoke.md làm system prompt.

  URL: http://localhost:3001
  Flow: login -> mở Sinh hiệu -> tạo mới một record -> verify record xuất hiện trong list.
  Expected: tạo thành công, list update.
  Không sửa code.

  Bắt đầu.

  ## 7. Nhóm Spec / Design

  ### UI spec từ DOCX/mockup

  Dùng engine/prompts/ui-spec-from-docs-mockups.md

  Khi dùng:

  - Có DOCX/mockup/screenshot.
  - Muốn tạo hoặc refine specs/<module>/03-ui.md.
  - Muốn reuse map UI trước khi implement.

  Ví dụ:

  Đọc engine/prompts/ui-spec-from-docs-mockups.md làm system prompt.

  Module: vital-signs
  Sources:
  - specs/Tài liệu Nội trú.docx
  - specs/vital-signs/assets/mockup.png
  Target: specs/vital-signs/03-ui.md

  Không implement code.
  Bắt đầu.

  ### Technical/API design

  Dùng engine/prompts/technical-api-design.md

  Khi dùng:

  - Cần thiết kế API/DTO/schema.
  - Có requirements đã confirmed.
  - Chưa implement.

  Ví dụ:

  Đọc engine/prompts/technical-api-design.md làm system prompt.

  Module: vital-signs
  Spec path: specs/vital-signs/
  Task: thiết kế API create/update/list sinh hiệu nội trú.
  Không implement code, chỉ cập nhật/đề xuất 08-api và 07-schema nếu cần.

  Bắt đầu.

  ### Task slicing

  Dùng engine/prompts/task-slicing.md

  Khi dùng:

  - Spec/design đã tương đối rõ.
  - Muốn chia thành slices để nhiều agent làm.
  - Muốn dependency order BE -> DTO -> FE -> tests.

  Ví dụ:

  Đọc engine/prompts/task-slicing.md làm system prompt.

  Module: vital-signs
  Spec path: specs/vital-signs/
  Goal: chia implementation plan thành các slice nhỏ, có allowed_writes và validation.

  Bắt đầu.

  ### Clinical UI design

  Dùng engine/prompts/clinical-ui-design.md

  Khi dùng:

  - Bạn thấy UI bị generic, thiếu chất HIS.
  - Muốn thiết kế layout/interaction trước khi code.
  - Muốn review clinical usability.

  Ví dụ:

  Đọc engine/prompts/clinical-ui-design.md làm system prompt.

  Screen: màn hình nhập sinh hiệu nội trú.
  User: điều dưỡng.
  Context: nhập nhanh nhiều chỉ số trong ca trực.
  Hãy đề xuất layout, component reuse, keyboard flow, error states.
  Không code.

  Bắt đầu.

  ## 8. Nhóm Runtime / Governance Chuyên Sâu

  ### Envelope/runtime hardening

  Dùng engine/prompts/envelope-runtime-hardening.md

  Khi dùng:

  - Workflow artifact/envelope chưa thống nhất.
  - Muốn harden path/hash/status/verdict.
  - Muốn adapter-first, không breaking schema cũ.

  Ví dụ:

  Đọc engine/prompts/envelope-runtime-hardening.md làm system prompt.

  Scope: robust-test artifact contract + removed progressive-test/super-test cleanup.
  Mục tiêu: adapter-first compatibility với envelope shared, không phục hồi autonomous handoff cũ.
  Không breaking schema cũ.

  Bắt đầu.

  ### Eval/lifecycle governance

  Dùng engine/prompts/eval-lifecycle-governance.md

  Khi dùng:

  - Muốn promote workflow từ DRAFT -> LAB -> PROVEN.
  - Muốn kiểm tra artifact evidence.
  - Muốn tránh auto-route workflow chưa chứng minh.

  Ví dụ:

  Đọc engine/prompts/eval-lifecycle-governance.md làm system prompt.

  Kiểm tra lifecycle của toàn bộ workflow.
  Đề xuất workflow nào đủ evidence để lên PROVEN.
  Không promote nếu thiếu artifact/eval evidence.

  Bắt đầu.

  ### Workflow consolidation/deprecation

  Dùng engine/prompts/workflow-consolidation-deprecation.md

  Khi dùng:

  - Bạn nghi workflow overlap.
  - Muốn gom/deprecate nhưng không phá compatibility.
  - Cần evidence trước khi kill.

  Ví dụ:

  Đọc engine/prompts/workflow-consolidation-deprecation.md làm system prompt.

  Đánh giá overlap giữa bug-fix, robust-test, incremental-impl, và removed progressive-test/super-test aliases.
  Chỉ đề xuất consolidation/deprecation nếu có replacement rõ và compatibility alias.

  Bắt đầu.

  ### External executor wrapper boundary

  Dùng engine/prompts/external-executor-wrapper.md

  Khi dùng:

  - Muốn harden cách gọi external executor khi owner explicitly yêu cầu.
  - Muốn tránh raw prompt bypass.
  - Muốn kiểm tra wrapper/log/output schema/allowlist.

  Ví dụ:

  Đọc engine/prompts/external-executor-wrapper.md làm system prompt.

  Review boundary cho legacy external executor wrapper.
  Mục tiêu: đảm bảo không bypass owner-gated robust-test và output có schema/log rõ.

  Bắt đầu.

  ### Doctor/drift repair

  Dùng engine/prompts/doctor-drift-repair.md

  Khi dùng:

  - harness_doctor.py báo warning/fail.
  - Registry/manifest/doc bị lệch.
  - Prompt/docs nói một kiểu, script làm kiểu khác.

  Ví dụ:

  Đọc engine/prompts/doctor-drift-repair.md làm system prompt.

  Doctor đang có warning về workflow manifest lifecycle.
  Sửa drift nhỏ nhất, không đổi runtime behavior.

  Bắt đầu.

  ## 9. Nhóm Memory / Environment

  ### Learning capture

  Dùng engine/prompts/learning-capture.md

  Khi dùng:

  - Bạn nói “nhớ cái này”.
  - Có bug-class lặp lại.
  - Có convention mới cần lưu.
  - Muốn capture vào second-brain, không viết main-brain.

  Ví dụ:

  Đọc engine/prompts/learning-capture.md làm system prompt.

  Nhớ cái này: khi audit UI HIS, phải verify live widget/pattern thật, không chỉ nhìn tên component.
  Capture thành provisional learning phù hợp.

  Bắt đầu.

  ### Worktree/environment recovery

  Dùng engine/prompts/worktree-environment-recovery.md

  Khi dùng:

  - Slot DB lỗi.
  - BE/FE port conflict.
  - Dev server không lên.
  - Worktree environment hỏng.

  Ví dụ:

  Đọc engine/prompts/worktree-environment-recovery.md làm system prompt.

  Worktree: worktrees/vital-signs
  Slot: 1
  Vấn đề: FE lên được nhưng BE 5001 không respond.
  Chẩn đoán và đề xuất recovery an toàn.

  Bắt đầu.

  ## 10. Chuỗi Dùng Thực Tế Theo Tình Huống

  ### Case A: Làm feature mới từ spec

  Dùng chuỗi:

  ui-spec-from-docs-mockups.md
  -> technical-api-design.md
  -> task-slicing.md
  -> mh-implement-feature.md
  -> scope-aware-review.md
  -> browser-e2e-smoke.md

  Nếu high-risk trước merge:

  -> deep-audit-orchestrator.md
  -> bugfix-from-report.md

  ### Case B: Fix bug user báo

  Dùng:

  bugfix-rca-single.md

  Nếu bug có E2E cụ thể:

  robust-test.md

  Nếu bug đến từ audit report:

  bugfix-from-report.md

  ### Case C: Chuẩn bị merge module

  Dùng:

  deep-audit-orchestrator.md
  -> bugfix-from-report.md
  -> harness/eval record nếu cần

  Nếu chỉ review diff nhỏ:

  scope-aware-review.md

  ### Case D: Muốn tối ưu harness tiếp

  Dùng:

  harness-readiness-check.md

  Nếu thấy vấn đề:

  doctor-drift-repair.md

  Nếu muốn chạy phase:

  harness-governance-phase-runner.md

  Nếu muốn chạy toàn bộ:

  harness-full-optimization-runner.md

  ### Case E: Không biết task nên chạy gì

  Dùng:

  router-dry-run-classifier.md

  Ví dụ:

  Đọc engine/prompts/router-dry-run-classifier.md làm system prompt.

  Classify prompt này:
  "thêm field số giường vào màn hình hội chẩn và lưu xuống DB"

  Không execute.

  Bắt đầu.

  Expected classification có thể là T2 vì chạm API/schema/DB/FE.

  ## 11. Quy Tắc Chọn Nhanh

  Nếu câu của bạn là:

  - “Audit sâu module này” -> deep-audit-orchestrator.md
  - “Sửa các bug trong report này” -> bugfix-from-report.md
  - “Sửa bug này” -> bugfix-rca-single.md
  - “Patch finding này thôi” -> mh-fix-approved-finding.md
  - “Implement feature này” -> mh-implement-feature.md
  - “Review diff này” -> scope-aware-review.md
  - “Test browser flow này” -> browser-e2e-smoke.md
  - “Harvest bug cả module” -> robust-test.md
  - “Flow E2E này fail, kiểm thử chắc rồi lập hồ sơ bug” -> robust-test.md
  - “Thiết kế UI từ mockup/doc” -> ui-spec-from-docs-mockups.md
  - “Thiết kế API/schema” -> technical-api-design.md
  - “Chia task cho agent” -> task-slicing.md
  - “Giao một task nhỏ cho subagent” -> incremental-impl-worker.md
  - “Không biết nên dùng workflow nào” -> router-dry-run-classifier.md
  - “Code này ở đâu/ai gọi?” -> codegraph-source-discovery.md
  - “Đổi này ảnh hưởng gì?” -> impact-analysis-preflight.md
  - “Harness có sẵn sàng chưa?” -> harness-readiness-check.md
  - “Doctor báo drift” -> doctor-drift-repair.md
  - “Cần lưu learning” -> learning-capture.md

  ## 12. Lưu Ý Quan Trọng

  Các prompt này không phải replacement cho harness rules. Chúng là wrapper mental model cho agent.

  Nếu prompt nói được làm nhưng AGENTS.md/guard nói không được, thì guard thắng.

  Nếu task có rủi ro nghiệp vụ, permission, billing, insurance, schema, migration, state-machine, multi-module, thì không dùng fast-path.

  Nếu không chắc prompt nào, dùng:

  Đọc engine/prompts/router-dry-run-classifier.md làm system prompt.

  Classify task sau và nói tôi nên dùng prompt nào:
  <task>

  Không execute.

  Đây là cách an toàn nhất để chọn prompt mà không đốt workflow sai.
