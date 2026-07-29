"""
odoo-bootstrap status: Show system and project status.
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from odoo_bootstrap.core.constants import ODOO_PORTS, SERVICE_PORTS, WORKSPACE_ROOT
from odoo_bootstrap.core.logger import get_logger
from odoo_bootstrap.utils.system import get_disk_free_gb, get_total_ram_gb, get_cpu_count

logger = get_logger("status")
console = Console()


def run_status(config_manager) -> None:
    """Print status overview."""
    _print_workspace_status()
    _print_container_status()
    _print_project_status(config_manager)
    _print_port_status()


def _print_workspace_status() -> None:
    disk_gb = get_disk_free_gb(WORKSPACE_ROOT if WORKSPACE_ROOT.exists() else __import__("pathlib").Path.home())
    ram_gb = get_total_ram_gb()
    cpus = get_cpu_count()

    panel_content = (
        f"Workspace:  [cyan]{WORKSPACE_ROOT}[/cyan]  "
        f"({'[green]exists[/green]' if WORKSPACE_ROOT.exists() else '[red]missing[/red]'})\n"
        f"Disk free:  [cyan]{disk_gb:.1f} GB[/cyan]\n"
        f"RAM total:  [cyan]{ram_gb:.1f} GB[/cyan]\n"
        f"CPU cores:  [cyan]{cpus}[/cyan]"
    )
    console.print(Panel(panel_content, title="[bold]System[/bold]", border_style="blue"))


def _print_container_status() -> None:
    try:
        from odoo_bootstrap.docker.docker_service import DockerService
        ds = DockerService()
        containers = ds.list_containers(all=True)

        table = Table(title="Docker Containers", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="bold")
        table.add_column("Status")
        table.add_column("Image")
        table.add_column("Ports")

        for c in containers:
            status_style = "green" if c.status == "running" else "red"
            table.add_row(
                c.name,
                f"[{status_style}]{c.status}[/{status_style}]",
                c.image,
                c.ports,
            )

        if containers:
            console.print(table)
        else:
            console.print("[dim]No containers found[/dim]")
    except Exception as e:
        console.print(f"[yellow]Cannot reach Docker: {e}[/yellow]")


def _print_project_status(config_manager) -> None:
    projects = config_manager.list_projects()
    if not projects:
        console.print("[dim]No projects configured[/dim]")
        return

    table = Table(title="Projects", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="bold")
    table.add_column("Version")
    table.add_column("Database")
    table.add_column("Port")
    table.add_column("Directory")
    table.add_column("Status")

    for proj in projects:
        exists = "[green]✓[/green]" if proj.project_dir.exists() else "[red]✗[/red]"
        table.add_row(
            proj.name,
            str(proj.version),
            proj.db.name,
            str(proj.odoo_port),
            str(proj.project_dir),
            exists,
        )

    console.print(table)


def _print_port_status() -> None:
    from odoo_bootstrap.utils.system import is_port_in_use

    table = Table(title="Port Status", show_header=True, header_style="bold cyan")
    table.add_column("Service")
    table.add_column("Port")
    table.add_column("Status")

    all_ports: dict[str, int] = {f"Odoo {v}": p for v, p in ODOO_PORTS.items()}
    all_ports.update({
        "PgAdmin": SERVICE_PORTS["pgadmin"],
        "Mailpit HTTP": SERVICE_PORTS["mailpit_http"],
        "Mailpit SMTP": SERVICE_PORTS["mailpit_smtp"],
        "Redis": SERVICE_PORTS["redis"],
    })

    for service, port in all_ports.items():
        in_use = is_port_in_use(port)
        status = "[green]● listening[/green]" if in_use else "[dim]○ free[/dim]"
        table.add_row(service, str(port), status)

    console.print(table)
