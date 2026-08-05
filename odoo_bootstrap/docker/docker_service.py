"""
Docker service layer: build images, manage containers, networks, volumes.
Uses the Docker SDK for Python.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import docker
from docker.errors import DockerException, ImageNotFound, NotFound
from docker.models.containers import Container

from odoo_bootstrap.core.exceptions import DockerError
from odoo_bootstrap.core.logger import get_logger
from odoo_bootstrap.core.models import ContainerStatus

logger = get_logger("docker_service")


class DockerService:
    """Abstraction over the Docker SDK for Odoo-specific operations."""

    def __init__(self) -> None:
        try:
            self.client = docker.from_env()
            self.client.ping()
        except DockerException as e:
            raise DockerError(
                f"Cannot connect to Docker daemon. Is Docker running? Detail: {e}"
            ) from e

    # ── Image operations ──────────────────────────────────────────────────────

    def image_exists(self, image_name: str) -> bool:
        try:
            self.client.images.get(image_name)
            return True
        except ImageNotFound:
            return False

    def build_image(
        self,
        dockerfile_path: Path,
        image_name: str,
        build_args: dict[str, str] | None = None,
        no_cache: bool = False,
    ) -> None:
        """Build a Docker image from a Dockerfile."""
        logger.info(f"Building image {image_name} from {dockerfile_path}")
        try:
            image, logs = self.client.images.build(
                path=str(dockerfile_path.parent),
                dockerfile=str(dockerfile_path.name),
                tag=image_name,
                buildargs=build_args or {},
                nocache=no_cache,
                rm=True,
            )
            for chunk in logs:
                if "stream" in chunk:
                    line = chunk["stream"].strip()
                    if line:
                        logger.debug(f"  {line}")
            logger.info(f"Image {image_name} built successfully")
        except Exception as e:
            raise DockerError(f"Failed to build image {image_name}: {e}") from e

    def pull_image(self, image_name: str) -> None:
        """Pull an image from Docker Hub."""
        logger.info(f"Pulling image {image_name}")
        try:
            self.client.images.pull(image_name)
        except Exception as e:
            raise DockerError(f"Failed to pull image {image_name}: {e}") from e

    # ── Container operations ──────────────────────────────────────────────────

    def get_container(self, name: str) -> Container | None:
        try:
            return self.client.containers.get(name)
        except NotFound:
            return None

    def container_is_running(self, name: str) -> bool:
        container = self.get_container(name)
        return container is not None and container.status == "running"

    def start_container(self, name: str) -> None:
        container = self.get_container(name)
        if container:
            container.start()
            logger.info(f"Container {name} started")
        else:
            logger.warning(f"Container {name} not found")

    def stop_container(self, name: str, timeout: int = 10) -> None:
        container = self.get_container(name)
        if container and container.status == "running":
            container.stop(timeout=timeout)
            logger.info(f"Container {name} stopped")

    def restart_container(self, name: str) -> None:
        container = self.get_container(name)
        if container:
            container.restart()
            logger.info(f"Container {name} restarted")

    def remove_container(self, name: str, force: bool = False) -> None:
        container = self.get_container(name)
        if container:
            container.remove(force=force)
            logger.info(f"Container {name} removed")

    def get_container_logs(self, name: str, tail: int = 100) -> str:
        container = self.get_container(name)
        if not container:
            return f"Container {name} not found"
        return container.logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")

    def exec_in_container(
        self, name: str, command: list[str], user: str = "root"
    ) -> tuple[int, str]:
        """Execute a command inside a running container."""
        container = self.get_container(name)
        if not container or container.status != "running":
            raise DockerError(f"Container {name} is not running")
        result = container.exec_run(command, user=user)
        return result.exit_code, result.output.decode("utf-8", errors="replace")

    def list_containers(self, all: bool = True) -> list[ContainerStatus]:
        """Return status of all containers."""
        containers = self.client.containers.list(all=all)
        result = []
        for c in containers:
            ports_str = ", ".join(
                f"{h['HostPort']}->{k}" for k, v in (c.ports or {}).items() if v for h in v
            )
            result.append(
                ContainerStatus(
                    name=c.name,
                    status=c.status,
                    image=c.image.tags[0] if c.image.tags else c.image.short_id,
                    ports=ports_str or "—",
                )
            )
        return result

    # ── Compose operations ────────────────────────────────────────────────────

    def compose_up(self, compose_dir: Path, project_name: str, detach: bool = True) -> None:
        """Run docker compose up."""
        cmd = [
            "docker",
            "compose",
            "-p",
            project_name.lower(),
            "-f",
            str(compose_dir / "docker-compose.yml"),
        ]
        override = compose_dir / "docker-compose.override.yml"
        if override.exists():
            cmd += ["-f", str(override)]
        cmd += ["up", "--build"]
        if detach:
            cmd.append("-d")
        logger.info(f"Starting compose project {project_name}")
        self._run_subprocess(cmd, cwd=compose_dir)

    def compose_down(self, compose_dir: Path, project_name: str, volumes: bool = False) -> None:
        """Run docker compose down."""
        cmd = [
            "docker",
            "compose",
            "-p",
            project_name.lower(),
            "-f",
            str(compose_dir / "docker-compose.yml"),
            "down",
        ]
        if volumes:
            cmd.append("-v")
        self._run_subprocess(cmd, cwd=compose_dir)

    def compose_restart(
        self, compose_dir: Path, project_name: str, service: str | None = None
    ) -> None:
        cmd = [
            "docker",
            "compose",
            "-p",
            project_name.lower(),
            "-f",
            str(compose_dir / "docker-compose.yml"),
            "restart",
        ]
        if service:
            cmd.append(service)
        self._run_subprocess(cmd, cwd=compose_dir)

    def _run_subprocess(self, cmd: list[str], cwd: Path | None = None) -> None:
        try:
            subprocess.run(cmd, cwd=cwd, check=True)
        except subprocess.CalledProcessError as e:
            raise DockerError(
                f"Docker command failed: {' '.join(cmd)}\nReturn code: {e.returncode}"
            ) from e

    # ── Network / Volume ──────────────────────────────────────────────────────

    def ensure_network(self, name: str) -> None:
        networks = [n.name for n in self.client.networks.list()]
        if name not in networks:
            self.client.networks.create(name, driver="bridge")
            logger.info(f"Network {name} created")

    def ensure_volume(self, name: str) -> None:
        volumes = [v.name for v in self.client.volumes.list()]
        if name not in volumes:
            self.client.volumes.create(name)
            logger.info(f"Volume {name} created")

    def get_docker_version(self) -> str:
        try:
            return self.client.version()["Version"]
        except Exception:
            return "unknown"

    def get_compose_version(self) -> str:
        try:
            result = subprocess.run(
                ["docker", "compose", "version", "--short"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"
