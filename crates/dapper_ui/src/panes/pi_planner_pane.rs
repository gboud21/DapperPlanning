use dapper_core::AppContext;
use dapper_domain::CapacityCalculator;

#[derive(Debug)]
pub struct PiPlannerPane {
    pub days_in_sprint: f64,
    pub global_utilization: f64,
}

impl Default for PiPlannerPane {
    fn default() -> Self {
        Self {
            days_in_sprint: 10.0,
            global_utilization: 100.0,
        }
    }
}

impl PiPlannerPane {
    pub fn ui(&mut self, ui: &mut egui::Ui, ctx: &AppContext) {
        ui.vertical(|ui| {
            ui.heading("PI Planning Capacity Calculator");
            ui.separator();

            ui.horizontal(|ui| {
                ui.label("Days in Sprint:");
                ui.add(egui::DragValue::new(&mut self.days_in_sprint).speed(0.5).range(1.0..=30.0));

                ui.add_space(20.0);
                ui.label("Global Utilization %:");
                ui.add(egui::DragValue::new(&mut self.global_utilization).speed(1.0).range(0.0..=200.0));
            });

            ui.separator();

            egui::ScrollArea::vertical()
                .id_salt("pi_planner_scroll_area")
                .show(ui, |ui| {

                let workspace_lock = ctx.workspace.try_read();
                if let Ok(workspace) = workspace_lock {
                    ui.label(format!("Product: {}", workspace.active_product_name.as_deref().unwrap_or("None")));

                    let mut team_capacities = Vec::new();

                    for team in &workspace.product_teams {
                        ui.collapsing(format!("Team: {}", team.name), |ui| {
                            let mut member_caps = Vec::new();
                            egui::Grid::new(format!("grid_{}", team.id))
                                .striped(true)
                                .show(ui, |ui| {
                                    ui.label("Member ID");
                                    ui.label("PTO Days");
                                    ui.label("Allocation %");
                                    ui.label("Velocity %");
                                    ui.label("Net Capacity");
                                    ui.end_row();

                                    for cap_rec in &workspace.member_capacities {
                                        if cap_rec.team_id == team.id {
                                            let net = CapacityCalculator::calculate_member_capacity_from_record(
                                                cap_rec,
                                                self.days_in_sprint,
                                                Some(self.global_utilization),
                                            );
                                            member_caps.push(net);

                                            ui.label(format!("{}", cap_rec.member_id));
                                            ui.label(format!("{}", cap_rec.pto));
                                            ui.label(format!("{}%", cap_rec.allocation_pct));
                                            ui.label(format!("{}%", cap_rec.velocity_factor));
                                            ui.label(format!("{:.2} pts", net));
                                            ui.end_row();
                                        }
                                    }
                                });

                            let team_total = CapacityCalculator::calculate_team_capacity(&member_caps);
                            team_capacities.push(team_total);
                            ui.label(format!("Total Team Capacity: {:.2} pts", team_total));
                        });
                    }

                    let product_total = CapacityCalculator::calculate_product_capacity(&team_capacities);
                    ui.separator();
                    ui.heading(format!("Total Product Sprint Capacity: {:.2} pts", product_total));
                } else {
                    ui.label("Loading PI Planning data...");
                }
            });
        });
    }
}
