import pytest
from worker_cli.employees import get_targets, VALID_CAFE_LOCATIONS


# ── enterprise ────────────────────────────────────────────────────────────────

def test_enterprise_hr_returns_4():
    targets = get_targets("enterprise", "enterprise-hr")
    ids = [t.employee.employee_id for t in targets]
    assert len(ids) == 4
    assert all(e.startswith("enter-hr") for e in ids)


def test_enterprise_sales_returns_4():
    targets = get_targets("enterprise", "enterprise-sales")
    ids = [t.employee.employee_id for t in targets]
    assert len(ids) == 4
    assert all(e.startswith("enter-sales") for e in ids)


def test_enterprise_finance_returns_4():
    targets = get_targets("enterprise", "enterprise-finance")
    ids = [t.employee.employee_id for t in targets]
    assert len(ids) == 4
    assert all(e.startswith("enter-fin") for e in ids)


def test_enterprise_no_location_returns_12():
    targets = get_targets("enterprise", None)
    assert len(targets) == 12


def test_enterprise_no_location_location_ids_are_home():
    targets = get_targets("enterprise", None)
    for t in targets:
        assert t.location_id == t.employee.home_location


def test_enterprise_invalid_location_raises():
    with pytest.raises(ValueError, match="Unknown enterprise location"):
        get_targets("enterprise", "nonexistent-loc")


# ── branch ────────────────────────────────────────────────────────────────────

def test_branch_dev_returns_4():
    targets = get_targets("branch", "branch-dev")
    ids = [t.employee.employee_id for t in targets]
    assert len(ids) == 4
    assert all(e.startswith("branch-dev") for e in ids)


def test_branch_it_returns_4():
    targets = get_targets("branch", "branch-it")
    ids = [t.employee.employee_id for t in targets]
    assert len(ids) == 4
    assert all(e.startswith("branch-it") for e in ids)


def test_branch_no_location_returns_8():
    targets = get_targets("branch", None)
    assert len(targets) == 8


def test_branch_no_location_location_ids_are_home():
    targets = get_targets("branch", None)
    for t in targets:
        assert t.location_id == t.employee.home_location


def test_branch_invalid_location_raises():
    with pytest.raises(ValueError, match="Unknown branch location"):
        get_targets("branch", "branch-xyz")


# ── cafe ──────────────────────────────────────────────────────────────────────

def test_cafe_outdoor_cafe_1_returns_20():
    targets = get_targets("cafe", "outdoor-cafe-1")
    assert len(targets) == 20


def test_cafe_outdoor_cafe_2_returns_20():
    targets = get_targets("cafe", "outdoor-cafe-2")
    assert len(targets) == 20



def test_cafe_no_location_raises():
    with pytest.raises(ValueError, match="requires a location"):
        get_targets("cafe", None)


def test_cafe_invalid_location_raises():
    with pytest.raises(ValueError, match="Unknown cafe location"):
        get_targets("cafe", "indoor-office")


def test_cafe_location_id_is_cafe_location():
    targets = get_targets("cafe", "outdoor-cafe-2")
    for t in targets:
        assert t.location_id == "outdoor-cafe-2"


def test_cafe_contains_all_enterprise_and_branch():
    targets = get_targets("cafe", "outdoor-cafe-1")
    ids = {t.employee.employee_id for t in targets}
    # sample from each group
    assert "enter-hr-staff" in ids
    assert "enter-sales-director" in ids
    assert "enter-fin-manager" in ids
    assert "branch-dev-senior" in ids
    assert "branch-it-staff" in ids
