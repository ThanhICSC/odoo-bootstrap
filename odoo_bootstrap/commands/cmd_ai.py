"""
odoo-bootstrap ai-setup / ai / ai-fix:
- Cài Ollama + model local miễn phí
- Mở Aider web UI trỏ vào custom_addons của project
- Tự động sửa module sai version
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from rich.console import Console

from odoo_bootstrap.core.constants import WORKSPACE_ROOT
from odoo_bootstrap.core.logger import get_logger

logger = get_logger("ai")
console = Console()

# Model mặc định — chạy tốt trên CPU 14GB RAM
DEFAULT_MODEL = "qwen2.5-coder:7b"
OLLAMA_BASE_URL = "http://localhost:11434"

# System prompt Odoo-specific cho Aider
ODOO_SYSTEM_PROMPT = """You are an expert Odoo developer. Follow these rules strictly:
- Always use correct Odoo version syntax (check __manifest__.py version field)
- Python models: inherit from models.Model, use Odoo fields (fields.Char, fields.Many2one, etc.)
- Views: use proper XML with <odoo><data> wrapper
- Always include __init__.py in each directory
- Security: always add ir.model.access.csv entries for new models
- Manifest: include all dependencies, set installable=True
- Vietnamese comments are OK
- Never use deprecated APIs
"""


def _check_ollama() -> bool:
    """Kiểm tra Ollama đã cài chưa."""
    return shutil.which("ollama") is not None


def _ollama_running() -> bool:
    """Kiểm tra Ollama service đang chạy."""
    import urllib.request

    try:
        urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        return True
    except Exception:
        return False


def _model_pulled(model: str) -> bool:
    """Kiểm tra model đã pull về chưa."""
    import json
    import urllib.request

    try:
        resp = urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        data = json.loads(resp.read())
        names = [m["name"] for m in data.get("models", [])]
        return any(model in n for n in names)
    except Exception:
        return False


def run_ai_setup(model: str = DEFAULT_MODEL) -> None:
    """Cài đặt toàn bộ AI stack: Ollama + model + Aider + Open WebUI."""

    console.print("\n[bold cyan]╔══════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║   odoo-bootstrap AI Setup            ║[/bold cyan]")
    console.print("[bold cyan]╚══════════════════════════════════════╝[/bold cyan]\n")

    # ── Bước 1: Cài Ollama ────────────────────────────────────────────────────
    if _check_ollama():
        console.print("[green]✓ Ollama đã cài sẵn[/green]")
    else:
        console.print("[cyan]→ Cài Ollama...[/cyan]")
        result = subprocess.run(
            "curl -fsSL https://ollama.com/install.sh | sh",
            shell=True,
            capture_output=False,
        )
        if result.returncode != 0:
            console.print("[red]✗ Cài Ollama thất bại[/red]")
            return
        console.print("[green]✓ Ollama đã cài[/green]")

    # ── Bước 2: Start Ollama service ──────────────────────────────────────────
    if not _ollama_running():
        console.print("[cyan]→ Khởi động Ollama service...[/cyan]")
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(3)

    if _ollama_running():
        console.print("[green]✓ Ollama service đang chạy[/green]")
    else:
        console.print("[red]✗ Không thể khởi động Ollama[/red]")
        return

    # ── Bước 3: Pull model ────────────────────────────────────────────────────
    if _model_pulled(model):
        console.print(f"[green]✓ Model {model} đã có sẵn[/green]")
    else:
        console.print(f"[cyan]→ Downloading {model} (~4.7GB, lần đầu thôi)...[/cyan]")
        console.print("[dim]  Có thể mất 10-20 phút tùy tốc độ mạng[/dim]")
        result = subprocess.run(["ollama", "pull", model])
        if result.returncode != 0:
            console.print("[red]✗ Pull model thất bại[/red]")
            return
        console.print(f"[green]✓ Model {model} đã tải xong[/green]")

    # ── Bước 4: Cài Aider ─────────────────────────────────────────────────────
    # Tim aider: uu tien PATH (uv tool install), sau do venv
    aider_bin_str = shutil.which("aider")
    if aider_bin_str:
        console.print("[green]✓ Aider đã cài sẵn[/green]")
    else:
        console.print("[cyan]→ Cài Aider qua uv...[/cyan]")
        uv_bin = shutil.which("uv")
        if uv_bin:
            result = subprocess.run([uv_bin, "tool", "install", "aider-chat"])
        else:
            result = subprocess.run(
                ["pip", "install", "--break-system-packages", "-q", "aider-chat"],
                capture_output=False,
            )
        aider_bin_str = shutil.which("aider")
        if aider_bin_str:
            console.print("[green]✓ Aider đã cài[/green]")
        else:
            console.print("[red]✗ Cài Aider thất bại. Chạy: uv tool install aider-chat[/red]")
            return

    # ── Bước 5: Cài Open WebUI (Docker) ──────────────────────────────────────
    console.print("[cyan]→ Cài Open WebUI (giao diện chat local)...[/cyan]")
    result = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            "open-webui",
            "--restart",
            "unless-stopped",
            "-p",
            "3000:8080",
            "--add-host=host.docker.internal:host-gateway",
            "-e",
            "OLLAMA_BASE_URL=http://host.docker.internal:11434",
            "-v",
            "open-webui:/app/backend/data",
            "ghcr.io/open-webui/open-webui:main",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        console.print("[green]✓ Open WebUI đang cài (chạy ngầm)[/green]")
    elif "already in use" in result.stderr:
        console.print("[green]✓ Open WebUI đã chạy rồi[/green]")
    else:
        console.print(f"[yellow]⚠ Open WebUI: {result.stderr[:80]}[/yellow]")

    # ── Tạo Aider config cho Odoo ─────────────────────────────────────────────
    aider_conf = Path.home() / ".aider.conf.yml"
    if not aider_conf.exists():
        aider_conf.write_text(
            f"model: ollama/{model}\n"
            "ollama-api-base: http://localhost:11434\n"
            "auto-commits: true\n"
            "dirty-commits: true\n"
            "show-model-warnings: false\n"
            "map-tokens: 1024\n",
            encoding="utf-8",
        )
        console.print("[green]✓ Aider config tạo xong[/green]")

    # ── Tổng kết ──────────────────────────────────────────────────────────────
    console.print()
    console.print("[bold green]╔══════════════════════════════════════════╗[/bold green]")
    console.print("[bold green]║  ✓  AI Stack cài đặt hoàn tất!          ║[/bold green]")
    console.print("[bold green]╚══════════════════════════════════════════╝[/bold green]")
    console.print()
    console.print("Các công cụ đã sẵn sàng:")
    console.print("  [cyan]Ollama:[/cyan]    http://localhost:11434")
    console.print("  [cyan]Open WebUI:[/cyan] http://localhost:3000  (chat với AI)")
    console.print(f"  [cyan]Model:[/cyan]     {model} (chạy CPU, miễn phí)")
    console.print()
    console.print("Dùng ngay:")
    console.print("  [cyan]odoo-bootstrap ai kh19ce[/cyan]         ← viết module")
    console.print("  [cyan]odoo-bootstrap ai-fix my_module --target 19[/cyan]  ← sửa module")


def run_ai(project_name: str, config_manager) -> None:
    """
    Mở Aider web UI trỏ vào custom_addons của project.
    Nhập mô tả bằng tiếng Việt → AI viết module Odoo.
    """
    proj = config_manager.get_project(project_name)
    if not proj:
        console.print(f"[red]Project '{project_name}' không tồn tại[/red]")
        return

    addons_dir = proj.custom_addons_dir
    addons_dir.mkdir(parents=True, exist_ok=True)

    aider_bin = shutil.which("aider") or ""
    if not aider_bin:
        console.print("[red]Aider chưa cài. Chạy: uv tool install aider-chat[/red]")
        return

    if not _ollama_running():
        console.print("[cyan]→ Khởi động Ollama...[/cyan]")
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(3)

    # Tạo system prompt file cho Odoo version cụ thể
    prompt_file = addons_dir / ".aider-odoo-prompt.md"
    prompt_file.write_text(
        f"# Odoo {proj.version} Development Context\n\n"
        f"Project: {project_name}\n"
        f"Odoo version: {proj.version}\n"
        f"Edition: {'Enterprise' if (WORKSPACE_ROOT / 'versions' / str(proj.version) / 'enterprise').exists() else 'Community'}\n"
        f"Custom addons dir: {addons_dir}\n\n" + ODOO_SYSTEM_PROMPT,
        encoding="utf-8",
    )

    console.print(f"\n[bold]Aider AI — Project: {project_name} (Odoo {proj.version})[/bold]")
    console.print(f"Custom addons: [cyan]{addons_dir}[/cyan]")
    console.print()
    console.print("[dim]Gõ lệnh ví dụ:[/dim]")
    console.print("  [cyan]/ask Tạo module quản lý hợp đồng khách hàng cho Odoo 19[/cyan]")
    console.print("  [cyan]/ask Thêm field ngày_ky_hop_dong vào model contract[/cyan]")
    console.print("  [cyan]/exit[/cyan] để thoát\n")

    # Chạy Aider trong custom_addons dir
    os.chdir(addons_dir)

    # Init git nếu chưa có
    if not (addons_dir / ".git").exists():
        subprocess.run(["git", "init"], cwd=addons_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "init"],
            cwd=addons_dir,
            capture_output=True,
            env={
                **os.environ,
                "GIT_AUTHOR_NAME": "odoo-bootstrap",
                "GIT_AUTHOR_EMAIL": "dev@bizapps.vn",
                "GIT_COMMITTER_NAME": "odoo-bootstrap",
                "GIT_COMMITTER_EMAIL": "dev@bizapps.vn",
            },
        )

    cmd = [
        aider_bin,
        "--model",
        f"ollama/{DEFAULT_MODEL}",
        "--ollama-api-base",
        OLLAMA_BASE_URL,
        "--read",
        str(prompt_file),
        "--auto-commits",
        "--git",
        "--no-check-update",
    ]

    try:
        subprocess.run(cmd, cwd=str(addons_dir))
    except KeyboardInterrupt:
        console.print("\n[dim]Đã thoát Aider[/dim]")


def run_ai_fix(addon_path: Path, target_version: int, config_manager) -> None:
    """
    Tự động sửa module Odoo sang version đích.
    Dùng OCA module migrator + Aider để fix các lỗi còn lại.
    """
    if not addon_path.exists():
        console.print(f"[red]Không tìm thấy: {addon_path}[/red]")
        return

    console.print(f"\n[bold]AI Fix:[/bold] {addon_path.name} → Odoo {target_version}")

    venv = Path.home() / ".venv-odoo-bootstrap"
    pip = str(venv / "bin" / "pip")

    # ── Bước 1: Chạy OCA module migrator ─────────────────────────────────────
    migrator = venv / "bin" / "odoo-module-migrator"
    if not migrator.exists():
        console.print("[cyan]→ Cài OCA module migrator...[/cyan]")
        subprocess.run([pip, "install", "-q", "odoo-module-migrator"], capture_output=True)

    if migrator.exists():
        console.print(f"[cyan]→ Chạy OCA migrator → Odoo {target_version}...[/cyan]")
        result = subprocess.run(
            [
                str(migrator),
                "--path",
                str(addon_path),
                "--target-version",
                str(target_version),
                "--no-commit",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            console.print("[green]✓ OCA migrator chạy xong[/green]")
            if result.stdout:
                console.print(f"[dim]{result.stdout[:200]}[/dim]")
        else:
            console.print(f"[yellow]⚠ Migrator: {result.stderr[:100]}[/yellow]")

    # ── Bước 2: Aider fix các lỗi còn lại ────────────────────────────────────
    if not _ollama_running():
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)

    aider_bin = str(venv / "bin" / "aider")
    if not Path(aider_bin).exists():
        console.print(
            "[yellow]Aider chưa cài, bỏ qua bước AI fix. Chạy: odoo-bootstrap ai-setup[/yellow]"
        )
        return

    fix_prompt = (
        f"Fix this Odoo module to be compatible with Odoo {target_version}. "
        "Check and fix: manifest version field, deprecated API calls, "
        "XML view syntax (use <chatter/> if v17+), Python syntax, "
        "field definitions, security files. Make minimal changes."
    )

    console.print("[cyan]→ Aider đang fix tự động...[/cyan]")

    # Init git nếu chưa có
    if not (addon_path / ".git").exists():
        subprocess.run(["git", "init"], cwd=addon_path, capture_output=True)

    result = subprocess.run(
        [
            aider_bin,
            "--model",
            f"ollama/{DEFAULT_MODEL}",
            "--ollama-api-base",
            OLLAMA_BASE_URL,
            "--message",
            fix_prompt,
            "--auto-commits",
            "--yes",
            "--no-check-update",
        ],
        cwd=str(addon_path),
        capture_output=False,
    )

    console.print(f"\n[green]✓ AI Fix hoàn tất: {addon_path.name}[/green]")
    console.print("Kiểm tra lại và chạy:")
    console.print(f"  [cyan]odoo-bootstrap sync-addons --project kh{target_version}ce[/cyan]")
