from pathlib import Path
from worker_cli.filesystem import employee_paths


DATA_ROOT = "/data/zt"


def test_profile_path_structure():
    paths = employee_paths(DATA_ROOT, "enterprise-hr", "enter-hr-staff")
    assert paths.profile == Path("/data/zt/profiles/enterprise-hr/enter-hr-staff")


def test_results_path_structure():
    paths = employee_paths(DATA_ROOT, "enterprise-hr", "enter-hr-staff")
    assert paths.results == Path("/data/zt/results/enterprise-hr/enter-hr-staff")


def test_logs_path_structure():
    paths = employee_paths(DATA_ROOT, "enterprise-hr", "enter-hr-staff")
    assert paths.logs == Path("/data/zt/logs/enterprise-hr/enter-hr-staff")


def test_path_contains_location_id():
    paths = employee_paths(DATA_ROOT, "branch-dev", "branch-dev-manager")
    assert "branch-dev" in str(paths.profile)
    assert "branch-dev" in str(paths.results)
    assert "branch-dev" in str(paths.logs)


def test_path_contains_employee_id():
    paths = employee_paths(DATA_ROOT, "branch-dev", "branch-dev-manager")
    assert "branch-dev-manager" in str(paths.profile)
    assert "branch-dev-manager" in str(paths.results)
    assert "branch-dev-manager" in str(paths.logs)


def test_cafe_paths_use_cafe_location():
    paths = employee_paths(DATA_ROOT, "outdoor-cafe-1", "enter-sales-staff")
    assert "outdoor-cafe-1" in str(paths.profile)
    assert "enter-sales-staff" in str(paths.profile)


def test_custom_data_root():
    from pathlib import Path
    paths = employee_paths("/mnt/data", "enterprise-sales", "enter-sales-director")
    assert paths.profile == Path("/mnt/data/profiles/enterprise-sales/enter-sales-director")


def test_home_vs_cafe_paths_differ():
    home_paths = employee_paths(DATA_ROOT, "enterprise-hr", "enter-hr-staff")
    cafe_paths  = employee_paths(DATA_ROOT, "outdoor-cafe-1", "enter-hr-staff")
    assert home_paths.profile != cafe_paths.profile
