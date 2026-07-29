"""
odoo-bootstrap CLI — Main entry point.
All commands are registered here via Typer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from odoo_bootstrap import __version__
from odoo_bootstrap.core.config_manager import ConfigManager
from odoo_bootstrap.core.constants import SUPPORTED_VERSIONS, WORKSPACE_ROOT
from odoo_bootstrap.core.logger import setup_logging

app = typer.Typer(
    name="odoo-bootstrap",
    help="Professional CLI toolkit for Odoo Partner development teams.",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()

# Shared state
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def version_callback(value: bool) -> None:
    if value:
        console.print(f"odoo-bootstrap [cyan]{__version__}[/cyan]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose logging."),
    log_file: bool = typer.Option(True, "--log-file/--no-log-file", help="Write logs to file."),
) -> None:
    """
    [bold cyan]odoo-bootstrap[/bold cyan] — Odoo Partner development toolkit.

    Manages workspaces, projects, Docker images, backups and more.
    """
    level = "DEBUG" if verbose else "INFO"
    setup_logging(level=level, log_to_file=log_file)


# ── init ─────────────────────────────────────────────────────────────────────

@app.command("init")
def cmd_init(
    workspace: Path = typer.Option(WORKSPACE_ROOT, help="Workspace root directory."),
    versions: str = typer.Option(
        ",".join(str(v) for v in SUPPORTED_VERSIONS),
        help="Comma-separated Odoo versions to initialize (e.g. 17,18,19).",
    ),
    skip_git: bool = typer.Option(False, help="Skip git clone/pull of Odoo source."),
    skip_docker: bool = typer.Option(False, help="Skip Docker image build."),
    skip_shared: bool = typer.Option(False, help="Skip shared services setup."),
) -> None:
    """
    Initialize the Odoo development workspace.

    Creates workspace directories, clones Odoo source, builds Docker images,
    and generates all configuration files.
    """
    from odoo_bootstrap.commands.cmd_init import run_init

    parsed_versions = [int(v.strip()) for v in versions.split(",") if v.strip().isdigit()]
    run_init(
        workspace=workspace,
        versions=parsed_versions,
        skip_git=skip_git,
        skip_docker_build=skip_docker,
        skip_shared=skip_shared,
    )


# ── doctor ───────────────────────────────────────────────────────────────────

@app.command("doctor")
def cmd_doctor() -> None:
    """
    Check system health: Docker, Git, Python, disk, RAM, ports, projects.
    """
    from odoo_bootstrap.commands.cmd_doctor import run_doctor, print_doctor_report

    report = run_doctor(get_config_manager())
    print_doctor_report(report)
    if report.has_errors:
        raise typer.Exit(code=1)


# ── status ───────────────────────────────────────────────────────────────────

@app.command("status")
def cmd_status() -> None:
    """Show running containers, projects, ports, and system resources."""
    from odoo_bootstrap.commands.cmd_status import run_status

    run_status(get_config_manager())


# ── create-project ────────────────────────────────────────────────────────────

@app.command("create-project")
def cmd_create_project(
    name: str = typer.Argument(..., help="Tên project (chữ, số, gạch dưới, gạch ngang)."),
    version: int = typer.Option(..., "--version", "-v", help="Phiên bản Odoo (17, 18, 19)."),
    edition: str = typer.Option("auto", "--edition", "-e", help="enterprise | community | auto"),
    port: int = typer.Option(0, "--port", help="Port tùy chỉnh (mặc định: tự động)."),
    db_name: str = typer.Option("", help="Tên database (mặc định: odoo_<name>_<version>)."),
    db_user: str = typer.Option("odoo", help="PostgreSQL user."),
    db_password: str = typer.Option("odoo", help="PostgreSQL password."),
) -> None:
    """
    Tạo project Odoo mới với đầy đủ cấu hình.

    Ví dụ:
      odoo-bootstrap create-project kh_a --version 19 --edition enterprise
      odoo-bootstrap create-project kh_b --version 19 --edition community
      odoo-bootstrap create-project kh_c --version 19 --edition enterprise --port 8071
    """
    from odoo_bootstrap.commands.cmd_project import run_create_project

    run_create_project(
        name=name,
        version=version,
        config_manager=get_config_manager(),
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
        port=port,
        edition=edition,
    )


# ── remove-project ────────────────────────────────────────────────────────────

@app.command("remove-project")
def cmd_remove_project(
    name: str = typer.Argument(..., help="Project name to remove."),
    keep_data: bool = typer.Option(False, help="Keep project data directory."),
) -> None:
    """Remove a project from the configuration (and optionally its data)."""
    from odoo_bootstrap.commands.cmd_project import run_remove_project

    run_remove_project(name=name, config_manager=get_config_manager(), keep_data=keep_data)


# ── start ─────────────────────────────────────────────────────────────────────

@app.command("start")
def cmd_start(
    name: str = typer.Argument(..., help="Project name to start."),
) -> None:
    """Start a project (docker compose up)."""
    from odoo_bootstrap.commands.cmd_service import run_start

    run_start(name=name, config_manager=get_config_manager())


# ── stop ──────────────────────────────────────────────────────────────────────

@app.command("stop")
def cmd_stop(
    name: str = typer.Argument(..., help="Project name to stop."),
) -> None:
    """Stop a project (docker compose down)."""
    from odoo_bootstrap.commands.cmd_service import run_stop

    run_stop(name=name, config_manager=get_config_manager())


# ── restart ───────────────────────────────────────────────────────────────────

@app.command("restart")
def cmd_restart(
    name: str = typer.Argument(..., help="Project name to restart."),
    service: Optional[str] = typer.Option(None, help="Specific service to restart (e.g. odoo)."),
) -> None:
    """Restart a project or specific service."""
    from odoo_bootstrap.commands.cmd_service import run_restart

    run_restart(name=name, config_manager=get_config_manager(), service=service)


# ── logs ──────────────────────────────────────────────────────────────────────

@app.command("logs")
def cmd_logs(
    name: str = typer.Argument(..., help="Project name."),
    follow: bool = typer.Option(False, "-f", "--follow", help="Follow log output."),
    tail: int = typer.Option(100, help="Number of lines from the end."),
) -> None:
    """Show container logs for a project."""
    from odoo_bootstrap.commands.cmd_service import run_logs

    run_logs(name=name, config_manager=get_config_manager(), follow=follow, tail=tail)


# ── shell ─────────────────────────────────────────────────────────────────────

@app.command("shell")
def cmd_shell(
    name: str = typer.Argument(..., help="Project name."),
    db: Optional[str] = typer.Option(None, help="Database name override."),
) -> None:
    """Open an interactive Odoo shell inside the project container."""
    from odoo_bootstrap.commands.cmd_service import run_shell

    run_shell(name=name, config_manager=get_config_manager(), db=db)


# ── rebuild ───────────────────────────────────────────────────────────────────

@app.command("rebuild")
def cmd_rebuild(
    version: Optional[int] = typer.Argument(None, help="Odoo version to rebuild (default: all)."),
    no_cache: bool = typer.Option(False, help="Build without Docker cache."),
) -> None:
    """Rebuild Docker images for one or all Odoo versions."""
    from odoo_bootstrap.commands.cmd_service import run_rebuild

    run_rebuild(version=version, config_manager=get_config_manager(), no_cache=no_cache)


# ── clean ─────────────────────────────────────────────────────────────────────

@app.command("clean")
def cmd_clean() -> None:
    """Remove stopped containers and dangling Docker images."""
    from odoo_bootstrap.commands.cmd_service import run_clean

    run_clean(get_config_manager())


# ── update ────────────────────────────────────────────────────────────────────

@app.command("update")
def cmd_update(
    version: Optional[int] = typer.Argument(None, help="Odoo version to update (default: all)."),
) -> None:
    """Git pull all Odoo sources and rebuild Docker images if needed."""
    from odoo_bootstrap.commands.cmd_service import run_update

    run_update(version=version, config_manager=get_config_manager())


# ── backup ────────────────────────────────────────────────────────────────────

@app.command("backup")
def cmd_backup(
    name: str = typer.Argument(..., help="Project name to backup."),
    label: str = typer.Option("", help="Optional label suffix for the archive name."),
) -> None:
    """
    Backup a project: database + filestore + config into a .tar.gz archive.
    """
    from odoo_bootstrap.commands.cmd_backup import run_backup

    run_backup(name=name, config_manager=get_config_manager(), label=label)


# ── restore ───────────────────────────────────────────────────────────────────

@app.command("restore")
def cmd_restore(
    name: str = typer.Argument(..., help="Project name to restore into."),
    archive: Path = typer.Argument(..., help="Path to the .tar.gz backup archive."),
    drop_existing: bool = typer.Option(False, help="Drop and recreate the database before restore."),
) -> None:
    """Restore a project from a backup archive."""
    from odoo_bootstrap.commands.cmd_backup import run_restore

    run_restore(
        name=name,
        config_manager=get_config_manager(),
        archive_path=archive,
        drop_existing=drop_existing,
    )


# ── requirements ──────────────────────────────────────────────────────────────

@app.command("requirements")
def cmd_requirements(
    name: Optional[str] = typer.Argument(None, help="Project name (default: all projects)."),
) -> None:
    """Install Python packages from custom_addons/requirements.txt inside containers."""
    from odoo_bootstrap.commands.cmd_service import run_requirements

    run_requirements(name=name, config_manager=get_config_manager())



# ── sync-addons ───────────────────────────────────────────────────────────────

@app.command("sync-addons")
def cmd_sync_addons(
    source: Optional[str] = typer.Option(
        None,
        "--source", "-s",
        help="Thư mục chứa addon/ZIP. Mặc định: /home/thanh/ownCloud/Z - Other/modules/",
    ),
    project: Optional[str] = typer.Option(
        None,
        "--project", "-p",
        help="Chỉ sync vào project cụ thể (mặc định: tất cả project).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Xem trước, không thay đổi thực tế.",
    ),
    keep_duplicates: bool = typer.Option(
        False,
        "--keep-duplicates",
        help="Không xóa addon trùng với Odoo core.",
    ),
) -> None:
    """
    Tự động scan ZIP/folder addon, phát hiện version Odoo,
    copy vào đúng custom_addons của project.

    Tính năng:
    - Hỗ trợ ZIP và folder
    - Đoán version qua manifest, Python syntax, XML pattern, dependencies
    - Kiểm tra trùng với Odoo core/enterprise → xóa khỏi source
    - Trùng tên trong project → bỏ qua

    Ví dụ:
      odoo-bootstrap sync-addons
      odoo-bootstrap sync-addons --dry-run
      odoo-bootstrap sync-addons --project kh_enterprise
      odoo-bootstrap sync-addons --source ~/Downloads/my_modules/
      odoo-bootstrap sync-addons --keep-duplicates
    """
    from pathlib import Path as _Path
    from odoo_bootstrap.commands.cmd_sync_addons import run_sync_addons

    src = _Path(source) if source else None
    run_sync_addons(
        config_manager=get_config_manager(),
        source_dir=src,
        project_name=project,
        dry_run=dry_run,
        remove_core_duplicates=not keep_duplicates,
    )

if __name__ == "__main__":
    app()
