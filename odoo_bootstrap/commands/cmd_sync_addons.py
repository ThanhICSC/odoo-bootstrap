"""
odoo-bootstrap sync-addons: Tự động scan ZIP/folder addon,
phát hiện version, copy vào đúng project, build test khi có lỗi báo ngay.

Hỗ trợ cấu trúc thư mục:
  modules/
  ├── 17/          ← tất cả addon trong này → Odoo 17
  ├── 18/          ← tất cả addon trong này → Odoo 18
  ├── 19/          ← tất cả addon trong này → Odoo 19
  ├── my_addon/    ← tự đoán version
  └── module.zip   ← giải nén + tự đoán version
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from rich.console import Console
from rich.table import Table

from odoo_bootstrap.core.constants import SUPPORTED_VERSIONS, WORKSPACE_ROOT
from odoo_bootstrap.core.logger import get_logger
from odoo_bootstrap.utils.addon import parse_manifest

logger = get_logger("sync_addons")
console = Console()

DEFAULT_MODULES_DIR = Path("/home/thanh/ownCloud/Z - Other/modules")


# ── Extract / Find ────────────────────────────────────────────────────────────


def _extract_zip_to_temp(zip_path: Path) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="ob_addon_"))
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(tmp)
    return tmp


def _find_addon_dirs(search_dir: Path, max_depth: int = 3) -> list[Path]:
    """Tìm tất cả addon hợp lệ trong thư mục, tối đa max_depth cấp."""
    addons: list[Path] = []
    seen: set[str] = set()

    def _scan(directory: Path, depth: int = 0) -> None:
        if depth > max_depth or not directory.is_dir():
            return
        has_manifest = (directory / "__manifest__.py").exists() or (
            directory / "__openerp__.py"
        ).exists()
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


# ── Core index ────────────────────────────────────────────────────────────────


def _build_core_index(versions: list[int]) -> dict[str, list[tuple[int, str]]]:
    """Build {addon_name: [(version, 'community'|'enterprise')]}."""
    index: dict[str, list[tuple[int, str]]] = {}
    for v in versions:
        ver_dir = WORKSPACE_ROOT / "versions" / str(v)
        for src in [ver_dir / "source" / "addons", ver_dir / "source" / "odoo" / "addons"]:
            if src.exists():
                for item in src.iterdir():
                    if item.is_dir() and (item / "__manifest__.py").exists():
                        index.setdefault(item.name, []).append((v, "community"))
        ent = ver_dir / "enterprise"
        if ent.exists():
            for item in ent.iterdir():
                if item.is_dir() and (item / "__manifest__.py").exists():
                    index.setdefault(item.name, []).append((v, "enterprise"))
    return index


# ── Version detection ─────────────────────────────────────────────────────────


def _from_manifest(addon_dir: Path) -> int | None:
    manifest = parse_manifest(addon_dir)
    if manifest:
        v = manifest.get_odoo_version()
        if v and v in SUPPORTED_VERSIONS:
            return v
    return None


def _from_python_syntax(addon_dir: Path) -> int | None:
    scores = {17: 0, 18: 0, 19: 0}
    for py_file in list(addon_dir.rglob("*.py"))[:30]:
        try:
            src = py_file.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"^\s*match\s+\w+", src, re.MULTILINE):
                scores[17] += 3
            if "fields.Json(" in src:
                scores[17] += 2
            if "precompute=True" in src or "precompute = True" in src:
                scores[17] += 2
            if "api.model_create_multi" in src:
                scores[17] += 1
            # Odoo 18+ patterns
            if "BaseModel" in src and "model_fields" in src:
                scores[18] += 2
        except Exception:
            continue
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] >= 2 else None


def _from_xml_patterns(addon_dir: Path) -> int | None:
    scores = {17: 0, 18: 0, 19: 0, 16: 0}
    for xml_file in list(addon_dir.rglob("*.xml"))[:20]:
        try:
            src = xml_file.read_text(encoding="utf-8", errors="ignore")
            if "<chatter/>" in src or "<chatter />" in src:
                scores[17] += 3
            if "t-component" in src:
                scores[17] += 2
            if 'class="oe_chatter"' in src:
                scores[16] += 3
            if "groups_by=" in src:
                scores[18] += 2
            if "is_published" in src:
                scores[17] += 1
        except Exception:
            continue
    # Chỉ xét supported versions
    relevant = {v: s for v, s in scores.items() if v in SUPPORTED_VERSIONS}
    if not relevant:
        return None
    best = max(relevant, key=lambda k: relevant[k])
    return best if relevant[best] >= 2 else None


def _from_dependencies(addon_dir: Path) -> int | None:
    manifest = parse_manifest(addon_dir)
    if not manifest:
        return None
    depends = set(manifest.depends)
    v17_modules = {"discuss", "spreadsheet", "web_grid", "knowledge", "sign"}
    if depends & v17_modules:
        return 17
    return None


def _guess_version(
    addon_dir: Path, core_index: dict, forced_version: int | None = None
) -> tuple[int | None, str]:
    """Trả về (version, method)."""
    if forced_version:
        return forced_version, "folder-name"

    v = _from_manifest(addon_dir)
    if v:
        return v, "manifest"

    matches = core_index.get(addon_dir.name, [])
    if len(matches) == 1:
        return matches[0][0], "core-match"

    v = _from_python_syntax(addon_dir)
    if v:
        return v, "python-syntax"

    v = _from_xml_patterns(addon_dir)
    if v:
        return v, "xml-pattern"

    v = _from_dependencies(addon_dir)
    if v:
        return v, "dependencies"

    if matches:
        return max(mv for mv, _ in matches), "core-latest"

    return None, "unknown"


# ── Build test ────────────────────────────────────────────────────────────────


def _build_test_addon(addon_dir: Path, version: int) -> tuple[bool, str]:
    """
    Thử build/validate addon:
    1. Parse __manifest__.py
    2. Import tất cả __init__.py bằng Python syntax check
    3. Validate XML với xmllint nếu có
    Trả về (passed, error_message).
    """
    errors = []

    # 1. Parse manifest
    manifest_file = addon_dir / "__manifest__.py"
    if manifest_file.exists():
        try:
            import ast

            ast.literal_eval(manifest_file.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"__manifest__.py parse error: {e}")

    # 2. Python syntax check tất cả .py files
    py_files = list(addon_dir.rglob("*.py"))
    for py_file in py_files:
        result = subprocess.run(
            ["python3", "-m", "py_compile", str(py_file)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            rel = py_file.relative_to(addon_dir)
            errors.append(f"Syntax error {rel}: {result.stderr.strip()}")

    # 3. XML validation
    xml_files = list(addon_dir.rglob("*.xml"))
    if shutil.which("xmllint"):
        for xml_file in xml_files[:10]:  # giới hạn 10 file
            result = subprocess.run(
                ["xmllint", "--noout", str(xml_file)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                rel = xml_file.relative_to(addon_dir)
                errors.append(f"XML error {rel}: {result.stderr.strip()[:100]}")

    if errors:
        return False, "\n".join(errors[:3])  # tối đa 3 lỗi đầu
    return True, ""


# ── Main ──────────────────────────────────────────────────────────────────────


def run_sync_addons(
    config_manager,
    source_dir: Path | None = None,
    project_name: str | None = None,
    dry_run: bool = False,
    remove_core_duplicates: bool = True,
    build_test: bool = True,
) -> None:
    scan_dir = source_dir or DEFAULT_MODULES_DIR

    if not scan_dir.exists():
        console.print(f"[red]Thư mục không tồn tại: {scan_dir}[/red]")
        return

    console.print(f"\n[bold]Scanning:[/bold] [cyan]{scan_dir}[/cyan]")
    if dry_run:
        console.print("[yellow]DRY RUN — không thay đổi thực tế[/yellow]")

    # Build core index
    console.print("[dim]Đang build index Odoo core...[/dim]")
    core_index = _build_core_index(SUPPORTED_VERSIONS)
    console.print(f"[dim]Core index: {len(core_index)} modules[/dim]\n")

    # Target map
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

    if not target_map:
        console.print("[yellow]Chưa có project nào.[/yellow]")
        return

    # ── Scan source items ─────────────────────────────────────────────────────
    temp_dirs: list[Path] = []
    # (addon_dir, source_item, forced_version)
    all_addons: list[tuple[Path, Path, int | None]] = []

    for item in sorted(scan_dir.iterdir()):
        if item.name.startswith(".") or item.name.startswith("_"):
            continue

        # Folder có tên là version number: 17/ 18/ 19/
        if item.is_dir() and item.name.isdigit() and int(item.name) in SUPPORTED_VERSIONS:
            forced_ver = int(item.name)
            console.print(f"[green]Folder /{item.name}/ → ép version Odoo {forced_ver}[/green]")
            # Scan addon trực tiếp bên trong
            for subitem in sorted(item.iterdir()):
                if subitem.is_file() and subitem.suffix.lower() == ".zip":
                    try:
                        tmp = _extract_zip_to_temp(subitem)
                        temp_dirs.append(tmp)
                        for a in _find_addon_dirs(tmp):
                            all_addons.append((a, subitem, forced_ver))
                    except Exception as e:
                        console.print(f"[red]Lỗi giải nén {subitem.name}: {e}[/red]")
                elif subitem.is_dir():
                    for a in _find_addon_dirs(subitem):
                        all_addons.append((a, subitem, forced_ver))
            continue

        # File ZIP bình thường
        if item.is_file() and item.suffix.lower() == ".zip":
            try:
                tmp = _extract_zip_to_temp(item)
                temp_dirs.append(tmp)
                for a in _find_addon_dirs(tmp):
                    all_addons.append((a, item, None))
            except Exception as e:
                console.print(f"[red]Lỗi giải nén {item.name}: {e}[/red]")

        # Folder addon thường
        elif item.is_dir():
            for a in _find_addon_dirs(item):
                all_addons.append((a, item, None))

    if not all_addons:
        console.print("[yellow]Không tìm thấy addon nào.[/yellow]")
        return

    console.print(f"Tìm thấy [bold green]{len(all_addons)}[/bold green] addon\n")

    # ── Xử lý từng addon ─────────────────────────────────────────────────────
    table = Table(show_header=True, header_style="bold cyan", show_lines=False)
    table.add_column("Addon", style="bold", min_width=22)
    table.add_column("Ver", width=5)
    table.add_column("Cách đoán", width=14)
    table.add_column("Build", width=8)
    table.add_column("Project", width=14)
    table.add_column("Kết quả")

    stats = {"copied": 0, "skipped": 0, "core_dup": 0, "no_target": 0, "build_fail": 0}
    items_to_delete: set[Path] = set()

    for addon_dir, source_item, forced_version in all_addons:
        addon_name = addon_dir.name
        detected_version, method = _guess_version(addon_dir, core_index, forced_version)

        # Kiểm tra trùng core (chỉ khi không có forced version)
        if not forced_version:
            core_matches = core_index.get(addon_name, [])
            if core_matches:
                core_desc = ", ".join(f"v{v} {t}" for v, t in core_matches)
                table.add_row(
                    addon_name,
                    str(detected_version) if detected_version else "?",
                    method,
                    "—",
                    "—",
                    f"[red]✗ Trùng core ({core_desc})[/red]",
                )
                stats["core_dup"] += 1
                items_to_delete.add(source_item)
                continue

        # Không có target
        if not detected_version or detected_version not in target_map:
            table.add_row(
                addon_name,
                str(detected_version) if detected_version else "?",
                method,
                "—",
                "—",
                "[yellow]⚠ Không có project phù hợp[/yellow]",
            )
            stats["no_target"] += 1
            continue

        # Build test
        build_ok = True
        build_msg = "[green]✓[/green]"
        if build_test and not dry_run:
            build_ok, build_error = _build_test_addon(addon_dir, detected_version)
            if not build_ok:
                build_msg = "[red]✗ FAIL[/red]"
                stats["build_fail"] += 1
                # Hiển thị lỗi rõ ràng
                table.add_row(
                    addon_name,
                    str(detected_version),
                    method,
                    build_msg,
                    "—",
                    "[red]Build lỗi — bỏ qua[/red]",
                )
                # In chi tiết lỗi bên dưới
                console.print(f"\n  [red bold]BUILD FAIL:[/red bold] {addon_name}")
                for line in build_error.split("\n"):
                    if line.strip():
                        console.print(f"    [red]{line}[/red]")
                continue

        # Copy
        targets = target_map[detected_version]
        for target_addons_dir in targets:
            dest = target_addons_dir / addon_name
            proj_label = target_addons_dir.parent.name

            if dest.exists():
                table.add_row(
                    addon_name,
                    str(detected_version),
                    method,
                    build_msg,
                    proj_label,
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
                    build_msg,
                    proj_label,
                    "[green]✓ Copied[/green]",
                )
            else:
                table.add_row(
                    addon_name,
                    str(detected_version),
                    method,
                    "—",
                    proj_label,
                    "[cyan]→ Sẽ copy[/cyan]",
                )
            stats["copied"] += 1

    # Dọn temp
    for tmp in temp_dirs:
        shutil.rmtree(tmp, ignore_errors=True)

    console.print(table)

    # Xóa trùng core
    if items_to_delete and remove_core_duplicates and not dry_run:
        console.print(f"\n[yellow]Xóa {len(items_to_delete)} item trùng Odoo core:[/yellow]")
        for item in items_to_delete:
            if item.exists():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                console.print(f"  [red]✗ Đã xóa: {item.name}[/red]")
    elif items_to_delete and dry_run:
        console.print(f"\n[dim]Sẽ xóa {len(items_to_delete)} item trùng core[/dim]")

    # Tổng kết
    console.print(
        f"\n[bold]Tổng kết:[/bold]\n"
        f"  [green]✓ Copied:              {stats['copied']}[/green]\n"
        f"  [dim]  Skip (đã có):        {stats['skipped']}[/dim]\n"
        f"  [red]✗ Trùng core (đã xóa): {stats['core_dup']}[/red]\n"
        f"  [red]✗ Build fail:           {stats['build_fail']}[/red]\n"
        f"  [yellow]⚠ Không có project:   {stats['no_target']}[/yellow]"
    )

    if stats["copied"] > 0 and not dry_run:
        console.print("\n[yellow]Restart project để load addon mới:[/yellow]")
        for proj in config_manager.list_projects():
            console.print(f"  odoo-bootstrap restart {proj.name}")

    if stats["build_fail"] > 0:
        console.print(
            f"\n[red bold]⚠ {stats['build_fail']} addon bị lỗi build — "
            "kiểm tra lại trước khi dùng[/red bold]"
        )
