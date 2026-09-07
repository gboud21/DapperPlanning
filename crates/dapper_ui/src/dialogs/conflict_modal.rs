use dapper_core::AppContext;

#[derive(Default, Debug)]
pub struct ConflictResolutionModal {
    pub is_open: bool,
    pub conflicted_item_id: Option<String>,
}

impl ConflictResolutionModal {
    pub fn ui(&mut self, ctx: &egui::Context, app_ctx: &AppContext) {
        if !self.is_open {
            return;
        }

        let mut is_open = self.is_open;
        let mut close_modal = false;

        egui::Window::new("Interactive Conflict Resolution Editor")
            .collapsible(false)
            .resizable(true)
            .default_size([700.0, 500.0])
            .open(&mut is_open)
            .show(ctx, |ui| {
                ui.vertical(|ui| {
                    ui.heading("Resolve Merge Conflict");
                    ui.separator();

                    if let Some(item_id) = &self.conflicted_item_id {
                        ui.label(format!("Conflicted Item ID: {}", item_id));
                        ui.separator();

                        ui.columns(2, |columns| {
                            columns[0].vertical(|ui| {
                                ui.heading("Local Version");
                                ui.label("Title: Modified Local Title");
                                ui.label("Parent: feat-NEW");
                                if ui.button("Accept Local Version").clicked() {
                                    let _ = app_ctx.command_bus.try_dispatch(
                                        dapper_core::Command::ResolveConflict {
                                            item_id: item_id.clone(),
                                            resolved_data: serde_json::json!({ "version": "local" }),
                                        },
                                    );
                                    close_modal = true;
                                }
                            });

                            columns[1].vertical(|ui| {
                                ui.heading("Remote Version");
                                ui.label("Title: Modified Remote Title");
                                ui.label("Parent: feat-OLD");
                                if ui.button("Accept Remote Version").clicked() {
                                    let _ = app_ctx.command_bus.try_dispatch(
                                        dapper_core::Command::ResolveConflict {
                                            item_id: item_id.clone(),
                                            resolved_data: serde_json::json!({ "version": "remote" }),
                                        },
                                    );
                                    close_modal = true;
                                }
                            });
                        });
                    } else {
                        ui.label("No conflicted item selected.");
                    }

                    ui.separator();
                    if ui.button("Cancel").clicked() {
                        close_modal = true;
                    }
                });
            });

        if !is_open || close_modal {
            self.is_open = false;
        }
    }
}
