from __future__ import annotations

from .config import WorkerConfig
from .docker_manager import DockerManager
from .employees import get_targets
from .filesystem import employee_paths


_STATUS_SYMBOL = {
    "running": "✓",
    "exited":  "✗",
    "dead":    "✗",
    "missing": "?",
    "created": "·",
    "paused":  "‖",
    "restarting": "↺",
}


def print_status(cfg: WorkerConfig, dm: DockerManager) -> None:
    targets = get_targets(cfg.mode, cfg.location_id)

    print(f"Worker mode:       {cfg.mode}")
    print(f"Location:          {cfg.location_id or '(all)'}")
    print(f"Controller URL:    {cfg.controller_url}")
    print(f"Image:             {cfg.employee_image}")
    print(f"Managed employees: {len(targets)}")
    print()

    from .docker_manager import container_name
    names = [container_name(t.location_id, t.employee.employee_id) for t in targets]
    statuses = dm.container_statuses(names)

    for target in targets:
        name = container_name(target.location_id, target.employee.employee_id)
        st = statuses.get(name, "missing")
        sym = _STATUS_SYMBOL.get(st, "?")
        paths = employee_paths(cfg.data_root, target.location_id, target.employee.employee_id)
        print(f"  {sym} {name}: {st}")
        print(f"      profile: {paths.profile}")
        print(f"      results: {paths.results}")
        print(f"      logs:    {paths.logs}")
