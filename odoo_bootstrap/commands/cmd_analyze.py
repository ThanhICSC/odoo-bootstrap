"""
odoo-bootstrap analyze: Đọc module Odoo, xuất báo cáo Markdown
để paste vào Claude/Gemini/ChatGPT phân tích.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from rich.console import Console

from odoo_bootstrap.core.logger import get_logger

logger = get_logger("analyze")
console = Console()


def _parse_manifest(addon_dir: Path) -> dict:
    """Parse __manifest__.py trả về dict."""
    for fname in ["__manifest__.py", "__openerp__.py"]:
        f = addon_dir / fname
        if f.exists():
            try:
                return ast.literal_eval(f.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {}


def _find_xml_records(xml_file: Path, tag: str) -> list[str]:
    """Tìm các record theo tag trong XML."""
    results = []
    try:
        content = xml_file.read_text(encoding="utf-8", errors="ignore")
        pattern = rf'<{tag}[^>]*\bid=["\']([^"\']+)["\']'
        results = re.findall(pattern, content)
    except Exception:
        pass
    return results


def _analyze_python_file(py_file: Path) -> dict:
    """Phân tích file Python: models, fields, methods."""
    result = {"models": [], "fields": [], "methods": [], "api_decorators": []}
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8", errors="ignore"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Tim _name va _inherit
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                if target.id == "_name":
                                    if isinstance(item.value, ast.Constant):
                                        result["models"].append(item.value.value)
                                elif target.id in ("_inherit", "_inherits"):
                                    if isinstance(item.value, ast.Constant):
                                        result["models"].append(f"inherit:{item.value.value}")
                    # Tim fields va methods
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                val = item.value
                                if isinstance(val, ast.Call):
                                    func = val.func
                                    fname = ""
                                    if isinstance(func, ast.Attribute):
                                        fname = func.attr
                                    elif isinstance(func, ast.Name):
                                        fname = func.id
                                    if fname.startswith(
                                        (
                                            "Char",
                                            "Integer",
                                            "Float",
                                            "Boolean",
                                            "Many2one",
                                            "One2many",
                                            "Many2many",
                                            "Text",
                                            "Html",
                                            "Binary",
                                            "Date",
                                            "Datetime",
                                            "Selection",
                                            "Monetary",
                                            "Json",
                                            "Properties",
                                        )
                                    ):
                                        result["fields"].append(f"{target.id}:{fname}")
                    if isinstance(item, ast.FunctionDef):
                        decorators = [
                            ast.unparse(d) if hasattr(ast, "unparse") else ""
                            for d in item.decorator_list
                        ]
                        result["methods"].append(
                            {
                                "name": item.name,
                                "decorators": [d for d in decorators if d],
                            }
                        )
    except Exception:
        pass
    return result


def run_analyze(
    addon_path: Path,
    output_file: Path | None = None,
    verbose: bool = False,
) -> str:
    """
    Phân tích 1 addon, xuất Markdown để paste vào AI.
    """
    if not addon_path.exists():
        console.print(f"[red]Không tìm thấy: {addon_path}[/red]")
        return ""

    manifest = _parse_manifest(addon_path)
    addon_name = addon_path.name
    lines = []

    # Header
    lines += [
        f"# Odoo Module Analysis: `{addon_name}`",
        "",
        "## Manifest",
        f"- **Name**: {manifest.get('name', addon_name)}",
        f"- **Version**: {manifest.get('version', '?')}",
        f"- **Author**: {manifest.get('author', '?')}",
        f"- **Category**: {manifest.get('category', '?')}",
        f"- **License**: {manifest.get('license', '?')}",
        f"- **Installable**: {manifest.get('installable', True)}",
        "",
        "### Dependencies",
    ]
    for dep in manifest.get("depends", []):
        lines.append(f"- `{dep}`")

    # Python analysis
    lines += ["", "## Models & Fields"]
    py_files = sorted(addon_path.rglob("*.py"))
    all_models = []
    all_fields = []
    all_methods = []

    for py_file in py_files:
        rel = py_file.relative_to(addon_path)
        if any(p in str(rel) for p in ["__pycache__", "test_", "_test"]):
            continue
        info = _analyze_python_file(py_file)
        if info["models"] or info["fields"]:
            lines.append(f"\n### `{rel}`")
            for m in info["models"]:
                lines.append(f"- Model: `{m}`")
                all_models.append(m)
            for f in info["fields"][:30]:  # max 30 fields per file
                lines.append(f"- Field: `{f}`")
                all_fields.append(f)
            if verbose:
                for meth in info["methods"][:20]:
                    decs = ", ".join(meth["decorators"]) if meth["decorators"] else ""
                    lines.append(f"- Method: `{meth['name']}`" + (f" ({decs})" if decs else ""))
                    all_methods.append(meth["name"])

    # XML analysis
    lines += ["", "## Views, Menus, Actions"]
    xml_files = sorted(addon_path.rglob("*.xml"))
    for xml_file in xml_files:
        rel = xml_file.relative_to(addon_path)
        views = _find_xml_records(xml_file, "record")
        acts = _find_xml_records(xml_file, "menuitem")
        if views or acts:
            lines.append(f"\n### `{rel}`")
            for v in views[:20]:
                lines.append(f"- record: `{v}`")
            for a in acts[:10]:
                lines.append(f"- menu: `{a}`")

    # Security
    lines += ["", "## Security"]
    for sec_file in addon_path.rglob("*.csv"):
        rel = sec_file.relative_to(addon_path)
        lines.append(f"- `{rel}`")
        try:
            for row in sec_file.read_text().splitlines()[1:6]:
                lines.append(f"  - {row}")
        except Exception:
            pass

    # File structure
    lines += ["", "## File Structure"]
    for item in sorted(addon_path.rglob("*")):
        rel = item.relative_to(addon_path)
        parts = rel.parts
        if any(p.startswith(".") or p == "__pycache__" for p in parts):
            continue
        if len(parts) <= 2:
            indent = "  " * (len(parts) - 1)
            icon = "📁" if item.is_dir() else "📄"
            lines.append(f"{indent}{icon} `{rel}`")

    # Summary for AI
    lines += [
        "",
        "## Summary for AI Analysis",
        f"- Total Python files: {len(py_files)}",
        f"- Total XML files: {len(xml_files)}",
        f"- Models defined/inherited: {len(all_models)}",
        f"- Fields: {len(all_fields)}",
        "",
        "**Ask AI:**",
        "- How does this module work?",
        "- What is the main business flow?",
        "- Which methods should I override to customize?",
        "- What are the dependencies and why?",
    ]

    report = "\n".join(lines)

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(report, encoding="utf-8")
        console.print(f"[green]✓ Báo cáo: {output_file}[/green]")
        console.print("[dim]  Paste vào Claude/Gemini để phân tích[/dim]")
    else:
        console.print(report)

    return report


def run_analyze_project(project_name: str, config_manager) -> None:
    """Phân tích toàn bộ custom_addons của project."""
    proj = config_manager.get_project(project_name)
    if not proj:
        console.print(f"[red]Project '{project_name}' không tồn tại[/red]")
        return

    addons_dir = proj.custom_addons_dir
    if not addons_dir.exists():
        console.print(f"[yellow]custom_addons trống: {addons_dir}[/yellow]")
        return

    addons = [d for d in addons_dir.iterdir() if d.is_dir() and (d / "__manifest__.py").exists()]
    if not addons:
        console.print("[yellow]Không tìm thấy addon nào[/yellow]")
        return

    console.print(f"[bold]Analyzing {len(addons)} addons in {project_name}...[/bold]")

    reports_dir = proj.project_dir / "reports"
    reports_dir.mkdir(exist_ok=True)

    index_lines = [f"# Project Report: {project_name}", "", "## Addons"]
    for addon in sorted(addons):
        out = reports_dir / f"{addon.name}.md"
        run_analyze(addon, output_file=out)
        index_lines.append(f"- [{addon.name}]({addon.name}.md)")

    index_file = reports_dir / "index.md"
    index_file.write_text("\n".join(index_lines), encoding="utf-8")
    console.print(f"\n[green]✓ Reports: {reports_dir}[/green]")
    console.print("[dim]Paste từng file .md vào Claude để phân tích[/dim]")
