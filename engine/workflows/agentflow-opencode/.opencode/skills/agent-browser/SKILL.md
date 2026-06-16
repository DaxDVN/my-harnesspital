---
name: agent-browser
description: Browser automation CLI for AI agents. Use for E2E testing, navigating pages, clicking, filling forms, taking screenshots, reading accessibility-tree snapshots, collecting browser evidence, exploratory QA, and web app bug hunts. Prefer agent-browser over Playwright MCP, webfetch, websearch, raw curl, or ad-hoc browser scripts for browser E2E work.
compatibility: opencode
metadata:
  source: vercel-labs/agent-browser
  installed_version: 0.27.3
---

# agent-browser

Fast browser automation CLI for AI agents. Chrome/Chromium via CDP with
accessibility-tree snapshots and compact `@eN` element refs.

This project uses the vendored shim:

```bash
.agentflow/bin/agent-browser
```

The wrapper scripts prepend `.agentflow/bin` to `PATH`, so OpenCode can normally
run:

```bash
agent-browser skills get core
agent-browser open https://example.com
agent-browser snapshot -i
agent-browser click @e2
agent-browser fill @e3 "value"
agent-browser screenshot body .agentflow/logs/agent-browser/page.png
agent-browser close
```

Before running browser tasks, load the installed version's current guide:

```bash
agent-browser skills get core
```

Use specialized guides when relevant:

```bash
agent-browser skills get dogfood
agent-browser skills get electron
agent-browser skills get slack
agent-browser skills get vercel-sandbox
agent-browser skills get agentcore
```

Important workflow rules:

- Use `agent-browser open <url>` for real browser navigation.
- Use `agent-browser snapshot -i` after opening and after every page-changing action.
- Interact with refs from the most recent snapshot, for example `@e1`.
- Re-snapshot after clicks, navigation, form submits, modal opens, or dynamic UI changes.
- Use `agent-browser wait --text "..."`, `wait --url "**/..."`, or `wait --load networkidle` instead of blind sleeps.
- Save screenshots under `.agentflow/logs/agent-browser/` or the current round's `logs/` directory.
- Close sessions with `agent-browser close` or `agent-browser close --all` when done.
- Do not use Playwright MCP for E2E in this harness unless the user explicitly asks for a fallback.
