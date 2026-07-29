"""
odoo-bootstrap sync-addons: Tự động scan ZIP/folder addon,
phát hiện version Odoo, copy vào đúng project.
"""

from __future__ import annotations

import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from odoo_bootstrap.core.constants import WORKSPACE_ROOT, SUPPORTED_VERSIONS
from odoo_bootstrap.core.logger import get_logger
from odoo_bootstrap.utils.addon import parse_manifest, find_addons

logger = get_logger("sync_addons")
console = Console()

# Thư mục mặc định chứa addon của bạn
DEFAULT_MODULES_DIR = Path("/home/thanh/ownCloud/Z - Other/modules")


def _extract_zip_to_temp(zip_path: Path) -> Path:
    """Giải nén ZIP vào thư mục tạm, trả về path thư mục tạm."""
    tmp = Path(tempfile.mkdtemp(prefix="ob_addon_"))
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(tmp)
    return tmp


def _find_addon_dirs(search_dir: Path) -> list[Path]:
    """
    Tìm tất cả thư mục addon hợp lệ (có __manifest__.py) trong search_dir.
    Tìm đệ quy tối đa 3 cấp.
    """
    addons = []
    seen = set()

    def _scan(directory: Path, depth: int = 0) -> None:
        if depth > 3:
            return
        if not directory.is_dir():
            return
        # Nếu chính thư mục này là addon
        if (directory / "__manifest__.py").exists():
            if directory.name not in seen:
                addons.append(directory)
                seen.add(directory.name)
            return
        # Không phải addon, scan các sub-dir
        for child in sorted(directory.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                _scan(child, depth + 1)

    _scan(search_dir)
    return addons


def _detect_addon_version(addon_dir: Path) -> Optional[int]:
    """Đọc __manifest__.py và trả về major Odoo version."""
    manifest = parse_manifest(addon_dir)
    if manifest:
        return manifest.get_odoo_version()
    return None


def _get_project_addons_dirs(config_manager, version: Optional[int] = None) -> dict[int, list[Path]]:
    """
    Trả về dict {version: [custom_addons_dir, ...]} của tất cả project.
    Nếu version được chỉ định, chỉ trả về project của version đó.
    """
    result: dict[int, list[Path]] = {}
    for proj in config_manager.list_projects():
        if version and proj.version != version:
            continue
        v = proj.version
        if v not in result:
            result[v] = []
        result[v].append(proj.custom_addons_dir)
    return result


def run_sync_addons(
    config_manager,
    source_dir: Optional[Path] = None,
    project_name: Optional[str] = None,
    dry_run: bool = False,
) -> None:
    """
    Scan source_dir, tìm tất cả addon (ZIP + folder),
    phát hiện version, copy vào đúng custom_addons của project.
    """
    scan_dir = source_dir or DEFAULT_MODULES_DIR

    if not scan_dir.exists():
        console.print(f"[red]Thư mục không tồn tại: {scan_dir}[/red]")
        return

    console.print(f"\n[bold]Scanning:[/bold] [cyan]{scan_dir}[/cyan]")
    if dry_run:
        console.print("[yellow]DRY RUN — không copy thực tế[/yellow]")

    # Lấy danh sách project
    if project_name:
        proj = config_manager.get_project(project_name)
        if not proj:
            console.print(f"[red]Project '{project_name}' không tồn tại[/red]")
            return
        target_map = {proj.version: [proj.custom_addons_dir]}
    else:
        target_map = _get_project_addons_dirs(config_manager)

    if not target_map:
        console.print("[yellow]Chưa có project nào. Tạo project trước:[/yellow]")
        console.print("  odoo-bootstrap create-project ten_kh --version 19")
        return

    # Thống kê kết quả
    results = []  # (addon_name, detected_version, targets, action)

    # Xử lý từng item trong scan_dir
    items = sorted(scan_dir.iterdir())
    temp_dirs = []

    all_addon_dirs: list[tuple[Path, Path]] = []  # (addon_dir, source_item)

    for item in items:
        if item.name.startswith(".") or item.name.startswith("_"):
            continue

        if item.is_file() and item.suffix.lower() == ".zip":
            # Giải nén ZIP vào temp
            try:
                tmp = _extract_zip_to_temp(item)
                temp_dirs.append(tmp)
                addons = _find_addon_dirs(tmp)
                for a in addons:
                    all_addon_dirs.append((a, item))
            except Exception as e:
                console.print(f"[red]Lỗi giải nén {item.name}: {e}[/red]")

        elif item.is_dir():
            # Có thể là addon trực tiếp hoặc folder chứa nhiều addon
            addons = _find_addon_dirs(item)
            for a in addons:
                all_addon_dirs.append((a, item))

    if not all_addon_dirs:
        console.print("[yellow]Không tìm thấy addon nào trong thư mục.[/yellow]")
        return

    console.print(f"[green]Tìm thấy {len(all_addon_dirs)} addon[/green]\n")

    # Xử lý từng addon
    for addon_dir, source_item in all_addon_dirs:
        addon_name = addon_dir.name
        detected_version = _detect_addon_version(addon_dir)

        # Xác định targets
        if detected_version and detected_version in target_map:
            targets = target_map[detected_version]
            version_label = str(detected_version)
        elif detected_version is None:
            # Không có version trong manifest — copy vào tất cả project
            all_dirs = []
            for dirs in target_map.values():
                all_dirs.extend(dirs)
            targets = all_dirs
            version_label = "?"
        else:
            # Version không khớp project nào
            results.append((addon_name, str(detected_version), "—", "SKIP (không có project)"))
            continue

        # Copy vào từng target
        for target_addons_dir in targets:
            dest = target_addons_dir / addon_name

            if dest.exists():
                results.append((addon_name, version_label, target_addons_dir.parent.name, "SKIP (đã tồn tại)"))
                continue

            if not dry_run:
                target_addons_dir.mkdir(parents=True, exist_ok=True)
                shutil.copytree(str(addon_dir), str(dest))
                results.append((addon_name, version_label, target_addons_dir.parent.name, "[green]✓ Copied[/green]"))
            else:
                results.append((addon_name, version_label, target_addons_dir.parent.name, "[cyan]→ Would copy[/cyan]"))

    # Dọn temp
    for tmp in temp_dirs:
        shutil.rmtree(tmp, ignore_errors=True)

    # Hiển thị bảng kết quả
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Addon", style="bold")
    table.add_column("Version")
    table.add_column("Project")
    table.add_column("Trạng thái")

    for addon_name, ver, proj_name, action in results:
        table.add_row(addon_name, ver, proj_name, action)

    console.print(table)

    copied = sum(1 for _, _, _, a in results if "Copied" in a)
    skipped = sum(1 for _, _, _, a in results if "SKIP" in a)
    console.print(f"\n[green]✓ Copy: {copied}[/green]  [dim]Bỏ qua: {skipped}[/dim]")

    if copied > 0 and not dry_run:
        console.print("\n[yellow]Restart project để load addon mới:[/yellow]")
        for proj in config_manager.list_projects():
            console.print(f"  odoo-bootstrap restart {proj.name}")
