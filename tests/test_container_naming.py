from worker_cli.docker_manager import container_name
from worker_cli.employees import get_targets


def test_name_includes_location_and_employee():
    name = container_name("enterprise-hr", "enter-hr-staff")
    assert "enterprise-hr" in name
    assert "enter-hr-staff" in name


def test_name_prefix():
    name = container_name("enterprise-hr", "enter-hr-staff")
    assert name.startswith("zt-")


def test_exact_format():
    assert container_name("enterprise-hr", "enter-hr-staff") == "zt-enterprise-hr-enter-hr-staff"
    assert container_name("branch-dev", "branch-dev-manager") == "zt-branch-dev-branch-dev-manager"
    assert container_name("outdoor-cafe-1", "enter-sales-staff") == "zt-outdoor-cafe-1-enter-sales-staff"


def test_same_employee_different_location_gives_different_names():
    home_name = container_name("enterprise-hr", "enter-hr-staff")
    cafe_name  = container_name("outdoor-cafe-1", "enter-hr-staff")
    assert home_name != cafe_name


def test_enterprise_hr_target_names():
    targets = get_targets("enterprise", "enterprise-hr")
    names = [container_name(t.location_id, t.employee.employee_id) for t in targets]
    assert "zt-enterprise-hr-enter-hr-director" in names
    assert "zt-enterprise-hr-enter-hr-manager" in names
    assert "zt-enterprise-hr-enter-hr-senior" in names
    assert "zt-enterprise-hr-enter-hr-staff" in names


def test_cafe_names_include_cafe_location():
    targets = get_targets("cafe", "outdoor-cafe-2")
    names = [container_name(t.location_id, t.employee.employee_id) for t in targets]
    for n in names:
        assert "outdoor-cafe-2" in n
