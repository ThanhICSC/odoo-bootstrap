from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()

CLAUDE_CONFIG_PATH = Path.home() / ".config" / "claude" / "claude_desktop_config.json"
ODOO_DEV = Path.home() / "odoo-dev"
MCP_ALLOWED_PATHS = [
    str(ODOO_DEV / "versions" / "19" / "source" / "addons"),
    str(ODOO_DEV / "versions" / "19" / "enterprise"),
    str(ODOO_DEV / "versions" / "18" / "source" / "addons"),
    str(ODOO_DEV / "versions" / "17" / "source" / "addons"),
    str(Path.home() / "ownCloud" / "Z - Other" / "modules"),
]


def _check_node():
    return shutil.which("node") is not None


def _install_node():
    console.print("[cyan]-> Cai Node.js LTS...[/cyan]")
    try:
        subprocess.run(
            "curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -",
            shell=True, check=True,
        )
        subprocess.run(["sudo", "apt", "install", "-y", "nodejs"], check=True)
        version = subprocess.check_output(["node", "--version"], text=True).strip()
        console.print(f"[green]✓ Node.js: {version}[/green]")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Cai that bai: {e}[/red]")
        return False


def _write_claude_config():
    existing = [p for p in MCP_ALLOWED_PATHS if Path(p).exists()]
    missing = [p for p in MCP_ALLOWED_PATHS if not Path(p).exists()]

    if missing:
        console.print("[yellow]⚠ Bo qua (chua ton tai):[/yellow]")
        for p in missing:
            console.print(f"  [dim]{p}[/dim]")

    if not existing:
        console.print("[red]✗ Khong co thu muc nao ton tai.[/red]")
        return

    config = {}
    if CLAUDE_CONFIG_PATH.exists():
        try:
            config = json.loads(CLAUDE_CONFIG_PATH.read_text())
        except json.JSONDecodeError:
            pass

    config.setdefault("mcpServers", {})
    config["mcpServers"]["filesystem"] = {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem"] + existing,
    }

    CLAUDE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False))
    console.print(f"[green]✓ Da ghi: {CLAUDE_CONFIG_PATH}[/green]")
    for p in existing:
        console.print(f"  • {p}")


def run_mcp_setup():
    console.print()
    console.print("[bold cyan]━━ MCP Setup ━━[/bold cyan]")

    if _check_node():
        v = subprocess.check_output(["node", "--version"], text=True).strip()
        console.print(f"[green]✓ Node.js: {v}[/green]")
    else:
        if not _install_node():
            return

    _write_claude_config()

    console.print()
    console.print("[bold green]✓ Xong! Khoi dong lai Claude Desktop.[/bold green]")
    console.print("  Settings -> Developer -> kiem tra MCP [cyan]filesystem[/cyan] Active")


def run_mcp_status():
    console.print()
    console.print("[bold cyan]━━ MCP Status ━━[/bold cyan]")

    if _check_node():
        v = subprocess.check_output(["node", "--version"], text=True).strip()
        console.print(f"[green]✓ Node.js: {v}[/green]")
    else:
        console.print("[red]✗ Node.js chua cai[/red]")

    if CLAUDE_CONFIG_PATH.exists():
        try:
            config = json.loads(CLAUDE_CONFIG_PATH.read_text())
            servers = config.get("mcpServers", {})
            console.print(f"[green]✓ Config: {CLAUDE_CONFIG_PATH}[/green]")
            for name in servers:
                console.print(f"  • [cyan]{name}[/cyan]")
        except json.JSONDecodeError:
            console.print("[red]✗ Config loi JSON.[/red]")
    else:
        console.print("[red]✗ Chua co config. Chay mcp-setup truoc.[/red]")
    console.print()
