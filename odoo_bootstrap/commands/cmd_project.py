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


def _detect_enterprise(version: int) -> bool:
    """Return True if enterprise modules exist for this version."""
    ent_dir = WORKSPACE_ROOT / "versions" / str(version) / "enterprise"
    if not ent_dir.exists():
        return False
    # Co it nhat 1 module hop le
    for item in ent_dir.iterdir():
        if item.is_dir() and (item / "__manifest__.py").exists():
            return True
    return False


def _find_free_port(base_port: int, used_ports: list[int]) -> int:
    """Find next free port starting from base_port."""
    port = base_port
    while port in used_ports:
        port += 1
    return port


def _get_used_ports(config_manager) -> list[int]:
    """Get all ports already used by existing projects."""
    ports = []
    for proj in config_manager.list_projects():
        ports.append(proj.odoo_port)
        ports.append(proj.odoo_port + 3)  # longpoll
    return ports


def run_create_project(
    name: str,
    version: int,
    config_manager,
    db_name: str = "",
    db_user: str = "odoo",
    db_password: str = "odoo",
    port: int = 0,
) -> None:
    """Create a new Odoo project with full configuration."""
    renderer = TemplateRenderer()

    if not name.replace("_", "").replace("-", "").isalnum():
        raise ProjectError(f"Project name '{name}' is invalid. Use only alphanumeric, underscore, hyphen.")

    existing = config_manager.get_project(name)
    if existing:
        console.print(f"[yellow]Project '{name}' already exists. Re-generating files.[/yellow]")

    resolved_db = db_name or f"odoo_{name}_{version}"

    # Tu dong chon port neu khong chi dinh
    used_ports = _get_used_ports(config_manager)
    base_port = ODOO_PORTS.get(version, 8069)
    if port == 0:
        odoo_port = _find_free_port(base_port, used_ports)
    else:
        odoo_port = port
    longpoll_port = odoo_port + 3

    # Detect enterprise
    has_enterprise = _detect_enterprise(version)
    if has_enterprise:
        console.print(f"[green]✓ Enterprise modules detected for Odoo {version}[/green]")
    else:
        console.print(f"[dim]Enterprise not found — using Community only[/dim]")

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

    # Tao thu muc
    for subdir in PROJECT_SUBDIRS:
        (project.project_dir / subdir).mkdir(parents=True, exist_ok=True)

    config_dir = project.project_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Build addons_path
    addons_path = []
    source_dir = WORKSPACE_ROOT / "versions" / str(version) / "source"
    if source_dir.exists():
        addons_path.append(f"/opt/odoo/{version}.0/addons")
        addons_path.append(f"/opt/odoo/{version}.0/odoo/addons")
    else:
        addons_path.append(f"/opt/odoo/{version}.0/addons")

    if has_enterprise:
        addons_path.append("/opt/enterprise")

    addons_path.append("/opt/custom_addons")

    # Generate odoo.conf
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
            "longpoll_port": longpoll_port,
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
        "longpoll_port": longpoll_port,
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
        "has_enterprise": has_enterprise,
        "enterprise_dir": str(WORKSPACE_ROOT / "versions" / str(version) / "enterprise"),
    }
    renderer.render_to_file(
        "compose/docker-compose.yml.j2",
        project.project_dir / "docker-compose.yml",
        context=compose_context,
        overwrite=True,
    )

    renderer.render_to_file(
        "compose/docker-compose.override.yml.j2",
        project.project_dir / "docker-compose.override.yml",
        context={"project_name": name},
        overwrite=False,
    )

    readme = project.project_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# Odoo {version} {'Enterprise' if has_enterprise else 'Community'} — {name}\n\n"
            f"Port: http://localhost:{odoo_port}\n\n"
            f"```\nodoo-bootstrap start {name}\n```\n",
            encoding="utf-8",
        )

    gitignore = project.custom_addons_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("__pycache__/\n*.pyc\n.DS_Store\n", encoding="utf-8")

    # Luu port thuc su vao config
    project_with_port = ProjectConfig(
        name=name,
        version=version,
        db=db_config,
        odoo=odoo_config,
    )
    config_manager.add_project(project_with_port)

    # Hien thi ket qua
    edition = "Enterprise ✓" if has_enterprise else "Community"
    console.print(f"\n[green bold]✓ Project '{name}' (Odoo {version} {edition}) created[/green bold]")
    console.print(f"  URL:        [cyan]http://localhost:{odoo_port}[/cyan]")
    console.print(f"  Directory:  [cyan]{project.project_dir}[/cyan]")
    console.print(f"  Database:   [cyan]{resolved_db}[/cyan]")
    console.print(f"  Addons:     [cyan]{', '.join(addons_path)}[/cyan]")
    console.print()
    console.print("Chạy:")
    console.print(f"  [cyan]odoo-bootstrap start {name}[/cyan]")


def run_remove_project(name: str, config_manager, keep_data: bool = False) -> None:
    """Remove a project and optionally its data."""
    project = config_manager.get_project(name)
    if not project:
        raise ProjectError(f"Project '{name}' not found")

    console.print(f"[yellow]Removing project '{name}'...[/yellow]")

    if not keep_data and project.project_dir.exists():
        confirmed = Confirm.ask(
            f"Delete all data in {project.project_dir}?",
            default=False,
        )
        if confirmed:
            shutil.rmtree(project.project_dir)
            console.print(f"[red]Removed {project.project_dir}[/red]")

    config_manager.remove_project(name)
    console.print(f"[green]✓ Project '{name}' removed[/green]")
