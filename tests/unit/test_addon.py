"""Unit tests for addon utilities."""

from pathlib import Path

import pytest

from odoo_bootstrap.utils.addon import (
    parse_manifest,
    find_addons,
    check_addons_compatibility,
    collect_python_dependencies,
    AddonManifest,
)


def _make_addon(tmp_path: Path, name: str, manifest_content: str) -> Path:
    addon_dir = tmp_path / name
    addon_dir.mkdir()
    (addon_dir / "__manifest__.py").write_text(manifest_content, encoding="utf-8")
    (addon_dir / "__init__.py").write_text("", encoding="utf-8")
    return addon_dir


def test_parse_manifest_valid(tmp_path):
    content = """
{
    'name': 'Test Addon',
    'version': '19.0.1.0.0',
    'depends': ['base'],
    'installable': True,
}
"""
    addon_dir = _make_addon(tmp_path, "test_addon", content)
    manifest = parse_manifest(addon_dir)
    assert manifest is not None
    assert manifest.name == "Test Addon"
    assert manifest.version == "19.0.1.0.0"
    assert manifest.depends == ["base"]


def test_parse_manifest_missing_file(tmp_path):
    empty_dir = tmp_path / "no_manifest"
    empty_dir.mkdir()
    result = parse_manifest(empty_dir)
    assert result is None


def test_get_odoo_version_from_manifest(tmp_path):
    content = "{'name': 'X', 'version': '17.0.2.0.0'}"
    addon_dir = _make_addon(tmp_path, "x", content)
    manifest = parse_manifest(addon_dir)
    assert manifest.get_odoo_version() == 17


def test_is_compatible_with(tmp_path):
    content = "{'name': 'X', 'version': '19.0.1.0.0'}"
    addon_dir = _make_addon(tmp_path, "x", content)
    manifest = parse_manifest(addon_dir)
    assert manifest.is_compatible_with(19) is True
    assert manifest.is_compatible_with(18) is False


def test_find_addons_multiple(tmp_path):
    for i in range(3):
        _make_addon(tmp_path, f"addon_{i}", f"{{'name': 'Addon {i}', 'version': '19.0.1.0.0'}}")
    addons = find_addons(tmp_path)
    assert len(addons) == 3


def test_check_addons_compatibility(tmp_path):
    _make_addon(tmp_path, "ok_addon", "{'name': 'OK', 'version': '19.0.1.0.0'}")
    _make_addon(tmp_path, "bad_addon", "{'name': 'Bad', 'version': '17.0.1.0.0'}")
    results = check_addons_compatibility(tmp_path, 19)
    names = {name: compat for name, compat, _ in results}
    assert names["OK"] is True
    assert names["Bad"] is False


def test_collect_python_dependencies(tmp_path):
    content = "{'name': 'X', 'external_dependencies': {'python': ['boto3', 'requests']}}"
    _make_addon(tmp_path, "x", content)
    deps = collect_python_dependencies(tmp_path)
    assert "boto3" in deps
    assert "requests" in deps
