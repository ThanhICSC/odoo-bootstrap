"""
Cấu hình trung tâm cho toàn bộ odoo-bootstrap.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

# Thư mục gốc workspace
HOME_DIR = Path.home()
WORKSPACE_DIR = HOME_DIR / "odoo-dev"
PROJECT_DIR = Path(__file__).resolve().parent.parent


@dataclass
class OdooVersion:
    version: str          # "17", "18", "19"
    branch: str           # "17.0", "18.0", "19.0"
    port: int             # 8067, 8068, 8069
    python: str = "python3"

    @property
    def service_name(self) -> str:
        return f"odoo{self.version}"

    @property
    def image_name(self) -> str:
        return f"odoo-dev:{self.version}"

    @property
    def workspace(self) -> Path:
        return WORKSPACE_DIR / f"odoo{self.version}"

    @property
    def source_dir(self) -> Path:
        return self.workspace / "source"

    @property
    def custom_addons_dir(self) -> Path:
        return self.workspace / "custom_addons"

    @property
    def enterprise_dir(self) -> Path:
        return self.workspace / "enterprise"

    @property
    def config_dir(self) -> Path:
        return self.workspace / "config"

    @property
    def filestore_dir(self) -> Path:
        return self.workspace / "filestore"

    @property
    def backup_dir(self) -> Path:
        return self.workspace / "backup"

    @property
    def logs_dir(self) -> Path:
        return self.workspace / "logs"

    @property
    def dockerfile_path(self) -> Path:
        return PROJECT_DIR / "docker" / f"Dockerfile.odoo{self.version}"

    @property
    def github_url(self) -> str:
        return f"https://github.com/odoo/odoo.git"


ODOO_VERSIONS: List[OdooVersion] = [
    OdooVersion(version="17", branch="17.0", port=8067),
    OdooVersion(version="18", branch="18.0", port=8068),
    OdooVersion(version="19", branch="19.0", port=8069),
]

ODOO_VERSION_MAP: Dict[str, OdooVersion] = {v.version: v for v in ODOO_VERSIONS}


@dataclass
class PostgresConfig:
    container_name: str = "odoo-postgres"
    image: str = "postgres:16"
    port: int = 5432
    user: str = "odoo"
    password: str = "odoo"
    data_dir: Path = field(default_factory=lambda: WORKSPACE_DIR / "postgres_data")


@dataclass
class PgAdminConfig:
    container_name: str = "odoo-pgadmin"
    image: str = "dpage/pgadmin4"
    port: int = 5050
    email: str = "admin@odoo.dev"
    password: str = "admin"


@dataclass
class MailpitConfig:
    container_name: str = "odoo-mailpit"
    image: str = "axllent/mailpit"
    smtp_port: int = 1025
    ui_port: int = 8025


@dataclass
class RedisConfig:
    container_name: str = "odoo-redis"
    image: str = "redis:7-alpine"
    port: int = 6379


@dataclass
class ServicesConfig:
    postgres: PostgresConfig = field(default_factory=PostgresConfig)
    pgadmin: PgAdminConfig = field(default_factory=PgAdminConfig)
    mailpit: MailpitConfig = field(default_factory=MailpitConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    network_name: str = "odoo-network"
    compose_file: Path = field(default_factory=lambda: WORKSPACE_DIR / "docker-compose.yml")


# Singleton config instances
POSTGRES_CONFIG = PostgresConfig()
PGADMIN_CONFIG = PgAdminConfig()
MAILPIT_CONFIG = MailpitConfig()
REDIS_CONFIG = RedisConfig()
SERVICES_CONFIG = ServicesConfig()

# Các thư viện Python chung cần cài đặt
COMMON_PIP_PACKAGES: List[str] = [
    "wheel",
    "setuptools",
    "pip",
    "Babel",
    "chardet",
    "cryptography",
    "decorator",
    "docutils",
    "ebaysdk",
    "freezegun",
    "geoip2",
    "gevent",
    "greenlet",
    "html2text",
    "humanize",
    "idna",
    "Jinja2",
    "libsass",
    "lxml",
    "MarkupSafe",
    "num2words",
    "ofxparse",
    "passlib",
    "Pillow",
    "polib",
    "psutil",
    "psycopg2-binary",
    "pydot",
    "pyotp",
    "PyPDF2",
    "pypiwin32; sys_platform == 'win32'",
    "pyserial",
    "python-dateutil",
    "python-ldap; sys_platform != 'win32'",
    "python-slugify",
    "python-stdnum",
    "pytz",
    "pyusb",
    "qrcode",
    "reportlab",
    "requests",
    "rjsmin",
    "vobject",
    "Werkzeug",
    "xlrd",
    "XlsxWriter",
    "xlwt",
    "zeep",
    "PyYAML",
    "redis",
    "boto3",
    "paramiko",
    "phonenumbers",
    "Markdown",
    "PyJWT",
    "pycountry",
    "python-barcode",
    "Wand",
    "cssselect",
    "pre-commit",
    "black",
    "flake8",
    "isort",
    "pylint",
    "pylint-odoo",
    "debugpy",
]

ODOO_GITHUB_REPO = "https://github.com/odoo/odoo.git"
DOCKER_NETWORK = "odoo-network"
