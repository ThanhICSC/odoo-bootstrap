"""
Clone hoặc cập nhật mã nguồn Odoo từ GitHub.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.config import ODOO_VERSIONS, OdooVersion, ODOO_GITHUB_REPO
from core.logger import log
from core.runner import runner


class SourceManager:
    """Quản lý mã nguồn Odoo Community từ GitHub."""

    def _is_git_repo(self, path: Path) -> bool:
        """Kiểm tra xem thư mục có phải là git repo không."""
        return (path / ".git").exists()

    def _get_current_branch(self, path: Path) -> Optional[str]:
        """Lấy nhánh hiện tại của git repo."""
        try:
            branch = runner.output(f"git -C {path} rev-parse --abbrev-ref HEAD")
            return branch
        except Exception:
            return None

    def clone_source(self, version: OdooVersion) -> None:
        """Clone mã nguồn Odoo cho một phiên bản."""
        source_dir = version.source_dir

        if self._is_git_repo(source_dir):
            log.info(f"  Odoo {version.version}: source đã tồn tại → git pull")
            self._pull_source(version)
            return

        if source_dir.exists() and any(source_dir.iterdir()):
            log.warning(
                f"  Odoo {version.version}: thư mục {source_dir} không phải git repo"
                " nhưng đã có nội dung → bỏ qua"
            )
            return

        log.info(
            f"  Odoo {version.version}: clone branch {version.branch} từ GitHub..."
        )
        log.info("  (Quá trình này có thể mất vài phút tùy tốc độ mạng)")

        source_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "git", "clone",
            "--depth", "1",
            "--branch", version.branch,
            "--single-branch",
            ODOO_GITHUB_REPO,
            str(source_dir),
        ]

        try:
            runner.run(cmd, stream=True)
            log.info(f"  Odoo {version.version}: clone hoàn tất")
        except Exception as exc:
            log.error(f"  Odoo {version.version}: clone thất bại: {exc}")
            log.warning(
                f"  Bỏ qua clone Odoo {version.version}. "
                "Bạn có thể clone thủ công sau."
            )

    def _pull_source(self, version: OdooVersion) -> None:
        """Pull cập nhật mới nhất từ GitHub."""
        source_dir = version.source_dir
        try:
            runner.run(
                f"git -C {source_dir} pull --ff-only origin {version.branch}",
                capture=True,
                check=False,
            )
            log.info(f"  Odoo {version.version}: đã cập nhật source")
        except Exception as exc:
            log.warning(f"  Odoo {version.version}: pull thất bại: {exc}")

    def setup_all(self, skip_clone: bool = False) -> None:
        """Clone hoặc cập nhật tất cả phiên bản."""
        log.info("=" * 60)
        log.info("CLONE/CẬP NHẬT MÃ NGUỒN ODOO")
        log.info("=" * 60)

        if skip_clone:
            log.info("Bỏ qua bước clone source (--skip-clone)")
            return

        for version in ODOO_VERSIONS:
            self.clone_source(version)

        log.info("Hoàn tất clone/cập nhật mã nguồn")
