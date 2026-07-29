"""
odoo-bootstrap create-project / remove-project commands.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from odoo_bootstrap.config.template_renderer import TemplateRenderer
from odoo_bootstrap.core.constants import (
    ODOO_PORTS,
    SERVICE_PORTS,
    PROJECT_SUBDIRS,
    WORKSPACE_ROOT,
)
from odoo_bootstrap.core.exceptions import ProjectError
from odoo_bootstrap.core.logger import get_logger
from odoo_bootstrap.core.models import DatabaseConfig, OdooConfig, ProjectConfig

logger = get_logger("project")
console = Console()


def run_create_project(
    name: str,
    version: int,
    config_manager,
    db_name: str = "",
    db_user: str = "odoo",
    db_password: str = "odoo",
) -> None:
    """Create a new Odoo project with all required files."""
    renderer = TemplateRenderer()

    # Validate name
    if not name.replace("_", "").replace("-", "").isalnum():
        raise ProjectError(f"Project name '{name}' is invalid. Use only alphanumeric, underscore, hyphen.")

    # Check for conflicts
    existing = config_manager.get_project(name)
    if existing:
        console.print(f"[yellow]Project '{name}' already exists. Re-generating files.[/yellow]")

    # Resolve database name
    resolved_db = db_name or f"odoo_{name}_{version}"

    # Build config
    db_config = DatabaseConfig(
        host="postgres",
        port=5432,
        user=db_user,
        password=db_password,
        name=resolved_db,
    )
    odoo_config = OdooConfig()
    project = ProjectConfig(
        name=name,
        version=version,
        db=db_config,
        odoo=odoo_config,
    )

    # Create directories
    for subdir in PROJECT_SUBDIRS:
        (project.project_dir / subdir).mkdir(parents=True, exist_ok=True)

    config_dir = project.project_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Generate odoo.conf
    addons_path = project.get_addons_path()
    # Check if enterprise exists and add it
    enterprise_dir = WORKSPACE_ROOT / "versions" / str(version) / "enterprise"
    has_enterprise = any(
        (enterprise_dir / d / "__manifest__.py").exists()
        for d in (enterprise_dir.iterdir() if enterprise_dir.exists() else [])
        if (enterprise_dir / d).is_dir()
    )

    renderer.render_to_file(
        "odoo/odoo.conf.j2",
        config_dir / "odoo.conf",
        context={
            "version": version,
            "project_name": name,
            "db": db_config,
            "odoo": odoo_config,
            "addons_path": addons_path,
        },
        overwrite=True,
    )

    # Generate .env
    odoo_port = ODOO_PORTS[version]
    renderer.render_to_file(
        "project/env.j2",
        project.project_dir / ".env",
        context={
            "project_name": name,
            "version": version,
            "db_user": db_user,
            "db_password": db_password,
            "db_name": resolved_db,
            "odoo_port": odoo_port,
            "longpoll_port": odoo_port + 3,  # e.g. 8072 for v19
            "mailpit_http_port": SERVICE_PORTS["mailpit_http"],
            "mailpit_smtp_port": SERVICE_PORTS["mailpit_smtp"],
            "redis_port": SERVICE_PORTS["redis"],
            "pgadmin_port": SERVICE_PORTS["pgadmin"],
            "pgadmin_email": config_manager.config.pgadmin_email,
            "pgadmin_password": config_manager.config.pgadmin_password,
            "adminer_port": SERVICE_PORTS["adminer"],
        },
        overwrite=True,
    )

    # Generate docker-compose.yml
    compose_context = {
        "project_name": name,
        "version": version,
        "postgres_version": config_manager.config.postgres_version,
        "db_user": db_user,
        "db_password": db_password,
        "db_name": resolved_db,
        "odoo_port": odoo_port,
        "longpoll_port": odoo_port + 3,
        "filestore_dir": str(project.filestore_dir),
        "custom_addons_dir": str(project.custom_addons_dir),
        "config_dir": str(config_dir),
        "logs_dir": str(project.logs_dir),
        "enable_mailpit": config_manager.config.enable_mailpit,
        "enable_redis": config_manager.config.enable_redis,
        "enable_pgadmin": config_manager.config.enable_pgadmin,
        "enable_adminer": config_manager.config.enable_adminer,
        "mailpit_http_port": SERVICE_PORTS["mailpit_http"],
        "mailpit_smtp_port": SERVICE_PORTS["mailpit_smtp"],
        "redis_port": SERVICE_PORTS["redis"],
        "pgadmin_port": SERVICE_PORTS["pgadmin"],
        "pgadmin_email": config_manager.config.pgadmin_email,
        "pgadmin_password": config_manager.config.pgadmin_password,
        "adminer_port": SERVICE_PORTS["adminer"],
    }
    renderer.render_to_file(
        "compose/docker-compose.yml.j2",
        project.project_dir / "docker-compose.yml",
        context=compose_context,
        overwrite=True,
    )

    # Generate override (only if not exists — user editable)
    renderer.render_to_file(
        "compose/docker-compose.override.yml.j2",
        project.project_dir / "docker-compose.override.yml",
        context={"project_name": name},
        overwrite=False,  # Don't overwrite user customizations
    )

    # Create placeholder README
    readme = project.project_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# Odoo {version} — {name}\n\n"
            f"Generated by odoo-bootstrap.\n\n"
            f"## Start\n```\nodoo-bootstrap start {name}\n```\n\n"
            f"## Stop\n```\nodoo-bootstrap stop {name}\n```\n\n"
            f"## Logs\n```\nodoo-bootstrap logs {name}\n```\n",
            encoding="utf-8",
        )

    # Create .gitignore in custom_addons
    gitignore = project.custom_addons_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "__pycache__/\n*.pyc\n*.pyo\n.DS_Store\n",
            encoding="utf-8",
        )

    # Save to config
    config_manager.add_project(project)

    console.print(f"[green bold]✓ Project '{name}' (Odoo {version}) created[/green bold]")
    console.print(f"  Directory:  [cyan]{project.project_dir}[/cyan]")
    console.print(f"  Database:   [cyan]{resolved_db}[/cyan]")
    console.print(f"  Odoo port:  [cyan]{odoo_port}[/cyan]")
    console.print(f"  Config:     [cyan]{config_dir / 'odoo.conf'}[/cyan]")
    console.print()
    console.print("Commands:")
    console.print(f"  [cyan]odoo-bootstrap start {name}[/cyan]")
    console.print(f"  [cyan]odoo-bootstrap logs {name}[/cyan]")
    console.print(f"  [cyan]odoo-bootstrap backup {name}[/cyan]")


def run_remove_project(name: str, config_manager, keep_data: bool = False) -> None:
    """Remove a project and optionally its data."""
    project = config_manager.get_project(name)
    if not project:
        raise ProjectError(f"Project '{name}' not found")

    console.print(f"[yellow]Removing project '{name}'...[/yellow]")

    if not keep_data and project.project_dir.exists():
        confirmed = Confirm.ask(
            f"Delete all data in {project.project_dir}? This cannot be undone!",
            default=False,
        )
        if confirmed:
            shutil.rmtree(project.project_dir)
            console.print(f"[red]Removed {project.project_dir}[/red]")
        else:
            console.print("[dim]Data directory kept[/dim]")

    config_manager.remove_project(name)
    console.print(f"[green]✓ Project '{name}' removed from configuration[/green]")
