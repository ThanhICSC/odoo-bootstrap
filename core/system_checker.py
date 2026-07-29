"""
Kiểm tra các phụ thuộc hệ thống cần thiết.
"""

from __future__ import annotations

import sys
from typing import List, Tuple

from core.logger import log
from core.runner import runner


class SystemChecker:
    """Kiểm tra và cài đặt các phụ thuộc hệ thống."""

    REQUIRED_TOOLS = [
        ("git", "git"),
        ("docker", "docker.io docker-ce"),
        ("python3", "python3"),
        ("pip3", "python3-pip"),
        ("curl", "curl"),
        ("wget", "wget"),
        ("zip", "zip"),
        ("unzip", "unzip"),
    ]

    APT_DEPENDENCIES = [
        "build-essential",
        "python3-dev",
        "python3-pip",
        "python3-venv",
        "libxml2-dev",
        "libxslt1-dev",
        "libldap2-dev",
        "libsasl2-dev",
        "libtiff5-dev",
        "libjpeg8-dev",
        "libopenjp2-7-dev",
        "zlib1g-dev",
        "libfreetype6-dev",
        "liblcms2-dev",
        "libwebp-dev",
        "libharfbuzz-dev",
        "libfribidi-dev",
        "libxcb1-dev",
        "libpq-dev",
        "node-less",
        "npm",
        "nodejs",
        "libssl-dev",
        "libffi-dev",
        "wkhtmltopdf",
        "git",
        "curl",
        "wget",
        "zip",
        "unzip",
        "jq",
        "htop",
        "net-tools",
    ]

    def check_python_version(self) -> bool:
        """Kiểm tra phiên bản Python."""
        major, minor = sys.version_info[:2]
        if major < 3 or (major == 3 and minor < 10):
            log.error(f"Python 3.10+ là bắt buộc, hiện tại: {major}.{minor}")
            return False
        log.info(f"Python {major}.{minor} - OK")
        return True

    def check_docker(self) -> bool:
        """Kiểm tra Docker đã được cài đặt và đang chạy."""
        if not runner.is_installed("docker"):
            log.warning("Docker chưa được cài đặt")
            return False

        ok = runner.run_ok("docker info")
        if not ok:
            log.warning("Docker daemon chưa chạy. Hãy khởi động Docker.")
            return False

        version = runner.output("docker --version")
        log.info(f"Docker - OK ({version})")
        return True

    def check_docker_compose(self) -> bool:
        """Kiểm tra Docker Compose."""
        # Thử docker compose (V2)
        if runner.run_ok("docker compose version"):
            version = runner.output("docker compose version")
            log.info(f"Docker Compose V2 - OK ({version})")
            return True
        # Thử docker-compose (V1)
        if runner.is_installed("docker-compose"):
            version = runner.output("docker-compose --version")
            log.info(f"Docker Compose V1 - OK ({version})")
            return True

        log.warning("Docker Compose chưa được cài đặt")
        return False

    def check_git(self) -> bool:
        """Kiểm tra Git."""
        if not runner.is_installed("git"):
            log.warning("Git chưa được cài đặt")
            return False
        version = runner.output("git --version")
        log.info(f"Git - OK ({version})")
        return True

    def install_apt_dependencies(self) -> None:
        """Cài đặt các gói APT cần thiết."""
        log.info("Cập nhật danh sách gói APT...")
        runner.run("sudo apt-get update -qq", check=False)

        log.info("Cài đặt các gói phụ thuộc hệ thống...")
        packages = " ".join(self.APT_DEPENDENCIES)
        runner.run(
            f"sudo apt-get install -y -qq {packages}",
            stream=True,
            check=False,
        )

    def install_node_tools(self) -> None:
        """Cài đặt các công cụ Node.js cần thiết."""
        if not runner.run_ok("npm list -g less less-plugin-clean-css"):
            log.info("Cài đặt less và less-plugin-clean-css...")
            runner.run("sudo npm install -g less less-plugin-clean-css", check=False)

    def ensure_user_in_docker_group(self) -> None:
        """Đảm bảo user hiện tại thuộc nhóm docker."""
        import os
        username = os.environ.get("USER", "")
        if username:
            runner.run(f"sudo usermod -aG docker {username}", check=False)

    def run_all_checks(self) -> Tuple[bool, List[str]]:
        """
        Chạy tất cả kiểm tra.

        Returns:
            (all_ok, missing_items)
        """
        issues: List[str] = []

        if not self.check_python_version():
            issues.append("Python 3.10+")

        if not self.check_git():
            issues.append("git")

        docker_ok = self.check_docker()
        if not docker_ok:
            issues.append("docker")

        compose_ok = self.check_docker_compose()
        if not compose_ok:
            issues.append("docker-compose")

        return len(issues) == 0, issues

    def ensure_all(self) -> None:
        """Đảm bảo tất cả phụ thuộc đều có sẵn, cài đặt nếu thiếu."""
        log.info("=" * 60)
        log.info("KIỂM TRA PHỤ THUỘC HỆ THỐNG")
        log.info("=" * 60)

        all_ok, issues = self.run_all_checks()

        if not all_ok:
            log.warning(f"Thiếu: {', '.join(issues)}")
            log.info("Đang cài đặt các phụ thuộc còn thiếu...")
            self.install_apt_dependencies()
            self.install_node_tools()

            # Kiểm tra lại
            all_ok, issues = self.run_all_checks()
            if not all_ok:
                log.error(f"Vẫn còn thiếu sau khi cài đặt: {', '.join(issues)}")
                log.error("Vui lòng cài đặt thủ công trước khi tiếp tục.")
                sys.exit(1)

        log.info("Tất cả phụ thuộc hệ thống đã sẵn sàng!")
