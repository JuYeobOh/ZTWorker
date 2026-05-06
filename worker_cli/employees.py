from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .config import Mode


@dataclass(frozen=True)
class Employee:
    employee_id: str
    home_location: str
    worker_group: str


# ── Enterprise ────────────────────────────────────────────────────────────────
_ENTERPRISE_HR = [
    Employee("enter-hr-director", "enterprise-hr", "enterprise"),
    Employee("enter-hr-manager",  "enterprise-hr", "enterprise"),
    Employee("enter-hr-senior",   "enterprise-hr", "enterprise"),
    Employee("enter-hr-staff",    "enterprise-hr", "enterprise"),
]

_ENTERPRISE_SALES = [
    Employee("enter-sales-director", "enterprise-sales", "enterprise"),
    Employee("enter-sales-manager",  "enterprise-sales", "enterprise"),
    Employee("enter-sales-senior",   "enterprise-sales", "enterprise"),
    Employee("enter-sales-staff",    "enterprise-sales", "enterprise"),
]

_ENTERPRISE_FINANCE = [
    Employee("enter-fin-director", "enterprise-finance", "enterprise"),
    Employee("enter-fin-manager",  "enterprise-finance", "enterprise"),
    Employee("enter-fin-senior",   "enterprise-finance", "enterprise"),
    Employee("enter-fin-staff",    "enterprise-finance", "enterprise"),
]

_ENTERPRISE_LOCATION_MAP: dict[str, list[Employee]] = {
    "enterprise-hr":      _ENTERPRISE_HR,
    "enterprise-sales":   _ENTERPRISE_SALES,
    "enterprise-finance": _ENTERPRISE_FINANCE,
}

_ENTERPRISE_ALL: list[Employee] = (
    _ENTERPRISE_HR + _ENTERPRISE_SALES + _ENTERPRISE_FINANCE
)

# ── Branch ────────────────────────────────────────────────────────────────────
_BRANCH_DEV = [
    Employee("branch-dev-director", "branch-dev", "branch"),
    Employee("branch-dev-manager",  "branch-dev", "branch"),
    Employee("branch-dev-senior",   "branch-dev", "branch"),
    Employee("branch-dev-staff",    "branch-dev", "branch"),
]

_BRANCH_IT = [
    Employee("branch-it-director", "branch-it", "branch"),
    Employee("branch-it-manager",  "branch-it", "branch"),
    Employee("branch-it-senior",   "branch-it", "branch"),
    Employee("branch-it-staff",    "branch-it", "branch"),
]

_BRANCH_LOCATION_MAP: dict[str, list[Employee]] = {
    "branch-dev": _BRANCH_DEV,
    "branch-it":  _BRANCH_IT,
}

_BRANCH_ALL: list[Employee] = _BRANCH_DEV + _BRANCH_IT

# ── Cafe candidates (all 20) ──────────────────────────────────────────────────
_CAFE_CANDIDATES: list[Employee] = _ENTERPRISE_ALL + _BRANCH_ALL

VALID_CAFE_LOCATIONS = {"outdoor-cafe-1", "outdoor-cafe-2"}
VALID_ENTERPRISE_LOCATIONS = set(_ENTERPRISE_LOCATION_MAP.keys())
VALID_BRANCH_LOCATIONS = set(_BRANCH_LOCATION_MAP.keys())


@dataclass(frozen=True)
class EmployeeTarget:
    """An employee together with the location_id to use for this deployment."""
    employee: Employee
    location_id: str


def get_targets(mode: Mode, location_id: Optional[str]) -> list[EmployeeTarget]:
    """Return the list of EmployeeTarget objects for the given mode/location."""
    if mode == "enterprise":
        return _enterprise_targets(location_id)
    if mode == "branch":
        return _branch_targets(location_id)
    if mode == "cafe":
        return _cafe_targets(location_id)
    raise ValueError(f"Unknown mode: {mode}")


def _enterprise_targets(location_id: Optional[str]) -> list[EmployeeTarget]:
    if location_id is None:
        return [EmployeeTarget(e, e.home_location) for e in _ENTERPRISE_ALL]
    if location_id not in _ENTERPRISE_LOCATION_MAP:
        raise ValueError(
            f"Unknown enterprise location '{location_id}'. "
            f"Valid: {sorted(VALID_ENTERPRISE_LOCATIONS)}"
        )
    return [
        EmployeeTarget(e, location_id)
        for e in _ENTERPRISE_LOCATION_MAP[location_id]
    ]


def _branch_targets(location_id: Optional[str]) -> list[EmployeeTarget]:
    if location_id is None:
        return [EmployeeTarget(e, e.home_location) for e in _BRANCH_ALL]
    if location_id not in _BRANCH_LOCATION_MAP:
        raise ValueError(
            f"Unknown branch location '{location_id}'. "
            f"Valid: {sorted(VALID_BRANCH_LOCATIONS)}"
        )
    return [
        EmployeeTarget(e, location_id)
        for e in _BRANCH_LOCATION_MAP[location_id]
    ]


def _cafe_targets(location_id: Optional[str]) -> list[EmployeeTarget]:
    if not location_id:
        raise ValueError("cafe mode requires a location (--location)")
    if location_id not in VALID_CAFE_LOCATIONS:
        raise ValueError(
            f"Unknown cafe location '{location_id}'. "
            f"Valid: {sorted(VALID_CAFE_LOCATIONS)}"
        )
    return [EmployeeTarget(e, location_id) for e in _CAFE_CANDIDATES]
