import pytest
from worker_cli.config import WorkerConfig
from worker_cli.docker_manager import build_spec, container_name
from worker_cli.employees import get_targets, EmployeeTarget
from worker_cli.filesystem import employee_paths


def _make_cfg(**kwargs) -> WorkerConfig:
    defaults = dict(
        mode="enterprise",
        location_id="enterprise-hr",
        controller_url="http://controller.internal:8443",
        llm_api_key="test-llm-key",
        data_root="/data/zt",
        employee_image="employee-agent:latest",
        restart_policy="unless-stopped",
        shm_size="2g",
    )
    defaults.update(kwargs)
    return WorkerConfig(**defaults)


def _first_spec(mode="enterprise", location="enterprise-hr"):
    cfg = _make_cfg(mode=mode, location_id=location)
    targets = get_targets(mode, location)
    target = targets[0]
    paths = employee_paths(cfg.data_root, target.location_id, target.employee.employee_id)
    return build_spec(target, paths, cfg)


# ── environment variables ─────────────────────────────────────────────────────

def test_employee_id_in_env():
    spec = _first_spec()
    assert "EMPLOYEE_ID" in spec.environment
    assert spec.environment["EMPLOYEE_ID"] == "enter-hr-director"


def test_location_id_in_env():
    spec = _first_spec()
    assert spec.environment["LOCATION_ID"] == "enterprise-hr"


def test_worker_group_in_env():
    spec = _first_spec()
    assert spec.environment["WORKER_GROUP"] == "enterprise"


def test_controller_url_in_env():
    spec = _first_spec()
    assert spec.environment["CONTROLLER_URL"] == "http://controller.internal:8443"


def test_llm_api_key_in_env():
    spec = _first_spec()
    assert spec.environment["LLM_API_KEY"] == "test-llm-key"


def test_immutable_env_not_injected_by_worker():
    """PROFILE_DIR/RESULTS_DIR/LOG_DIR/TZ/BROWSER_HEADLESS/ANONYMIZED_TELEMETRY는
    Agent Dockerfile의 ENV 또는 pydantic Settings 기본값이 보장. Worker가 또 주입하면 안 됨."""
    spec = _first_spec()
    for k in (
        "PROFILE_DIR", "RESULTS_DIR", "LOG_DIR",
        "TZ", "BROWSER_HEADLESS", "ANONYMIZED_TELEMETRY",
        "CONTROLLER_TOKEN",
    ):
        assert k not in spec.environment, f"{k} should not be injected by Worker"


# ── volume mounts ─────────────────────────────────────────────────────────────

def test_profile_volume_mounted():
    spec = _first_spec()
    bound_paths = [v["bind"] for v in spec.volumes.values()]
    assert "/app/profile" in bound_paths


def test_results_volume_mounted():
    spec = _first_spec()
    bound_paths = [v["bind"] for v in spec.volumes.values()]
    assert "/app/results" in bound_paths


def test_logs_volume_mounted():
    spec = _first_spec()
    bound_paths = [v["bind"] for v in spec.volumes.values()]
    assert "/app/logs" in bound_paths


def test_volume_host_path_contains_location_and_employee():
    spec = _first_spec()
    host_paths = list(spec.volumes.keys())
    assert any("enterprise-hr" in p and "enter-hr-director" in p for p in host_paths)


def test_three_volumes_mounted():
    spec = _first_spec()
    assert len(spec.volumes) == 3


# ── no port publishing ────────────────────────────────────────────────────────

def test_no_ports_in_spec():
    # ContainerSpec has no ports field at all
    spec = _first_spec()
    assert not hasattr(spec, "ports") or not getattr(spec, "ports", None)


# ── restart policy and shm ────────────────────────────────────────────────────

def test_restart_policy_set():
    spec = _first_spec()
    assert spec.restart_policy == {"Name": "unless-stopped"}


def test_shm_size_set():
    spec = _first_spec()
    assert spec.shm_size == "2g"


def test_image_set():
    spec = _first_spec()
    assert spec.image == "employee-agent:latest"


# ── cafe mode ─────────────────────────────────────────────────────────────────

def test_cafe_spec_location_id_is_cafe():
    cfg = _make_cfg(mode="cafe", location_id="outdoor-cafe-1")
    targets = get_targets("cafe", "outdoor-cafe-1")
    target = targets[0]
    paths = employee_paths(cfg.data_root, target.location_id, target.employee.employee_id)
    spec = build_spec(target, paths, cfg)
    assert spec.environment["LOCATION_ID"] == "outdoor-cafe-1"


def test_worker_group_branch_in_env():
    spec = _first_spec(mode="branch", location="branch-dev")
    assert spec.environment["WORKER_GROUP"] == "branch"
