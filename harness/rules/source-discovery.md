# Source-code discovery policy — canonical reference

> Single source of truth for **how agents find and understand source code** in this
> workspace. `AGENTS.md` and `CLAUDE.md` carry a short version and point here.
> User-facing commands are **fish**; the tools themselves are shell-agnostic.

This policy exists to stop two expensive anti-patterns:

1. Broad-scanning all of `myhospital-fe/` / `myhospital-be/` with `rg`/`fd` and dumping
   the output into context (slow, token-heavy, misleading).
2. Using **graphify** as a source-code finder. Graphify maps `docs/`+`specs/` **design
   intent only — never code** (see `docs/graphify-agent-guide.md`).

## Tool roles (do not mix them up)

| Tool | Use it for | Never use it for |
|---|---|---|
| **CodeGraph** | Broad **source-code** exploration: how a flow works, where a feature lives, call relationships, blast radius, symbol discovery. | Docs/specs design intent. `.docx`/`.pdf`. |
| **rg / fd / bat** | **Bounded, exact** search in a **known, small** scope (`rg -l`, a single package, a few files). | Broad "scan the whole FE/BE and dump" discovery. |
| **ast-grep** | Structural / AST pattern search when text search is too blunt. | Plain string lookups (use `rg -l`). |
| **rga** | Exact keyword inside `.docx` / `.pdf`. | Source code. |
| **graphify** | `docs/`+`specs/` **design/business** relationships — *only when the graph is fresh* (it is currently STALE; see graphify guide). | Source code. Anything in `myhospital-fe/`, `myhospital-be/`, `worktrees/`. |

## Discovery order for SOURCE CODE

1. **CodeGraph first** for any "how / where / what-calls / what-breaks" question.
   - Agents with the CodeGraph **MCP server** (Claude Code, Codex, opencode, …): call the
     MCP tools — `codegraph_explore`, `codegraph_node`, `codegraph_search`, `codegraph_callers`.
   - From a shell, the equivalent CLI (run inside the indexed repo — `myhospital-be/`,
     `myhospital-fe/`, or a `worktrees/<slug>/{be,fe}`):

     | Question | Command |
     |---|---|
     | How does a flow work? | `codegraph explore "How is AdmissionOrder created and processed?"` |
     | Find a symbol by name | `codegraph query AdmissionOrder` |
     | One symbol's source + caller/callee trail, or read a file | `codegraph node AdmissionService.Create` |
     | Who calls this? | `codegraph callers CreateAdmission` |
     | What does it call? | `codegraph callees CreateAdmission` |
     | Blast radius of a change | `codegraph impact AdmissionOrder` |
     | Which files/tests depend on changed files | `codegraph affected path/to/Changed.cs` |

2. **Bounded `rg`** only when you need an exact string in an already-narrow scope. Always
   scope the path and cap output:

   ```fish
   rg -l "AdmissionOrder" worktrees/<slug>/be worktrees/<slug>/fe | head -20
   rg -n -C 2 -m 5 "DepartmentStay" worktrees/<slug>/be
   ```

3. **`ast-grep`** when you need structural matches (e.g. all call sites with a specific
   argument shape) that text search can't express cleanly.

4. **Read files only after** CodeGraph (or a bounded `rg`) has narrowed you to a small
   candidate set. Treat source returned by CodeGraph as **already read** — only open the
   real file when you need exact line numbers to edit or quote.

### Bad vs good

```fish
# BAD — broad scan + dump, no scope, no cap
rg "Admission" .

# GOOD — CodeGraph for the "how/where", bounded rg for the exact hit
codegraph explore "How is AdmissionOrder created and processed?"
codegraph query AdmissionOrder
codegraph impact AdmissionOrder
rg -l "AdmissionOrder" worktrees/<slug>/be | head -20
```

## Discovery order for DOCS / SPECS (unchanged)

- **`rga`** for an exact keyword inside `.docx` / `.pdf` (BA docs).
- **graphify** *only* for a docs/specs **design-decision / relationship** question, and
  *only* when the graph is fresh — it is currently STALE (Windows-built). Reading the
  spec file directly is always an acceptable substitute. graphify is **never** required
  before reading or searching code.

  ```fish
  graphify query "Ngày giường nội trú được tính theo rule nghiệp vụ nào?"
  rga "Ngày giường" specs/
  ```

## Where the CodeGraph index lives

CodeGraph indexes a single git repo per `.codegraph/` directory and honors that repo's
`.gitignore`. The **workspace root is NOT indexed** — the root `.gitignore` excludes
`myhospital-fe/`, `myhospital-be/`, and `worktrees/`, so a root index would see almost no
code. Indexes are therefore created **per code repo**:

- `myhospital-be/.codegraph/` and `myhospital-fe/.codegraph/` (the stable main repos).
- `worktrees/<slug>/be/.codegraph/` and `.../fe/.codegraph/` for an **active** worktree
  (initialize when the worktree becomes an active task — see
  `harness/rules/worktree-workflow.md`).

CodeGraph auto-skips `node_modules`, `dist`, `build`, `target`, `.venv`, `.next`, files
> 1 MB, and anything gitignored. It auto-syncs on file change (inotify, ~2 s debounce),
so after edits the graph is normally current; if in doubt run `codegraph status` (or
`codegraph sync`) inside the repo.

## Quick commands

```fish
# Index status / refresh for the main repos
just codegraph-status          # status for be + fe
just codegraph-init-main       # one-time init for be + fe
just codegraph-sync-main       # force incremental sync

# For an active worktree
just codegraph-init-worktree <slug>
just codegraph-status-worktree <slug>
just codegraph-sync-worktree <slug>

# Health check (includes CodeGraph)
just doctor
```

## Rollback

```fish
codegraph uninstall            # remove CodeGraph MCP wiring from agents
codegraph uninit               # remove a project's .codegraph/ index (run in the repo)
```
