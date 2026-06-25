#!/usr/bin/env python3
"""Linux-friendly MyHospital workspace worktree tooling.

This CLI replaces the old PowerShell workspace scripts with a shell-agnostic
Python entrypoint. It intentionally keeps subprocess calls as argv lists and
avoids fish/bash-specific syntax.
"""

from __future__ import annotations

import argparse
import json
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
DEFAULT_INTERNAL_TOKEN_SECRET = os.environ.get(
    "MYHOSPITAL_INTERNAL_TOKEN_SECRET",
    "0a3ab85d1105f192703ca4fadf429817b3e2145f2a84eae27c00d0084ed60fcd",
)
DEFAULT_BFF_BRIDGE_URL = os.environ.get("MYHOSPITAL_BFF_BRIDGE_URL", "http://localhost:5000")
DEFAULT_BFF_BRIDGE_SECRET = os.environ.get("MYHOSPITAL_BFF_BRIDGE_SECRET", "dev-only-dummy")

# === Source DB (main server - private) ===
# Chỉ cái này mới cần export vì là server thật.
SOURCE_DB_SERVER = os.environ.get("MYHOSPITAL_SOURCE_DB_SERVER", os.environ.get("MYHOSPITAL_MAIN_DB_SERVER", "localhost"))
SOURCE_DB_PORT = int(os.environ.get("MYHOSPITAL_SOURCE_DB_PORT", os.environ.get("MYHOSPITAL_MAIN_DB_PORT", "1433")))
SOURCE_DB_NAME = os.environ.get("MYHOSPITAL_SOURCE_DB_NAME", os.environ.get("MYHOSPITAL_MAIN_DB_NAME", "MyHospital"))
SOURCE_DB_USER = os.environ.get("MYHOSPITAL_SOURCE_DB_USER", os.environ.get("MYHOSPITAL_MAIN_DB_USER", "sa"))
SOURCE_DB_PASSWORD = os.environ.get("MYHOSPITAL_SOURCE_DB_PASSWORD", os.environ.get("MYHOSPITAL_MAIN_DB_PASSWORD", DEFAULT_SQL_PASSWORD))

# === Target slot DB (local trong container) ===
# Local config giống nhau hết + không public network → để default trong code luôn.
# Chỉ set MYHOSPITAL_TARGET_DB_PASSWORD nếu bạn muốn override.
TARGET_DB_PASSWORD = os.environ.get("MYHOSPITAL_TARGET_DB_PASSWORD", DEFAULT_SQL_PASSWORD)
WORKTREE_META_FILE = ".myhospital-worktree.json"


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


def with_dotnet_tools_on_path(env: dict[str, str]) -> dict[str, str]:
    """Make dotnet global tools available to child processes.

    The workspace relies on tools such as `dotnet ef` and ServiceStack `x`.
    Dotnet installs them under ~/.dotnet/tools, but non-interactive agent
    sessions do not always include that directory in PATH.
    """
    tools_dir = Path.home() / ".dotnet" / "tools"
    if not tools_dir.exists():
        return env
    current_path = env.get("PATH", "")
    paths = current_path.split(os.pathsep) if current_path else []
    tools_path = str(tools_dir)
    if tools_path not in paths:
        env["PATH"] = os.pathsep.join([current_path, tools_path]) if current_path else tools_path
    return env


def ensure_dotnet_sdk_workaround(be_path: Path, *, dry_run: bool = False) -> None:
    """Keep older feature branches buildable with the installed .NET SDK.

    SDK 10.0.108 can fail net10.0 restores with NETSDK1226 unless this property
    is present. Main has it, but older feature worktrees may not.
    """
    props = be_path / "Directory.Build.props"
    if not props.exists():
        print(f"Warning: {props} not found; cannot apply SDK restore workaround.")
        return
    content = props.read_text(encoding="utf-8")
    if "AllowMissingPrunePackageData" in content:
        mark_skip_worktree_if_task(be_path, ("Directory.Build.props",), dry_run=dry_run)
        return
    marker = "<PropertyGroup>"
    insertion = (
        "    <!-- Work around SDK 10.0.108 missing prune-package metadata for net10.0 restore. -->\n"
        "    <AllowMissingPrunePackageData>true</AllowMissingPrunePackageData>\n"
    )
    if marker not in content:
        raise ToolError(f"Cannot apply SDK restore workaround; missing {marker} in {props}")
    updated = content.replace(marker, marker + "\n" + insertion, 1)
    print(f"> patch {props} (AllowMissingPrunePackageData)")
    if not dry_run:
        props.write_text(updated, encoding="utf-8")
    mark_skip_worktree_if_task(be_path, ("Directory.Build.props",), dry_run=dry_run)


def ensure_servicestack_license(be_path: Path, *, dry_run: bool = False) -> None:
    """Ensure local ServiceStack runtime patch exists in a BE worktree.

    Older harness versions inserted `ServiceStack.Licensing.RegisterLicense`
    into Program.cs. Current local-dev setup uses a patched ServiceStack.Text
    DLL copied by MyHospital.csproj after Build/Publish, so new worktrees must
    have both `patched/` files and the MSBuild target.
    """
    root = workspace_root()
    source_dir = root / "myhospital-be" / "patched"
    target_dir = be_path / "patched"
    required = ("ServiceStack.Text.dll", "ServiceStack.Text.xml")
    for name in required:
        src = source_dir / name
        dst = target_dir / name
        if not src.exists():
            raise ToolError(f"ServiceStack patched assembly source missing: {src}")
        if dst.exists():
            continue
        print(f"> copy {src} -> {dst}")
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    csproj = be_path / "MyHospital" / "MyHospital.csproj"
    if not csproj.exists():
        raise ToolError(f"MyHospital.csproj not found: {csproj}")
    content = csproj.read_text(encoding="utf-8")
    if "OverwritePatchedServiceStackText" not in content:
        source_csproj = root / "myhospital-be" / "MyHospital" / "MyHospital.csproj"
        source_content = source_csproj.read_text(encoding="utf-8") if source_csproj.exists() else ""
        marker = "<!--\n    Copy đè ServiceStack.Text.dll"
        if marker not in source_content:
            raise ToolError(f"Patched ServiceStack MSBuild target missing from {source_csproj}")
        target_block = source_content[source_content.index(marker): source_content.rindex("</Project>")].rstrip()
        updated = content.replace("</Project>", f"\n  {target_block}\n\n</Project>", 1)
        print(f"> patch {csproj} (ServiceStack.Text patched DLL target)")
        if not dry_run:
            csproj.write_text(updated, encoding="utf-8")


def python_has_module(python_exe: str, module_name: str) -> bool:
    proc = subprocess.run(
        [python_exe, "-c", f"import {module_name}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


def ensure_db_sync_python(python_exe: str, *, dry_run: bool = False) -> str:
    """Return a Python executable that can run DB export/import helpers."""
    if dry_run or python_has_module(python_exe, "pymssql"):
        return python_exe

    venv_dir = Path("/tmp") / f"myhospital-db-sync-py{sys.version_info.major}{sys.version_info.minor}"
    venv_python = venv_dir / "bin" / "python"
    if not venv_python.exists():
        print(f"> create Python venv for DB sync: {venv_dir}")
        run([sys.executable, "-m", "venv", str(venv_dir)])
    if not python_has_module(str(venv_python), "pymssql"):
        print("> install DB sync dependency: pymssql")
        run([str(venv_python), "-m", "pip", "install", "pymssql"])
    return str(venv_python)


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
    merged_env = with_dotnet_tools_on_path(os.environ.copy())
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


def parse_env_lines(lines: list[str], source: str) -> dict[str, str]:
    """Parse simple KEY=VALUE env lines without invoking a shell."""
    values: dict[str, str] = {}
    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            raise ToolError(f"Invalid .env line {source}:{line_no}: missing '='")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", key):
            raise ToolError(f"Invalid .env key {source}:{line_no}: {key!r}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file without invoking a shell."""
    if not path.exists():
        raise ToolError(f"Env file not found: {path}")
    return parse_env_lines(path.read_text(encoding="utf-8").splitlines(), str(path))


def int_or_none(value: object | None) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except ValueError:
        return None


def url_port(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r":(\d+)(?:[/;]|$)", value)
    return int(match.group(1)) if match else None


def sql_connection_port(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"\bServer\s*=\s*[^,;]+,\s*(\d+)", value, re.IGNORECASE)
    return int(match.group(1)) if match else None


def safe_parse_env(path: Path) -> tuple[dict[str, str], str | None]:
    if not path.exists():
        return {}, "missing"
    try:
        return parse_env_file(path), None
    except ToolError as exc:
        return {}, str(exc)


def relative_to_root(path: Path) -> str:
    root = workspace_root()
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path)


def is_git_worktree_dir(path: Path) -> bool:
    """Return true only for an actual Git worktree checkout at this path.

    `git -C path status` is not sufficient inside this workspace because a
    partial folder under `worktrees/` can be treated as part of the harness root
    Git repository. Real linked worktrees have a `.git` file or directory.
    """
    return (path / ".git").exists()


def is_harness_partial_task_root(task_root: Path) -> bool:
    """Detect a failed create attempt that left only harness-generated artifacts."""
    if not task_root.exists() or not task_root.is_dir():
        return False
    allowed_files = {
        WORKTREE_META_FILE,
        "be/patched/ServiceStack.Text.dll",
        "be/patched/ServiceStack.Text.xml",
    }
    for path in task_root.rglob("*"):
        if path.is_dir():
            continue
        try:
            rel = path.relative_to(task_root).as_posix()
        except ValueError:
            return False
        if rel not in allowed_files:
            return False
    return True


def remove_harness_partial_task_root(task_root: Path, *, dry_run: bool = False) -> None:
    print(f"> remove partial harness-created task folder {task_root}")
    if dry_run:
        return
    for path in sorted(task_root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_file() or path.is_symlink():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    task_root.rmdir()


def write_worktree_metadata(
    *,
    task_root: Path,
    slug: str,
    cfg: SlotConfig,
    fe_worktree: Path,
    be_worktree: Path,
    fe_branch: str,
    be_branch: str,
    dry_run: bool = False,
) -> None:
    metadata = {
        "schema": 1,
        "slug": slug,
        "slot": cfg.slot,
        "ports": {
            "fe": cfg.fe_port,
            "be": cfg.be_port,
            "sql": cfg.sql_port,
        },
        "urls": {
            "fe": f"http://localhost:{cfg.fe_port}",
            "be": f"http://localhost:{cfg.be_port}",
        },
        "db": {
            "server": "localhost",
            "port": cfg.sql_port,
            "database": cfg.database_name,
            "container": cfg.container_name,
            "volume": cfg.volume_name,
        },
        "paths": {
            "root": relative_to_root(task_root),
            "fe": relative_to_root(fe_worktree),
            "be": relative_to_root(be_worktree),
        },
        "branches": {
            "fe": fe_branch,
            "be": be_branch,
        },
    }
    path = task_root / WORKTREE_META_FILE
    print(f"> write {path}")
    if dry_run:
        return
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def collect_worktree_info(task_root: Path) -> dict[str, object]:
    meta_path = task_root / WORKTREE_META_FILE
    metadata: dict[str, object] = {}
    errors: list[str] = []
    if meta_path.exists():
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"bad-meta:{exc.lineno}")
    else:
        errors.append("no-meta")

    fe_env, fe_error = safe_parse_env(task_root / "fe" / ".env")
    be_env, be_error = safe_parse_env(task_root / "be" / ".env")
    if fe_error:
        errors.append(f"fe-env:{fe_error}")
    if be_error:
        errors.append(f"be-env:{be_error}")
    if not is_git_worktree_dir(task_root / "fe"):
        errors.append("fe-worktree:missing")
    if not is_git_worktree_dir(task_root / "be"):
        errors.append("be-worktree:missing")
    appsettings, appsettings_error = read_json_object(task_root / "be" / "MyHospital" / "appsettings.Development.json")
    if appsettings_error and appsettings_error != "missing":
        errors.append(f"appsettings:{appsettings_error}")
    launch_settings, launch_error = read_json_object(task_root / "be" / "MyHospital" / "Properties" / "launchSettings.json")
    if launch_error and launch_error != "missing":
        errors.append(f"launch:{launch_error}")

    meta_ports = metadata.get("ports") if isinstance(metadata.get("ports"), dict) else {}
    meta_urls = metadata.get("urls") if isinstance(metadata.get("urls"), dict) else {}
    meta_db = metadata.get("db") if isinstance(metadata.get("db"), dict) else {}

    fe_port = int_or_none(fe_env.get("VITE_DEV_PORT")) or url_port(str(meta_urls.get("fe", ""))) or int_or_none(meta_ports.get("fe"))
    be_port = (
        url_port(fe_env.get("VITE_BACKEND_URL"))
        or url_port(be_env.get("ASPNETCORE_URLS"))
        or url_port(str(meta_urls.get("be", "")))
        or int_or_none(meta_ports.get("be"))
    )
    sql_port = (
        sql_connection_port(be_env.get("ConnectionStrings__DefaultConnection"))
        or int_or_none(meta_db.get("port"))
        or int_or_none(meta_ports.get("sql"))
    )
    appsettings_sql_port = sql_connection_port(nested_str(appsettings, "ConnectionStrings", "DefaultConnection"))
    launch_be_port = url_port(first_launch_application_url(launch_settings))

    candidates: list[tuple[str, int]] = []
    if fe_port is not None and 3001 <= fe_port <= 3004:
        candidates.append(("fe", fe_port - 3000))
    if be_port is not None and 5001 <= be_port <= 5004:
        candidates.append(("be", be_port - 5000))
    if sql_port is not None and 1434 <= sql_port <= 1437:
        candidates.append(("sql", sql_port - 1433))
    meta_slot = int_or_none(metadata.get("slot"))
    if meta_slot is not None:
        candidates.append(("meta", meta_slot))

    unique_slots = sorted({slot for _label, slot in candidates})
    missing = []
    if fe_port is None:
        missing.append("fe")
    if be_port is None:
        missing.append("be")
    if sql_port is None:
        missing.append("sql")

    if len(unique_slots) == 1 and not missing:
        status = "OK"
        slot: int | None = unique_slots[0]
    elif len(unique_slots) > 1:
        status = "MISMATCH " + ",".join(f"{label}=slot{slot}" for label, slot in candidates)
        slot = None
    else:
        status = "MISSING " + ",".join(missing or ["slot"])
        slot = unique_slots[0] if unique_slots else None

    config_mismatches: list[str] = []
    if sql_port is not None and appsettings_sql_port is not None and appsettings_sql_port != sql_port:
        config_mismatches.append(f"appsettings-sql={appsettings_sql_port}")
    if be_port is not None and launch_be_port is not None and launch_be_port != be_port:
        config_mismatches.append(f"launch-be={launch_be_port}")
    if config_mismatches:
        status = "MISMATCH " + ",".join(config_mismatches)
        slot = None

    if errors and status == "OK":
        status = "OK " + ",".join(errors)
    elif errors:
        status = status + " " + ",".join(errors)

    return {
        "slug": task_root.name,
        "slot": slot,
        "fe_port": fe_port,
        "be_port": be_port,
        "sql_port": sql_port,
        "status": status,
    }


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


def read_json_object(path: Path) -> tuple[dict[str, object] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"bad-json:{exc.lineno}"
    if not isinstance(data, dict):
        return None, "not-object"
    return data, None


def write_json_object(path: Path, data: dict[str, object], *, dry_run: bool = False) -> None:
    print(f"> write {path}")
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def nested_dict(parent: dict[str, object], key: str) -> dict[str, object]:
    current = parent.get(key)
    if isinstance(current, dict):
        return current
    created: dict[str, object] = {}
    parent[key] = created
    return created


def nested_str(data: dict[str, object] | None, *keys: str) -> str | None:
    current: object = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current if isinstance(current, str) else None


def first_launch_application_url(data: dict[str, object] | None) -> str | None:
    profiles = data.get("profiles") if isinstance(data, dict) else None
    if not isinstance(profiles, dict):
        return None
    for profile in profiles.values():
        if isinstance(profile, dict) and profile.get("commandName") == "Project":
            value = profile.get("applicationUrl")
            return value if isinstance(value, str) else None
    return None


def mark_skip_worktree(repo: Path, rel_paths: Iterable[str], *, dry_run: bool = False) -> None:
    for rel in rel_paths:
        path = repo / rel
        if not path.exists():
            continue
        proc = run(["git", "-C", str(repo), "ls-files", "--error-unmatch", rel], capture=True, check=False)
        if proc.returncode == 0:
            run(["git", "-C", str(repo), "update-index", "--skip-worktree", rel], dry_run=dry_run)


def mark_skip_worktree_if_task(repo: Path, rel_paths: Iterable[str], *, dry_run: bool = False) -> None:
    try:
        repo.resolve().relative_to(workspace_root() / "worktrees")
    except ValueError:
        return
    mark_skip_worktree(repo, rel_paths, dry_run=dry_run)


def configure_be_local_runtime(
    be_path: Path,
    *,
    cfg: SlotConfig,
    connection_string: str,
    env_values: dict[str, str] | None = None,
    dry_run: bool = False,
) -> None:
    """Patch local-only BE runtime config so direct dotnet run uses the slot.

    Worktree .env is not enough: `dotnet run` uses Development launch settings
    and appsettings even when the user does not go through `worktree.py run-be`.
    """
    appsettings = be_path / "MyHospital" / "appsettings.Development.json"
    data, error = read_json_object(appsettings)
    if error and error != "missing":
        raise ToolError(f"Cannot patch {appsettings}: {error}")
    if data is not None:
        conn = nested_dict(data, "ConnectionStrings")
        conn["DefaultConnection"] = connection_string
        conn["ReadOnlyConnection"] = connection_string
        if env_values and "ConnectionStrings__RedisConnection" in env_values:
            conn["RedisConnection"] = env_values["ConnectionStrings__RedisConnection"]
        typescript = nested_dict(data, "TypeScript")
        typescript["ServerUrl"] = f"http://localhost:{cfg.be_port}"
        write_json_object(appsettings, data, dry_run=dry_run)

    launch = be_path / "MyHospital" / "Properties" / "launchSettings.json"
    data, error = read_json_object(launch)
    if error and error != "missing":
        raise ToolError(f"Cannot patch {launch}: {error}")
    if data is not None:
        iis_settings = nested_dict(data, "iisSettings")
        iis_express = nested_dict(iis_settings, "iisExpress")
        iis_express["applicationUrl"] = f"http://localhost:{cfg.be_port}/"
        profiles = nested_dict(data, "profiles")
        for profile in profiles.values():
            if not isinstance(profile, dict):
                continue
            env = nested_dict(profile, "environmentVariables")
            if env_values:
                env.update(env_values)
            env["ASPNETCORE_ENVIRONMENT"] = "Development"
            env["ASPNETCORE_URLS"] = f"http://localhost:{cfg.be_port}"
            env["MyHospital__LoginUrl"] = f"http://localhost:{cfg.fe_port}/login"
            env["ConnectionStrings__DefaultConnection"] = connection_string
            env["ConnectionStrings__ReadOnlyConnection"] = connection_string
            if profile.get("commandName") == "Project":
                profile["applicationUrl"] = f"http://localhost:{cfg.be_port}"
        write_json_object(launch, data, dry_run=dry_run)

    reporting = be_path / "MyHospital.Reporting" / "appsettings.json"
    if reporting.exists():
        content = reporting.read_text(encoding="utf-8")
        updated, count = re.subn(
            r'("POSEntities"\s*:\s*")[^"]*(")',
            lambda match: f"{match.group(1)}{connection_string}{match.group(2)}",
            content,
            count=1,
        )
        if count:
            print(f"> write {reporting}")
            if not dry_run:
                reporting.write_text(updated, encoding="utf-8")

    mark_skip_worktree(
        be_path,
        (
            "MyHospital/appsettings.Development.json",
            "MyHospital/Properties/launchSettings.json",
            "MyHospital.Reporting/appsettings.json",
        ),
        dry_run=dry_run,
    )


def local_cors_origins() -> str:
    return ",".join(
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


def configure_fe_env(fe_worktree: Path, cfg: SlotConfig, template_path: Path, *, dry_run: bool = False) -> None:
    fe_lines = read_env_lines(template_path)
    fe_lines = set_env_line(fe_lines, "VITE_DEV_PORT", cfg.fe_port)
    fe_lines = set_env_line(fe_lines, "VITE_BACKEND_URL", f"http://localhost:{cfg.be_port}")
    fe_lines = set_env_line(fe_lines, "VITE_CDN_URL", f"http://localhost:{cfg.be_port}")
    fe_lines = set_env_line(fe_lines, "VITE_INDEXEDDB_VERSION", 100 + cfg.slot)
    fe_lines = set_env_line(fe_lines, "VITE_DEV_PERSIST_ALL", "true")
    fe_lines = set_env_line(fe_lines, "VITE_HOSPITAL_TEMPLATE_URL", f"http://localhost:{cfg.fe_port}/import-templates/")
    write_lines(fe_worktree / ".env", fe_lines, dry_run=dry_run)


def configure_be_env(
    be_worktree: Path,
    cfg: SlotConfig,
    template_path: Path,
    *,
    sql_password: str,
    dry_run: bool = False,
) -> str:
    target_connection = sql_connection_string(cfg.sql_port, database=cfg.database_name, password=sql_password)
    be_lines = read_env_lines(template_path)
    be_lines = set_env_line(be_lines, "ASPNETCORE_ENVIRONMENT", "Development")
    be_lines = set_env_line(be_lines, "ASPNETCORE_URLS", f"http://localhost:{cfg.be_port}")
    be_lines = set_env_line(be_lines, "MyHospital__LoginUrl", f"http://localhost:{cfg.fe_port}/login")
    be_lines = set_env_line(be_lines, "ConnectionStrings__DefaultConnection", target_connection)
    be_lines = set_env_line(be_lines, "ConnectionStrings__ReadOnlyConnection", target_connection)
    be_lines = set_env_line(be_lines, "CORS_ORIGINS", local_cors_origins())
    be_lines = set_env_line(be_lines, "InternalTokenSecret", DEFAULT_INTERNAL_TOKEN_SECRET)
    be_lines = set_env_line(be_lines, "Bff__BridgeUrl", DEFAULT_BFF_BRIDGE_URL)
    be_lines = set_env_line(be_lines, "Bff__BridgeSecret", DEFAULT_BFF_BRIDGE_SECRET)
    be_env = parse_env_lines(be_lines, str(be_worktree / ".env"))
    write_lines(be_worktree / ".env", be_lines, dry_run=dry_run)
    configure_be_local_runtime(
        be_worktree,
        cfg=cfg,
        connection_string=target_connection,
        env_values=be_env,
        dry_run=dry_run,
    )
    return target_connection


def current_git_branch(path: Path) -> str:
    branch = output(["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"], check=False)
    return branch or "HEAD"


def infer_slot_config(task_root: Path) -> SlotConfig:
    metadata: dict[str, object] = {}
    meta_path = task_root / WORKTREE_META_FILE
    if meta_path.exists():
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            metadata = {}

    fe_env, _ = safe_parse_env(task_root / "fe" / ".env")
    be_env, _ = safe_parse_env(task_root / "be" / ".env")
    candidates: list[int] = []

    meta_slot = int_or_none(metadata.get("slot"))
    if meta_slot is not None and 1 <= meta_slot <= 4:
        candidates.append(meta_slot)
    fe_port = int_or_none(fe_env.get("VITE_DEV_PORT"))
    if fe_port is not None and 3001 <= fe_port <= 3004:
        candidates.append(fe_port - 3000)
    be_port = url_port(be_env.get("ASPNETCORE_URLS"))
    if be_port is not None and 5001 <= be_port <= 5004:
        candidates.append(be_port - 5000)
    sql_port = sql_connection_port(be_env.get("ConnectionStrings__DefaultConnection"))
    if sql_port is not None and 1434 <= sql_port <= 1437:
        candidates.append(sql_port - 1433)

    unique = sorted(set(candidates))
    if len(unique) != 1:
        raise ToolError(f"Cannot infer a single slot for {task_root}; candidates={candidates or 'none'}")
    return slot_config(unique[0])


def repair_worktree_config(args: argparse.Namespace) -> None:
    root = workspace_root()
    if args.all == bool(args.slug):
        raise ToolError("Pass exactly one of --slug or --all.")
    worktrees_root = root / "worktrees"
    task_roots = [worktrees_root / safe_slug(args.slug)] if args.slug else [
        child for child in sorted(worktrees_root.iterdir(), key=lambda p: p.name)
        if child.is_dir() and child.name != "_db-backups"
    ]

    for task_root in task_roots:
        if not task_root.exists():
            raise ToolError(f"Task worktree folder not found: {task_root}")
        cfg = infer_slot_config(task_root)
        fe_worktree = task_root / "fe"
        be_worktree = task_root / "be"
        if not is_git_worktree_dir(fe_worktree):
            raise ToolError(f"FE git worktree not found: {fe_worktree}")
        if not is_git_worktree_dir(be_worktree):
            raise ToolError(f"BE git worktree not found: {be_worktree}")
        ensure_dotnet_sdk_workaround(be_worktree, dry_run=args.dry_run)
        ensure_servicestack_license(be_worktree, dry_run=args.dry_run)
        fe_template = fe_worktree / ".env" if (fe_worktree / ".env").exists() else root / "myhospital-fe" / ".env"
        if not fe_template.exists():
            alt = root / "myhospital-fe" / "env"
            fe_template = alt if alt.exists() else fe_template
        be_template = be_worktree / ".env" if (be_worktree / ".env").exists() else root / "myhospital-be" / ".env"
        print()
        print(f"Repairing {task_root.name}: slot {cfg.slot}")
        configure_fe_env(fe_worktree, cfg, fe_template, dry_run=args.dry_run)
        configure_be_env(
            be_worktree,
            cfg,
            be_template,
            sql_password=TARGET_DB_PASSWORD,
            dry_run=args.dry_run,
        )
        write_worktree_metadata(
            task_root=task_root,
            slug=task_root.name,
            cfg=cfg,
            fe_worktree=fe_worktree,
            be_worktree=be_worktree,
            fe_branch=current_git_branch(fe_worktree),
            be_branch=current_git_branch(be_worktree),
            dry_run=args.dry_run,
        )

        # Backfill common local excludes on repair so old worktrees also benefit.
        ensure_common_local_excludes(fe_worktree, be_worktree, dry_run=args.dry_run)


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
    if args.dry_run:
        print("DB slot dry-run complete. No containers were created or started.")
    else:
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


def ensure_local_git_exclude(repo: Path, pattern: str, *, dry_run: bool = False) -> None:
    """Add a worktree-local ignore pattern without changing tracked .gitignore."""
    proc = run(["git", "-C", str(repo), "rev-parse", "--git-path", "info/exclude"], capture=True, check=False)
    if proc.returncode != 0:
        print(f"Warning: cannot resolve git exclude path for {repo}; skipping {pattern!r}.")
        return
    exclude_path = Path(proc.stdout.strip())
    if not exclude_path.is_absolute():
        exclude_path = repo / exclude_path
    existing = exclude_path.read_text(encoding="utf-8").splitlines() if exclude_path.exists() else []
    if pattern in existing:
        return
    print(f"> add {pattern} to {exclude_path}")
    if dry_run:
        return
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    with exclude_path.open("a", encoding="utf-8") as handle:
        if existing and existing[-1] != "":
            handle.write("\n")
        handle.write(f"{pattern}\n")


def ensure_common_local_excludes(
    fe_worktree: Path, be_worktree: Path, *, dry_run: bool = False
) -> None:
    """Ensure common local-only noise folders are added to .git/info/exclude.

    These folders (generated by tools like codegraph, graphify, playwright)
    frequently pollute `git status` inside worktrees and block `cleanup`.
    We use per-worktree exclude (not .gitignore) so they never need to be committed.

    Covers:
      - .codegraph/          (CodeGraph local index)
      - graphify-out/        (graphify skill output, often created inside worktrees)
      - e2e test artifacts   (reports, local round specs, etc.)
    """
    common_patterns = [
        ".codegraph/",
        "graphify-out/",
    ]

    # FE-specific noise (e2e artifacts often appear with suffixes or inside e2e/)
    fe_patterns = [
        "test-results/",
        "playwright-report/",
        "playwright-report*/",
        "blob-report/",
        "e2e/test-results/",
        "e2e/playwright-report/",
        "e2e/playwright-report*/",
        "e2e/",  # local e2e experiments / generated outputs (tracked e2e source changes still visible)
    ]

    for wt in (fe_worktree, be_worktree):
        if not wt.exists():
            continue
        for pat in common_patterns:
            ensure_local_git_exclude(wt, pat, dry_run=dry_run)

    if fe_worktree.exists():
        for pat in fe_patterns:
            ensure_local_git_exclude(fe_worktree, pat, dry_run=dry_run)


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


def init_codegraph(fe_worktree: Path, be_worktree: Path, *, dry_run: bool = False) -> None:
    """Build the CodeGraph index for a freshly-created worktree (be + fe).

    Best-effort: CodeGraph is an optional local aid. If the binary is missing or a
    build fails, warn and continue — a worktree without an index still works (callers
    fall back to bounded `rg`). Never let this roll back an otherwise-good worktree.
    """
    if shutil.which("codegraph") is None:
        print("Skipping CodeGraph index: 'codegraph' not found on PATH.")
        return
    # Also ensure common excludes (in case this is run on an older worktree
    # that was created before the auto-exclude logic).
    ensure_common_local_excludes(fe_worktree, be_worktree, dry_run=dry_run)
    for label, wt in (("BE", be_worktree), ("FE", fe_worktree)):
        if not wt.exists():
            continue
        print(f"Building CodeGraph index ({label}: {wt}) ...")
        if dry_run:
            print(f"> codegraph init  (cwd={wt})")
            continue
        proc = subprocess.run(["codegraph", "init"], cwd=str(wt))
        if proc.returncode != 0:
            print(f"Warning: CodeGraph index for {label} failed (exit {proc.returncode}); "
                  f"run `cd {wt} && codegraph init` manually later.", file=sys.stderr)


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
    if not args.skip_db_sync and args.db_setup == "migrate-data":
        require_command("make")
    if not fe_repo.exists():
        raise ToolError(f"FE repo not found: {fe_repo}")
    if not be_repo.exists():
        raise ToolError(f"BE repo not found: {be_repo}")
    if task_root.exists():
        if is_harness_partial_task_root(task_root):
            remove_harness_partial_task_root(task_root, dry_run=args.dry_run)
        else:
            raise ToolError(f"Task worktree folder already exists: {task_root}")

    fe_source_ref = f"refs/remotes/origin/{args.fe_base}"
    be_source_ref = f"refs/remotes/origin/{args.be_base}"
    run(["git", "-C", str(fe_repo), "fetch", "origin", f"+refs/heads/{args.fe_base}:{fe_source_ref}"], dry_run=args.dry_run)
    run(["git", "-C", str(be_repo), "fetch", "origin", f"+refs/heads/{args.be_base}:{be_source_ref}"], dry_run=args.dry_run)

    for repo, ref, label in ((fe_repo, args.fe_base, "FE base"), (be_repo, args.be_base, "BE base")):
        proc = run(
            ["git", "-C", str(repo), "rev-parse", "--verify", f"{ref}^{{commit}}"],
            capture=True,
            check=False,
        )
        if proc.returncode != 0:
            run(
                ["git", "-C", str(repo), "rev-parse", "--verify", f"refs/remotes/origin/{ref}^{{commit}}"],
                capture=True,
            )
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

        # Always set up local excludes early so generated noise never blocks cleanup.
        ensure_common_local_excludes(fe_worktree, be_worktree, dry_run=args.dry_run)

        ensure_dotnet_sdk_workaround(be_worktree, dry_run=args.dry_run)
        ensure_servicestack_license(be_worktree, dry_run=args.dry_run)

        remove_telerik_from_solution(be_worktree, dry_run=args.dry_run)

        fe_template = fe_repo / ".env"
        if not fe_template.exists():
            fe_template = fe_repo / "env"
        configure_fe_env(fe_worktree, cfg, fe_template, dry_run=args.dry_run)
        configure_be_env(
            be_worktree,
            cfg,
            be_repo / ".env",
            sql_password=TARGET_DB_PASSWORD,
            dry_run=args.dry_run,
        )
        write_worktree_metadata(
            task_root=task_root,
            slug=slug,
            cfg=cfg,
            fe_worktree=fe_worktree,
            be_worktree=be_worktree,
            fe_branch=fe_branch,
            be_branch=be_branch,
            dry_run=args.dry_run,
        )

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

        if not args.skip_db_sync and args.db_setup == "migrate-data":
            print()
            print("Running BE migrate-data for the slot DB (recreate schema)...")
            init_db_slots(
                argparse.Namespace(
                    slots=[args.slot],
                    image=args.image,
                    sa_password=TARGET_DB_PASSWORD,
                    pull=False,
                    dry_run=args.dry_run,
                )
            )
            run(["make", "migrate-data", "CONFIRM=yes"], cwd=be_worktree, dry_run=args.dry_run)

            # Sau make migrate-data (recreate schema), tự sync data từ source (main server)
            # dùng SOURCE_* env. Target thì để default local.
            print()
            print("Auto-syncing data from main DB server (SOURCE_* env)...")
            migration_be_path = str(Path(args.migration_be_path).resolve()) if args.migration_be_path else str(be_worktree)
            sync_args = argparse.Namespace(
                slot=args.slot,
                be_path=str(be_worktree),
                migration_be_path=migration_be_path,
                source_server=SOURCE_DB_SERVER,
                source_port=SOURCE_DB_PORT,
                source_database=SOURCE_DB_NAME,
                target_database="MyHospital",
                sql_user=SOURCE_DB_USER,
                sql_password=SOURCE_DB_PASSWORD or TARGET_DB_PASSWORD,
                python="python",
                backup_dir=None,
                yes=True,
                dry_run=args.dry_run,
                scan_worktrees=args.scan_worktrees,
            )
            sync_db(sync_args)

        elif not args.skip_db_sync and args.db_setup == "sync-db":
            migration_be_path = str(Path(args.migration_be_path).resolve()) if args.migration_be_path else str(be_worktree)
            sync_args = argparse.Namespace(
                slot=args.slot,
                be_path=str(be_worktree),
                migration_be_path=migration_be_path,
                source_server=SOURCE_DB_SERVER,
                source_port=SOURCE_DB_PORT,
                source_database=SOURCE_DB_NAME,
                target_database="MyHospital",
                sql_user=SOURCE_DB_USER,
                sql_password=SOURCE_DB_PASSWORD or TARGET_DB_PASSWORD,
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
                    sa_password=TARGET_DB_PASSWORD,
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

    if not getattr(args, "skip_codegraph", False):
        print()
        print("Building CodeGraph index for the new worktree...")
        init_codegraph(fe_worktree, be_worktree, dry_run=args.dry_run)
    else:
        print()
        print("Skipping CodeGraph index because --skip-codegraph was passed.")

    print()
    print(f"Worktree ready: {task_root}")
    print(f"FE: {fe_worktree}")
    print(f"BE: {be_worktree}")
    print()
    print("Run BE:")
    print(f"  cd {root}")
    print(f"  python scripts/worktree.py run-be --be-path {be_worktree}")
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
    db_python = ensure_db_sync_python(args.python, dry_run=args.dry_run)
    ensure_dotnet_sdk_workaround(be_path, dry_run=args.dry_run)
    run(["dotnet", "ef", "--version"], dry_run=args.dry_run, capture=True)

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
        run([db_python, "Scripts/export_db_data.py"], cwd=be_path, dry_run=args.dry_run)

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
        run([db_python, "Scripts/drop_db_objects.py"], cwd=be_path, dry_run=args.dry_run)

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
        run([db_python, "Scripts/import_db_data.py", str(backup_file)], cwd=be_path, dry_run=args.dry_run)

    print()
    if args.dry_run:
        print("DB sync dry-run complete. No backup, schema reset, migration, or import was executed.")
        print(f"Target preview: localhost,{cfg.sql_port}/{args.target_database}")
        print(f"Backup preview path: {backup_file}")
    else:
        print("DB sync complete.")
        print(f"Target: localhost,{cfg.sql_port}/{args.target_database}")
        print(f"Backup kept at: {backup_file}")


def run_be(args: argparse.Namespace) -> None:
    if bool(args.slug) == bool(args.be_path):
        raise ToolError("Pass exactly one of --slug or --be-path.")
    be_path = (workspace_root() / "worktrees" / safe_slug(args.slug) / "be").resolve() if args.slug else Path(args.be_path).resolve()
    env_file = Path(args.env_file).resolve() if args.env_file else be_path / ".env"
    if not be_path.exists():
        raise ToolError(f"BE path not found: {be_path}")
    require_command("dotnet")
    ensure_dotnet_sdk_workaround(be_path)
    ensure_servicestack_license(be_path)
    env_values = parse_env_file(env_file)
    sql_port = sql_connection_port(env_values.get("ConnectionStrings__DefaultConnection"))
    be_port = url_port(env_values.get("ASPNETCORE_URLS"))
    if sql_port is not None and be_port is not None and 1434 <= sql_port <= 1437 and 5001 <= be_port <= 5004:
        slot = sql_port - 1433
        if slot == be_port - 5000:
            configure_be_local_runtime(
                be_path,
                cfg=slot_config(slot),
                connection_string=env_values["ConnectionStrings__DefaultConnection"],
                env_values=env_values,
            )
    project = args.project or "MyHospital/MyHospital.csproj"
    cmd = ["dotnet", "run", "--project", project, "--no-launch-profile"]
    if args.no_build:
        cmd.append("--no-build")
    run(cmd, cwd=be_path, env=env_values)


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

    metadata_file = task_root / WORKTREE_META_FILE
    if metadata_file.exists():
        print(f"> remove managed metadata {metadata_file}")
        if not args.dry_run:
            metadata_file.unlink()

    if task_root.exists() and not any(task_root.iterdir()):
        print(f"> remove empty {task_root}")
        if not args.dry_run:
            task_root.rmdir()
    elif task_root.exists():
        print(f"Warning: task root still contains non-worktree artifacts: {task_root}")
    print(f"Cleanup complete for {slug!r}.")


def list_worktrees(args: argparse.Namespace) -> None:
    root = workspace_root()
    worktrees_root = root / "worktrees"
    if not worktrees_root.exists():
        print("No worktrees directory found.")
        return
    children = [child for child in sorted(worktrees_root.iterdir(), key=lambda p: p.name) if child.is_dir() and child.name != "_db-backups"]
    if not children:
        print("No active worktrees.")
        return
    if args.plain:
        for child in children:
            print(child.name)
        return
    rows = [collect_worktree_info(child) for child in children]
    print(f"{'slug':<22} {'slot':<4} {'FE':<22} {'BE':<22} {'SQL':<24} status")
    for row in rows:
        slot = row["slot"] if row["slot"] is not None else "?"
        fe = f"http://localhost:{row['fe_port']}" if row["fe_port"] else "?"
        be = f"http://localhost:{row['be_port']}" if row["be_port"] else "?"
        sql = f"localhost,{row['sql_port']}/MyHospital" if row["sql_port"] else "?"
        print(f"{row['slug']:<22} {slot!s:<4} {fe:<22} {be:<22} {sql:<24} {row['status']}")


def info_worktree(args: argparse.Namespace) -> None:
    root = workspace_root()
    slug = safe_slug(args.slug)
    task_root = root / "worktrees" / slug
    if not task_root.exists():
        raise ToolError(f"Task worktree folder not found: {task_root}")
    row = collect_worktree_info(task_root)
    print(f"slug={row['slug']}")
    print(f"slot={row['slot'] if row['slot'] is not None else '?'}")
    print(f"fe_url={'http://localhost:' + str(row['fe_port']) if row['fe_port'] else '?'}")
    print(f"be_url={'http://localhost:' + str(row['be_port']) if row['be_port'] else '?'}")
    print(f"sql={'localhost,' + str(row['sql_port']) + '/MyHospital' if row['sql_port'] else '?'}")
    print(f"fe_path={relative_to_root(task_root / 'fe')}")
    print(f"be_path={relative_to_root(task_root / 'be')}")
    print(f"status={row['status']}")


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
    p.add_argument("--plain", action="store_true", help="Print only slugs for scripts that need legacy output.")
    p.set_defaults(func=list_worktrees)

    p = sub.add_parser("info", help="Print slot, ports, URLs, and paths for one worktree slug.")
    p.add_argument("--slug", required=True)
    p.set_defaults(func=info_worktree)

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
    p.add_argument("--sql-password", default=DEFAULT_SQL_PASSWORD,
                   help="Override target slot password (local). Thường thì để default trong code vì local config giống nhau.")
    p.add_argument("--image", default="mcr.microsoft.com/mssql/server:2022-latest")
    p.add_argument(
        "--db-setup",
        choices=["migrate-data", "sync-db"],
        default="migrate-data",
        help=(
            "Default 'migrate-data': chạy make migrate-data (recreate schema) "
            "rồi tự sync data từ SOURCE_* (main server) vào slot. "
            "Chỉ cần export MYHOSPITAL_SOURCE_* cho main DB. "
            "Local slot target để default trong code."
        ),
    )
    p.add_argument("--skip-db-sync", action="store_true", help="Skip DB data/migration setup; still ensures the slot SQL container exists.")
    p.add_argument("--skip-db-init", action="store_true", help="With --skip-db-sync, also skip Docker/SQL slot init (true light worktree, no DB infra touched).")
    p.add_argument("--skip-fe-install", action="store_true")
    p.add_argument("--skip-codegraph", action="store_true", help="Skip building the CodeGraph index for the new worktree (be+fe).")
    p.add_argument("--allow-port-in-use", action="store_true")
    p.add_argument("--scan-worktrees", action="store_true", help="Allow scanning existing worktrees for migration sources.")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=create_worktree)

    p = sub.add_parser("repair-config", help="Rewrite existing worktree FE/BE local runtime config from its slot.")
    p.add_argument("--slug", help="Task worktree slug to repair.")
    p.add_argument("--all", action="store_true", help="Repair every active worktree under worktrees/.")
    p.add_argument("--sql-password", default=DEFAULT_SQL_PASSWORD)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=repair_worktree_config)

    p = sub.add_parser("sync-db", help="Reset a slot DB from the main DB data and BE migrations.")
    p.add_argument("--slot", type=int, required=True, choices=[1, 2, 3, 4])
    p.add_argument("--be-path", required=True)
    p.add_argument("--migration-be-path")
    p.add_argument("--source-server", default=SOURCE_DB_SERVER)
    p.add_argument("--source-port", type=int, default=SOURCE_DB_PORT)
    p.add_argument("--source-database", default=SOURCE_DB_NAME)
    p.add_argument("--target-database", default="MyHospital")
    p.add_argument("--sql-user", default=SOURCE_DB_USER)
    p.add_argument("--sql-password", default=SOURCE_DB_PASSWORD or TARGET_DB_PASSWORD)
    p.add_argument("--python", default="python")
    p.add_argument("--backup-dir")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--scan-worktrees", action="store_true", help="Allow scanning existing worktrees for migration sources.")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=sync_db)

    p = sub.add_parser("run-be", help="Run a BE checkout with environment loaded from its .env file.")
    p.add_argument("--slug", help="Task worktree slug; resolves to worktrees/<slug>/be.")
    p.add_argument("--be-path")
    p.add_argument("--env-file")
    p.add_argument("--project", default="MyHospital/MyHospital.csproj")
    p.add_argument("--no-build", action="store_true")
    p.set_defaults(func=run_be)

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
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
