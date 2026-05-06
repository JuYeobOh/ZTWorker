from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class EmployeePaths:
    profile: Path
    results: Path
    logs: Path


def employee_paths(data_root: str, location_id: str, employee_id: str) -> EmployeePaths:
    root = Path(data_root)
    return EmployeePaths(
        profile=root / "profiles" / location_id / employee_id,
        results=root / "results"  / location_id / employee_id,
        logs=root   / "logs"     / location_id / employee_id,
    )


def ensure_directories(paths: EmployeePaths) -> None:
    for p in (paths.profile, paths.results, paths.logs):
        p.mkdir(parents=True, exist_ok=True)
