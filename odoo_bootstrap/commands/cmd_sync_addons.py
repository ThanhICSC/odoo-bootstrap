"""
odoo-bootstrap sync-addons: Tự động scan ZIP/folder addon,
phát hiện version Odoo, copy vào đúng project.
- Kiểm tra trùng với Odoo core/enterprise → xóa khỏi source
- Đoán version thông minh qua nhiều phương pháp
"""

from __future__ import annotations

import ast
import re
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from odoo_bootstrap.core.constants import WORKSPACE_ROOT, SUPPORTED_VERSIONS
from odoo_bootstrap.core.logger import get_logger
from odoo_bootstrap.utils.addon import parse_manifest

logger = get_logger("sync_addons")
console = Console()

DEFAULT_MODULES_DIR = Path("/home/thanh/ownCloud/Z - Other/modules")


# ── Tìm addon dirs ────────────────────────────────────────────────────────────

def _extract_zip_to_temp(zip_path: Path) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="ob_addon_"))
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(tmp)
    return tmp


def _find_addon_dirs(search_dir: Path) -> list[Path]:
    """Tìm tất cả addon hợp lệ (có __manifest__.py hoặc __openerp__.py) tối đa 3 cấp."""
    addons = []
    seen = set()

    def _scan(directory: Path, depth: int = 0) -> None:
        if depth > 3 or not directory.is_dir():
            return
        has_manifest = (
            (directory / "__manifest__.py").exists()
            or (directory / "__openerp__.py").exists()
        )
        has_init = (directory / "__init__.py").exists()
        if has_manifest and has_init:
            if directory.name not in seen:
                addons.append(directory)
                seen.add(directory.name)
            return
        for child in sorted(directory.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                _scan(child, depth + 1)

    _scan(search_dir)
    return addons


# ── Kiểm tra trùng với Odoo core ─────────────────────────────────────────────

def _build_core_addon_index(versions: list[int]) -> dict[str, list[tuple[int, str]]]:
    """
    Build index: {addon_name: [(version, 'community'|'enterprise'), ...]}
    từ tất cả Odoo source đã clone.
    """
    index: dict[str, list[tuple[int, str]]] = {}

    for v in versions:
        ver_dir = WORKSPACE_ROOT / "versions" / str(v)

        # Community
        for source_root in [
            ver_dir / "source" / "addons",
            ver_dir / "source" / "odoo" / "addons",
        ]:
            if source_root.exists():
                for item in source_root.iterdir():
                    if item.is_dir() and (item / "__manifest__.py").exists():
                        index.setdefault(item.name, []).append((v, "community"))

        # Enterprise
        ent_dir = ver_dir / "enterprise"
        if ent_dir.exists():
            for item in ent_dir.iterdir():
                if item.is_dir() and (item / "__manifest__.py").exists():
                    index.setdefault(item.name, []).append((v, "enterprise"))

    return index


def _is_in_core(addon_name: str, core_index: dict) -> list[tuple[int, str]]:
    """Trả về list [(version, type)] nếu addon có trong Odoo core."""
    return core_index.get(addon_name, [])


# ── Đoán version thông minh ───────────────────────────────────────────────────

def _guess_version_from_manifest(addon_dir: Path) -> Optional[int]:
    """Đọc version field trong __manifest__.py."""
    manifest = parse_manifest(addon_dir)
    if manifest:
        v = manifest.get_odoo_version()
        if v and v in SUPPORTED_VERSIONS:
            return v
    return None


def _guess_version_from_python_syntax(addon_dir: Path) -> Optional[int]:
    """
    Phân tích syntax Python trong addon:
    - Python 3.10+ match/case → Odoo 17+
    - f-string walrus operator := → Odoo 16+
    - Kiểm tra các API pattern đặc trưng từng version
    """
    py_files = list(addon_dir.rglob("*.py"))[:20]  # Giới hạn 20 file

    has_match_case = False
    has_walrus = False
    api_patterns: dict[str, int] = {}

    for py_file in py_files:
        try:
            source = py_file.read_text(encoding="utf-8", errors="ignore")

            # match/case (Python 3.10+, Odoo 17+)
            if re.search(r"^\s*match\s+\w+", source, re.MULTILINE):
                has_match_case = True

            # Walrus operator (Python 3.8+, Odoo 16+)
            if ":=" in source:
                has_walrus = True

            # API patterns đặc trưng
            # Odoo 17+: _inherit as list, new field types
            if re.search(r"fields\.Json\(", source):
                api_patterns["17+"] = api_patterns.get("17+", 0) + 1
            if re.search(r"api\.model_create_multi", source):
                api_patterns["16+"] = api_patterns.get("16+", 0) + 1

            # Odoo 17 specific
            if re.search(r"precompute\s*=\s*True", source):
                api_patterns["17+"] = api_patterns.get("17+", 0) + 1

            # Odoo 18/19: new ORM patterns
            if re.search(r"@api\.depends_context", source):
                api_patterns["14+"] = api_patterns.get("14+", 0) + 1

        except Exception:
            continue

    if has_match_case:
        return 17  # Minimum 17
    if api_patterns.get("17+", 0) >= 2:
        return 17

    return None


def _guess_version_from_xml(addon_dir: Path) -> Optional[int]:
    """
    Phân tích XML views để đoán version:
    - Odoo 17+: <chatter/> shorthand, owl components
    - Odoo 18+: new kanban syntax
    - Odoo 16-: old chatter <div class="oe_chatter">
    """
    xml_files = list(addon_dir.rglob("*.xml"))[:15]
    scores: dict[int, int] = {17: 0, 18: 0, 19: 0, 16: 0}

    for xml_file in xml_files:
        try:
            content = xml_file.read_text(encoding="utf-8", errors="ignore")

            # Odoo 17+: shorthand chatter
            if "<chatter/>" in content or "<chatter />" in content:
                scores[17] += 2
            # Odoo 17+: owl component syntax
            if "t-component" in content or "owl" in content.lower():
                scores[17] += 1
            # Odoo 18+: new list view syntax
            if 'groups_by="' in content:
                scores[18] += 1
            # Odoo 16 và cũ hơn: oe_chatter div
            if 'class="oe_chatter"' in content:
                scores[16] += 2
            # Odoo 17+: website_published field mới
            if "is_published" in content:
                scores[17] += 1

        except Exception:
            continue

    # Chọn version có score cao nhất
    best = max(scores, key=lambda k: scores[k])
    if scores[best] > 0:
        # Map về supported versions
        if best >= 19:
            return 19
        elif best == 18:
            return 18
        elif best == 17:
            return 17
    return None


def _guess_version_from_dependencies(addon_dir: Path) -> Optional[int]:
    """
    Đoán version dựa vào depends trong manifest:
    - Depend vào module chỉ có từ version nào đó
    """
    manifest = parse_manifest(addon_dir)
    if not manifest:
        return None

    depends = set(manifest.depends)

    # Module chỉ có từ Odoo 17+
    v17_only = {"discuss", "spreadsheet", "web_grid"}
    # Module chỉ có từ Odoo 16+
    v16_only = {"payment", "website_sale_collect"}

    if depends & v17_only:
        return 17
    return None


def _guess_version_smart(addon_dir: Path, core_index: dict) -> tuple[Optional[int], str]:
    """
    Tổng hợp tất cả phương pháp đoán version.
    Trả về (version, method_used).
    """
    # 1. Manifest version field (chắc chắn nhất)
    v = _guess_version_from_manifest(addon_dir)
    if v:
        return v, "manifest"

    # 2. Tên addon trùng với core của 1 version cụ thể
    core_matches = _is_in_core(addon_dir.name, core_index)
    if len(core_matches) == 1:
        return core_matches[0][0], "core-match"
    elif len(core_matches) > 1:
        # Trùng nhiều version — thử phương pháp khác để phân biệt
        versions_in_core = [v for v, _ in core_matches]
        # fallthrough to other methods

    # 3. Python syntax
    v = _guess_version_from_python_syntax(addon_dir)
    if v:
        return v, "python-syntax"

    # 4. XML view patterns
    v = _guess_version_from_xml(addon_dir)
    if v:
        return v, "xml-pattern"

    # 5. Dependencies
    v = _guess_version_from_dependencies(addon_dir)
    if v:
        return v, "dependencies"

    # 6. Nếu trùng nhiều version trong core, lấy version mới nhất
    if core_matches:
        return max(v for v, _ in core_matches), "core-latest"

    return None, "unknown"


# ── Main sync logic ───────────────────────────────────────────────────────────

def run_sync_addons(
    config_manager,
    source_dir: Optional[Path] = None,
    project_name: Optional[str] = None,
    dry_run: bool = False,
    remove_core_duplicates: bool = True,
) -> None:
    scan_dir = source_dir or DEFAULT_MODULES_DIR

    if not scan_dir.exists():
        console.print(f"[red]Thư mục không tồn tại: {scan_dir}[/red]")
        return

    console.print(f"\n[bold]Scanning:[/bold] [cyan]{scan_dir}[/cyan]")
    if dry_run:
        console.print("[yellow]DRY RUN — không thay đổi thực tế[/yellow]\n")

    # Build core index
    console.print("[dim]Đang build index Odoo core...[/dim]")
    core_index = _build_core_addon_index(SUPPORTED_VERSIONS)
    console.print(f"[dim]Core index: {len(core_index)} modules[/dim]\n")

    # Target projects
    if project_name:
        proj = config_manager.get_project(project_name)
        if not proj:
            console.print(f"[red]Project '{project_name}' không tồn tại[/red]")
            return
        target_map: dict[int, list[Path]] = {proj.version: [proj.custom_addons_dir]}
    else:
        target_map = {}
        for proj in config_manager.list_projects():
            target_map.setdefault(proj.version, []).append(proj.custom_addons_dir)

    # Scan source items
    temp_dirs = []
    # (addon_dir, source_item_path, is_from_zip)
    all_addon_dirs: list[tuple[Path, Path, bool]] = []

    for item in sorted(scan_dir.iterdir()):
        if item.name.startswith(".") or item.name.startswith("_"):
            continue

        if item.is_file() and item.suffix.lower() == ".zip":
            try:
                tmp = _extract_zip_to_temp(item)
                temp_dirs.append(tmp)
                for a in _find_addon_dirs(tmp):
                    all_addon_dirs.append((a, item, True))
            except Exception as e:
                console.print(f"[red]Lỗi giải nén {item.name}: {e}[/red]")

        elif item.is_dir():
            found = _find_addon_dirs(item)
            if found:
                for a in found:
                    all_addon_dirs.append((a, item, False))

    if not all_addon_dirs:
        console.print("[yellow]Không tìm thấy addon nào.[/yellow]")
        return

    console.print(f"Tìm thấy [green]{len(all_addon_dirs)}[/green] addon\n")

    # Bảng kết quả
    table = Table(show_header=True, header_style="bold cyan", show_lines=False)
    table.add_column("Addon", style="bold", min_width=25)
    table.add_column("Version", width=8)
    table.add_column("Đoán bằng", width=14)
    table.add_column("Project", width=16)
    table.add_column("Trạng thái")

    stats = {"copied": 0, "skipped": 0, "duplicate_core": 0, "no_target": 0}

    # Track source items cần xóa (trùng với core)
    items_to_delete: set[Path] = set()

    for addon_dir, source_item, is_from_zip in all_addon_dirs:
        addon_name = addon_dir.name

        # Đoán version
        detected_version, method = _guess_version_smart(addon_dir, core_index)

        # Kiểm tra trùng với Odoo core
        core_matches = _is_in_core(addon_name, core_index)
        if core_matches:
            core_desc = ", ".join(f"v{v} {t}" for v, t in core_matches)
            table.add_row(
                addon_name,
                str(detected_version) if detected_version else "?",
                method,
                "—",
                f"[red]✗ Trùng core ({core_desc})[/red]",
            )
            stats["duplicate_core"] += 1
            # Đánh dấu để xóa source gốc
            items_to_delete.add(source_item)
            continue

        # Không có target project cho version này
        if not detected_version or detected_version not in target_map:
            ver_str = str(detected_version) if detected_version else "?"
            table.add_row(
                addon_name, ver_str, method, "—",
                "[yellow]⚠ Không có project phù hợp[/yellow]",
            )
            stats["no_target"] += 1
            continue

        # Copy vào từng project target
        targets = target_map[detected_version]
        for target_addons_dir in targets:
            dest = target_addons_dir / addon_name
            proj_name_label = target_addons_dir.parent.name

            if dest.exists():
                table.add_row(
                    addon_name,
                    str(detected_version),
                    method,
                    proj_name_label,
                    "[dim]SKIP (đã có)[/dim]",
                )
                stats["skipped"] += 1
                continue

            if not dry_run:
                target_addons_dir.mkdir(parents=True, exist_ok=True)
                shutil.copytree(str(addon_dir), str(dest))
                table.add_row(
                    addon_name,
                    str(detected_version),
                    method,
                    proj_name_label,
                    "[green]✓ Copied[/green]",
                )
            else:
                table.add_row(
                    addon_name,
                    str(detected_version),
                    method,
                    proj_name_label,
                    f"[cyan]→ Sẽ copy vào {proj_name_label}[/cyan]",
                )
            stats["copied"] += 1

    # Dọn temp dirs
    for tmp in temp_dirs:
        shutil.rmtree(tmp, ignore_errors=True)

    # Hiển thị bảng
    console.print(table)

    # Xóa file/folder trùng với core
    if items_to_delete and remove_core_duplicates and not dry_run:
        console.print(f"\n[yellow]Xóa {len(items_to_delete)} item trùng với Odoo core:[/yellow]")
        for item in items_to_delete:
            if item.exists():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                console.print(f"  [red]✗ Đã xóa: {item.name}[/red]")
    elif items_to_delete and dry_run:
        console.print(f"\n[dim]Sẽ xóa {len(items_to_delete)} item trùng core (dry-run)[/dim]")

    # Tổng kết
    console.print(f"""
[bold]Tổng kết:[/bold]
  [green]✓ Copied:          {stats['copied']}[/green]
  [dim]  Bỏ qua (đã có):  {stats['skipped']}[/dim]
  [red]✗ Trùng core:      {stats['duplicate_core']} (đã xóa khỏi source)[/red]
  [yellow]⚠ Không có project: {stats['no_target']}[/yellow]
""")

    if stats["copied"] > 0 and not dry_run:
        console.print("[yellow]Restart project để load addon mới:[/yellow]")
        for proj in config_manager.list_projects():
            console.print(f"  odoo-bootstrap restart {proj.name}")
