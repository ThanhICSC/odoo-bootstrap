"""
Configuration manager: load, save, and validate bootstrap.yaml.
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Optional

from odoo_bootstrap.core.constants import WORKSPACE_ROOT, BOOTSTRAP_CONFIG_FILE
from odoo_bootstrap.core.exceptions import ConfigurationError
from odoo_bootstrap.core.logger import get_logger
from odoo_bootstrap.core.models import BootstrapConfig, ProjectConfig, DatabaseConfig, OdooConfig

logger = get_logger("config_manager")

DEFAULT_CONFIG_PATH = WORKSPACE_ROOT / BOOTSTRAP_CONFIG_FILE


class ConfigManager:
    """Manages bootstrap.yaml lifecycle."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._config: Optional[BootstrapConfig] = None

    @property
    def config(self) -> BootstrapConfig:
        if self._config is None:
            self._config = self.load()
        return self._config

    def load(self) -> BootstrapConfig:
        """Load config from YAML file. Returns default config if file not found."""
        if not self.config_path.exists():
            logger.debug(f"Config file not found at {self.config_path}, using defaults")
            return BootstrapConfig()
        try:
            with open(self.config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            # Convert nested project dicts
            projects_raw = data.pop("projects", {})
            projects = {}
            for name, proj_data in (projects_raw or {}).items():
                proj_data["name"] = name
                # nested db
                if "db" in proj_data and isinstance(proj_data["db"], dict):
                    proj_data["db"] = DatabaseConfig(**proj_data["db"])
                if "odoo" in proj_data and isinstance(proj_data["odoo"], dict):
                    proj_data["odoo"] = OdooConfig(**proj_data["odoo"])
                projects[name] = ProjectConfig(**proj_data)
            data["projects"] = projects
            if "workspace" in data:
                data["workspace"] = Path(data["workspace"])
            config = BootstrapConfig(**data)
            logger.debug(f"Config loaded from {self.config_path}")
            return config
        except Exception as e:
            raise ConfigurationError(f"Failed to load config from {self.config_path}: {e}") from e

    def save(self, config: Optional[BootstrapConfig] = None) -> None:
        """Save config to YAML file."""
        cfg = config or self._config
        if cfg is None:
            raise ConfigurationError("No config to save")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = self._serialize(cfg)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        logger.debug(f"Config saved to {self.config_path}")
        self._config = cfg

    def _serialize(self, config: BootstrapConfig) -> dict:
        """Convert BootstrapConfig to a plain dict for YAML serialization."""
        projects_dict = {}
        for name, proj in config.projects.items():
            projects_dict[name] = {
                "version": proj.version,
                "enabled": proj.enabled,
                "db": {
                    "host": proj.db.host,
                    "port": proj.db.port,
                    "user": proj.db.user,
                    "password": proj.db.password,
                    "name": proj.db.name,
                },
                "odoo": {
                    "workers": proj.odoo.workers,
                    "proxy_mode": proj.odoo.proxy_mode,
                    "dev_mode": proj.odoo.dev_mode,
                    "log_level": proj.odoo.log_level,
                },
                "extra_pip_packages": proj.extra_pip_packages,
            }
        return {
            "workspace": str(config.workspace),
            "versions": config.versions,
            "postgres_version": config.postgres_version,
            "postgres_user": config.postgres_user,
            "postgres_password": config.postgres_password,
            "enable_pgadmin": config.enable_pgadmin,
            "enable_mailpit": config.enable_mailpit,
            "enable_redis": config.enable_redis,
            "enable_adminer": config.enable_adminer,
            "pgadmin_email": config.pgadmin_email,
            "pgadmin_password": config.pgadmin_password,
            "projects": projects_dict,
        }

    def add_project(self, project: ProjectConfig) -> None:
        """Add or update a project in the config."""
        self.config.projects[project.name] = project
        self.save()

    def remove_project(self, name: str) -> None:
        """Remove a project from the config."""
        if name in self.config.projects:
            del self.config.projects[name]
            self.save()

    def get_project(self, name: str) -> Optional[ProjectConfig]:
        """Get a project config by name."""
        return self.config.projects.get(name)

    def list_projects(self) -> list[ProjectConfig]:
        """Return all project configs."""
        return list(self.config.projects.values())
