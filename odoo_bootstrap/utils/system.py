"""
System utilities: check disk, RAM, CPU, ports, installed tools.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
from pathlib import Path
from typing import Optional


def check_command_exists(command: str) -> bool:
    """Return True if a command is available on PATH."""
    return shutil.which(command) is not None


def get_command_version(command: str, version_flag: str = "--version") -> Optional[str]:
    """Return version string for a CLI tool, or None if not found."""
    try:
        result = subprocess.run(
            [command, version_flag],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return (result.stdout or result.stderr).strip().splitlines()[0]
    except Exception:
        return None


def get_disk_free_gb(path: Path) -> float:
    """Return free disk space in GB for the given path."""
    try:
        stat = shutil.disk_usage(str(path))
        return round(stat.free / (1024 ** 3), 2)
    except Exception:
        return 0.0


def get_total_ram_gb() -> float:
    """Return total system RAM in GB."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return round(kb / (1024 ** 2), 2)
    except Exception:
        pass
    return 0.0


def get_cpu_count() -> int:
    """Return number of CPU cores."""
    import os
    return os.cpu_count() or 1


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Return True if the port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((host, port))
            return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            return False


def get_python_version() -> str:
    """Return the current Python version string."""
    import sys
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def run_command(
    cmd: list[str],
    cwd: Optional[Path] = None,
    capture: bool = True,
    timeout: int = 300,
) -> tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=capture,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout or "", result.stderr or ""


def ensure_directory(path: Path, mode: int = 0o755) -> None:
    """Create directory with correct permissions if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(mode)


def get_git_version() -> Optional[str]:
    return get_command_version("git")


def get_docker_version_str() -> Optional[str]:
    return get_command_version("docker")
