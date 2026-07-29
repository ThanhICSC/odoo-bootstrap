"""
odoo-bootstrap backup / restore commands.
"""

from __future__ import annotations

import shutil
import tarfile
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from odoo_bootstrap.core.exceptions import BackupError, ProjectError
from odoo_bootstrap.core.logger import get_logger
from odoo_bootstrap.utils.database import create_database, drop_database, pg_dump, pg_restore

logger = get_logger("backup")
console = Console()

BACKUP_DB_FILENAME = "database.dump"
BACKUP_FILESTORE_DIRNAME = "filestore"
BACKUP_CONFIG_DIRNAME = "config"


def run_backup(name: str, config_manager, label: str = "") -> Path:
    """
    Backup a project: database + filestore + config.
    Returns the path to the created backup archive.
    """
    project = config_manager.get_project(name)
    if not project:
        raise ProjectError(f"Project '{name}' not found")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{label}" if label else ""
    archive_name = f"{name}{suffix}_{timestamp}.tar.gz"
    backup_dir = project.backup_dir
    backup_dir.mkdir(parents=True, exist_ok=True)
    archive_path = backup_dir / archive_name

    # Temp staging dir
    staging = backup_dir / f"_staging_{timestamp}"
    staging.mkdir(parents=True, exist_ok=True)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        try:
            # ── Dump database ─────────────────────────────────────────────────
            task = progress.add_task(f"Dumping database {project.db.name}...", total=None)
            db_dump_path = str(staging / BACKUP_DB_FILENAME)
            pg_dump(project.db, db_dump_path)
            progress.update(task, description="[green]✓ Database dumped")

            # ── Copy filestore ────────────────────────────────────────────────
            if project.filestore_dir.exists():
                task2 = progress.add_task("Copying filestore...", total=None)
                dest_filestore = staging / BACKUP_FILESTORE_DIRNAME
                shutil.copytree(str(project.filestore_dir), str(dest_filestore), dirs_exist_ok=True)
                progress.update(task2, description="[green]✓ Filestore copied")

            # ── Copy config ───────────────────────────────────────────────────
            config_dir = project.project_dir / "config"
            if config_dir.exists():
                task3 = progress.add_task("Copying configuration...", total=None)
                dest_config = staging / BACKUP_CONFIG_DIRNAME
                shutil.copytree(str(config_dir), str(dest_config), dirs_exist_ok=True)
                progress.update(task3, description="[green]✓ Configuration copied")

            # ── Compress ──────────────────────────────────────────────────────
            task4 = progress.add_task("Compressing archive...", total=None)
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(staging, arcname=name)
            progress.update(task4, description="[green]✓ Archive created")

        finally:
            shutil.rmtree(staging, ignore_errors=True)

    size_mb = archive_path.stat().st_size / (1024 * 1024)
    console.print("[green bold]✓ Backup complete[/green bold]")
    console.print(f"  Archive: [cyan]{archive_path}[/cyan]")
    console.print(f"  Size:    [cyan]{size_mb:.1f} MB[/cyan]")
    return archive_path


def run_restore(name: str, config_manager, archive_path: Path, drop_existing: bool = False) -> None:
    """
    Restore a project from a backup archive.
    """
    project = config_manager.get_project(name)
    if not project:
        raise ProjectError(f"Project '{name}' not found")

    if not archive_path.exists():
        raise BackupError(f"Archive not found: {archive_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    staging = project.backup_dir / f"_restore_staging_{timestamp}"
    staging.mkdir(parents=True, exist_ok=True)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        try:
            # ── Extract archive ───────────────────────────────────────────────
            task = progress.add_task("Extracting archive...", total=None)
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(str(staging))
            # Find the inner directory (named after the project)
            inner_dirs = list(staging.iterdir())
            if inner_dirs:
                extract_dir = inner_dirs[0]
            else:
                raise BackupError("Archive appears to be empty")
            progress.update(task, description="[green]✓ Archive extracted")

            # ── Restore database ──────────────────────────────────────────────
            db_dump = extract_dir / BACKUP_DB_FILENAME
            if db_dump.exists():
                task2 = progress.add_task("Restoring database...", total=None)
                if drop_existing:
                    drop_database(project.db)
                create_database(project.db)
                pg_restore(project.db, str(db_dump))
                progress.update(task2, description="[green]✓ Database restored")

            # ── Restore filestore ─────────────────────────────────────────────
            src_filestore = extract_dir / BACKUP_FILESTORE_DIRNAME
            if src_filestore.exists():
                task3 = progress.add_task("Restoring filestore...", total=None)
                project.filestore_dir.mkdir(parents=True, exist_ok=True)
                shutil.copytree(str(src_filestore), str(project.filestore_dir), dirs_exist_ok=True)
                progress.update(task3, description="[green]✓ Filestore restored")

            # ── Restore config ────────────────────────────────────────────────
            src_config = extract_dir / BACKUP_CONFIG_DIRNAME
            if src_config.exists():
                task4 = progress.add_task("Restoring configuration...", total=None)
                config_dir = project.project_dir / "config"
                config_dir.mkdir(parents=True, exist_ok=True)
                shutil.copytree(str(src_config), str(config_dir), dirs_exist_ok=True)
                progress.update(task4, description="[green]✓ Configuration restored")

            # ── Fix permissions ───────────────────────────────────────────────
            task5 = progress.add_task("Fixing permissions...", total=None)
            _fix_permissions(project.project_dir)
            progress.update(task5, description="[green]✓ Permissions fixed")

        finally:
            shutil.rmtree(staging, ignore_errors=True)

    console.print(f"[green bold]✓ Restore complete for project '{name}'[/green bold]")
    console.print(f"  Restart: [cyan]odoo-bootstrap restart {name}[/cyan]")


def list_backups(name: str, config_manager) -> list[Path]:
    """List all backup archives for a project."""
    project = config_manager.get_project(name)
    if not project:
        raise ProjectError(f"Project '{name}' not found")
    if not project.backup_dir.exists():
        return []
    archives = sorted(project.backup_dir.glob(f"{name}_*.tar.gz"), reverse=True)
    return archives


def _fix_permissions(directory: Path) -> None:
    """Set ownership to current user recursively."""
    import os

    uid = os.getuid()
    gid = os.getgid()
    for path in directory.rglob("*"):
        try:
            os.chown(path, uid, gid)
        except (PermissionError, OSError):
            pass
