use crate::entities::MemberCapacity;

pub struct CapacityCalculator;

impl CapacityCalculator {
    pub fn calculate_member_capacity(
        days_in_sprint: f64,
        pto: f64,
        allocation_pct: f64,
        velocity_factor: f64,
        utilization_factor: f64,
    ) -> f64 {
        let net_days = (days_in_sprint - pto).max(0.0);
        let alloc = (allocation_pct / 100.0).clamp(0.0, 1.0);
        let vel = (velocity_factor / 100.0).clamp(0.0, 1.0);
        let util = (utilization_factor / 100.0).clamp(0.0, 1.0);

        net_days * alloc * vel * util
    }

    pub fn calculate_member_capacity_from_record(
        record: &MemberCapacity,
        days_in_sprint: f64,
        override_utilization_factor: Option<f64>,
    ) -> f64 {
        let util = override_utilization_factor.unwrap_or(record.utilization_factor);
        Self::calculate_member_capacity(
            days_in_sprint,
            record.pto,
            record.allocation_pct,
            record.velocity_factor,
            util,
        )
    }

    pub fn calculate_team_capacity(member_capacities: &[f64]) -> f64 {
        member_capacities.iter().sum()
    }

    pub fn calculate_product_capacity(team_capacities: &[f64]) -> f64 {
        team_capacities.iter().sum()
    }
}
