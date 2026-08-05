"""
odoo-bootstrap diagnose: Thu thập thông tin hệ thống + logs
để paste vào AI phân tích lỗi.
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from rich.console import Console

from odoo_bootstrap.core.constants import WORKSPACE_ROOT
from odoo_bootstrap.core.logger import get_logger

logger = get_logger("diagnose")
console = Console()


def _run(cmd: list[str], timeout: int = 10) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return "N/A"


def run_diagnose(
    project_name: str | None,
    config_manager,
    output_file: Path | None = None,
    tail_lines: int = 100,
) -> None:
    """Thu thập toàn bộ thông tin để gửi AI phân tích."""

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Odoo Diagnose Report",
        f"Generated: {now}",
        "",
    ]

    # ── System info ───────────────────────────────────────────────────
    lines += [
        "## System",
        f"- OS: {_run(['uname', '-a'])}",
        f"- Python: {_run(['python3', '--version'])}",
        f"- Docker: {_run(['docker', '--version'])}",
        f"- Docker Compose: {_run(['docker', 'compose', 'version', '--short'])}",
        "",
    ]

    # ── Docker containers ─────────────────────────────────────────────
    lines += ["## Running Containers"]
    containers = _run(["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"])
    lines += [f"```\n{containers}\n```", ""]

    # ── Project info ──────────────────────────────────────────────────
    if project_name:
        proj = config_manager.get_project(project_name)
        if proj:
            lines += [
                f"## Project: {project_name}",
                f"- Odoo version: {proj.version}",
                f"- Database: {proj.db.name}",
                f"- Port: {proj.odoo_port}",
                f"- Directory: {proj.project_dir}",
                "",
            ]

            # odoo.conf
            conf_file = proj.project_dir / "config" / "odoo.conf"
            if conf_file.exists():
                lines += [
                    "### odoo.conf",
                    "```ini",
                    conf_file.read_text(encoding="utf-8"),
                    "```",
                    "",
                ]

            # Container logs
            container = f"{project_name}-odoo"
            logs = _run(["docker", "logs", container, "--tail", str(tail_lines)], timeout=15)
            if logs:
                lines += [
                    f"### Odoo Logs (last {tail_lines} lines)",
                    "```",
                    logs,
                    "```",
                    "",
                ]

            # Installed addons
            addons_dir = proj.custom_addons_dir
            if addons_dir.exists():
                addons = [
                    d.name
                    for d in addons_dir.iterdir()
                    if d.is_dir() and (d / "__manifest__.py").exists()
                ]
                lines += ["### Custom Addons"]
                for a in sorted(addons):
                    lines.append(f"- `{a}`")
                lines.append("")

    # ── Pip packages ──────────────────────────────────────────────────
    lines += [
        "## Python Packages (odoo-bootstrap venv)",
        "```",
        _run(["pip", "list", "--format=columns"], timeout=15),
        "```",
        "",
        "## How to use this report",
        "Paste toàn bộ nội dung này vào Claude/Gemini với câu hỏi:",
        '- "Phân tích lỗi trong logs và cho tôi biết nguyên nhân"',
        '- "Cấu hình này có vấn đề gì không?"',
        '- "Module nào đang conflict?"',
    ]

    report = "\n".join(lines)

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(report, encoding="utf-8")
        console.print(f"[green]✓ Diagnose report: {output_file}[/green]")
    else:
        # Luu vao thu muc logs
        log_dir = WORKSPACE_ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        fname = log_dir / f"diagnose_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        fname.write_text(report, encoding="utf-8")
        console.print(f"[green]✓ Diagnose report: {fname}[/green]")

    console.print("[dim]→ Mở file và paste vào Claude/Gemini để phân tích[/dim]")
