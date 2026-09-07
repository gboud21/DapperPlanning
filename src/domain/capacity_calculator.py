from typing import List, Optional
from src.domain.entities import TeamMemberCapacity

class CapacityCalculator:
    """
    Utility for calculating individual member capacity, team capacity rollups,
    and product capacity rollups.
    """

    @staticmethod
    def calculate_member_capacity(
        days_in_sprint: float,
        pto: float = 0.0,
        allocation_pct: float = 100.0,
        velocity_factor: float = 100.0,
        utilization_factor: float = 100.0
    ) -> float:
        """
        Calculates individual member capacity based on the standard formula:
        Capacity = (DaysInSprint - PTO) * (Allocation / 100) * (Velocity / 100) * (Utilization / 100)
        """
        net_days = max(0.0, days_in_sprint - pto)
        alloc = allocation_pct / 100.0
        vel = velocity_factor / 100.0
        util = utilization_factor / 100.0
        return net_days * alloc * vel * util

    @staticmethod
    def calculate_member_capacity_from_object(
        capacity_record: Optional[TeamMemberCapacity],
        days_in_sprint: float,
        utilization_factor: float = 100.0
    ) -> float:
        """
        Helper method to calculate capacity given a TeamMemberCapacity domain record.
        """
        if not capacity_record:
            return CapacityCalculator.calculate_member_capacity(
                days_in_sprint=days_in_sprint,
                utilization_factor=utilization_factor
            )

        return CapacityCalculator.calculate_member_capacity(
            days_in_sprint=days_in_sprint,
            pto=capacity_record.pto,
            allocation_pct=capacity_record.allocation_pct,
            velocity_factor=capacity_record.velocity_factor,
            utilization_factor=utilization_factor
        )

    @staticmethod
    def calculate_team_capacity(member_capacities: List[float]) -> float:
        """
        Rolls up individual member capacities for a team.
        """
        return float(sum(member_capacities))

    @staticmethod
    def calculate_product_capacity(team_capacities: List[float]) -> float:
        """
        Rolls up team capacities for a product.
        """
        return float(sum(team_capacities))
