"""
Module logging tập trung cho odoo-bootstrap.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


class ColorFormatter(logging.Formatter):
    """Formatter có màu sắc cho terminal."""

    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    ICONS = {
        logging.DEBUG: "🔍",
        logging.INFO: "✅",
        logging.WARNING: "⚠️ ",
        logging.ERROR: "❌",
        logging.CRITICAL: "💀",
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        icon = self.ICONS.get(record.levelno, "")
        reset = self.RESET
        bold = self.BOLD

        message = super().format(record)
        return f"{color}{bold}{icon} {message}{reset}"


def get_logger(name: str = "odoo-bootstrap") -> logging.Logger:
    """Trả về logger đã được cấu hình."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        ColorFormatter("%(message)s")
    )
    logger.addHandler(console_handler)

    # File handler
    log_file = Path(__file__).resolve().parent.parent / "bootstrap.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(file_handler)

    return logger


# Logger mặc định
log = get_logger()
