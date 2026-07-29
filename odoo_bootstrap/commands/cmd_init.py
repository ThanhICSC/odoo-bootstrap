"""
odoo-bootstrap init: Set up the complete Odoo development workspace.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from odoo_bootstrap.config.template_renderer import TemplateRenderer
from odoo_bootstrap.core.config_manager import ConfigManager
from odoo_bootstrap.core.constants import (
    ODOO_COMMUNITY_REPO,
    ODOO_PORTS,
    SERVICE_PORTS,
    VERSION_SUBDIRS,
    WORKSPACE_DIRS,
)
from odoo_bootstrap.core.logger import get_logger
from odoo_bootstrap.docker.docker_service import DockerService

logger = get_logger("init")
console = Console()


def run_init(
    workspace: Path,
    versions: list[int],
    skip_git: bool = False,
    skip_docker_build: bool = False,
    skip_shared: bool = False,
) -> None:
    """Execute the full init sequence."""
    cfg_manager = ConfigManager()
    config = cfg_manager.config
    renderer = TemplateRenderer()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # ── Step 1: Create workspace directories ──────────────────────────────
        task = progress.add_task("Creating workspace directories...", total=None)
        _create_workspace(workspace)
        progress.update(task, description="[green]✓ Workspace directories created")

        # ── Step 2: Create version directories ────────────────────────────────
        task2 = progress.add_task("Creating version directories...", total=None)
        _create_version_dirs(workspace, versions)
        progress.update(task2, description="[green]✓ Version directories created")

        # ── Step 3: Clone/pull Odoo source ────────────────────────────────────
        if not skip_git:
            task3 = progress.add_task("Cloning/pulling Odoo source...", total=None)
            _clone_odoo_sources(workspace, versions)
            progress.update(task3, description="[green]✓ Odoo source up to date")

        # ── Step 4: Generate Dockerfiles ──────────────────────────────────────
        task4 = progress.add_task("Generating Dockerfiles...", total=None)
        _generate_dockerfiles(workspace, versions, renderer)
        progress.update(task4, description="[green]✓ Dockerfiles generated")

        # ── Step 5: Build Docker images ───────────────────────────────────────
        if not skip_docker_build:
            try:
                docker = DockerService()
                task5 = progress.add_task("Building Docker images...", total=None)
                _build_docker_images(workspace, versions, docker)
                progress.update(task5, description="[green]✓ Docker images built")
            except Exception as e:
                console.print(f"[yellow]Warning: Docker build skipped: {e}")

        # ── Step 6: Generate shared docker-compose ────────────────────────────
        if not skip_shared:
            task6 = progress.add_task("Generating shared services...", total=None)
            _generate_shared_compose(workspace, config, renderer)
            progress.update(task6, description="[green]✓ Shared services configured")

        # ── Step 7: Generate VS Code config ──────────────────────────────────
        task7 = progress.add_task("Generating VS Code config...", total=None)
        _generate_vscode(workspace, versions, renderer)
        progress.update(task7, description="[green]✓ VS Code configuration generated")

        # ── Step 8: Generate Makefile ─────────────────────────────────────────
        task8 = progress.add_task("Generating Makefile...", total=None)
        _generate_makefile(workspace, config, renderer)
        progress.update(task8, description="[green]✓ Makefile generated")

        # ── Step 9: Save config ───────────────────────────────────────────────
        task9 = progress.add_task("Saving configuration...", total=None)
        cfg_manager.save()
        progress.update(task9, description="[green]✓ Configuration saved")

    console.print()
    console.print("[bold green]✓ odoo-bootstrap init complete![/bold green]")
    console.print(f"  Workspace: [cyan]{workspace}[/cyan]")
    console.print(f"  Versions:  [cyan]{', '.join(str(v) for v in versions)}[/cyan]")
    console.print()
    console.print("Next steps:")
    console.print("  [cyan]odoo-bootstrap create-project my_customer --version 19[/cyan]")
    console.print("  [cyan]odoo-bootstrap start my_customer[/cyan]")
    console.print("  [cyan]odoo-bootstrap doctor[/cyan]")


def _create_workspace(workspace: Path) -> None:
    for d in WORKSPACE_DIRS:
        (workspace / d).mkdir(parents=True, exist_ok=True)
    logger.debug(f"Workspace directories created under {workspace}")


def _create_version_dirs(workspace: Path, versions: list[int]) -> None:
    for v in versions:
        ver_dir = workspace / "versions" / str(v)
        for subdir in VERSION_SUBDIRS:
            (ver_dir / subdir).mkdir(parents=True, exist_ok=True)
        # Create README in enterprise dir
        ent_readme = ver_dir / "enterprise" / "README.md"
        if not ent_readme.exists():
            ent_readme.write_text(
                f"# Odoo {v} Enterprise\n\n"
                "Copy your Enterprise source code here.\n"
                "odoo-bootstrap will automatically detect and include it in addons_path.\n",
                encoding="utf-8",
            )


def _clone_odoo_sources(workspace: Path, versions: list[int]) -> None:
    from odoo_bootstrap.utils.git import clone_or_pull

    for v in versions:
        source_dir = workspace / "versions" / str(v) / "source"
        branch = f"{v}.0"
        try:
            result = clone_or_pull(
                ODOO_COMMUNITY_REPO,
                source_dir,
                branch=branch,
                depth=1,  # shallow clone for speed
            )
            logger.info(f"Odoo {v}: {result}")
        except Exception as e:
            logger.warning(f"Could not clone Odoo {v}: {e}. Skipping.")


def _generate_dockerfiles(workspace: Path, versions: list[int], renderer: TemplateRenderer) -> None:
    for v in versions:
        docker_dir = workspace / "versions" / str(v) / "docker"
        source_dir = workspace / "versions" / str(v) / "source"
        docker_dir.mkdir(parents=True, exist_ok=True)

        # Dockerfile
        renderer.render_to_file(
            "docker/Dockerfile.j2",
            docker_dir / "Dockerfile",
            context={"version": v, "extra_pip_packages": []},
            overwrite=True,
        )

        # entrypoint.sh
        renderer.render_to_file(
            "docker/entrypoint.sh.j2",
            docker_dir / "entrypoint.sh",
            context={"version": v},
            overwrite=True,
        )
        (docker_dir / "entrypoint.sh").chmod(0o755)

        # Symlink or copy source into docker build context
        source_link = docker_dir / "source"
        if not source_link.exists() and source_dir.exists():
            try:
                source_link.symlink_to(source_dir)
            except Exception:
                pass  # symlink not critical


def _build_docker_images(workspace: Path, versions: list[int], docker: DockerService) -> None:
    for v in versions:
        image_name = f"bizapps-odoo:{v}"
        if not docker.image_exists(image_name):
            docker_dir = workspace / "versions" / str(v) / "docker"
            dockerfile = docker_dir / "Dockerfile"
            if dockerfile.exists():
                try:
                    docker.build_image(dockerfile, image_name)
                except Exception as e:
                    logger.warning(f"Failed to build {image_name}: {e}")
            else:
                logger.warning(f"No Dockerfile for Odoo {v}, skipping build")
        else:
            logger.info(f"Image {image_name} already exists")


def _generate_shared_compose(workspace: Path, config, renderer: TemplateRenderer) -> None:
    shared_dir = workspace / "shared"
    shared_dir.mkdir(parents=True, exist_ok=True)

    databases = [p.db.name for p in config.projects.values() if p.db.name]

    renderer.render_to_file(
        "shared/docker-compose.shared.yml.j2",
        shared_dir / "docker-compose.yml",
        context={
            "postgres_version": config.postgres_version,
            "postgres_user": config.postgres_user,
            "postgres_password": config.postgres_password,
            "enable_pgadmin": config.enable_pgadmin,
            "enable_mailpit": config.enable_mailpit,
            "enable_redis": config.enable_redis,
            "enable_adminer": config.enable_adminer,
            "pgadmin_email": config.pgadmin_email,
            "pgadmin_password": config.pgadmin_password,
            "pgadmin_port": SERVICE_PORTS["pgadmin"],
            "mailpit_http_port": SERVICE_PORTS["mailpit_http"],
            "mailpit_smtp_port": SERVICE_PORTS["mailpit_smtp"],
            "redis_port": SERVICE_PORTS["redis"],
            "adminer_port": SERVICE_PORTS["adminer"],
        },
        overwrite=True,
    )

    renderer.render_to_file(
        "shared/init-db.sh.j2",
        shared_dir / "init-db.sh",
        context={
            "postgres_user": config.postgres_user,
            "databases": databases,
        },
        overwrite=True,
    )
    (shared_dir / "init-db.sh").chmod(0o755)


def _generate_vscode(workspace: Path, versions: list[int], renderer: TemplateRenderer) -> None:
    vscode_dir = workspace / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)

    projects_data = [
        (
            str(v),
            ODOO_PORTS[v],
            v,
            str(workspace / "versions" / str(v) / "source"),
            str(workspace / "versions" / str(v) / "source"),
            str(workspace / "versions" / str(v) / "config"),
        )
        for v in versions
    ]
    source_paths = [str(workspace / "versions" / str(v) / "source") for v in versions]

    renderer.render_to_file(
        "vscode/launch.json.j2",
        vscode_dir / "launch.json",
        context={"projects": projects_data},
        overwrite=True,
    )
    renderer.render_to_file(
        "vscode/tasks.json.j2",
        vscode_dir / "tasks.json",
        context={"projects": [(str(v), v) for v in versions]},
        overwrite=True,
    )
    renderer.render_to_file(
        "vscode/settings.json.j2",
        vscode_dir / "settings.json",
        context={"source_paths": source_paths, "workspace": str(workspace)},
        overwrite=True,
    )


def _generate_makefile(workspace: Path, config, renderer: TemplateRenderer) -> None:
    project_names = list(config.projects.keys())
    renderer.render_to_file(
        "shared/Makefile.j2",
        workspace / "Makefile",
        context={"project_names": project_names},
        overwrite=True,
    )
