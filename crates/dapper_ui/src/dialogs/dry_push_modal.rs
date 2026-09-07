use dapper_core::AppContext;
use dapper_workflows::DryPushSummary;

#[derive(Default, Debug)]
pub struct DryPushModal {
    pub is_open: bool,
    pub summary: Option<DryPushSummary>,
}

impl DryPushModal {
    pub fn ui(&mut self, ctx: &egui::Context, app_ctx: &AppContext) {
        if !self.is_open {
            return;
        }

        let mut is_open = self.is_open;
        let mut close_modal = false;

        egui::Window::new("Dry Push Summary Report")
            .collapsible(false)
            .resizable(true)
            .default_size([600.0, 720.0])
            .open(&mut is_open)
            .show(ctx, |ui| {
                ui.vertical(|ui| {
                    ui.heading("Dry Push Simulation Details");
                    ui.separator();

                    if let Some(summary) = &self.summary {
                        egui::ScrollArea::vertical()
                            .max_height(550.0)
                            .show(ui, |ui| {
                                ui.collapsing(format!("Creations ({})", summary.creations_list.len()), |ui| {
                                    for item in &summary.creations_list {
                                        ui.label(item);
                                    }
                                });

                                ui.collapsing(format!("Updates ({})", summary.updates_list.len()), |ui| {
                                    for item in &summary.updates_list {
                                        ui.label(item);
                                    }
                                });

                                ui.collapsing(format!("Conflicts ({})", summary.conflicts_list.len()), |ui| {
                                    for item in &summary.conflicts_list {
                                        ui.colored_label(egui::Color32::RED, item);
                                    }
                                });

                                ui.collapsing(format!("Deletions ({})", summary.deletions_list.len()), |ui| {
                                    for item in &summary.deletions_list {
                                        ui.label(item);
                                    }
                                });
                            });
                    } else {
                        ui.label("No dry push simulation data available.");
                    }

                    ui.separator();
                    ui.horizontal(|ui| {
                        if ui.button("Execute Actual Push").clicked() {
                            let _ = app_ctx.command_bus.try_dispatch(dapper_core::Command::TriggerGitLabPush);
                            close_modal = true;
                        }
                        if ui.button("Close").clicked() {
                            close_modal = true;
                        }
                    });
                });
            });

        if !is_open || close_modal {
            self.is_open = false;
        }
    }
}
