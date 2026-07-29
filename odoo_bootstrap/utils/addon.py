"""
Odoo addon utilities: parse __manifest__.py, check compatibility.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional

from odoo_bootstrap.core.logger import get_logger

logger = get_logger("addon")


class AddonManifest:
    """Parsed content of an Odoo __manifest__.py file."""

    def __init__(self, path: Path, data: dict) -> None:
        self.path = path
        self.addon_dir = path.parent
        self.name = data.get("name", path.parent.name)
        self.version = data.get("version", "")
        self.depends = data.get("depends", [])
        self.installable = data.get("installable", True)
        self.author = data.get("author", "")
        self.license = data.get("license", "")
        self.category = data.get("category", "")
        self.external_dependencies = data.get("external_dependencies", {})
        self.raw = data

    def get_odoo_version(self) -> Optional[int]:
        """Extract major Odoo version from manifest version string (e.g. '19.0.1.0.0' → 19)."""
        if self.version:
            parts = self.version.split(".")
            if parts:
                try:
                    return int(parts[0])
                except ValueError:
                    pass
        return None

    def is_compatible_with(self, odoo_version: int) -> bool:
        """Return True if this addon is compatible with the given Odoo version."""
        addon_version = self.get_odoo_version()
        if addon_version is None:
            return True  # No version declared, assume compatible
        return addon_version == odoo_version

    def get_python_dependencies(self) -> list[str]:
        return self.external_dependencies.get("python", [])

    def get_bin_dependencies(self) -> list[str]:
        return self.external_dependencies.get("bin", [])


def parse_manifest(addon_dir: Path) -> Optional[AddonManifest]:
    """Parse __manifest__.py from an addon directory."""
    manifest_path = addon_dir / "__manifest__.py"
    if not manifest_path.exists():
        return None
    try:
        source = manifest_path.read_text(encoding="utf-8")
        data = ast.literal_eval(source)
        if not isinstance(data, dict):
            return None
        return AddonManifest(manifest_path, data)
    except Exception as e:
        logger.warning(f"Failed to parse {manifest_path}: {e}")
        return None


def find_addons(directory: Path) -> list[AddonManifest]:
    """Find all valid Odoo addons in a directory."""
    addons = []
    if not directory.is_dir():
        return addons
    for item in directory.iterdir():
        if item.is_dir():
            manifest = parse_manifest(item)
            if manifest:
                addons.append(manifest)
    return addons


def check_addons_compatibility(
    addons_dir: Path,
    odoo_version: int,
) -> list[tuple[str, bool, Optional[int]]]:
    """
    Check all addons in a directory for version compatibility.
    Returns list of (name, compatible, declared_version).
    """
    addons = find_addons(addons_dir)
    results = []
    for addon in addons:
        declared = addon.get_odoo_version()
        compatible = addon.is_compatible_with(odoo_version)
        results.append((addon.name, compatible, declared))
    return results


def find_requirements_files(custom_addons_dir: Path) -> list[Path]:
    """Find all requirements.txt files inside an addons directory."""
    if not custom_addons_dir.is_dir():
        return []
    return list(custom_addons_dir.rglob("requirements.txt"))


def collect_python_dependencies(addons_dir: Path) -> list[str]:
    """Collect all external Python dependencies from addons in a directory."""
    deps: set[str] = set()
    for addon in find_addons(addons_dir):
        deps.update(addon.get_python_dependencies())
    return sorted(deps)
