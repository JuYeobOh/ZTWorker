from __future__ import annotations

import time

from .config import WorkerConfig
from .docker_manager import DockerManager, ContainerSpec, build_spec
from .employees import get_targets
from .filesystem import employee_paths, ensure_directories


def build_specs(cfg: WorkerConfig) -> dict[str, ContainerSpec]:
    targets = get_targets(cfg.mode, cfg.location_id)
    specs: dict[str, ContainerSpec] = {}
    for target in targets:
        paths = employee_paths(cfg.data_root, target.location_id, target.employee.employee_id)
        spec = build_spec(target, paths, cfg)
        specs[spec.name] = spec
    return specs


def setup(cfg: WorkerConfig, dm: DockerManager) -> None:
    specs = build_specs(cfg)
    dm.pull_image_if_missing(cfg.employee_image)
    for spec in specs.values():
        paths = employee_paths(
            cfg.data_root,
            spec.environment["LOCATION_ID"],
            spec.environment["EMPLOYEE_ID"],
        )
        ensure_directories(paths)
        action = dm.ensure_container(spec)
        print(f"[setup] {spec.name}: {action}")


def supervise_once(cfg: WorkerConfig, dm: DockerManager) -> None:
    specs = build_specs(cfg)
    for spec in specs.values():
        action = dm.ensure_container(spec)
        if not action.startswith("ok"):
            print(f"[supervise] {spec.name}: {action}")


def supervise_loop(cfg: WorkerConfig, dm: DockerManager) -> None:
    interval = cfg.supervise_interval_seconds
    print(f"[supervise] Starting loop (interval={interval}s). Ctrl+C to stop.")
    while True:
        supervise_once(cfg, dm)
        time.sleep(interval)
