# main-brain knowledge — source of truth (LEAN)

> Owner-gated (guard-blocked; write only via `/promote`). **Loaded every session — keep it short.**
> One `##` section per durable, cross-cutting truth / lesson / decision. Link down to `engine/` + skills;
> do not duplicate their detail. Provisional knowledge lives in `second-brain/` until the owner promotes it.

## Owner Language / Agent Canon

Chat trả owner bằng tiếng Việt. Prompt/report canonical cho agent khác đọc có thể dùng tiếng Anh. Report dài
owner cần đọc nên có `.vi.md` companion hoặc tóm tắt tiếng Việt. Không dịch code, identifier, command, log lỗi.

## Verified Means Real Evidence

Chỉ nói `VERIFIED` khi đã chạy gate thật của project và test đúng user path thật. Nếu chưa chạy, nói
`NOT VERIFIED` và ghi residual risk. Với FE save/persist: thao tác thật, save, reload, đọc lại từ backend hoặc
state persisted.

## Convention Exceptions Need Current Evidence

Không skip project convention/pattern bằng trí nhớ cũ hoặc một exemplar đơn lẻ. Muốn ngoại lệ phải survey current
code population liên quan, cite evidence dạng N/total, và rà lại cascade decisions nếu premise cũ bị chứng minh sai.

## Test The Fix's New Risk

Fix là code mới nên có thể tạo bug mới. Sau fix, test edge cases của chính code path mới, không chỉ repro bug gốc.
Đặc biệt chú ý control mới, DTO path, state sync, migration, persistence, validation, permission, clinical/billing
logic.

## Batch Bugs By Dependency Phase

Khi owner approve fix nhiều bug: RCA/dedupe trước, gom owner decisions thành một batch, fix BE/contract trước rồi
build/migrate/regen DTO/test một lượt, sau đó fix FE rồi typecheck/smoke một lượt. Không tự launch workflow/agent
loop nếu chưa được confirm; không cắt manual review cho clinical, billing, permission, data correctness.

## Quality Comes From Harness Discipline

Đừng mặc định đổi model là tăng quality. Với harness này, quality chủ yếu đến từ reuse/Ponytail, quality gates,
scanner/checklist, workflow discipline, và validation thật. Chỉ đổi model khi có evidence rõ model hiện tại là
bottleneck.
