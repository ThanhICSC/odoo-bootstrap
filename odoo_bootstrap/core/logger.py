"""
Centralized logging configuration for odoo-bootstrap.
"""

import logging
import sys
from pathlib import Path

from rich.logging import RichHandler

from odoo_bootstrap.core.constants import LOG_FORMAT, LOG_DATE_FORMAT, WORKSPACE_ROOT


def setup_logging(level: str = "INFO", log_to_file: bool = True) -> logging.Logger:
    """Configure root logger with Rich console handler and optional file handler."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [
        RichHandler(
            rich_tracebacks=True,
            show_path=False,
            markup=True,
        )
    ]

    if log_to_file:
        log_dir = WORKSPACE_ROOT / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "bootstrap.log", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
        handlers.append(file_handler)

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers,
        force=True,
    )

    return logging.getLogger("odoo_bootstrap")


def get_logger(name: str) -> logging.Logger:
    """Get a named logger under the odoo_bootstrap namespace."""
    return logging.getLogger(f"odoo_bootstrap.{name}")
