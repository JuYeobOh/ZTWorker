import pytest
from pathlib import Path
from textwrap import dedent

from worker_cli.config import build_config, WorkerConfig


EXAMPLE_YAML = dedent("""\
    worker_id: enterprise-hr-worker
    mode: enterprise
    location_id: enterprise-hr
    controller_url: http://controller.internal:8443
    llm_api_key: test-llm-key
    data_root: /data/zt
    employee_image: employee-agent:latest
    restart_policy: unless-stopped
    shm_size: 2g
    supervise_interval_seconds: 30
""")


@pytest.fixture
def yaml_file(tmp_path: Path) -> Path:
    p = tmp_path / "worker.yaml"
    p.write_text(EXAMPLE_YAML)
    return p


def test_load_from_yaml(yaml_file: Path):
    cfg = build_config(config_file=yaml_file)
    assert cfg.mode == "enterprise"
    assert cfg.location_id == "enterprise-hr"
    assert cfg.controller_url == "http://controller.internal:8443"
    assert cfg.data_root == "/data/zt"
    assert cfg.employee_image == "employee-agent:latest"
    assert cfg.restart_policy == "unless-stopped"
    assert cfg.shm_size == "2g"
    assert cfg.supervise_interval_seconds == 30
    assert cfg.worker_id == "enterprise-hr-worker"


def test_cli_overrides_config_mode(yaml_file: Path):
    cfg = build_config(config_file=yaml_file, mode="branch", location_id="branch-dev")
    assert cfg.mode == "branch"
    assert cfg.location_id == "branch-dev"


def test_cli_overrides_controller_url(yaml_file: Path):
    cfg = build_config(config_file=yaml_file, controller_url="http://other:9000")
    assert cfg.controller_url == "http://other:9000"


def test_cli_overrides_image(yaml_file: Path):
    cfg = build_config(config_file=yaml_file, employee_image="employee-agent:v2")
    assert cfg.employee_image == "employee-agent:v2"


def test_no_config_file_cli_only():
    cfg = build_config(
        config_file=None,
        mode="branch",
        location_id="branch-it",
        controller_url="http://ctrl:8443",
        llm_api_key="k",
    )
    assert cfg.mode == "branch"
    assert cfg.location_id == "branch-it"


def test_missing_required_fields_raises():
    with pytest.raises(Exception):
        build_config(config_file=None, mode="enterprise")  # missing controller_url/token/llm_api_key


def test_missing_llm_api_key_raises(tmp_path: Path):
    p = tmp_path / "no-llm.yaml"
    p.write_text(
        "mode: branch\nlocation_id: branch-dev\n"
        "controller_url: http://x\n"
    )
    with pytest.raises(Exception):
        build_config(config_file=p)


def test_cafe_without_location_raises(tmp_path: Path):
    p = tmp_path / "cafe.yaml"
    p.write_text(
        "mode: cafe\ncontroller_url: http://x\n"
        "llm_api_key: k\n"
    )
    with pytest.raises(Exception, match="cafe mode requires"):
        build_config(config_file=p)


def test_defaults_applied_when_not_in_yaml(tmp_path: Path):
    p = tmp_path / "minimal.yaml"
    p.write_text(
        "mode: branch\ncontroller_url: http://x\n"
        "llm_api_key: k\n"
    )
    cfg = build_config(config_file=p)
    assert cfg.data_root == "/data/zt"
    assert cfg.employee_image == "employee-agent:latest"
    assert cfg.shm_size == "2g"
    assert cfg.restart_policy == "unless-stopped"
    assert cfg.supervise_interval_seconds == 30
