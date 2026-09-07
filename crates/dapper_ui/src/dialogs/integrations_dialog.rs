use dapper_core::{AppContext, Command};
use dapper_persistence::{IntegrationSettings, SettingsManager};

#[derive(Debug, Clone, PartialEq)]
pub enum IntegrationsTab {
    Authentication,
    ProductRouting,
    Capabilities,
    SyncLabels,
}

#[derive(Debug)]
pub struct IntegrationsDialog {
    pub is_open: bool,
    pub active_tab: IntegrationsTab,

    // Authentication Tab
    pub host_url: String,
    pub pat_token: String,
    pub root_group_id: String,

    // Product Routing Tab
    pub active_product_name: String,
    pub new_product_name: String,
    pub new_project_id: String,
    pub new_group_id: String,
    pub selected_product: Option<String>,

    // Capabilities Tab
    pub new_capability: String,
    pub selected_capability: Option<String>,

    // Sync Labels & Legacy Status Tab
    pub epic_sync_label: String,
    pub feature_sync_label: String,
    pub legacy_status_enabled: bool,
    pub label_backlog: String,
    pub label_in_progress: String,
    pub label_in_review: String,
    pub label_done: String,
    pub label_closed: String,
}

impl Default for IntegrationsDialog {
    fn default() -> Self {
        let settings = SettingsManager::load_integration_settings();
        Self {
            is_open: false,
            active_tab: IntegrationsTab::Authentication,
            host_url: settings.auth_url,
            pat_token: settings.auth_pat,
            root_group_id: settings.epic_group_id,
            active_product_name: String::new(),
            new_product_name: String::new(),
            new_project_id: String::new(),
            new_group_id: String::new(),
            selected_product: None,
            new_capability: String::new(),
            selected_capability: None,
            epic_sync_label: settings.epic_sync_label,
            feature_sync_label: settings.feature_sync_label,
            legacy_status_enabled: settings.legacy_status_enabled,
            label_backlog: settings.label_backlog,
            label_in_progress: settings.label_in_progress,
            label_in_review: settings.label_in_review,
            label_done: settings.label_done,
            label_closed: settings.label_closed,
        }
    }
}

impl IntegrationsDialog {
    pub fn open(&mut self) {
        let settings = SettingsManager::load_integration_settings();
        self.host_url = settings.auth_url;
        self.pat_token = settings.auth_pat;
        self.root_group_id = settings.epic_group_id;
        self.epic_sync_label = settings.epic_sync_label;
        self.feature_sync_label = settings.feature_sync_label;
        self.legacy_status_enabled = settings.legacy_status_enabled;
        self.label_backlog = settings.label_backlog;
        self.label_in_progress = settings.label_in_progress;
        self.label_in_review = settings.label_in_review;
        self.label_done = settings.label_done;
        self.label_closed = settings.label_closed;
        self.is_open = true;
    }

    pub fn ui(&mut self, ctx: &egui::Context, app_ctx: &AppContext) {
        if !self.is_open {
            return;
        }

        let mut is_open = self.is_open;
        let mut close_dialog = false;

        egui::Window::new("Integration Settings")
            .collapsible(false)
            .resizable(true)
            .pivot(egui::Align2::CENTER_CENTER)
            .default_pos(ctx.screen_rect().center())
            .default_size([700.0, 600.0])
            .open(&mut is_open)
            .show(ctx, |ui| {

                ui.vertical(|ui| {
                    // Navigation Tabs
                    ui.horizontal(|ui| {
                        ui.selectable_value(
                            &mut self.active_tab,
                            IntegrationsTab::Authentication,
                            "Authentication",
                        );
                        ui.selectable_value(
                            &mut self.active_tab,
                            IntegrationsTab::ProductRouting,
                            "Product Routing",
                        );
                        ui.selectable_value(
                            &mut self.active_tab,
                            IntegrationsTab::Capabilities,
                            "Capabilities",
                        );
                        ui.selectable_value(
                            &mut self.active_tab,
                            IntegrationsTab::SyncLabels,
                            "Sync Labels",
                        );
                    });
                    ui.separator();

                    match self.active_tab {
                        IntegrationsTab::Authentication => {
                            ui.heading("GitLab Authentication");
                            ui.add_space(5.0);

                            egui::Grid::new("auth_settings_grid")
                                .min_col_width(180.0)
                                .max_col_width(ui.available_width() - 190.0)
                                .show(ui, |ui| {
                                    ui.label("Host URL:");
                                    ui.add(
                                        egui::TextEdit::singleline(&mut self.host_url)
                                            .desired_width(f32::INFINITY),
                                    );
                                    ui.end_row();

                                    ui.label("");
                                    ui.label(
                                        egui::RichText::new("Example: https://gitlab.com")
                                            .italics()
                                            .small(),
                                    );
                                    ui.end_row();

                                    ui.label("PAT (Personal Access Token):");
                                    ui.add(
                                        egui::TextEdit::singleline(&mut self.pat_token)
                                            .password(true)
                                            .desired_width(f32::INFINITY),
                                    );
                                    ui.end_row();

                                    ui.label("Root Epic Group ID:");
                                    ui.add(
                                        egui::TextEdit::singleline(&mut self.root_group_id)
                                            .desired_width(f32::INFINITY),
                                    );
                                    ui.end_row();
                                });
                        }

                        IntegrationsTab::ProductRouting => {
                            ui.heading("Product Routing & Sync Context");
                            ui.add_space(5.0);

                            let ws_lock = app_ctx.workspace.try_read();
                            if let Ok(workspace) = ws_lock {
                                ui.horizontal(|ui| {
                                    ui.label("Active Product for Sync:");
                                    egui::ComboBox::from_id_salt("active_prod_combo")
                                        .selected_text(&self.active_product_name)
                                        .show_ui(ui, |ui| {
                                            for prod in &workspace.products {
                                                if ui
                                                    .selectable_value(
                                                        &mut self.active_product_name,
                                                        prod.name.clone(),
                                                        &prod.name,
                                                    )
                                                    .clicked()
                                                {
                                                    let mut ws_mut = app_ctx.workspace.try_write();
                                                    if let Ok(ref mut ws) = ws_mut {
                                                        ws.active_product_name =
                                                            Some(prod.name.clone());
                                                    }
                                                }
                                            }
                                        });
                                });

                                ui.separator();
                                ui.label("Registered Products & Mappings:");
                                egui::ScrollArea::vertical()
                                    .id_salt("product_routing_scroll")
                                    .max_height(150.0)
                                    .show(ui, |ui| {
                                        for prod in &workspace.products {
                                            let display = format!(
                                                "Name: {} | Project ID: {} | Group ID: {}",
                                                prod.name,
                                                prod.gitlab_project_id
                                                    .map(|id| id.to_string())
                                                    .unwrap_or_else(|| "None".to_string()),
                                                prod.gitlab_group_id
                                                    .map(|id| id.to_string())
                                                    .unwrap_or_else(|| "None".to_string())
                                            );
                                            let is_sel = self.selected_product.as_deref()
                                                == Some(&prod.name);
                                            if ui.selectable_label(is_sel, &display).clicked() {
                                                self.selected_product = Some(prod.name.clone());
                                            }
                                        }
                                    });

                                ui.add_space(5.0);
                                egui::Grid::new("product_routing_form_grid")
                                    .min_col_width(120.0)
                                    .max_col_width(ui.available_width() - 130.0)
                                    .show(ui, |ui| {
                                        ui.label("Name:");
                                        ui.add(
                                            egui::TextEdit::singleline(&mut self.new_product_name)
                                                .desired_width(f32::INFINITY),
                                        );
                                        ui.end_row();

                                        ui.label("Project ID:");
                                        ui.add(
                                            egui::TextEdit::singleline(&mut self.new_project_id)
                                                .desired_width(f32::INFINITY),
                                        );
                                        ui.end_row();

                                        ui.label("Group ID:");
                                        ui.add(
                                            egui::TextEdit::singleline(&mut self.new_group_id)
                                                .desired_width(f32::INFINITY),
                                        );
                                        ui.end_row();
                                    });

                                ui.horizontal(|ui| {
                                    if ui.button("Add/Update Product").clicked()
                                        && !self.new_product_name.is_empty()
                                    {
                                        let proj_id = self.new_project_id.parse::<i64>().ok();
                                        let grp_id = self.new_group_id.parse::<i64>().ok();
                                        let p_name = self.new_product_name.clone();
                                        let _ = app_ctx.command_bus.try_dispatch(
                                            Command::AddProduct {
                                                product_name: p_name,
                                            },
                                        );
                                        if let Ok(mut ws) = app_ctx.workspace.try_write() {
                                            if let Some(prod) = ws
                                                .products
                                                .iter_mut()
                                                .find(|p| p.name == self.new_product_name)
                                            {
                                                prod.gitlab_project_id = proj_id;
                                                prod.gitlab_group_id = grp_id;
                                            }
                                        }
                                        self.new_product_name.clear();
                                        self.new_project_id.clear();
                                        self.new_group_id.clear();
                                    }
                                    if ui.button("Remove Selected Product").clicked() {
                                        if let Some(p_name) = &self.selected_product {
                                            let _ = app_ctx.command_bus.try_dispatch(
                                                Command::DeleteProduct {
                                                    product_name: p_name.clone(),
                                                },
                                            );
                                            self.selected_product = None;
                                        }
                                    }
                                });
                            }
                        }
                        IntegrationsTab::Capabilities => {
                            ui.heading("Capabilities Pool");
                            ui.label("Global Capabilities List:");

                            let caps = if let Ok(ws) = app_ctx.workspace.try_read() {
                                if ws.capabilities.is_empty() {
                                    vec![
                                        "Core Infrastructure".to_string(),
                                        "Data Analytics".to_string(),
                                        "User Auth".to_string(),
                                        "Reporting".to_string(),
                                    ]
                                } else {
                                    ws.capabilities.clone()
                                }
                            } else {
                                vec![
                                    "Core Infrastructure".to_string(),
                                    "Data Analytics".to_string(),
                                    "User Auth".to_string(),
                                    "Reporting".to_string(),
                                ]
                            };

                            egui::Frame::group(ui.style())
                                .fill(ui.visuals().extreme_bg_color)
                                .show(ui, |ui| {
                                    egui::ScrollArea::vertical()
                                        .id_salt("capabilities_settings_scroll")
                                        .max_height(180.0)
                                        .min_scrolled_height(180.0)
                                        .auto_shrink([false, false])
                                        .show(ui, |ui| {
                                            for cap in &caps {
                                                let is_sel =
                                                    self.selected_capability.as_deref() == Some(cap.as_str());
                                                if ui.selectable_label(is_sel, cap).clicked() {
                                                    self.selected_capability = Some(cap.clone());
                                                }
                                            }
                                        });
                                });

                            ui.add_space(5.0);
                            ui.horizontal(|ui| {
                                let input_width = (ui.available_width() - 250.0).max(100.0);
                                ui.add(
                                    egui::TextEdit::singleline(&mut self.new_capability)
                                        .desired_width(input_width),
                                );
                                if ui.button("Add Capability").clicked()
                                    && !self.new_capability.is_empty()
                                {
                                    let c_name = self.new_capability.clone();
                                    let _ = app_ctx.command_bus.try_dispatch(
                                        Command::AddCapability {
                                            capability_name: c_name.clone(),
                                        },
                                    );
                                    if let Ok(mut ws) = app_ctx.workspace.try_write() {
                                        if ws.capabilities.is_empty() {
                                            ws.capabilities = vec![
                                                "Core Infrastructure".to_string(),
                                                "Data Analytics".to_string(),
                                                "User Auth".to_string(),
                                                "Reporting".to_string(),
                                            ];
                                        }
                                        if !ws.capabilities.contains(&c_name) {
                                            ws.capabilities.push(c_name);
                                        }
                                    }
                                    self.new_capability.clear();
                                }
                                if ui.button("Remove Capability").clicked() {
                                    if let Some(cap) = &self.selected_capability {
                                        let _ = app_ctx.command_bus.try_dispatch(
                                            Command::DeleteCapability {
                                                capability_name: cap.clone(),
                                            },
                                        );
                                        if let Ok(mut ws) = app_ctx.workspace.try_write() {
                                            ws.capabilities.retain(|c| c != cap);
                                        }
                                        self.selected_capability = None;
                                    }
                                }
                            });
                        }
                        IntegrationsTab::SyncLabels => {
                            ui.heading("Sync Labels & Legacy Status");
                            ui.add_space(5.0);

                            ui.horizontal(|ui| {
                                ui.label("Epic Sync Label:");
                                ui.add(
                                    egui::TextEdit::singleline(&mut self.epic_sync_label)
                                        .desired_width(350.0),
                                );
                            });
                            ui.horizontal(|ui| {
                                ui.label("Feature Sync Label:");
                                ui.add(
                                    egui::TextEdit::singleline(&mut self.feature_sync_label)
                                        .desired_width(350.0),
                                );
                            });

                            ui.separator();
                            ui.checkbox(
                                &mut self.legacy_status_enabled,
                                "Enable Legacy Status Indication (Label-based)",
                            );
                            if self.legacy_status_enabled {
                                ui.add_space(5.0);
                                egui::Grid::new("legacy_status_labels_grid")
                                    .min_col_width(120.0)
                                    .show(ui, |ui| {
                                        ui.label("Backlog Label:");
                                        ui.add(
                                            egui::TextEdit::singleline(&mut self.label_backlog)
                                                .desired_width(350.0),
                                        );
                                        ui.end_row();

                                        ui.label("In Progress Label:");
                                        ui.add(
                                            egui::TextEdit::singleline(&mut self.label_in_progress)
                                                .desired_width(350.0),
                                        );
                                        ui.end_row();

                                        ui.label("In Review Label:");
                                        ui.add(
                                            egui::TextEdit::singleline(&mut self.label_in_review)
                                                .desired_width(350.0),
                                        );
                                        ui.end_row();

                                        ui.label("Done Label:");
                                        ui.add(
                                            egui::TextEdit::singleline(&mut self.label_done)
                                                .desired_width(350.0),
                                        );
                                        ui.end_row();

                                        ui.label("Closed Label:");
                                        ui.add(
                                            egui::TextEdit::singleline(&mut self.label_closed)
                                                .desired_width(350.0),
                                        );
                                        ui.end_row();
                                    });
                            }
                        }

                    }

                    ui.add_space(10.0);
                    ui.separator();
                    ui.horizontal(|ui| {
                        if ui.button("Save & Close").clicked() {
                            let settings = IntegrationSettings {
                                auth_url: self.host_url.clone(),
                                auth_pat: self.pat_token.clone(),
                                epic_group_id: self.root_group_id.clone(),
                                epic_sync_label: self.epic_sync_label.clone(),
                                feature_sync_label: self.feature_sync_label.clone(),
                                legacy_status_enabled: self.legacy_status_enabled,
                                label_backlog: self.label_backlog.clone(),
                                label_in_progress: self.label_in_progress.clone(),
                                label_in_review: self.label_in_review.clone(),
                                label_done: self.label_done.clone(),
                                label_closed: self.label_closed.clone(),
                            };
                            SettingsManager::save_integration_settings(&settings);
                            close_dialog = true;
                        }
                        if ui.button("Cancel").clicked() {
                            close_dialog = true;
                        }
                    });
                });
            });

        if !is_open || close_dialog {
            self.is_open = false;
        }
    }
}
