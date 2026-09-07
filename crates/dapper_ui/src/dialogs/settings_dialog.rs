use dapper_domain::{RolePermissionManager, UserRole, ViewName};

#[derive(Debug)]
pub struct SettingsDialog {
    pub is_open: bool,
    pub active_role: UserRole,
    pub gitlab_url: String,
    pub gitlab_token: String,
}

impl Default for SettingsDialog {
    fn default() -> Self {
        Self {
            is_open: false,
            active_role: UserRole::ProductManager,
            gitlab_url: "https://gitlab.com".to_string(),
            gitlab_token: "".to_string(),
        }
    }
}

impl SettingsDialog {
    pub fn ui(&mut self, ctx: &egui::Context) {
        if !self.is_open {
            return;
        }

        let mut is_open = self.is_open;
        let mut close_dialog = false;

        egui::Window::new("Application Settings & Role Permissions")
            .collapsible(false)
            .resizable(false)
            .default_size([500.0, 400.0])
            .open(&mut is_open)
            .show(ctx, |ui| {
                ui.vertical(|ui| {
                    ui.heading("Active User Role Perspective");
                    ui.horizontal(|ui| {
                        ui.radio_value(&mut self.active_role, UserRole::ProductManager, "Product Manager");
                        ui.radio_value(&mut self.active_role, UserRole::ProductOwner, "Product Owner");
                        ui.radio_value(&mut self.active_role, UserRole::ScrumMaster, "Scrum Master");
                        ui.radio_value(&mut self.active_role, UserRole::Engineer, "Engineer");
                    });

                    ui.separator();
                    ui.label("Visible Views for Role:");
                    ui.label(format!("- Backlog: {}", RolePermissionManager::is_view_visible(self.active_role, ViewName::Backlog)));
                    ui.label(format!("- PI Planner: {}", RolePermissionManager::is_view_visible(self.active_role, ViewName::PiPlanner)));
                    ui.label(format!("- Settings: {}", RolePermissionManager::is_view_visible(self.active_role, ViewName::Settings)));
                    ui.label(format!("- Integrations: {}", RolePermissionManager::is_view_visible(self.active_role, ViewName::Integrations)));

                    ui.separator();
                    ui.heading("GitLab Connection Credentials");
                    ui.horizontal(|ui| {
                        ui.label("GitLab URL:");
                        ui.text_edit_singleline(&mut self.gitlab_url);
                    });
                    ui.horizontal(|ui| {
                        ui.label("Private Token:");
                        ui.text_edit_singleline(&mut self.gitlab_token);
                    });

                    ui.separator();
                    if ui.button("Save & Close").clicked() {
                        close_dialog = true;
                    }
                });
            });

        if !is_open || close_dialog {
            self.is_open = false;
        }
    }
}
