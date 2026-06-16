# Independent Harness Review Report

## A. Executive summary

* **Overall Verdict**: **Usable with issues**. The workspace harness is mostly well-adapted to the CachyOS Linux + fish terminal environment.
* **Core Strengths**: The Python-based `scripts/worktree.py` CLI is extremely robust, utilizes explicit `argv` list executions (blocking command injection risks), and properly supports custom slot allocations, dry-run flags, and safety assertions.
* **Crucial Risks**: The root workspace (`/home/dax/Documents/arabica/roast`) is **not a Git repository**. This presents a critical vulnerability because all root harness configs (`AGENTS.md`, `CLAUDE.md`, `justfile`, and scripts/hooks) are untracked and risk permanent loss during updates or system wipes unless explicitly backed up.
* **Shell Compatibility**: The `justfile` explicitly configures `set shell := ["bash", "-lc"]` which is a bash-only invocation, despite the active shell being `fish`.
* **Legacy Pollution**: Windows/PowerShell scripts and hardcoded Windows paths (`D:\arabica\roast`) are kept in the `scripts/legacy-powershell` directory, which is fine for historical reference but could theoretically cause confusion if indexers include them.
* **Security & Safety**: Subprocess executions are highly secure due to avoiding `shell=True`. However, there is a minor path-traversal/validation risk in `sync_db` where `args.be_path` is passed into `resolve_migration_source` and `scripts` without strict subdirectory validation.

---

## B. Scope reviewed

| Area | Files/paths checked | Method | Confidence |
|---|---|---|---|
| Workspace Root | `/home/dax/Documents/arabica/roast` | Directory listing, file content inspection | High |
| AGENTS.md Protocol | `AGENTS.md` | Full file analysis | High |
| CLAUDE.md Config | `CLAUDE.md` | Full file analysis | High |
| Worktree Tooling | `scripts/worktree.py` | Full code review (Python CLI & logic) | High |
| Hooks & Guards | `.claude/hooks/myhospital_guard.py`, `graphify_stale_check.py`, `.claude/settings.json` | Syntax check, parse verification, regex analysis | High |
| Tooling Documents | `scripts/README.md`, `scripts/WORKTREE-TOOLING.md` | Documentation matching & consistency check | High |
| Justfile Command Runner | `justfile` | Syntax review, recipe validation | High |
| Legacy Artifacts | `scripts/legacy-powershell/` | Grep-based legacy pattern verification | High |

---

## C. Validation commands run

| Command | Result | Notes |
|---|---|---|
| `python scripts/worktree.py --help` | Success | Correctly shows subcommands and help interface |
| `python scripts/worktree.py list` | Success | Returns "No worktrees directory found" safely |
| `python scripts/worktree.py create --slug audit-smoke --slot 1 --skip-db-sync --skip-fe-install --dry-run` | Success | Properly validates branch existences, fetches main repo status, and logs simulated operations without side-effects |
| `python scripts/worktree.py sync-main --dry-run` | Success | Simulates branch pull and stash extraction |
| `python -m py_compile .claude/hooks/graphify_stale_check.py ...` | Success | Syntax check successful for hook scripts |
| `git status --short` (root) | Failed | Exit code 128 (Root is not a Git repo) |
| `git -C myhospital-be status --short` | Success | Shows modified files in BE repository |
| `graphify --version` | Success | `graphify 0.8.39` |
| `just --list` | Success | Shows 4 recipes |

---

## D. Findings by severity

| ID | Severity | Area | Evidence | Why it matters | Recommended fix | Confidence |
|---|---|---|---|---|---|---|
| **F-01** | **High** | Git Repository / Infrastructure | `git status` output at root folder: `fatal: not a git repository` | If the root directory is not Git-tracked, changes to hooks, rules, helper scripts, and plans can easily be overwritten, lost, or diverge silently. | Initialize a Git repository at root and track all harness files, `.claude/settings.json`, and configs. Add `worktrees/`, `myhospital-fe/`, `myhospital-be/` to `.gitignore`. | High |
| **F-02** | **Medium** | Shell Compatibility | [justfile:L1](file:///home/dax/Documents/arabica/roast/justfile#L1): `set shell := ["bash", "-lc"]` | Forces bash syntax and environment execution inside `just` recipes, ignoring the user's `fish` shell environment. | Either change the shell configuration to fish syntax if strictly required, or specify shell wrappers per recipe. | High |
| **F-03** | **Medium** | Tooling Validation / Security | [worktree.py:L573-579](file:///home/dax/Documents/arabica/roast/scripts/worktree.py#L573-L579): `be_path` and `migration_be_path` parameters in `sync_db` | Path traversal or directory manipulation is possible if arbitrary paths are supplied by an agent or user without validating they reside in `/home/dax/Documents/arabica/roast/worktrees` or `/home/dax/Documents/arabica/roast/myhospital-be`. | Add path assertions to ensure targets are subdirectories of the workspace root. | High |
| **F-04** | **Low** | Hook Configuration | [.claude/settings.json:L61](file:///home/dax/Documents/arabica/roast/.claude/settings.json#L61) and [L70](file:///home/dax/Documents/arabica/roast/.claude/settings.json#L70) | These hook commands are inline shell/bash scripts containing specific pipes/subshells (`python3 -c ...`). If executed directly by an engine that doesn't use a POSIX shell parser, they might fail. | Port the inline python/shell string checks into `.claude/hooks/graphify_stale_check.py` or a dedicated python hook file rather than inline bash commands. | Medium |
| **F-05** | **Nit** | Legacy Code Pollution | [graphify-stale-check.ps1:L12](file:///home/dax/Documents/arabica/roast/scripts/legacy-powershell/claude-hooks/graphify-stale-check.ps1#L12): `D:\arabica\roast` | Legacy files references Windows directories like `D:\` and use PowerShell constructs which are deprecated. | Clean up or explicitly isolate legacy configs to avoid IDEs scanning and indexed token pollution. | High |

---

## E. Contradictions / ambiguities

| ID | Files/sections | Contradiction | Impact | Fix |
|---|---|---|---|---|
| **C-01** | `AGENTS.md` vs `justfile` | `AGENTS.md` says "no PowerShell... user shell is fish". `justfile` declares `set shell := ["bash", "-lc"]`. | Running commands via `just` runs them in `bash` rather than `fish`. | Update `justfile` to match the target environment shell, or clarify why `bash -lc` is required. |
| **C-02** | `AGENTS.md` vs `worktree.py` | `AGENTS.md` lists `sync DB, sync database = run python scripts/worktree.py sync-db`. However, `sync-db` CLI parameter `--be-path` is mandatory, but not stated as mandatory or explained how the agent should resolve it when routing instructions. | The agent might execute `sync-db` without `--be-path` and trigger CLI parse errors. | Update documentation to explain how the agent should supply/infer `--be-path` or default to the active worktree slug's BE folder. |

---

## F. Safety/security review

1. **Subprocess Invocation**: `scripts/worktree.py` uses `subprocess.run(argv, ...)` with list parameters and doesn't set `shell=True`. This is **very safe** and completely prevents command injection from variables such as custom slugs or slot options.
2. **Hook System Guard**: The `myhospital_guard.py` hook successfully catches dangerous operations like `git reset --hard`, `npm install <dep>`, and `rm -rf`. The hook is executed before tool calls and uses regex rules to trigger exits. It behaves as a **fail-closed** system: if the guard exits with code 2, the tool invocation is blocked.
3. **Database Safeguards**: Destructive actions (like drops and clears) are gated behind confirmation prompts (`confirm_or_exit`), unless `--yes` or `--dry-run` are supplied, preventing accidental execution.

---

## G. Workflow fit review

* **Linux/fish Fit**: Good. Executables are referenced cleanly, and fish fallbacks for Zellij attachments are provided in `AGENTS.md` and `CLAUDE.md`.
* **1 Worktree = 2 Sessions**: Standardized conventions are clear, naming configurations (`mh-<slug>-orch-<tool>`) are solid, and zellij scripts/fallbacks map onto this behavior correctly.
* **Root non-Git harness risk**: Very high. If the user works on multi-agent updates, there is no history or diff control of changes inside `scripts/`, `justfile`, `.claude/settings.json`, `AGENTS.md`, and `CLAUDE.md`.

---

## H. Upgrade backlog

| Priority | Upgrade | Why | Suggested implementation | Effort | Risk |
|---|---|---|---|---|---|
| **P0** | Track Workspace Root via Git | Avoid loss of harness scripts and allow tracking edits/updates to hooks/docs | Run `git init` in `/home/dax/Documents/arabica/roast`, add a `.gitignore` ignoring FE/BE/worktree folders, and commit the configs. | Low | None |
| **P1** | Add "Doctor" script / command | Validate local system dependencies (`docker`, `dotnet`, `node`, `graphify`) in one step | Add `scripts/harness_doctor.py` and a `just doctor` recipe. | Low | None |
| **P1** | Clean/Isolate Legacy folder | Avoid indexing Windows/PowerShell files | Pack `scripts/legacy-powershell` into a `.zip` archive or add it to ignore configs. | Low | None |
| **P2** | Port inline hooks to Python | Reduce shell dependence in `.claude/settings.json` hook definitions | Move the regex checks from settings.json hooks into `myhospital_guard.py`. | Medium | Low |

---

## I. Quick wins

* Update the `justfile` shell setting to fish, or add comments explaining the requirement for `bash -lc`.
* Archive the `scripts/legacy-powershell` directory to clean up raw files from workspace search/grep indexes.

---

## J. Questions for user

* Có kế hoạch đưa root workspace (`/home/dax/Documents/arabica/roast`) vào một repository Git riêng (hoặc submodule/harness repo) để quản lý cấu hình tiện ích này không?

---

## K. Final recommendation

1. **Có nên dùng harness hiện tại chưa?**
   **Nên dùng**. Nó đã sẵn sàng và hoạt động cực kì mượt mà trên môi trường Linux hiện tại. Các lệnh CLI dry-run đều chính xác.
2. **Cần sửa gì trước?**
   * Giải quyết việc quản lý phiên bản Git cho root workspace (hoặc back-up thủ công các file cấu hình).
3. **Ưu tiên 3 việc đầu tiên**:
   * Khởi tạo Git quản lý thư mục root (chỉ track files cấu hình harness).
   * Dọn dẹp/Zip thư mục `scripts/legacy-powershell` tránh pollute tìm kiếm.
   * Chuyển các inline hooks trong `.claude/settings.json` sang file Python thuần để tăng tính nhất quán và bảo mật.
