"""
odoo-bootstrap doctor: Comprehensive system health checker.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from odoo_bootstrap.core.constants import (
    ODOO_PORTS,
    SERVICE_PORTS,
    SUPPORTED_VERSIONS,
    WORKSPACE_ROOT,
)
from odoo_bootstrap.core.logger import get_logger
from odoo_bootstrap.core.models import DoctorCheck, DoctorReport
from odoo_bootstrap.utils.system import (
    check_command_exists,
    get_command_version,
    get_cpu_count,
    get_disk_free_gb,
    get_python_version,
    get_total_ram_gb,
    is_port_in_use,
)

logger = get_logger("doctor")
console = Console()

# Minimum requirements
MIN_DISK_GB = 20.0
MIN_RAM_GB = 4.0
MIN_CPU = 2


def run_doctor(config_manager) -> DoctorReport:
    """Run all doctor checks and return a DoctorReport."""
    report = DoctorReport()

    _check_python(report)
    _check_docker(report)
    _check_docker_compose(report)
    _check_git(report)
    _check_disk(report)
    _check_ram(report)
    _check_cpu(report)
    _check_ports(report)
    _check_workspace(report)
    _check_docker_daemon(report)
    _check_postgres_reachable(report)
    _check_python_packages(report)
    _check_projects(report, config_manager)
    _check_docker_images(report)

    return report


def _ok(report: DoctorReport, name: str, message: str, detail: str = None) -> None:
    report.checks.append(DoctorCheck(name=name, status="ok", message=message, detail=detail))


def _warn(report: DoctorReport, name: str, message: str, detail: str = None) -> None:
    report.checks.append(DoctorCheck(name=name, status="warning", message=message, detail=detail))


def _error(report: DoctorReport, name: str, message: str, detail: str = None) -> None:
    report.checks.append(DoctorCheck(name=name, status="error", message=message, detail=detail))


def _check_python(report: DoctorReport) -> None:
    version = get_python_version()
    major, minor = map(int, version.split(".")[:2])
    if major >= 3 and minor >= 12:
        _ok(report, "Python", f"Python {version}")
    elif major >= 3 and minor >= 10:
        _warn(report, "Python", f"Python {version} — recommend 3.12+")
    else:
        _error(report, "Python", f"Python {version} — minimum 3.10 required")


def _check_docker(report: DoctorReport) -> None:
    if not check_command_exists("docker"):
        _error(report, "Docker", "Docker not found on PATH")
        return
    version = get_command_version("docker") or "unknown"
    _ok(report, "Docker", f"Docker found: {version}")


def _check_docker_compose(report: DoctorReport) -> None:
    import subprocess

    try:
        result = subprocess.run(
            ["docker", "compose", "version", "--short"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            _ok(report, "Docker Compose", f"Docker Compose v{result.stdout.strip()}")
        else:
            _error(report, "Docker Compose", "docker compose plugin not working")
    except Exception:
        _error(report, "Docker Compose", "docker compose command failed")


def _check_git(report: DoctorReport) -> None:
    if not check_command_exists("git"):
        _error(report, "Git", "Git not found on PATH")
        return
    version = get_command_version("git") or "unknown"
    _ok(report, "Git", f"Git found: {version}")


def _check_disk(report: DoctorReport) -> None:
    path = WORKSPACE_ROOT if WORKSPACE_ROOT.exists() else Path.home()
    free_gb = get_disk_free_gb(path)
    if free_gb >= MIN_DISK_GB:
        _ok(report, "Disk space", f"{free_gb:.1f} GB free")
    elif free_gb >= 10.0:
        _warn(report, "Disk space", f"{free_gb:.1f} GB free — recommend {MIN_DISK_GB}+ GB")
    else:
        _error(report, "Disk space", f"{free_gb:.1f} GB free — minimum {MIN_DISK_GB} GB required")


def _check_ram(report: DoctorReport) -> None:
    ram = get_total_ram_gb()
    if ram >= MIN_RAM_GB:
        _ok(report, "RAM", f"{ram:.1f} GB total")
    else:
        _warn(report, "RAM", f"{ram:.1f} GB total — recommend {MIN_RAM_GB}+ GB")


def _check_cpu(report: DoctorReport) -> None:
    cpus = get_cpu_count()
    if cpus >= MIN_CPU:
        _ok(report, "CPU", f"{cpus} cores")
    else:
        _warn(report, "CPU", f"{cpus} cores — recommend {MIN_CPU}+")


def _check_ports(report: DoctorReport) -> None:
    all_ports: dict[str, int] = {f"Odoo {v}": p for v, p in ODOO_PORTS.items()}
    all_ports.update(
        {
            "PgAdmin": SERVICE_PORTS["pgadmin"],
            "Mailpit HTTP": SERVICE_PORTS["mailpit_http"],
            "Mailpit SMTP": SERVICE_PORTS["mailpit_smtp"],
            "Redis": SERVICE_PORTS["redis"],
        }
    )
    occupied = []
    for name, port in all_ports.items():
        if is_port_in_use(port):
            occupied.append(f"{name}:{port}")

    if not occupied:
        _ok(report, "Ports", "All configured ports are free")
    else:
        _warn(report, "Ports", f"Ports in use: {', '.join(occupied)}")


def _check_workspace(report: DoctorReport) -> None:
    if WORKSPACE_ROOT.exists():
        _ok(report, "Workspace", f"{WORKSPACE_ROOT} exists")
    else:
        _warn(report, "Workspace", f"{WORKSPACE_ROOT} not yet created — run: odoo-bootstrap init")


def _check_docker_daemon(report: DoctorReport) -> None:
    try:
        from odoo_bootstrap.docker.docker_service import DockerService

        ds = DockerService()
        ver = ds.get_docker_version()
        _ok(report, "Docker daemon", f"Docker daemon responding (v{ver})")
    except Exception as e:
        _error(report, "Docker daemon", f"Docker daemon not responding: {e}")


def _check_postgres_reachable(report: DoctorReport) -> None:
    from odoo_bootstrap.utils.database import postgres_is_reachable

    if postgres_is_reachable():
        _ok(report, "PostgreSQL", "PostgreSQL reachable on localhost:5432")
    else:
        _warn(
            report,
            "PostgreSQL",
            "PostgreSQL not reachable on localhost:5432 (shared services may not be running)",
        )


def _check_python_packages(report: DoctorReport) -> None:
    import importlib.util

    required = [
        ("typer", "typer"),
        ("rich", "rich"),
        ("pydantic", "pydantic"),
        ("yaml", "pyyaml"),
        ("jinja2", "jinja2"),
        ("docker", "docker"),
        ("psycopg2", "psycopg2-binary"),
    ]
    missing = []
    for module, pkg in required:
        if importlib.util.find_spec(module) is None:
            missing.append(pkg)
    if not missing:
        _ok(report, "Python packages", "All required packages installed")
    else:
        _error(report, "Python packages", f"Missing: {', '.join(missing)}")


def _check_projects(report: DoctorReport, config_manager) -> None:
    projects = config_manager.list_projects()
    if not projects:
        _ok(report, "Projects", "No projects configured yet")
        return
    for proj in projects:
        if proj.project_dir.exists():
            _ok(report, f"Project: {proj.name}", f"Directory exists, Odoo {proj.version}")
        else:
            _warn(report, f"Project: {proj.name}", f"Directory missing: {proj.project_dir}")


def _check_docker_images(report: DoctorReport) -> None:
    try:
        from odoo_bootstrap.docker.docker_service import DockerService

        ds = DockerService()
        for v in SUPPORTED_VERSIONS:
            image = f"bizapps-odoo:{v}"
            if ds.image_exists(image):
                _ok(report, f"Image: {image}", "Built and available")
            else:
                _warn(report, f"Image: {image}", "Not yet built — run: odoo-bootstrap init")
    except Exception:
        pass


def print_doctor_report(report: DoctorReport) -> None:
    """Print the doctor report as a Rich table."""
    table = Table(
        title="[bold]odoo-bootstrap doctor[/bold]", show_header=True, header_style="bold cyan"
    )
    table.add_column("Check", style="bold", width=28)
    table.add_column("Status", width=10)
    table.add_column("Message")

    status_styles = {
        "ok": "[green]✓ OK[/green]",
        "warning": "[yellow]⚠ WARN[/yellow]",
        "error": "[red]✗ ERROR[/red]",
        "skip": "[dim]— SKIP[/dim]",
    }

    for check in report.checks:
        table.add_row(
            check.name,
            status_styles.get(check.status, check.status),
            check.message,
        )

    console.print(table)

    if report.has_errors:
        console.print("\n[red bold]✗ Errors found — please fix before continuing.[/red bold]")
    elif report.has_warnings:
        console.print("\n[yellow]⚠ Warnings found — some features may not work correctly.[/yellow]")
    else:
        console.print("\n[green bold]✓ All checks passed — system is healthy.[/green bold]")
