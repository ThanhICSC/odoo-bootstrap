"""
Core constants for odoo-bootstrap.
To add Odoo 20: append 20 to SUPPORTED_VERSIONS and add port mapping.
"""

from pathlib import Path

# ── Supported Odoo versions ──────────────────────────────────────────────────
# Add future versions here only — nothing else needs to change.
SUPPORTED_VERSIONS: list[int] = [17, 18, 19]

# ── Port assignments ─────────────────────────────────────────────────────────
ODOO_PORTS: dict[int, int] = {
    17: 8067,
    18: 8068,
    19: 8069,
}

SERVICE_PORTS: dict[str, int] = {
    "pgadmin": 5050,
    "mailpit_http": 8025,
    "mailpit_smtp": 1025,
    "redis": 6379,
    "adminer": 8080,
}

# ── PostgreSQL ───────────────────────────────────────────────────────────────
POSTGRES_VERSION = "16"
POSTGRES_DEFAULT_USER = "odoo"
POSTGRES_DEFAULT_PASSWORD = "odoo"
POSTGRES_DEFAULT_HOST = "localhost"
POSTGRES_DEFAULT_PORT = 5432

# ── Workspace layout ─────────────────────────────────────────────────────────
WORKSPACE_ROOT = Path.home() / "odoo-dev"

WORKSPACE_DIRS = [
    "versions",
    "projects",
    "shared",
    "backups",
    "logs",
]

VERSION_SUBDIRS = [
    "source",
    "enterprise",
    "docker",
    "config",
]

PROJECT_SUBDIRS = [
    "custom_addons",
    "filestore",
    "backup",
    "logs",
]

# ── Git repositories ─────────────────────────────────────────────────────────
ODOO_COMMUNITY_REPO = "https://github.com/odoo/odoo.git"
ODOO_BRANCH_PATTERN = "{version}.0"  # e.g. "19.0"

# ── Python packages to install inside containers ─────────────────────────────
REQUIRED_PYTHON_PACKAGES: list[str] = [
    "wheel",
    "setuptools",
    "pip",
    "Pillow",
    "lxml",
    "openpyxl",
    "xlsxwriter",
    "xlrd",
    "pandas",
    "numpy",
    "matplotlib",
    "beautifulsoup4",
    "reportlab",
    "cryptography",
    "qrcode",
    "requests",
    "zeep",
    "phonenumbers",
    "paramiko",
    "pdfplumber",
    "num2words",
    "Babel",
    "passlib",
    "watchdog",
    "jinja2",
    "black",
    "ruff",
    "isort",
    "pyyaml",
    "psycopg2-binary",
]

# ── Docker image naming ───────────────────────────────────────────────────────
DOCKER_IMAGE_PREFIX = "bizapps-odoo"

# ── Config filenames ─────────────────────────────────────────────────────────
BOOTSTRAP_CONFIG_FILE = "bootstrap.yaml"
ODOO_CONF_FILE = "odoo.conf"
DOCKER_COMPOSE_FILE = "docker-compose.yml"
DOCKER_COMPOSE_OVERRIDE_FILE = "docker-compose.override.yml"
ENV_FILE = ".env"

# ── Log format ────────────────────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
