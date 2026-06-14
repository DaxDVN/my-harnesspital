#!/usr/bin/env python3
"""Linux-friendly MyHospital workspace worktree tooling.

This CLI replaces the old PowerShell workspace scripts with a shell-agnostic
Python entrypoint. It intentionally keeps subprocess calls as argv lists and
avoids fish/bash-specific syntax.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_SQL_PASSWORD = os.environ.get("MYHOSPITAL_SQL_PASSWORD", "Hospital123!")


@dataclass(frozen=True)
class SlotConfig:
    slot: int
    fe_port: int
    be_port: int
    sql_port: int
    container_name: str
    volume_name: str
    database_name: str = "MyHospital"


@dataclass(frozen=True)
class MigrationSource:
    path: Path
    migrations_path: Path
    label: str
    stamp: float


class ToolError(RuntimeError):
    pass


def workspace_root() -> Path:
    script_root = Path(__file__).resolve().parent
    return script_root.parent


def slot_config(slot: int) -> SlotConfig:
    if slot not in {1, 2, 3, 4}:
        raise ToolError("Slot must be one of 1, 2, 3, 4.")
    return SlotConfig(
        slot=slot,
        fe_port=3000 + slot,
        be_port=5000 + slot,
        sql_port=1433 + slot,
        container_name=f"mssql-hospital-wt{slot}",
        volume_name=f"myhospital-mssql-wt{slot}",
    )


def safe_slug(slug: str) -> str:
    # Collapse anything that is not [a-z0-9] into single dashes. This drops path
    # separators and dots, so ".."/leading-dot/traversal inputs cannot survive
    # into a filesystem path or a git branch name.
    value = re.sub(r"[^a-z0-9]+", "-", (slug or "").strip().lower()).strip("-")
    if not value:
        raise ToolError(
            f"Slug {slug!r} has no usable [a-z0-9-] characters for a branch/path name."
        )
    # Defensive belt-and-suspenders: the regex above already guarantees this.
    if value in {".", ".."} or "/" in value or "\\" in value or value.startswith("."):
        raise ToolError(f"Refusing unsafe slug {slug!r}.")
    return value


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise ToolError(f"Required command {name!r} was not found on PATH.")


def format_cmd(argv: Iterable[object]) -> str:
    return " ".join(str(part) for part in argv)


_SECRET_KEY_RE = re.compile(r"(SA_)?(PASSWORD|PASSWD|PWD|TOKEN|SECRET)", re.IGNORECASE)
_CONN_PW_RE = re.compile(r"(Password|Pwd)=([^;]*)", re.IGNORECASE)


def redact_cmd(argv: Iterable[object]) -> str:
    """Render a command for logging with secrets masked.

    Masks the value after ``-P``/``--password`` (sqlcmd), any ``KEY=VALUE`` whose
    key looks like a credential (e.g. ``MSSQL_SA_PASSWORD=``), and ``Password=...``
    inside connection strings.
    """
    parts = [str(part) for part in argv]
    out: list[str] = []
    mask_next = False
    for part in parts:
        if mask_next:
            out.append("***")
            mask_next = False
            continue
        if part in ("-P", "--password"):
            out.append(part)
            mask_next = True
            continue
        if "=" in part:
            key = part.split("=", 1)[0]
            if _SECRET_KEY_RE.fullmatch(key) or _SECRET_KEY_RE.search(key):
                out.append(f"{key}=***")
                continue
        if _CONN_PW_RE.search(part):
            out.append(_CONN_PW_RE.sub(r"\1=***", part))
            continue
        out.append(part)
    return " ".join(out)


def run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    dry_run: bool = False,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    print(f"> {redact_cmd(argv)}")
    if dry_run:
        return subprocess.CompletedProcess(argv, 0, "", "")
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        env=merged_env,
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def output(argv: list[str], *, cwd: Path | None = None, check: bool = True) -> str:
    proc = run(argv, cwd=cwd, check=check, capture=True)
    return proc.stdout.strip()


@contextmanager
def temp_env(values: dict[str, object]):
    old_values: dict[str, str | None] = {}
    for key, value in values.items():
        old_values[key] = os.environ.get(key)
        os.environ[key] = str(value)
    try:
        yield
    finally:
        for key, value in old_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def confirm_or_exit(prompt: str, yes: bool) -> None:
    if yes:
        return
    print()
    answer = input(f"{prompt}\nType 'yes' to continue: ")
    if answer != "yes":
        print("Cancelled.")
        raise SystemExit(1)


def read_env_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def set_env_line(lines: list[str], name: str, value: object) -> list[str]:
    pattern = re.compile(rf"^\s*{re.escape(name)}=")
    rendered = f"{name}={value}"
    updated: list[str] = []
    found = False
    for line in lines:
        if pattern.search(line):
            updated.append(rendered)
            found = True
        else:
            updated.append(line)
    if not found:
        updated.append(rendered)
    return updated


def write_lines(path: Path, lines: list[str], *, dry_run: bool = False) -> None:
    print(f"> write {path}")
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def migrations_path(be_path: Path) -> Path:
    return be_path / "MyHospital.ServiceInterface" / "Migrations"


def migration_stamp(path: Path) -> float:
    cs_files = list(path.glob("*.cs"))
    if cs_files:
        return max(file.stat().st_mtime for file in cs_files)
    return path.stat().st_mtime


def resolve_migration_source(
    root: Path,
    *,
    be_path: Path | None = None,
    preferred_path: Path | None = None,
    scan_worktrees: bool = False,
) -> MigrationSource:
    candidates: list[MigrationSource] = []
    seen: set[Path] = set()

    def add(path: Path | None, label: str) -> None:
        if path is None:
            return
        try:
            resolved = path.resolve(strict=True)
        except FileNotFoundError:
            return
        if resolved in seen:
            return
        seen.add(resolved)
        mig = migrations_path(resolved)
        if mig.exists():
            candidates.append(MigrationSource(resolved, mig, label, migration_stamp(mig)))

    if preferred_path:
        add(preferred_path, "preferred")
        if not candidates:
            raise ToolError(
                "Migration source does not contain "
                f"MyHospital.ServiceInterface/Migrations: {preferred_path}"
            )
        return candidates[0]

    add(be_path, "current BE")
    add(root / "myhospital-be", "main BE")

    if scan_worktrees:
        worktrees_root = root / "worktrees"
        if worktrees_root.exists():
            for child in worktrees_root.iterdir():
                if child.is_dir() and child.name != "_db-backups":
                    add(child / "be", f"worktree/{child.name}")

    if not candidates:
        raise ToolError(
            "No BE migrations folder found. Expected "
            "MyHospital.ServiceInterface/Migrations in myhospital-be or an explicit path."
        )
    return sorted(candidates, key=lambda item: item.stamp, reverse=True)[0]


def sql_connection_string(
    port: int,
    *,
    database: str = "MyHospital",
    user: str = "sa",
    password: str = DEFAULT_SQL_PASSWORD,
) -> str:
    return (
        f"Server=localhost,{port};Initial Catalog={database};User ID={user};"
        f"Password={password};MultipleActiveResultSets=False;Encrypt=False;"
        "TrustServerCertificate=True;Connection Timeout=30;"
    )


def assert_safe_sql_name(name: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise ToolError(f"Unsafe SQL identifier {name!r}. Use letters, numbers, and underscores only.")


def is_port_listening(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            return sock.connect_ex(("127.0.0.1", port)) == 0
    except OSError:
        # Never let a sandbox/permission/socket error abort a preview or create.
        return False


def wait_sql_container(container_name: str, password: str, *, timeout_seconds: int = 120) -> None:
    deadline = time.monotonic() + timeout_seconds
    command = [
        "docker",
        "exec",
        container_name,
        "/opt/mssql-tools18/bin/sqlcmd",
        "-S",
        "localhost",
        "-U",
        "sa",
        "-P",
        password,
        "-C",
        "-b",
        "-Q",
        "SELECT 1",
    ]
    while time.monotonic() < deadline:
        proc = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if proc.returncode == 0:
            return
        time.sleep(3)
    raise ToolError(f"SQL Server container {container_name!r} did not become ready within {timeout_seconds}s.")


def docker_container_id(name: str, *, running: bool = False) -> str:
    args = ["docker", "ps", "-q" if running else "-aq", "--filter", f"name=^{name}$"]
    return output(args, check=True)


def init_db_slots(args: argparse.Namespace) -> None:
    require_command("docker")
    image = args.image
    password = args.sa_password
    if args.pull:
        run(["docker", "pull", image], dry_run=args.dry_run)

    for slot in args.slots:
        cfg = slot_config(slot)
        print()
        print(f"== Slot {slot}: {cfg.container_name} localhost:{cfg.sql_port} ==")
        if args.dry_run:
            print(f"> inspect/start/create {cfg.container_name}")
            continue
        existing = docker_container_id(cfg.container_name)
        if existing:
            running = docker_container_id(cfg.container_name, running=True)
            if running:
                print("Container already running.")
            else:
                run(["docker", "start", cfg.container_name])
        else:
            run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    cfg.container_name,
                    "-e",
                    "ACCEPT_EULA=Y",
                    "-e",
                    f"MSSQL_SA_PASSWORD={password}",
                    "-e",
                    "MSSQL_PID=Developer",
                    "-p",
                    f"{cfg.sql_port}:1433",
                    "-v",
                    f"{cfg.volume_name}:/var/opt/mssql",
                    image,
                ]
            )
        wait_sql_container(cfg.container_name, password)
        print(f"Ready: SQL Server slot {slot} on localhost,{cfg.sql_port}")
    print()
    print("DB slots are ready.")


def git_skip_worktree_files(repo: Path) -> list[str]:
    proc = run(["git", "-C", str(repo), "ls-files", "-v"], capture=True, check=True)
    files: list[str] = []
    for line in proc.stdout.splitlines():
        if line.startswith("S "):
            files.append(line[2:].strip())
    return files


def remove_telerik_from_solution(be_path: Path, *, dry_run: bool = False) -> None:
    sln_files = list(be_path.glob("*.sln"))
    if not sln_files:
        print(f"Warning: no .sln file found in {be_path}; skipping Telerik removal.")
        return
    sln = sln_files[0]
    content = sln.read_text(encoding="utf-8", errors="ignore")
    matches = re.findall(r'Project\("[^"]+"\)\s*=\s*"[^"]*",\s*"([^"]*[Tt]elerik[^"]*\.csproj)"', content)
    if not matches:
        print(f"No Telerik projects found in {sln.name}; nothing to remove.")
        return
    for project in matches:
        print(f"Removing Telerik project: {project}")
        run(["dotnet", "sln", str(sln), "remove", project], cwd=be_path, dry_run=dry_run, check=False)
    print("Telerik removal done.")


def copy_skip_worktree_files(repo: Path, worktree: Path, label: str, *, dry_run: bool = False) -> None:
    skip_files = git_skip_worktree_files(repo)
    if not skip_files:
        print(f"  {label}: no skip-worktree files detected.")
        return
    for rel in skip_files:
        src = repo / rel
        dst = worktree / rel
        if src.exists():
            print(f"  {label} skip-worktree copied: {rel}")
            if not dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            run(["git", "-C", str(worktree), "update-index", "--skip-worktree", rel], dry_run=dry_run)
        else:
            print(f"Warning: {label} skip-worktree source not found in main repo: {rel}")


def _rollback_create(
    created: list[tuple[Path, str, Path]],
    task_root: Path,
    *,
    dry_run: bool,
) -> None:
    """Best-effort rollback of a partially-created worktree set.

    Only removes worktrees/branches this invocation actually created (tracked in
    ``created``). Each step is best-effort and logged so a stuck rollback never
    masks the original error.
    """
    if dry_run or not created:
        return
    print()
    print("Rolling back partially-created worktree(s)...", file=sys.stderr)
    for repo, branch, path in reversed(created):
        try:
            if path.exists():
                run(["git", "-C", str(repo), "worktree", "remove", "--force", str(path)], check=False)
            run(["git", "-C", str(repo), "worktree", "prune"], check=False)
            run(["git", "-C", str(repo), "branch", "-D", branch], check=False)
        except Exception as exc:  # noqa: BLE001 - rollback must never raise
            print(f"  rollback warning ({path}): {exc}", file=sys.stderr)
    try:
        if task_root.exists() and not any(task_root.iterdir()):
            task_root.rmdir()
    except OSError:
        pass


def create_worktree(args: argparse.Namespace) -> None:
    root = workspace_root()
    slug = safe_slug(args.slug)
    cfg = slot_config(args.slot)
    fe_repo = root / "myhospital-fe"
    be_repo = root / "myhospital-be"
    task_root = root / "worktrees" / slug
    fe_worktree = task_root / "fe"
    be_worktree = task_root / "be"
    fe_branch = args.fe_branch or f"feature/{slug}"
    be_branch = args.be_branch or f"feature/{slug}"

    require_command("git")
    if not args.skip_fe_install:
        require_command("npm")
    if not fe_repo.exists():
        raise ToolError(f"FE repo not found: {fe_repo}")
    if not be_repo.exists():
        raise ToolError(f"BE repo not found: {be_repo}")
    if task_root.exists():
        raise ToolError(f"Task worktree folder already exists: {task_root}")

    migration_source = None
    if not args.skip_db_sync or args.migration_be_path:
        migration_source = resolve_migration_source(
            root,
            preferred_path=Path(args.migration_be_path) if args.migration_be_path else None,
            scan_worktrees=args.scan_worktrees,
        )
        print(f"Using migration source: {migration_source.path} ({migration_source.label})")

    for repo, ref, label in ((fe_repo, args.fe_base, "FE base"), (be_repo, args.be_base, "BE base")):
        run(["git", "-C", str(repo), "rev-parse", "--verify", f"{ref}^{{commit}}"], capture=True)
        print(f"{label} OK: {ref}")

    for repo, branch, label in ((fe_repo, fe_branch, "FE branch"), (be_repo, be_branch, "BE branch")):
        proc = subprocess.run(
            ["git", "-C", str(repo), "show-ref", "--verify", f"refs/heads/{branch}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if proc.returncode == 0:
            raise ToolError(f"{label} {branch!r} already exists. Choose another slug or branch.")

    if not args.allow_port_in_use:
        for port in (cfg.fe_port, cfg.be_port):
            if is_port_listening(port):
                raise ToolError(
                    f"Port {port} is already listening. Stop that process, choose another slot, "
                    "or pass --allow-port-in-use."
                )

    fe_source_ref = f"refs/remotes/origin/{args.fe_base}"
    be_source_ref = f"refs/remotes/origin/{args.be_base}"
    run(["git", "-C", str(fe_repo), "fetch", "origin", f"+refs/heads/{args.fe_base}:{fe_source_ref}"], dry_run=args.dry_run)
    run(["git", "-C", str(be_repo), "fetch", "origin", f"+refs/heads/{args.be_base}:{be_source_ref}"], dry_run=args.dry_run)

    # Everything below mutates local state. Track what we create so a failure on
    # either side rolls back cleanly instead of leaving a half-built worktree
    # that blocks the next retry ("folder already exists").
    created: list[tuple[Path, str, Path]] = []
    try:
        if not args.dry_run:
            task_root.mkdir(parents=True, exist_ok=True)
        run(["git", "-C", str(fe_repo), "worktree", "add", "-b", fe_branch, str(fe_worktree), fe_source_ref], dry_run=args.dry_run)
        if not args.dry_run:
            created.append((fe_repo, fe_branch, fe_worktree))
        run(["git", "-C", str(be_repo), "worktree", "add", "-b", be_branch, str(be_worktree), be_source_ref], dry_run=args.dry_run)
        if not args.dry_run:
            created.append((be_repo, be_branch, be_worktree))

        remove_telerik_from_solution(be_worktree, dry_run=args.dry_run)

        fe_template = fe_repo / ".env"
        if not fe_template.exists():
            fe_template = fe_repo / "env"
        fe_lines = read_env_lines(fe_template)
        fe_lines = set_env_line(fe_lines, "VITE_DEV_PORT", cfg.fe_port)
        fe_lines = set_env_line(fe_lines, "VITE_BACKEND_URL", f"http://localhost:{cfg.be_port}")
        fe_lines = set_env_line(fe_lines, "VITE_INDEXEDDB_VERSION", 100 + args.slot)
        fe_lines = set_env_line(fe_lines, "VITE_DEV_PERSIST_ALL", "true")
        write_lines(fe_worktree / ".env", fe_lines, dry_run=args.dry_run)

        target_connection = sql_connection_string(cfg.sql_port, database=cfg.database_name, password=args.sql_password)
        cors_origins = ",".join(
            [
                "http://localhost:5173",
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:3002",
                "http://localhost:3003",
                "http://localhost:3004",
                "http://localhost:5000",
                "http://localhost:5001",
                "http://localhost:5002",
                "http://localhost:5003",
                "http://localhost:5004",
            ]
        )
        be_lines = read_env_lines(be_repo / ".env")
        be_lines = set_env_line(be_lines, "ASPNETCORE_ENVIRONMENT", "Development")
        be_lines = set_env_line(be_lines, "ASPNETCORE_URLS", f"http://localhost:{cfg.be_port}")
        be_lines = set_env_line(be_lines, "ConnectionStrings__DefaultConnection", target_connection)
        be_lines = set_env_line(be_lines, "ConnectionStrings__ReadOnlyConnection", target_connection)
        be_lines = set_env_line(be_lines, "CORS_ORIGINS", cors_origins)
        write_lines(be_worktree / ".env", be_lines, dry_run=args.dry_run)

        for rel in ("MyHospital/LocalBootstrap.cs", "nuget.config"):
            src = be_repo / rel
            dst = be_worktree / rel
            if src.exists():
                print(f"> copy {src} -> {dst}")
                if not args.dry_run:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
            else:
                print(f"Warning: local-only file not found in main BE repo: {rel}")

        print()
        print("Copying skip-worktree local-config files...")
        copy_skip_worktree_files(fe_repo, fe_worktree, "FE", dry_run=args.dry_run)
        copy_skip_worktree_files(be_repo, be_worktree, "BE", dry_run=args.dry_run)

        if not args.skip_fe_install:
            print()
            print("Installing FE dependencies...")
            package_lock = fe_worktree / "package-lock.json"
            npm_args = ["npm", "ci" if package_lock.exists() else "install", "--no-audit", "--fund=false"]
            run(npm_args, cwd=fe_worktree, dry_run=args.dry_run)
        else:
            print()
            print("Skipping FE dependency install because --skip-fe-install was passed.")

        if not args.skip_db_sync:
            sync_args = argparse.Namespace(
                slot=args.slot,
                be_path=str(be_worktree),
                migration_be_path=str(migration_source.path) if migration_source and migration_source.path != be_worktree else None,
                source_server="localhost",
                source_port=1433,
                source_database="MyHospital",
                target_database="MyHospital",
                sql_user="sa",
                sql_password=args.sql_password,
                python="python",
                backup_dir=None,
                yes=True,
                dry_run=args.dry_run,
                scan_worktrees=args.scan_worktrees,
            )
            sync_db(sync_args)
        elif not getattr(args, "skip_db_init", False):
            init_db_slots(
                argparse.Namespace(
                    slots=[args.slot],
                    image=args.image,
                    sa_password=args.sql_password,
                    pull=False,
                    dry_run=args.dry_run,
                )
            )
        else:
            print()
            print("Skipping DB slot init because --skip-db-init was passed (no Docker/SQL containers touched).")
    except (subprocess.CalledProcessError, ToolError, OSError) as exc:
        print(f"\nERROR: worktree creation failed: {exc}", file=sys.stderr)
        _rollback_create(created, task_root, dry_run=args.dry_run)
        raise

    print()
    print(f"Worktree ready: {task_root}")
    print(f"FE: {fe_worktree}")
    print(f"BE: {be_worktree}")
    print()
    print("Run BE:")
    print(f"  cd {be_worktree}")
    print("  dotnet run --project MyHospital --no-launch-profile")
    print()
    print("Run FE:")
    print(f"  cd {fe_worktree}")
    if args.skip_fe_install:
        print("  npm install")
    else:
        print("  # FE dependencies were installed by this script")
    print("  npm run dtos:update")
    print("  npm run client:generate")
    print("  npm run dev")
    print()
    print(f"URLs: FE http://localhost:{cfg.fe_port}, BE http://localhost:{cfg.be_port}, DB localhost,{cfg.sql_port}/{cfg.database_name}")


def backup_data_tables(backup_file: Path) -> list[tuple[str, str, int]]:
    tables: list[tuple[str, str, int]] = []
    pattern = re.compile(r"^--\s*=+\s*([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\s*\((\d+)\s*rows\)")
    for line in backup_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = pattern.search(line)
        if match:
            tables.append((match.group(1), match.group(2), int(match.group(3))))
    return tables


def sync_db(args: argparse.Namespace) -> None:
    root = workspace_root()
    cfg = slot_config(args.slot)
    be_path = Path(args.be_path).resolve()
    migration_source = resolve_migration_source(
        root,
        be_path=be_path,
        preferred_path=Path(args.migration_be_path) if args.migration_be_path else None,
        scan_worktrees=args.scan_worktrees,
    )

    assert_safe_sql_name(args.source_database)
    assert_safe_sql_name(args.target_database)
    for command in ("git", "docker", "dotnet", args.python):
        require_command(command)

    backup_dir = Path(args.backup_dir).resolve() if args.backup_dir else root / "_db-backups"
    if not args.dry_run:
        backup_dir.mkdir(parents=True, exist_ok=True)

    confirm_or_exit(
        (
            f"This will replace DB objects and data in slot {args.slot} "
            f"({cfg.container_name}, localhost,{cfg.sql_port}/{args.target_database}).\n"
            f"Source data: {args.source_server},{args.source_port}/{args.source_database}"
        ),
        args.yes or args.dry_run,
    )

    init_db_slots(
        argparse.Namespace(
            slots=[args.slot],
            image="mcr.microsoft.com/mssql/server:2022-latest",
            sa_password=args.sql_password,
            pull=False,
            dry_run=args.dry_run,
        )
    )

    if not args.dry_run:
        wait_sql_container(cfg.container_name, args.sql_password)

    create_db_sql = f"IF DB_ID(N'{args.target_database}') IS NULL CREATE DATABASE [{args.target_database}];"
    run(
        [
            "docker",
            "exec",
            cfg.container_name,
            "/opt/mssql-tools18/bin/sqlcmd",
            "-S",
            "localhost",
            "-U",
            args.sql_user,
            "-P",
            args.sql_password,
            "-C",
            "-b",
            "-Q",
            create_db_sql,
        ],
        dry_run=args.dry_run,
    )

    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    backup_file = backup_dir / f"backup-data-slot{args.slot}-{timestamp}.sql"

    print()
    print(f"Backing up source DB to {backup_file}")
    with temp_env(
        {
            "DB_SERVER": args.source_server,
            "DB_PORT": args.source_port,
            "DB_NAME": args.source_database,
            "DB_USER": args.sql_user,
            "DB_PASSWORD": args.sql_password,
            "OUTPUT_FILE": backup_file,
        }
    ):
        run([args.python, "Scripts/export_db_data.py"], cwd=be_path, dry_run=args.dry_run)

    print()
    print(f"Clearing target DB objects in slot {args.slot}")
    with temp_env(
        {
            "DB_SERVER": "localhost",
            "DB_PORT": cfg.sql_port,
            "DB_NAME": args.target_database,
            "DB_USER": args.sql_user,
            "DB_PASSWORD": args.sql_password,
        }
    ):
        run([args.python, "Scripts/drop_db_objects.py"], cwd=be_path, dry_run=args.dry_run)

    target_connection = sql_connection_string(
        cfg.sql_port,
        database=args.target_database,
        user=args.sql_user,
        password=args.sql_password,
    )

    print()
    print("Applying EF migrations to target DB")
    if migration_source.path != be_path:
        print(f"Migration source: {migration_source.path}")
    run(["dotnet", "restore", "MyHospital.sln"], cwd=migration_source.path, dry_run=args.dry_run)
    with temp_env(
        {
            "ASPNETCORE_ENVIRONMENT": "Development",
            "DOTNET_ENVIRONMENT": "Development",
            "ConnectionStrings__DefaultConnection": target_connection,
            "ConnectionStrings__ReadOnlyConnection": target_connection,
        }
    ):
        run(
            [
                "dotnet",
                "ef",
                "database",
                "update",
                "--connection",
                target_connection,
                "--project",
                "MyHospital.ServiceInterface",
                "--startup-project",
                "MyHospital",
            ],
            cwd=migration_source.path,
            dry_run=args.dry_run,
        )

    if not args.dry_run:
        table_count_sql = (
            "SET NOCOUNT ON; SELECT COUNT(*) FROM sys.tables "
            "WHERE is_ms_shipped = 0 AND name <> N'__EFMigrationsHistory';"
        )
        proc = run(
            [
                "docker",
                "exec",
                cfg.container_name,
                "/opt/mssql-tools18/bin/sqlcmd",
                "-S",
                "localhost",
                "-U",
                args.sql_user,
                "-P",
                args.sql_password,
                "-C",
                "-b",
                "-d",
                args.target_database,
                "-h",
                "-1",
                "-W",
                "-Q",
                table_count_sql,
            ],
            capture=True,
        )
        count = next((int(line) for line in proc.stdout.splitlines() if line.strip().isdigit()), 0)
        if count <= 0:
            raise ToolError(
                f"EF migrations did not create any user tables in localhost,{cfg.sql_port}/{args.target_database}."
            )

    if not args.dry_run and backup_file.exists():
        tables = backup_data_tables(backup_file)
    else:
        tables = []

    if tables:
        clear_file = backup_dir / f"pre-import-clear-slot{args.slot}-{timestamp}.sql"
        clear_lines = [
            "SET QUOTED_IDENTIFIER ON;",
            "SET ANSI_NULLS ON;",
            "SET ANSI_WARNINGS ON;",
            "SET ANSI_PADDING ON;",
            "SET ARITHABORT ON;",
            "SET CONCAT_NULL_YIELDS_NULL ON;",
            "SET NUMERIC_ROUNDABORT OFF;",
            "SET NOCOUNT ON;",
            "SET XACT_ABORT ON;",
            "PRINT 'Disabling foreign key constraints before pre-import cleanup';",
            "DECLARE @fkSql NVARCHAR(MAX) = N'';",
            "SELECT @fkSql = @fkSql + N'ALTER TABLE '",
            "    + QUOTENAME(OBJECT_SCHEMA_NAME(parent_object_id)) + N'.' + QUOTENAME(OBJECT_NAME(parent_object_id))",
            "    + N' NOCHECK CONSTRAINT ' + QUOTENAME(name) + N';' + CHAR(10)",
            "FROM sys.foreign_keys;",
            "EXEC sp_executesql @fkSql;",
            "",
            "PRINT 'Clearing migration-seeded rows from tables present in source backup';",
        ]
        seen: set[tuple[str, str]] = set()
        for schema, table, _rows in reversed(tables):
            key = (schema, table)
            if key in seen:
                continue
            seen.add(key)
            clear_lines.append(f"IF OBJECT_ID(N'{schema}.{table}', N'U') IS NOT NULL DELETE FROM [{schema}].[{table}];")
        write_lines(clear_file, clear_lines, dry_run=args.dry_run)
        container_clear_file = f"/tmp/pre-import-clear-slot{args.slot}-{timestamp}.sql"
        print()
        print("Clearing migration-seeded rows before source data import")
        run(["docker", "cp", str(clear_file), f"{cfg.container_name}:{container_clear_file}"], dry_run=args.dry_run)
        run(
            [
                "docker",
                "exec",
                cfg.container_name,
                "/opt/mssql-tools18/bin/sqlcmd",
                "-S",
                "localhost",
                "-U",
                args.sql_user,
                "-P",
                args.sql_password,
                "-C",
                "-b",
                "-d",
                args.target_database,
                "-i",
                container_clear_file,
            ],
            dry_run=args.dry_run,
        )
        run(["docker", "exec", "-u", "0", cfg.container_name, "rm", "-f", container_clear_file], dry_run=args.dry_run, check=False)

    print()
    print("Restoring source data into target DB")
    with temp_env(
        {
            "DB_SERVER": "localhost",
            "DB_PORT": cfg.sql_port,
            "DB_NAME": args.target_database,
            "DB_USER": args.sql_user,
            "DB_PASSWORD": args.sql_password,
        }
    ):
        run([args.python, "Scripts/import_db_data.py", str(backup_file)], cwd=be_path, dry_run=args.dry_run)

    print()
    print("DB sync complete.")
    print(f"Target: localhost,{cfg.sql_port}/{args.target_database}")
    print(f"Backup kept at: {backup_file}")


def cleanup(args: argparse.Namespace) -> None:
    root = workspace_root()
    slug = safe_slug(args.slug)
    task_root = root / "worktrees" / slug
    fe_worktree = task_root / "fe"
    be_worktree = task_root / "be"
    fe_repo = root / "myhospital-fe"
    be_repo = root / "myhospital-be"
    require_command("git")

    if not task_root.exists():
        raise ToolError(f"Task worktree folder not found: {task_root}")

    dirty: list[str] = []
    for label, path in (("FE", fe_worktree), ("BE", be_worktree)):
        if not path.exists():
            continue
        proc = run(["git", "-C", str(path), "status", "--short"], capture=True)
        if proc.stdout.strip():
            dirty.append(f"{label} tracked/untracked changes:\n{proc.stdout.rstrip()}")
    if dirty:
        print("Refusing cleanup because worktree still has Git-visible changes.")
        print()
        print("\n\n".join(dirty))
        raise SystemExit(1)

    confirm_or_exit(
        (
            "This will remove worktree folders, including ignored local files "
            "such as .env, node_modules, bin, and obj.\n"
            f"Target: {task_root}"
        ),
        args.yes or args.dry_run,
    )

    # Record the branch each worktree is on BEFORE removing it. Removing a
    # worktree does not delete its branch, so without this the branch lingers and
    # re-creating the same slug later fails with "branch already exists".
    branches: list[tuple[str, Path, str]] = []
    for label, repo, path in (("FE", fe_repo, fe_worktree), ("BE", be_repo, be_worktree)):
        if path.exists():
            branch = output(["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"], check=False)
            if branch and branch != "HEAD":
                branches.append((label, repo, branch))

    if fe_worktree.exists():
        run(["git", "-C", str(fe_repo), "worktree", "remove", "--force", str(fe_worktree)], dry_run=args.dry_run)
    if be_worktree.exists():
        run(["git", "-C", str(be_repo), "worktree", "remove", "--force", str(be_worktree)], dry_run=args.dry_run)
    run(["git", "-C", str(fe_repo), "worktree", "prune"], dry_run=args.dry_run)
    run(["git", "-C", str(be_repo), "worktree", "prune"], dry_run=args.dry_run)

    if branches:
        if args.delete_branch:
            for label, repo, branch in branches:
                run(["git", "-C", str(repo), "branch", "-D", branch], dry_run=args.dry_run, check=False)
                print(f"  deleted {label} branch: {branch}")
        else:
            print()
            print("Task branches left in place. Re-using this slug needs them gone first.")
            print("Re-run with --delete-branch, or delete manually:")
            for label, repo, branch in branches:
                print(f"  git -C {repo} branch -D {branch}   # {label}")

    if task_root.exists() and not any(task_root.iterdir()):
        print(f"> remove empty {task_root}")
        if not args.dry_run:
            task_root.rmdir()
    elif task_root.exists():
        print(f"Warning: task root still contains non-worktree artifacts: {task_root}")
    print(f"Cleanup complete for {slug!r}.")


def list_worktrees(_args: argparse.Namespace) -> None:
    root = workspace_root()
    worktrees_root = root / "worktrees"
    if not worktrees_root.exists():
        print("No worktrees directory found.")
        return
    for child in sorted(worktrees_root.iterdir(), key=lambda p: p.name):
        if child.is_dir() and child.name != "_db-backups":
            print(child.name)


def sync_main(args: argparse.Namespace) -> None:
    root = workspace_root()
    repos = [
        ("FE", root / "myhospital-fe", "master"),
        ("BE", root / "myhospital-be", "main"),
    ]
    require_command("git")
    confirm_or_exit(
        (
            "This will pull latest from origin for BOTH main repos and re-apply the "
            "'pre-config-before-dev' stash. All un-stashed local tracked changes may be lost."
        ),
        args.yes or args.dry_run,
    )
    for label, repo, branch in repos:
        print()
        print("=" * 40)
        print(f"  {label} ({branch})")
        print("=" * 40)
        current = output(["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"], check=False)
        if current != branch:
            if not args.checkout:
                print(
                    f"SKIP {label}: current branch is {current!r}, not the sync target {branch!r}.\n"
                    f"  Refusing to 'restore .' + 'pull origin {branch}' onto the wrong branch "
                    f"(that would merge {branch} into {current} and discard its changes).\n"
                    f"  Switch first, then re-run — or pass --checkout to switch automatically:\n"
                    f"    git -C {repo} checkout {branch}"
                )
                continue
            print(f"{label}: on {current!r}, --checkout given — switching to {branch!r} first.")
            run(["git", "-C", str(repo), "checkout", branch], dry_run=args.dry_run)
        skip_files = git_skip_worktree_files(repo)
        if skip_files:
            print(f"Detected skip-worktree files: {', '.join(skip_files)}")
        else:
            print("No skip-worktree files detected.")
        for file in skip_files:
            run(["git", "-C", str(repo), "update-index", "--no-skip-worktree", file], dry_run=args.dry_run)
        run(["git", "-C", str(repo), "restore", "."], dry_run=args.dry_run)
        run(["git", "-C", str(repo), "pull", "origin", branch], dry_run=args.dry_run)
        if args.dry_run:
            print("> find/apply stash pre-config-before-dev")
            continue
        stash_list = output(["git", "-C", str(repo), "stash", "list"], check=False)
        stash_ref = None
        for line in stash_list.splitlines():
            if "pre-config-before-dev" in line:
                match = re.match(r"^(stash@\{\d+\})", line)
                if match:
                    stash_ref = match.group(1)
                break
        if not stash_ref:
            print(f"Warning: {label}: no stash named 'pre-config-before-dev' found.")
            continue
        stash_files = output(["git", "-C", str(repo), "stash", "show", stash_ref, "--name-only"], check=False).splitlines()
        run(["git", "-C", str(repo), "stash", "apply", stash_ref], check=False)
        for file in stash_files:
            if file.strip():
                run(["git", "-C", str(repo), "update-index", "--skip-worktree", file.strip()])
                print(f"  skip-worktree: {file.strip()}")
        print(f"{label} sync complete.")
    print()
    print("Done. Main repos are up to date with local config preserved.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MyHospital Linux worktree tooling.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="List active task worktrees.")
    p.set_defaults(func=list_worktrees)

    p = sub.add_parser("init-db-slots", help="Create/start SQL Server containers for worktree slots.")
    p.add_argument("--slots", type=int, nargs="+", default=[1, 2, 3], choices=[1, 2, 3, 4])
    p.add_argument("--image", default="mcr.microsoft.com/mssql/server:2022-latest")
    p.add_argument("--sa-password", default=DEFAULT_SQL_PASSWORD)
    p.add_argument("--pull", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=init_db_slots)

    p = sub.add_parser("create", help="Create FE/BE task worktrees and configure slot env files.")
    p.add_argument("--slug", required=True)
    p.add_argument("--slot", type=int, required=True, choices=[1, 2, 3, 4])
    p.add_argument("--fe-base", default="master")
    p.add_argument("--be-base", default="main")
    p.add_argument("--fe-branch")
    p.add_argument("--be-branch")
    p.add_argument("--migration-be-path")
    p.add_argument("--sql-password", default=DEFAULT_SQL_PASSWORD)
    p.add_argument("--image", default="mcr.microsoft.com/mssql/server:2022-latest")
    p.add_argument("--skip-db-sync", action="store_true", help="Skip copying main DB data; still ensures the slot SQL container exists.")
    p.add_argument("--skip-db-init", action="store_true", help="With --skip-db-sync, also skip Docker/SQL slot init (true light worktree, no DB infra touched).")
    p.add_argument("--skip-fe-install", action="store_true")
    p.add_argument("--allow-port-in-use", action="store_true")
    p.add_argument("--scan-worktrees", action="store_true", help="Allow scanning existing worktrees for migration sources.")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=create_worktree)

    p = sub.add_parser("sync-db", help="Reset a slot DB from the main DB data and BE migrations.")
    p.add_argument("--slot", type=int, required=True, choices=[1, 2, 3, 4])
    p.add_argument("--be-path", required=True)
    p.add_argument("--migration-be-path")
    p.add_argument("--source-server", default="localhost")
    p.add_argument("--source-port", type=int, default=1433)
    p.add_argument("--source-database", default="MyHospital")
    p.add_argument("--target-database", default="MyHospital")
    p.add_argument("--sql-user", default="sa")
    p.add_argument("--sql-password", default=DEFAULT_SQL_PASSWORD)
    p.add_argument("--python", default="python")
    p.add_argument("--backup-dir")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--scan-worktrees", action="store_true", help="Allow scanning existing worktrees for migration sources.")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=sync_db)

    p = sub.add_parser("cleanup", help="Remove a clean task worktree.")
    p.add_argument("--slug", required=True)
    p.add_argument("--delete-branch", action="store_true", help="Also delete the task branch(es) so the slug can be reused.")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cleanup)

    p = sub.add_parser("sync-main", help="Pull main FE/BE branches and re-apply pre-config stash.")
    p.add_argument("--checkout", action="store_true", help="Switch a repo to its target branch first if it is on another branch (otherwise that repo is skipped).")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=sync_main)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"Command failed with exit code {exc.returncode}: {redact_cmd(exc.cmd)}", file=sys.stderr)
        if exc.stdout:
            print(exc.stdout, file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        return exc.returncode or 1
    except ToolError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
