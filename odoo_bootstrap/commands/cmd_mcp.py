"""
odoo-bootstrap mcp-setup / mcp-status:
Cài mart337i/odoo-dev-mcp + odoo-skills cho Claude Desktop.

Không cần Neo4j, không cần database phức tạp:
- 302+ trang docs Odoo searchable (v17, v18, v19)
- Code generation version-aware
- OWL frontend scaffolds
- Kết nối thẳng Claude Desktop / Claude Code
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from odoo_bootstrap.core.constants import WORKSPACE_ROOT
from odoo_bootstrap.core.logger import get_logger

logger = get_logger("mcp")
console = Console()

MCP_DIR = WORKSPACE_ROOT / "shared" / "mcp"
DEV_MCP_DIR = MCP_DIR / "odoo-dev-mcp"
SKILLS_DIR = MCP_DIR / "odoo-skills"

DEV_MCP_REPO = "https://github.com/mart337i/odoo-dev-mcp.git"
SKILLS_REPO = "https://github.com/mart337i/odoo-skills.git"

CLAUDE_CONFIG = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def _clone_or_pull(repo: str, target: Path, name: str) -> None:
    if (target / ".git").exists():
        console.print(f"[dim]Pulling {name}...[/dim]")
        subprocess.run(["git", "pull", "--ff-only"], cwd=target, capture_output=True, check=False)
    else:
        console.print(f"[cyan]-> Clone {name}...[/cyan]")
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", repo, str(target)], check=True)
    console.print(f"[green]OK {name}[/green]")


def _install_deps(target: Path) -> None:
    uv_bin = shutil.which("uv")
    venv = Path.home() / ".venv-odoo-bootstrap"
    pip = str(venv / "bin" / "pip") if (venv / "bin" / "pip").exists() else "pip3"
    console.print("[cyan]-> Cai dependencies...[/cyan]")
    if uv_bin and (target / "pyproject.toml").exists():
        r = subprocess.run([uv_bin, "sync"], cwd=target, capture_output=True, text=True)
        if r.returncode == 0:
            console.print("[green]OK uv sync[/green]")
            return
    req = target / "requirements.txt"
    if req.exists():
        subprocess.run([pip, "install", "-q", "-r", str(req)], check=False)
    subprocess.run([pip, "install", "-q", "mcp[cli]"], check=False)
    console.print("[green]OK pip install[/green]")


def _find_server_py(target: Path) -> Path | None:
    for c in [
        target / "src" / "odoo_mcp" / "server.py",
        target / "odoo_mcp_server.py",
        target / "server.py",
        target / "src" / "server.py",
    ]:
        if c.exists():
            return c
    return None


def _update_claude_config(server_py: Path) -> None:
    CLAUDE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    config: dict = {}
    if CLAUDE_CONFIG.exists():
        try:
            config = json.loads(CLAUDE_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            config = {}
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    uv_bin = shutil.which("uv")
    venv = Path.home() / ".venv-odoo-bootstrap"
    python_bin = str(venv / "bin" / "python") if (venv / "bin" / "python").exists() else "python3"
    env_vars = {
        "ODOO_SOURCE": str(WORKSPACE_ROOT / "versions" / "19" / "source"),
        "ODOO_VERSION": "19.0",
    }
    if uv_bin and (DEV_MCP_DIR / "pyproject.toml").exists():
        config["mcpServers"]["odoo-dev"] = {
            "command": uv_bin,
            "args": ["run", "--project", str(DEV_MCP_DIR), str(server_py)],
            "env": env_vars,
        }
    else:
        config["mcpServers"]["odoo-dev"] = {
            "command": python_bin,
            "args": [str(server_py)],
            "env": env_vars,
        }
    CLAUDE_CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"[green]OK Claude config: {CLAUDE_CONFIG}[/green]")


def run_mcp_setup() -> None:
    """Cai mart337i/odoo-dev-mcp + odoo-skills, config Claude Desktop."""
    console.print(
        Panel(
            "[bold cyan]MCP Dev Setup[/bold cyan]\n\n"
            "  mart337i/odoo-dev-mcp  - 302+ trang docs Odoo v17/18/19\n"
            "  mart337i/odoo-skills   - skills: debug, migrate, review\n\n"
            "Khong can Neo4j. Khong can DB phuc tap.",
            title="odoo-bootstrap mcp-setup",
        )
    )
    _clone_or_pull(DEV_MCP_REPO, DEV_MCP_DIR, "odoo-dev-mcp")
    _clone_or_pull(SKILLS_REPO, SKILLS_DIR, "odoo-skills")
    _install_deps(DEV_MCP_DIR)
    server_py = _find_server_py(DEV_MCP_DIR)
    if not server_py:
        console.print(f"[yellow]Khong tim thay server.py. Kiem tra: {DEV_MCP_DIR}[/yellow]")
        return
    _update_claude_config(server_py)
    console.print()
    console.print(
        Panel(
            "[bold green]MCP Dev xong![/bold green]\n\n"
            "[yellow]Restart Claude Desktop de load server.[/yellow]\n\n"
            "Sau khi restart hoi Claude:\n"
            "  'Search Odoo docs fields.Many2one version 19'\n"
            "  'Generate sale.order model Odoo 19'\n"
            "  'Create OWL component hien thi danh sach san pham'",
            title="Hoan tat",
        )
    )


def run_mcp_status() -> None:
    """Kiem tra trang thai MCP dev tools."""
    console.print("\n[bold]MCP Dev Status:[/bold]\n")
    for name, path in [("odoo-dev-mcp", DEV_MCP_DIR), ("odoo-skills", SKILLS_DIR)]:
        if (path / ".git").exists():
            r = subprocess.run(
                ["git", "log", "-1", "--format=%h %s"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            console.print(f"  [green]OK[/green] {name}: [dim]{r.stdout.strip()}[/dim]")
        else:
            console.print(f"  [red]X[/red] {name}: chua cai")
    console.print()
    if CLAUDE_CONFIG.exists():
        try:
            cfg = json.loads(CLAUDE_CONFIG.read_text())
            servers = list(cfg.get("mcpServers", {}).keys())
            console.print(f"  [green]OK[/green] Claude config: {servers}")
        except Exception:
            console.print("  [yellow]?[/yellow] Claude config: loi doc")
    else:
        console.print(f"  [yellow]?[/yellow] Claude config chua co: {CLAUDE_CONFIG}")
    server_py = _find_server_py(DEV_MCP_DIR)
    if server_py:
        console.print(f"\n  Server: [cyan]{server_py}[/cyan]")
    if SKILLS_DIR.exists():
        skills = sorted(SKILLS_DIR.glob("*.md"))
        if skills:
            console.print(f"\n  Skills ({len(skills)} files):")
            for s in skills[:6]:
                console.print(f"    [dim]{s.name}[/dim]")
