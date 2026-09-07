use crate::dialogs::conflict_modal::ConflictResolutionModal;
use crate::dialogs::dry_push_modal::DryPushModal;
use crate::dialogs::settings_dialog::SettingsDialog;
use crate::panes::backlog_pane::BacklogPane;
use crate::panes::pi_planner_pane::PiPlannerPane;
use dapper_core::{AppContext, Command, Event};
use dapper_domain::{RolePermissionManager, ViewName};
use eframe::App;
use std::path::PathBuf;
use tokio::sync::broadcast::Receiver;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ActiveTab {
    Backlog,
    PiPlanner,
}

pub struct DapperApp {
    pub app_context: AppContext,
    pub active_tab: ActiveTab,
    pub backlog_pane: BacklogPane,
    pub pi_planner_pane: PiPlannerPane,
    pub settings_dialog: SettingsDialog,
    pub dry_push_modal: DryPushModal,
    pub conflict_modal: ConflictResolutionModal,
    pub about_open: bool,
    pub event_rx: Receiver<Event>,
}

impl DapperApp {
    pub fn new(app_context: AppContext) -> Self {
        let event_rx = app_context.event_dispatcher.subscribe();
        Self {
            app_context,
            active_tab: ActiveTab::Backlog,
            backlog_pane: BacklogPane::default(),
            pi_planner_pane: PiPlannerPane::default(),
            settings_dialog: SettingsDialog::default(),
            dry_push_modal: DryPushModal::default(),
            conflict_modal: ConflictResolutionModal::default(),
            about_open: false,
            event_rx,
        }
    }

    fn poll_events(&mut self) {
        while let Ok(event) = self.event_rx.try_recv() {
            match event {
                Event::DryPushCompleted { summary, .. } => {
                    self.dry_push_modal.is_open = true;
                    tracing::info!("UI Received DryPushCompleted: {}", summary);
                }
                Event::ConflictDetected { item_id } => {
                    self.conflict_modal.conflicted_item_id = Some(item_id);
                    self.conflict_modal.is_open = true;
                }
                _ => {}
            }
        }
    }
}

impl App for DapperApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.poll_events();

        // 1. Top Menu Bar
        egui::TopBottomPanel::top("top_menu_bar").show(ctx, |ui| {
            egui::menu::bar(ui, |ui| {
                // File Menu
                ui.menu_button("File", |ui| {
                    if ui.button("New Workspace\tCtrl+N").clicked() {
                        let _ = self.app_context.command_bus.try_dispatch(Command::NewWorkspace);
                        ui.close_menu();
                    }

                    if ui.button("Open Workspace...\tCtrl+O").clicked() {
                        if let Some(path) = rfd::FileDialog::new()
                            .add_filter("JSON Workspace", &["json"])
                            .add_filter("CSV Files", &["csv"])
                            .pick_file()
                        {
                            let _ = self.app_context.command_bus.try_dispatch(Command::LoadWorkspace { path });
                        }
                        ui.close_menu();
                    }

                    if ui.button("Save Workspace\tCtrl+S").clicked() {
                        let _ = self.app_context.command_bus.try_dispatch(Command::SaveWorkspace {
                            path: PathBuf::from("workspace.json"),
                        });
                        ui.close_menu();
                    }

                    if ui.button("Save Workspace As...\tCtrl+Shift+S").clicked() {
                        if let Some(path) = rfd::FileDialog::new()
                            .add_filter("JSON Workspace", &["json"])
                            .set_file_name("workspace.json")
                            .save_file()
                        {
                            let _ = self.app_context.command_bus.try_dispatch(Command::SaveWorkspaceAs { path });
                        }
                        ui.close_menu();
                    }

                    ui.separator();

                    if ui.button("Import...").clicked() {
                        if let Some(path) = rfd::FileDialog::new()
                            .add_filter("JSON Workspace", &["json"])
                            .add_filter("CSV Files", &["csv"])
                            .pick_file()
                        {
                            let format = path
                                .extension()
                                .and_then(|s| s.to_str())
                                .unwrap_or("json")
                                .to_string();
                            let _ = self.app_context.command_bus.try_dispatch(Command::ImportWorkspace { path, format });
                        }
                        ui.close_menu();
                    }

                    ui.separator();

                    if ui.button("Export...").clicked() {
                        if let Some(path) = rfd::FileDialog::new()
                            .add_filter("JSON Workspace", &["json"])
                            .add_filter("CSV Files", &["csv"])
                            .set_file_name("exported_workspace.json")
                            .save_file()
                        {
                            let format = path
                                .extension()
                                .and_then(|s| s.to_str())
                                .unwrap_or("json")
                                .to_string();
                            let _ = self.app_context.command_bus.try_dispatch(Command::ExportWorkspace { path, format });
                        }
                        ui.close_menu();
                    }

                    ui.separator();

                    if ui.button("Preferences...").clicked() {
                        self.settings_dialog.is_open = true;
                        ui.close_menu();
                    }

                    ui.separator();

                    if ui.button("Exit").clicked() {
                        ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                    }
                });

                // Edit Menu
                ui.menu_button("Edit", |ui| {
                    let has_selected_story = self.backlog_pane.selected_story_id.is_some();
                    if ui.add_enabled(has_selected_story, egui::Button::new("Clone Selected Story")).clicked() {
                        if let Some(story_id) = &self.backlog_pane.selected_story_id {
                            let _ = self.app_context.command_bus.try_dispatch(Command::CloneStory {
                                story_id: story_id.clone(),
                            });
                        }
                        ui.close_menu();
                    }

                    if ui.add_enabled(has_selected_story, egui::Button::new("Split Selected Story")).clicked() {
                        if let Some(story_id) = &self.backlog_pane.selected_story_id {
                            let _ = self.app_context.command_bus.try_dispatch(Command::SplitStory {
                                story_id: story_id.clone(),
                                split_weight: 2.0,
                            });
                        }
                        ui.close_menu();
                    }

                    ui.separator();
                    if ui.button("Copy\tCtrl+C").clicked() {
                        ui.close_menu();
                    }
                    if ui.button("Cut\tCtrl+X").clicked() {
                        ui.close_menu();
                    }
                    if ui.button("Paste\tCtrl+V").clicked() {
                        ui.close_menu();
                    }
                });

                // GitLab Integrations Menu
                ui.menu_button("GitLab Integrations", |ui| {
                    if ui.button("Trigger GitLab Pull\tCtrl+Shift+L").clicked() {
                        let _ = self.app_context.command_bus.try_dispatch(Command::TriggerGitLabPull);
                        ui.close_menu();
                    }
                    if ui.button("Run Dry Push Simulation\tCtrl+Shift+D").clicked() {
                        let _ = self.app_context.command_bus.try_dispatch(Command::TriggerDryPush);
                        ui.close_menu();
                    }
                    if ui.button("Trigger GitLab Push\tCtrl+Shift+P").clicked() {
                        let _ = self.app_context.command_bus.try_dispatch(Command::TriggerGitLabPush);
                        ui.close_menu();
                    }
                });

                // Help Menu
                ui.menu_button("Help", |ui| {
                    if ui.button("About DapperPlanning").clicked() {
                        self.about_open = true;
                        ui.close_menu();
                    }
                });

                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    egui::widgets::global_theme_preference_buttons(ui);
                });
            });
        });

        // 2. Navigation Tab Bar
        egui::TopBottomPanel::top("navigation_tab_bar").show(ctx, |ui| {
            ui.horizontal(|ui| {
                if RolePermissionManager::is_view_visible(self.settings_dialog.active_role, ViewName::Backlog)
                    && ui.selectable_label(self.active_tab == ActiveTab::Backlog, "Agile Backlog").clicked()
                {
                    self.active_tab = ActiveTab::Backlog;
                }

                if RolePermissionManager::is_view_visible(self.settings_dialog.active_role, ViewName::PiPlanner)
                    && ui.selectable_label(self.active_tab == ActiveTab::PiPlanner, "PI Planner").clicked()
                {
                    self.active_tab = ActiveTab::PiPlanner;
                }
            });
        });

        // 3. Main Content Panel
        egui::CentralPanel::default().show(ctx, |ui| {
            match self.active_tab {
                ActiveTab::Backlog => self.backlog_pane.ui(ui, &self.app_context),
                ActiveTab::PiPlanner => self.pi_planner_pane.ui(ui, &self.app_context),
            }
        });

        // 4. Modal Dialog Windows
        self.settings_dialog.ui(ctx);
        self.dry_push_modal.ui(ctx, &self.app_context);
        self.conflict_modal.ui(ctx, &self.app_context);

        // 5. About Dialog Window
        if self.about_open {
            let mut about_open = self.about_open;
            let mut close_about = false;

            egui::Window::new("About DapperPlanning")
                .collapsible(false)
                .resizable(false)
                .default_size([400.0, 200.0])
                .open(&mut about_open)
                .show(ctx, |ui| {
                    ui.vertical_centered(|ui| {
                        ui.heading("DapperPlanning v1.0.0");
                        ui.label("Native Cross-Platform Agile & PI Planning Application in Rust.");
                        ui.add_space(10.0);
                        ui.label("CQRS Architecture with Tokio Async Engine & egui GUI.");
                        ui.add_space(15.0);
                        if ui.button("Close").clicked() {
                            close_about = true;
                        }
                    });
                });

            if !about_open || close_about {
                self.about_open = false;
            }
        }
    }
}
