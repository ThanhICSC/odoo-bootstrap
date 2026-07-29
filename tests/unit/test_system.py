"""Unit tests for system utilities."""

from pathlib import Path

from odoo_bootstrap.utils.system import (
    check_command_exists,
    ensure_directory,
    get_cpu_count,
    get_disk_free_gb,
    get_python_version,
    get_total_ram_gb,
    is_port_in_use,
)


def test_check_command_exists_python():
    assert check_command_exists("python3") or check_command_exists("python")


def test_check_command_missing():
    assert check_command_exists("nonexistent_cmd_xyz_123") is False


def test_get_disk_free_gb_returns_positive():
    free = get_disk_free_gb(Path.home())
    assert free > 0


def test_get_total_ram_gb_returns_positive():
    ram = get_total_ram_gb()
    assert ram > 0


def test_get_cpu_count_positive():
    assert get_cpu_count() >= 1


def test_get_python_version_format():
    v = get_python_version()
    parts = v.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_port_not_in_use_high_port():
    # Port 19999 is very unlikely to be in use
    assert is_port_in_use(19999) is False


def test_ensure_directory_creates(tmp_path):
    target = tmp_path / "a" / "b" / "c"
    ensure_directory(target)
    assert target.is_dir()


def test_ensure_directory_idempotent(tmp_path):
    target = tmp_path / "existing"
    ensure_directory(target)
    ensure_directory(target)  # Should not raise
    assert target.is_dir()
