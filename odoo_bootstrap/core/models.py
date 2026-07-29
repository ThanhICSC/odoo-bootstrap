"""
Pydantic models for all configuration and data structures.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from odoo_bootstrap.core.constants import SUPPORTED_VERSIONS, ODOO_PORTS, SERVICE_PORTS, WORKSPACE_ROOT


class OdooVersion(int, Enum):
    V17 = 17
    V18 = 18
    V19 = 19


class DatabaseConfig(BaseModel):
    host: str = "postgres"
    port: int = 5432
    user: str = "odoo"
    password: str = "odoo"
    name: str = ""

    def get_url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class OdooConfig(BaseModel):
    workers: int = 0
    proxy_mode: bool = True
    dev_mode: str = "reload,qweb,xml"
    log_level: str = "debug"
    max_cron_threads: int = 1
    limit_memory_hard: int = 2684354560
    limit_memory_soft: int = 2147483648
    limit_request: int = 8192
    limit_time_cpu: int = 60
    limit_time_real: int = 120
    smtp_server: str = "mailpit"
    smtp_port: int = 1025
    smtp_ssl: bool = False


class ProjectConfig(BaseModel):
    name: str
    version: int
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    odoo: OdooConfig = Field(default_factory=OdooConfig)
    custom_addons: list[str] = Field(default_factory=list)
    extra_pip_packages: list[str] = Field(default_factory=list)
    enabled: bool = True

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: int) -> int:
        if v not in SUPPORTED_VERSIONS:
            raise ValueError(f"Version {v} not supported. Supported: {SUPPORTED_VERSIONS}")
        return v

    @property
    def odoo_port(self) -> int:
        return ODOO_PORTS[self.version]

    @property
    def project_dir(self) -> Path:
        return WORKSPACE_ROOT / "projects" / self.name

    @property
    def version_dir(self) -> Path:
        return WORKSPACE_ROOT / "versions" / str(self.version)

    @property
    def source_dir(self) -> Path:
        return self.version_dir / "source"

    @property
    def enterprise_dir(self) -> Path:
        return self.version_dir / "enterprise"

    @property
    def custom_addons_dir(self) -> Path:
        return self.project_dir / "custom_addons"

    @property
    def filestore_dir(self) -> Path:
        return self.project_dir / "filestore"

    @property
    def backup_dir(self) -> Path:
        return self.project_dir / "backup"

    @property
    def logs_dir(self) -> Path:
        return self.project_dir / "logs"

    @property
    def branch_name(self) -> str:
        return f"{self.version}.0"

    @property
    def docker_image_name(self) -> str:
        return f"bizapps-odoo:{self.version}"

    def get_addons_path(self) -> list[str]:
        paths = [
            f"/opt/odoo/{self.version}.0/addons",
            f"/opt/odoo/{self.version}.0/odoo/addons",
            "/opt/enterprise",
            "/opt/custom_addons",
        ]
        return paths


class BootstrapConfig(BaseModel):
    workspace: Path = WORKSPACE_ROOT
    versions: list[int] = Field(default_factory=lambda: list(SUPPORTED_VERSIONS))
    projects: dict[str, ProjectConfig] = Field(default_factory=dict)
    postgres_version: str = "16"
    postgres_user: str = "odoo"
    postgres_password: str = "odoo"
    enable_pgadmin: bool = True
    enable_mailpit: bool = True
    enable_redis: bool = True
    enable_adminer: bool = False
    pgadmin_email: str = "admin@bizapps.vn"
    pgadmin_password: str = "admin"

    model_config = {"arbitrary_types_allowed": True}


class DoctorCheck(BaseModel):
    name: str
    status: str  # "ok" | "warning" | "error" | "skip"
    message: str
    detail: Optional[str] = None


class DoctorReport(BaseModel):
    checks: list[DoctorCheck] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(c.status == "error" for c in self.checks)

    @property
    def has_warnings(self) -> bool:
        return any(c.status == "warning" for c in self.checks)


class ContainerStatus(BaseModel):
    name: str
    status: str
    image: str
    ports: str
    project: Optional[str] = None
