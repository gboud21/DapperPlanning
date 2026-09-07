import pytest
from src.domain.capacity_calculator import CapacityCalculator
from src.domain.entities import TeamMemberCapacity

def test_member_capacity_formula_standard():
    """
    Tests member capacity calculation:
    Capacity = (DaysInSprint - PTO) * (Allocation / 100) * (Velocity / 100) * (Utilization / 100)
    Standard inputs: 10 days in sprint, 0 PTO, 100% alloc, 100% velocity, 100% utilization = 10.0
    """
    cap = CapacityCalculator.calculate_member_capacity(
        days_in_sprint=10,
        pto=0,
        allocation_pct=100,
        velocity_factor=100,
        utilization_factor=100
    )
    assert cap == 10.0

def test_member_capacity_formula_with_pto_and_factors():
    """
    Inputs: 10 sprint days, 2 PTO days, 80% allocation, 90% velocity, 100% utilization.
    Expected: (10 - 2) * (80/100) * (90/100) * (100/100) = 8 * 0.8 * 0.9 * 1.0 = 5.76
    """
    cap = CapacityCalculator.calculate_member_capacity(
        days_in_sprint=10,
        pto=2,
        allocation_pct=80,
        velocity_factor=90,
        utilization_factor=100
    )
    assert pytest.approx(cap, 0.001) == 5.76

def test_member_capacity_formula_with_global_utilization():
    """
    Inputs: 10 sprint days, 0 PTO, 100% allocation, 100% velocity, 80% utilization factor.
    Expected: 10 * 1.0 * 1.0 * 0.8 = 8.0
    """
    cap = CapacityCalculator.calculate_member_capacity(
        days_in_sprint=10,
        pto=0,
        allocation_pct=100,
        velocity_factor=100,
        utilization_factor=80
    )
    assert pytest.approx(cap, 0.001) == 8.0

def test_member_capacity_formula_excess_pto_clamped_to_zero():
    """
    Inputs: 10 sprint days, 12 PTO days.
    Expected: (10 - 12) <= 0 -> 0.0 capacity (never negative).
    """
    cap = CapacityCalculator.calculate_member_capacity(
        days_in_sprint=10,
        pto=12,
        allocation_pct=100,
        velocity_factor=100,
        utilization_factor=100
    )
    assert cap == 0.0

def test_member_capacity_formula_zero_factors():
    """
    Zero allocation, velocity, or utilization leads to 0 capacity.
    """
    assert CapacityCalculator.calculate_member_capacity(10, 0, allocation_pct=0) == 0.0
    assert CapacityCalculator.calculate_member_capacity(10, 0, velocity_factor=0) == 0.0
    assert CapacityCalculator.calculate_member_capacity(10, 0, utilization_factor=0) == 0.0

def test_member_capacity_from_entity_object():
    """
    Tests calculating member capacity directly using a TeamMemberCapacity object.
    """
    record = TeamMemberCapacity(
        team_id="team-1",
        member_id=42,
        iteration_id=100,
        pto=3,
        allocation_pct=50,
        velocity_factor=100
    )
    # 10 days sprint, pto=3 => 7 days * 0.5 * 1.0 * 0.9 = 3.15
    cap = CapacityCalculator.calculate_member_capacity_from_object(
        capacity_record=record,
        days_in_sprint=10,
        utilization_factor=90
    )
    assert pytest.approx(cap, 0.001) == 3.15

def test_team_capacity_rollup():
    """
    Tests team capacity calculation by summing member capacities.
    """
    member_caps = [5.76, 8.0, 10.0]
    team_cap = CapacityCalculator.calculate_team_capacity(member_caps)
    assert pytest.approx(team_cap, 0.001) == 23.76

def test_team_capacity_rollup_empty():
    assert CapacityCalculator.calculate_team_capacity([]) == 0.0

def test_product_capacity_rollup():
    """
    Tests product capacity calculation by summing team capacities.
    """
    team_caps = [23.76, 15.0]
    product_cap = CapacityCalculator.calculate_product_capacity(team_caps)
    assert pytest.approx(product_cap, 0.001) == 38.76

def test_product_capacity_rollup_empty():
    assert CapacityCalculator.calculate_product_capacity([]) == 0.0
