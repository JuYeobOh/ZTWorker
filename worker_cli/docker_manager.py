from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import docker
from docker.errors import NotFound, APIError
from docker.models.containers import Container

from .config import WorkerConfig
from .employees import EmployeeTarget
from .filesystem import EmployeePaths


def container_name(location_id: str, employee_id: str) -> str:
    return f"zt-{location_id}-{employee_id}"


@dataclass
class ContainerSpec:
    name: str
    image: str
    environment: dict[str, str]
    volumes: dict[str, dict]
    restart_policy: dict
    shm_size: str


def build_spec(
    target: EmployeeTarget,
    paths: EmployeePaths,
    cfg: WorkerConfig,
) -> ContainerSpec:
    emp = target.employee
    loc = target.location_id

    env: dict[str, str] = {
        "EMPLOYEE_ID":    emp.employee_id,
        "LOCATION_ID":    loc,
        "WORKER_GROUP":   emp.worker_group,
        "CONTROLLER_URL": cfg.controller_url,
        "LLM_API_KEY":    cfg.llm_api_key,
    }
    if cfg.worker_id:
        env["WORKER_ID"] = cfg.worker_id

    volumes = {
        str(paths.profile): {"bind": "/app/profile", "mode": "rw"},
        str(paths.results): {"bind": "/app/results", "mode": "rw"},
        str(paths.logs):    {"bind": "/app/logs",    "mode": "rw"},
    }

    return ContainerSpec(
        name=container_name(loc, emp.employee_id),
        image=cfg.employee_image,
        environment=env,
        volumes=volumes,
        restart_policy={"Name": cfg.restart_policy},
        shm_size=cfg.shm_size,
    )


class DockerManager:
    def __init__(self) -> None:
        self._client: Optional[docker.DockerClient] = None

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    def pull_image_if_missing(self, image: str) -> None:
        try:
            self.client.images.get(image)
        except docker.errors.ImageNotFound:
            print(f"[docker] Pulling image: {image}")
            self.client.images.pull(image)

    def get_container(self, name: str) -> Optional[Container]:
        try:
            return self.client.containers.get(name)
        except NotFound:
            return None

    def run_container(self, spec: ContainerSpec) -> Container:
        # Ports are intentionally never published — no ports kwarg
        return self.client.containers.run(
            image=spec.image,
            name=spec.name,
            detach=True,
            environment=spec.environment,
            volumes=spec.volumes,
            restart_policy=spec.restart_policy,
            shm_size=spec.shm_size,
            network_mode="bridge",
            ports={},           # explicit empty — no publish
        )

    def ensure_container(self, spec: ContainerSpec) -> str:
        """Create and start the container if it doesn't exist; return action taken."""
        container = self.get_container(spec.name)
        if container is None:
            self.run_container(spec)
            return "created"
        status = container.status
        if status in ("exited", "dead", "created"):
            try:
                container.start()
                return "restarted"
            except APIError as exc:
                # Container may be in a broken state — remove and recreate
                container.remove(force=True)
                self.run_container(spec)
                return f"recreated (was {status}: {exc})"
        return f"ok ({status})"

    def stop_containers(self, names: list[str], remove: bool = False) -> None:
        for name in names:
            c = self.get_container(name)
            if c is None:
                continue
            try:
                c.stop(timeout=10)
                if remove:
                    c.remove()
            except APIError as exc:
                print(f"[docker] Warning: could not stop {name}: {exc}")

    def restart_dead(self, names: list[str], specs: dict[str, ContainerSpec]) -> list[str]:
        restarted: list[str] = []
        for name in names:
            c = self.get_container(name)
            if c is None:
                spec = specs.get(name)
                if spec:
                    self.run_container(spec)
                    restarted.append(name)
            elif c.status in ("exited", "dead"):
                try:
                    c.start()
                    restarted.append(name)
                except APIError:
                    c.remove(force=True)
                    spec = specs.get(name)
                    if spec:
                        self.run_container(spec)
                    restarted.append(name)
        return restarted

    def container_statuses(self, names: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        for name in names:
            c = self.get_container(name)
            result[name] = c.status if c else "missing"
        return result
