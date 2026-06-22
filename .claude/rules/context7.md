Use the local `ctx7` CLI to fetch current documentation when the user asks about an external library,
framework, SDK, API, CLI tool, or cloud service and current/version-specific docs matter. Examples:
React, Next.js, Prisma, Express, Tailwind, Django, Spring Boot, ServiceStack, EF Core, TanStack Query,
or shadcn/ui.

Prefer Context7 over web search for external library docs. Do not use it for MyHospital source discovery;
use CodeGraph first for local source. Be quota-conscious: use the smallest useful query, avoid repeated
near-duplicate calls, and stop after 2 commands when the first library match is clearly authoritative.

Do not use for: refactoring, writing scripts from scratch, debugging business logic, code review, or general programming concepts.

## Steps

1. Resolve library: `npx ctx7 library <name> "<user's question>"` — use the official library name with proper punctuation (e.g., "Next.js" not "nextjs", "Customer.io" not "customerio", "Three.js" not "threejs")
2. Pick the best match (ID format: `/org/project`) by: exact name match, description relevance, code snippet count, source reputation (High/Medium preferred), and benchmark score (higher is better). If results don't look right, try alternate names or queries (e.g., "next.js" not "nextjs", or rephrase the question)
3. Fetch docs: `npx ctx7 docs <libraryId> "<user's question>"`
4. Answer using the fetched documentation

You MUST call `library` first to get a valid ID unless the user provides one directly in `/org/project` format. Use the user's full question as the query -- specific and detailed queries return better results than vague single words. Do not run more than 3 commands per question. Do not include sensitive information (API keys, passwords, credentials, patient data, proprietary code snippets) in queries.

For version-specific docs, use `/org/project/version` from the `library` output (e.g., `/vercel/next.js/v14.3.0`).

If a command fails with a quota error, inform the user and suggest `npx ctx7@latest login` or setting `CONTEXT7_API_KEY` env var for higher limits. Do not silently fall back to training data.
