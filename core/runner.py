"""
Tiện ích chạy lệnh shell với logging và xử lý lỗi nhất quán.
"""

from __future__ import annotations

import subprocess
import shlex
from typing import List, Optional, Tuple

from core.logger import log


class CommandRunner:
    """Chạy lệnh shell với kiểm soát đầu ra và lỗi."""

    def run(
        self,
        command: str | List[str],
        cwd: Optional[str] = None,
        capture: bool = False,
        check: bool = True,
        env: Optional[dict] = None,
        stream: bool = False,
    ) -> Tuple[int, str, str]:
        """
        Chạy lệnh shell.

        Args:
            command: Lệnh cần chạy (string hoặc list).
            cwd: Thư mục làm việc.
            capture: Có capture stdout/stderr không.
            check: Có raise exception khi lỗi không.
            env: Biến môi trường bổ sung.
            stream: In output ra màn hình theo thời gian thực.

        Returns:
            Tuple (returncode, stdout, stderr)
        """
        if isinstance(command, str):
            cmd_list = shlex.split(command)
            cmd_display = command
        else:
            cmd_list = command
            cmd_display = " ".join(command)

        log.debug(f"Chạy lệnh: {cmd_display}")

        if stream:
            proc = subprocess.Popen(
                cmd_list,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            output_lines: List[str] = []
            if proc.stdout:
                for line in proc.stdout:
                    print(line, end="", flush=True)
                    output_lines.append(line)
            proc.wait()
            stdout = "".join(output_lines)
            stderr = ""
            returncode = proc.returncode
        else:
            result = subprocess.run(
                cmd_list,
                cwd=cwd,
                env=env,
                capture_output=capture,
                text=True,
            )
            returncode = result.returncode
            stdout = result.stdout or ""
            stderr = result.stderr or ""

        if check and returncode != 0:
            log.error(f"Lệnh thất bại (exit {returncode}): {cmd_display}")
            if stderr:
                log.error(f"Stderr: {stderr.strip()}")
            raise subprocess.CalledProcessError(returncode, cmd_list, stdout, stderr)

        return returncode, stdout, stderr

    def run_ok(
        self,
        command: str | List[str],
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
    ) -> bool:
        """Chạy lệnh, trả về True nếu thành công."""
        try:
            self.run(command, cwd=cwd, capture=True, check=True, env=env)
            return True
        except subprocess.CalledProcessError:
            return False

    def output(
        self,
        command: str | List[str],
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
    ) -> str:
        """Chạy lệnh và trả về stdout."""
        _, stdout, _ = self.run(command, cwd=cwd, capture=True, check=False, env=env)
        return stdout.strip()

    def which(self, program: str) -> Optional[str]:
        """Kiểm tra xem chương trình có tồn tại trong PATH không."""
        import shutil
        return shutil.which(program)

    def is_installed(self, program: str) -> bool:
        """Kiểm tra xem chương trình đã được cài đặt chưa."""
        return self.which(program) is not None


# Singleton runner
runner = CommandRunner()
