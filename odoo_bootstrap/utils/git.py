"""
Git utilities: clone, pull, check status.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from odoo_bootstrap.core.exceptions import GitError
from odoo_bootstrap.core.logger import get_logger

logger = get_logger("git")


def clone_or_pull(
    repo_url: str,
    target_dir: Path,
    branch: Optional[str] = None,
    depth: Optional[int] = None,
) -> str:
    """
    Clone a repository if not present, or pull if already cloned.
    Returns 'cloned' | 'pulled' | 'up_to_date'.
    """
    if (target_dir / ".git").exists():
        logger.info(f"Pulling {target_dir.name} (branch: {branch or 'current'})")
        return _git_pull(target_dir, branch)
    else:
        logger.info(f"Cloning {repo_url} → {target_dir}")
        return _git_clone(repo_url, target_dir, branch, depth)


def _git_clone(
    repo_url: str,
    target_dir: Path,
    branch: Optional[str],
    depth: Optional[int],
) -> str:
    cmd = ["git", "clone", "--single-branch"]
    if branch:
        cmd += ["-b", branch]
    if depth:
        cmd += ["--depth", str(depth)]
    cmd += [repo_url, str(target_dir)]
    _run(cmd)
    return "cloned"


def _git_pull(target_dir: Path, branch: Optional[str]) -> str:
    if branch:
        _run(["git", "checkout", branch], cwd=target_dir)
    result = subprocess.run(
        ["git", "pull", "--ff-only"],
        cwd=str(target_dir),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(f"git pull failed in {target_dir}: {result.stderr}")
    output = result.stdout.strip()
    if "Already up to date" in output:
        return "up_to_date"
    return "pulled"


def get_current_branch(repo_dir: Path) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_last_commit(repo_dir: Path) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%h %s"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def _run(cmd: list[str], cwd: Optional[Path] = None) -> None:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(f"Git command failed: {' '.join(cmd)}\n{result.stderr}")
