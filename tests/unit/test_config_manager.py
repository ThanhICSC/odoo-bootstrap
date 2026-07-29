"""Unit tests for ConfigManager."""

import tempfile
from pathlib import Path

import pytest
import yaml

from odoo_bootstrap.core.config_manager import ConfigManager
from odoo_bootstrap.core.models import BootstrapConfig, ProjectConfig, DatabaseConfig


@pytest.fixture
def tmp_config(tmp_path):
    """ConfigManager backed by a temp directory."""
    config_file = tmp_path / "bootstrap.yaml"
    return ConfigManager(config_path=config_file)


def test_load_returns_default_when_file_missing(tmp_config):
    config = tmp_config.load()
    assert isinstance(config, BootstrapConfig)
    assert config.versions == [17, 18, 19]


def test_save_and_reload(tmp_config):
    config = tmp_config.load()
    tmp_config.save(config)
    assert tmp_config.config_path.exists()
    reloaded = ConfigManager(config_path=tmp_config.config_path).load()
    assert reloaded.versions == config.versions


def test_add_project(tmp_config):
    proj = ProjectConfig(
        name="test_client",
        version=19,
        db=DatabaseConfig(host="postgres", port=5432, user="odoo", password="odoo", name="test_db"),
    )
    tmp_config.add_project(proj)
    assert "test_client" in tmp_config.config.projects


def test_remove_project(tmp_config):
    proj = ProjectConfig(name="to_remove", version=18)
    tmp_config.add_project(proj)
    tmp_config.remove_project("to_remove")
    assert "to_remove" not in tmp_config.config.projects


def test_get_project_returns_none_for_unknown(tmp_config):
    assert tmp_config.get_project("nonexistent") is None


def test_project_version_validation():
    with pytest.raises(Exception):
        ProjectConfig(name="bad", version=99)


def test_project_odoo_port():
    proj = ProjectConfig(name="x", version=19)
    assert proj.odoo_port == 8069

    proj17 = ProjectConfig(name="y", version=17)
    assert proj17.odoo_port == 8067
