"""
Tạo và quản lý cấu trúc thư mục workspace.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from core.config import ODOO_VERSIONS, WORKSPACE_DIR, OdooVersion, POSTGRES_CONFIG
from core.logger import log


class WorkspaceManager:
    """Tạo cấu trúc thư mục workspace cho môi trường phát triển Odoo."""

    SUBDIRS: List[str] = [
        "source",
        "custom_addons",
        "enterprise",
        "config",
        "filestore",
        "backup",
        "logs",
    ]

    def create_workspace_root(self) -> None:
        """Tạo thư mục gốc workspace."""
        if WORKSPACE_DIR.exists():
            log.info(f"Workspace đã tồn tại: {WORKSPACE_DIR}")
        else:
            WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
            log.info(f"Đã tạo workspace: {WORKSPACE_DIR}")

        # Thư mục PostgreSQL data
        pg_data = POSTGRES_CONFIG.data_dir
        if not pg_data.exists():
            pg_data.mkdir(parents=True, exist_ok=True)
            log.info(f"Đã tạo thư mục PostgreSQL data: {pg_data}")

    def create_version_dirs(self, version: OdooVersion) -> None:
        """Tạo tất cả thư mục cho một phiên bản Odoo."""
        for subdir in self.SUBDIRS:
            target = version.workspace / subdir
            target.mkdir(parents=True, exist_ok=True)

        log.info(f"  Odoo {version.version}: cấu trúc thư mục hoàn tất")

    def create_gitkeep(self, version: OdooVersion) -> None:
        """Tạo file .gitkeep trong các thư mục trống."""
        empty_dirs = ["custom_addons", "enterprise", "backup", "logs"]
        for d in empty_dirs:
            gitkeep = version.workspace / d / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.touch()

    def create_custom_addons_placeholder(self, version: OdooVersion) -> None:
        """Tạo README trong custom_addons để hướng dẫn."""
        readme = version.custom_addons_dir / "README.md"
        if readme.exists():
            return
        readme.write_text(
            f"# Custom Addons - Odoo {version.version}\n\n"
            "Đặt các custom module của bạn vào thư mục này.\n\n"
            "Mỗi module có thể có file `requirements.txt` riêng.\n"
            "Bootstrap sẽ tự động cài đặt các thư viện trong đó.\n",
            encoding="utf-8",
        )

    def create_enterprise_placeholder(self, version: OdooVersion) -> None:
        """Tạo README trong enterprise để hướng dẫn."""
        readme = version.enterprise_dir / "README.md"
        if readme.exists():
            return
        readme.write_text(
            f"# Odoo Enterprise - Odoo {version.version}\n\n"
            "Copy source code Enterprise vào thư mục này.\n"
            "Bootstrap sẽ tự động mount vào container khi có.\n",
            encoding="utf-8",
        )

    def setup_all(self) -> None:
        """Tạo toàn bộ cấu trúc workspace."""
        log.info("=" * 60)
        log.info("KHỞI TẠO WORKSPACE")
        log.info("=" * 60)

        self.create_workspace_root()

        for version in ODOO_VERSIONS:
            log.info(f"Tạo cấu trúc cho Odoo {version.version}...")
            self.create_version_dirs(version)
            self.create_gitkeep(version)
            self.create_custom_addons_placeholder(version)
            self.create_enterprise_placeholder(version)

        log.info(f"Workspace đã sẵn sàng tại: {WORKSPACE_DIR}")
