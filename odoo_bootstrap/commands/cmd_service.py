"""
Service management commands: start, stop, restart, logs, shell, rebuild, clean, update.
"""

from __future__ import annotations

import subprocess

from rich.console import Console

from odoo_bootstrap.core.constants import SUPPORTED_VERSIONS, WORKSPACE_ROOT
from odoo_bootstrap.core.exceptions import DockerError, ProjectError
from odoo_bootstrap.core.logger import get_logger
from odoo_bootstrap.docker.docker_service import DockerService

logger = get_logger("service")
console = Console()


def run_start(name: str, config_manager) -> None:
    """Start a project using docker compose."""
    project = config_manager.get_project(name)
    if not project:
        raise ProjectError(
            f"Project '{name}' not found. Run: odoo-bootstrap create-project {name} --version 19"
        )

    if not project.project_dir.exists():
        raise ProjectError(f"Project directory missing: {project.project_dir}")

    compose_file = project.project_dir / "docker-compose.yml"
    if not compose_file.exists():
        raise ProjectError(f"docker-compose.yml not found in {project.project_dir}")

    docker = DockerService()
    docker.compose_up(project.project_dir, project_name=name)
    console.print(f"[green bold]✓ Project '{name}' started[/green bold]")
    console.print(f"  Odoo:    [cyan]http://localhost:{project.odoo_port}[/cyan]")
    console.print(f"  Logs:    [cyan]odoo-bootstrap logs {name}[/cyan]")


def run_stop(name: str, config_manager) -> None:
    """Stop a project."""
    project = config_manager.get_project(name)
    if not project:
        raise ProjectError(f"Project '{name}' not found")

    docker = DockerService()
    docker.compose_down(project.project_dir, project_name=name)
    console.print(f"[green]✓ Project '{name}' stopped[/green]")


def run_restart(name: str, config_manager, service: str | None = None) -> None:
    """Restart a project or specific service."""
    project = config_manager.get_project(name)
    if not project:
        raise ProjectError(f"Project '{name}' not found")

    docker = DockerService()
    docker.compose_restart(project.project_dir, project_name=name, service=service)
    target = f"service '{service}'" if service else f"project '{name}'"
    console.print(f"[green]✓ Restarted {target}[/green]")


def run_logs(name: str, config_manager, follow: bool = False, tail: int = 100) -> None:
    """Stream container logs for a project."""
    project = config_manager.get_project(name)
    if not project:
        raise ProjectError(f"Project '{name}' not found")

    compose_file = project.project_dir / "docker-compose.yml"
    cmd = [
        "docker",
        "compose",
        "-p",
        name,
        "-f",
        str(compose_file),
        "logs",
        "--tail",
        str(tail),
    ]
    if follow:
        cmd.append("-f")

    # Stream directly to stdout (not captured)
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        pass
    except subprocess.CalledProcessError as e:
        raise DockerError(f"Logs command failed: {e}") from e


def run_shell(name: str, config_manager, db: str | None = None) -> None:
    """Open an Odoo shell inside the running container."""
    project = config_manager.get_project(name)
    if not project:
        raise ProjectError(f"Project '{name}' not found")

    container_name = f"{name}-odoo"
    db_name = db or project.db.name

    cmd = [
        "docker",
        "exec",
        "-it",
        container_name,
        "python",
        f"/opt/odoo/{project.version}.0/odoo-bin",
        "shell",
        "--config=/etc/odoo/odoo.conf",
        f"--database={db_name}",
    ]
    console.print(f"[cyan]Opening Odoo shell for {name} (db: {db_name})...[/cyan]")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise DockerError(f"Shell command failed. Is the container running? ({e})") from e


def run_rebuild(version: int | None, config_manager, no_cache: bool = False) -> None:
    """Rebuild Docker images for one or all versions."""
    docker = DockerService()
    versions = [version] if version else SUPPORTED_VERSIONS

    for v in versions:
        image_name = f"bizapps-odoo:{v}"
        docker_dir = WORKSPACE_ROOT / "versions" / str(v) / "docker"
        dockerfile = docker_dir / "Dockerfile"

        if not dockerfile.exists():
            console.print(f"[yellow]No Dockerfile for Odoo {v}, skipping[/yellow]")
            continue

        console.print(f"[cyan]Building {image_name}...[/cyan]")
        docker.build_image(dockerfile, image_name, no_cache=no_cache)
        console.print(f"[green]✓ {image_name} built[/green]")


def run_clean(config_manager) -> None:
    """Remove stopped containers and dangling images."""
    DockerService()  # validate daemon is running

    console.print("[cyan]Pruning stopped containers...[/cyan]")
    subprocess.run(["docker", "container", "prune", "-f"], check=False)

    console.print("[cyan]Pruning dangling images...[/cyan]")
    subprocess.run(["docker", "image", "prune", "-f"], check=False)

    console.print("[green]✓ Clean complete[/green]")


def run_update(version: int | None, config_manager) -> None:
    """Git pull Odoo sources and rebuild images if needed."""
    from odoo_bootstrap.utils.git import clone_or_pull, is_git_repo

    versions = [version] if version else SUPPORTED_VERSIONS

    for v in versions:
        source_dir = WORKSPACE_ROOT / "versions" / str(v) / "source"
        if not is_git_repo(source_dir):
            console.print(
                f"[yellow]Odoo {v} source not cloned yet, run: odoo-bootstrap init[/yellow]"
            )
            continue

        console.print(f"[cyan]Updating Odoo {v}...[/cyan]")
        result = clone_or_pull(
            "https://github.com/odoo/odoo.git",
            source_dir,
            branch=f"{v}.0",
        )
        if result == "up_to_date":
            console.print(f"[dim]Odoo {v}: already up to date[/dim]")
        else:
            console.print(f"[green]✓ Odoo {v}: updated[/green]")
            # Rebuild image since source changed
            run_rebuild(v, config_manager)


def run_requirements(name: str | None, config_manager) -> None:
    """Install Python requirements from custom_addons into running container(s)."""
    docker = DockerService()

    projects = [config_manager.get_project(name)] if name else config_manager.list_projects()

    for project in projects:
        if not project:
            continue
        container = f"{project.name}-odoo"
        req_file = "/opt/custom_addons/requirements.txt"

        code, output = docker.exec_in_container(
            container,
            ["test", "-f", req_file],
        )
        if code != 0:
            console.print(f"[dim]{project.name}: no requirements.txt found[/dim]")
            continue

        console.print(f"[cyan]Installing requirements for {project.name}...[/cyan]")
        code, output = docker.exec_in_container(
            container,
            ["pip", "install", "--quiet", "-r", req_file],
        )
        if code == 0:
            console.print(f"[green]✓ {project.name}: requirements installed[/green]")
        else:
            console.print(f"[red]✗ {project.name}: pip install failed\n{output}[/red]")
