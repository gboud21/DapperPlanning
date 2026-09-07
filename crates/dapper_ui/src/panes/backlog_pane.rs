use dapper_core::{AppContext, Command};
use dapper_domain::Story;

#[derive(Default, Debug)]
pub struct BacklogPane {
    pub search_filter: String,
    pub selected_story_id: Option<String>,
}

impl BacklogPane {
    pub fn ui(&mut self, ui: &mut egui::Ui, ctx: &AppContext) {
        ui.vertical(|ui| {
            ui.horizontal(|ui| {
                ui.label("Search Backlog:");
                ui.text_edit_singleline(&mut self.search_filter);
                if ui.button("Clear").clicked() {
                    self.search_filter.clear();
                }
            });

            ui.separator();

            ui.columns(2, |columns| {
                // Left Column: Hierarchical Tree View
                columns[0].vertical(|ui| {
                    ui.heading("Agile Backlog Tree");
                    egui::ScrollArea::vertical().show(ui, |ui| {
                        let workspace_lock = ctx.workspace.try_read();
                        if let Ok(workspace) = workspace_lock {
                            if workspace.epics.is_empty() {
                                ui.label("No epics found in workspace.");
                            }
                            for epic in &workspace.epics {
                                ui.collapsing(format!("Epic: {}", epic.title), |ui| {
                                    for feature in &epic.features {
                                        ui.collapsing(format!("Feature: {}", feature.title), |ui| {
                                            for story in &feature.stories {
                                                if !self.search_filter.is_empty()
                                                    && !story.title.to_lowercase().contains(&self.search_filter.to_lowercase())
                                                {
                                                    continue;
                                                }
                                                let is_selected = self.selected_story_id.as_deref() == Some(&story.id);
                                                if ui.selectable_label(is_selected, format!("Story: {} (Weight: {})", story.title, story.weight)).clicked() {
                                                    self.selected_story_id = Some(story.id.clone());
                                                }
                                            }
                                        });
                                    }
                                });
                            }
                        } else {
                            ui.label("Loading workspace...");
                        }
                    });
                });

                // Right Column: Story Detail Editor
                columns[1].vertical(|ui| {
                    ui.heading("Story Detail Editor");
                    if let Some(story_id) = &self.selected_story_id {
                        let mut story_to_edit: Option<Story> = None;
                        if let Ok(workspace) = ctx.workspace.try_read() {
                            for epic in &workspace.epics {
                                for feature in &epic.features {
                                    for story in &feature.stories {
                                        if story.id == *story_id {
                                            story_to_edit = Some(story.clone());
                                            break;
                                        }
                                    }
                                }
                            }
                        }

                        if let Some(mut story) = story_to_edit {
                            ui.horizontal(|ui| {
                                ui.label("ID:");
                                ui.label(&story.id);
                            });
                            ui.horizontal(|ui| {
                                ui.label("Title:");
                                if ui.text_edit_singleline(&mut story.title).changed() {
                                    let _ = ctx.command_bus.try_dispatch(Command::UpdateStory {
                                        story: story.clone(),
                                    });
                                }
                            });
                            ui.horizontal(|ui| {
                                ui.label("Status:");
                                ui.label(&story.status);
                            });
                            ui.horizontal(|ui| {
                                ui.label("Weight:");
                                if ui.add(egui::DragValue::new(&mut story.weight)).changed() {
                                    let _ = ctx.command_bus.try_dispatch(Command::UpdateStory {
                                        story: story.clone(),
                                    });
                                }
                            });
                            ui.label("Description:");
                            if ui.text_edit_multiline(&mut story.description).changed() {
                                let _ = ctx.command_bus.try_dispatch(Command::UpdateStory {
                                    story: story.clone(),
                                });
                            }
                        } else {
                            ui.label("Select a story from the tree to edit details.");
                        }
                    } else {
                        ui.label("Select a story from the tree to edit details.");
                    }
                });
            });
        });
    }
}
