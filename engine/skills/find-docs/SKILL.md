---
name: find-docs
description: >-
  Fetch current external library/framework/API/CLI/cloud documentation with the
  local Context7 CLI. Use for version-sensitive docs such as React, Next.js,
  Prisma, Tailwind, EF Core, ServiceStack, TanStack Query, or shadcn/ui. Do not
  use for MyHospital source discovery; use CodeGraph first.
---

# find-docs

Use project-local Context7 only when current external docs matter.

Commands:

```bash
npx ctx7 library <name> "<specific question>"
npx ctx7 docs <libraryId> "<specific question>"
```

Rules:
- Call `library` first unless the owner/user provides a `/org/project` library ID.
- Prefer the best official/high-trust match; if ambiguous, ask instead of spending calls.
- Be quota-conscious: normally 2 commands total, never more than 3 commands per question.
- Never include API keys, credentials, patient data, or proprietary code in queries.
- If quota fails, say so and do not silently rely on stale training data.
