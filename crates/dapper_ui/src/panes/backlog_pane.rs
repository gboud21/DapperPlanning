use dapper_core::{AppContext, Command};
use dapper_domain::{Feature, Label, Story};


#[derive(Debug, Clone, PartialEq)]
pub enum SelectedItem {
    Epic(String),
    Feature(String),
    Story(String),
}

pub struct BacklogPane {
    pub search_filter: String,
    pub selected_item: Option<SelectedItem>,

    // Template parameters
    pub tool: String,
    pub methodology: String,
    pub desc_type: String,
    pub include_out_of_scope: bool,
    pub include_compliance: bool,

    // Dual-listbox entries & state
    pub new_product_name: String,
    pub new_capability_name: String,
    pub new_label_name: String,

    pub selected_avail_product: Option<String>,
    pub selected_assigned_product: Option<String>,
    pub selected_avail_capability: Option<String>,
    pub selected_assigned_capability: Option<String>,
    pub selected_avail_label: Option<String>,
    pub selected_assigned_label: Option<String>,
}

impl Default for BacklogPane {
    fn default() -> Self {
        Self {
            search_filter: String::new(),
            selected_item: None,
            tool: "GitLab".to_string(),
            methodology: "Scrum".to_string(),
            desc_type: "Heavyweight".to_string(),
            include_out_of_scope: false,
            include_compliance: false,
            new_product_name: String::new(),
            new_capability_name: String::new(),
            new_label_name: String::new(),
            selected_avail_product: None,
            selected_assigned_product: None,
            selected_avail_capability: None,
            selected_assigned_capability: None,
            selected_avail_label: None,
            selected_assigned_label: None,
        }
    }
}

pub fn generate_template(
    item_type: &str,
    tool: &str,
    desc_type: &str,
    out_of_scope: bool,
    compliance: bool,
) -> String {
    let is_jira = tool.eq_ignore_ascii_case("jira");
    let is_heavy = desc_type.eq_ignore_ascii_case("heavyweight");

    let mut out = String::new();

    match (item_type, is_heavy) {
        ("Epic", true) => {
            if is_jira {
                out.push_str("h2. Executive Summary\nProvide a high-level overview of this Epic. What are we building, and why does it matter to the organization?\n\n");
                out.push_str("h2. Business Value\n* *Objective:* \n* *Key Results (KPIs):* \n\n");
                out.push_str("h2. Acceptance Criteria\n* ( ) *Scenario 1:* Given [context], When [event], Then [outcome]\n* ( ) *Scenario 2:* \n\n");
                out.push_str("h2. Dependencies\n* *Upstream:* \n* *Downstream:* \n\n");
                out.push_str("h2. Target Audience\nIdentify the primary users (e.g., Engineering Teams, External Customers).\n\n");
            } else {
                out.push_str("## Executive Summary\nProvide a high-level overview of this Epic. What are we building, and why does it matter to the organization?\n\n");
                out.push_str("## Business Value\n- **Objective:** \n- **Key Results (KPIs):** \n\n");
                out.push_str("## Acceptance Criteria\n- [ ] **Scenario 1:** Given [context], When [event], Then [outcome]\n- [ ] **Scenario 2:** \n\n");
                out.push_str("## Dependencies\n- **Upstream:** \n- **Downstream:** \n\n");
                out.push_str("## Target Audience\nIdentify the primary users (e.g., Engineering Teams, External Customers).\n\n");
            }
        }
        ("Epic", false) => {
            if is_jira {
                out.push_str("h2. Executive Summary\nProvide a high-level overview of this Epic.\n\n");
                out.push_str("h2. Acceptance Criteria\n* ( ) *Scenario 1:*\n\n");
            } else {
                out.push_str("## Executive Summary\nProvide a high-level overview of this Epic.\n\n");
                out.push_str("## Acceptance Criteria\n- [ ] **Scenario 1:**\n\n");
            }
        }
        ("Feature", true) => {
            if is_jira {
                out.push_str("h2. Feature Description\nDescribe the functionality being delivered in this feature and how it fits into the broader Epic.\n\n");
                out.push_str("h2. User Impact\nHow will this change the user experience or workflow?\n\n");
                out.push_str("h2. Acceptance Criteria\n* ( ) *Scenario 1:* Given [context], When [event], Then [outcome]\n\n");
                out.push_str("h2. Technical Notes / Implementation Details\n* Architecture considerations:\n* API endpoints affected:\n\n");
            } else {
                out.push_str("## Feature Description\nDescribe the functionality being delivered in this feature and how it fits into the broader Epic.\n\n");
                out.push_str("## User Impact\nHow will this change the user experience or workflow?\n\n");
                out.push_str("## Acceptance Criteria\n- [ ] **Scenario 1:** Given [context], When [event], Then [outcome]\n\n");
                out.push_str("## Technical Notes / Implementation Details\n- Architecture considerations:\n- API endpoints affected:\n\n");
            }
        }
        ("Feature", false) => {
            if is_jira {
                out.push_str("h2. Feature Description\nDescribe the functionality.\n\n");
                out.push_str("h2. Acceptance Criteria\n* ( ) *Scenario 1:*\n\n");
            } else {
                out.push_str("## Feature Description\nDescribe the functionality.\n\n");
                out.push_str("## Acceptance Criteria\n- [ ] **Scenario 1:**\n\n");
            }
        }
        ("Story", true) => {
            if is_jira {
                out.push_str("h2. User Story\n*As a* [role/persona], \n*I want* [action/feature], \n*So that* [value/benefit].\n\n");
                out.push_str("h2. Acceptance Criteria\n* ( ) *Scenario 1:* Given [context], When [event], Then [outcome]\n\n");
                out.push_str("h2. Technical Notes / Implementation Details\n* Architecture considerations:\n\n");
                out.push_str("h2. Testing Notes\n* Edge cases to consider:\n\n");
            } else {
                out.push_str("## User Story\n**As a** [role/persona], \n**I want** [action/feature], \n**So that** [value/benefit].\n\n");
                out.push_str("## Acceptance Criteria\n- [ ] **Scenario 1:** Given [context], When [event], Then [outcome]\n\n");
                out.push_str("## Technical Notes / Implementation Details\n- Architecture considerations:\n\n");
                out.push_str("## Testing Notes\n- Edge cases to consider:\n\n");
            }
        }
        _ => {
            if is_jira {
                out.push_str("h2. User Story\n*As a* [role/persona], \n*I want* [action/feature], \n*So that* [value/benefit].\n\n");
            } else {
                out.push_str("## User Story\n**As a** [role/persona], \n**I want** [action/feature], \n**So that** [value/benefit].\n\n");
            }
        }
    }

    if out_of_scope {
        if is_jira {
            out.push_str("h2. Out of Scope\nExplicitly state what is NOT being delivered:\n* \n\n");
        } else {
            out.push_str("## Out of Scope\nExplicitly state what is NOT being delivered as part of this item to prevent scope creep:\n- [ ] \n\n");
        }
    }

    if compliance {
        if is_jira {
            out.push_str("h2. Security & Compliance\n* ( ) Does this impact PII/PHI?\n* ( ) Is a security review required?\n\n");
        } else {
            out.push_str("## Security & Compliance\n- [ ] Does this impact PII/PHI?\n- [ ] Is a security review required?\n- [ ] SOC2 / GDPR implications?\n\n");
        }
    }

    out
}

impl BacklogPane {
    pub fn selected_story_id(&self) -> Option<String> {
        if let Some(SelectedItem::Story(id)) = &self.selected_item {
            Some(id.clone())
        } else {
            None
        }
    }

    pub fn ui(&mut self, ui: &mut egui::Ui, ctx: &AppContext) {

        ui.vertical(|ui| {
            // Search Bar
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
                    egui::ScrollArea::vertical()
                        .id_salt("agile_tree_scroll_area")
                        .show(ui, |ui| {
                            let workspace_lock = ctx.workspace.try_read();
                            if let Ok(workspace) = workspace_lock {
                                if workspace.epics.is_empty() {
                                    ui.label("No epics found in workspace.");
                                }
                                for epic in &workspace.epics {
                                    let is_epic_selected = self.selected_item
                                        == Some(SelectedItem::Epic(epic.id.clone()));
                                    let epic_label = format!("Epic: {}", epic.title);

                                    ui.horizontal(|ui| {
                                        if ui
                                            .selectable_label(is_epic_selected, &epic_label)
                                            .clicked()
                                        {
                                            self.selected_item =
                                                Some(SelectedItem::Epic(epic.id.clone()));
                                        }
                                    });

                                    ui.indent(epic.id.clone(), |ui| {
                                        for feature in &epic.features {
                                            let is_feat_selected = self.selected_item
                                                == Some(SelectedItem::Feature(feature.id.clone()));
                                            let feat_label = format!("Feature: {}", feature.title);

                                            if ui
                                                .selectable_label(is_feat_selected, &feat_label)
                                                .clicked()
                                            {
                                                self.selected_item = Some(SelectedItem::Feature(
                                                    feature.id.clone(),
                                                ));
                                            }

                                            ui.indent(feature.id.clone(), |ui| {
                                                for story in &feature.stories {
                                                    if !self.search_filter.is_empty()
                                                        && !story.title.to_lowercase().contains(
                                                            &self.search_filter.to_lowercase(),
                                                        )
                                                    {
                                                        continue;
                                                    }
                                                    let is_story_selected = self.selected_item
                                                        == Some(SelectedItem::Story(
                                                            story.id.clone(),
                                                        ));
                                                    let story_label = format!(
                                                        "Story: {} (Weight: {})",
                                                        story.title, story.weight
                                                    );

                                                    if ui
                                                        .selectable_label(
                                                            is_story_selected,
                                                            &story_label,
                                                        )
                                                        .clicked()
                                                    {
                                                        self.selected_item = Some(
                                                            SelectedItem::Story(story.id.clone()),
                                                        );
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

                // Right Column: Issue Detail Editor
                columns[1].vertical(|ui| {
                    egui::ScrollArea::vertical()
                        .id_salt("issue_editor_scroll_area")
                        .show(ui, |ui| {
                            if let Some(selected) = &self.selected_item {
                                self.render_editor(ui, ctx, selected.clone());
                            } else {
                                ui.heading("Issue Detail Editor");
                                ui.label(
                                    "Select an Epic, Feature, or Story from the tree to edit details.",
                                );
                            }
                        });
                });

            });
        });
    }

    fn render_editor(&mut self, ui: &mut egui::Ui, ctx: &AppContext, selected: SelectedItem) {
        let (item_type_name, id) = match &selected {
            SelectedItem::Epic(id) => ("Epic", id.clone()),
            SelectedItem::Feature(id) => ("Feature", id.clone()),
            SelectedItem::Story(id) => ("Story", id.clone()),
        };

        ui.heading(format!("Editing {}", item_type_name));
        ui.separator();

        // --- Template Parameters Frame ---
        ui.group(|ui| {
            ui.label(egui::RichText::new("Template Parameters").strong());
            egui::Grid::new("template_params_grid").show(ui, |ui| {

                ui.label("Tool:");
                egui::ComboBox::from_id_salt("combo_tool")
                    .selected_text(&self.tool)
                    .show_ui(ui, |ui| {
                        ui.selectable_value(&mut self.tool, "GitLab".to_string(), "GitLab");
                        ui.selectable_value(&mut self.tool, "Jira".to_string(), "Jira");
                    });

                ui.label("Methodology:");
                egui::ComboBox::from_id_salt("combo_methodology")
                    .selected_text(&self.methodology)
                    .show_ui(ui, |ui| {
                        ui.selectable_value(&mut self.methodology, "Scrum".to_string(), "Scrum");
                        ui.selectable_value(&mut self.methodology, "Kanban".to_string(), "Kanban");
                        ui.selectable_value(&mut self.methodology, "SAFe".to_string(), "SAFe");
                    });
                ui.end_row();

                ui.label("Type:");
                egui::ComboBox::from_id_salt("combo_desc_type")
                    .selected_text(&self.desc_type)
                    .show_ui(ui, |ui| {
                        ui.selectable_value(
                            &mut self.desc_type,
                            "Heavyweight".to_string(),
                            "Heavyweight",
                        );
                        ui.selectable_value(
                            &mut self.desc_type,
                            "Lightweight".to_string(),
                            "Lightweight",
                        );
                    });
                ui.end_row();
            });

            ui.horizontal(|ui| {
                ui.checkbox(&mut self.include_out_of_scope, "Include Out of Scope");
                ui.checkbox(&mut self.include_compliance, "Include Compliance & Security");
            });
        });

        ui.add_space(5.0);

        // Fetch workspace data safely
        let ws_lock = ctx.workspace.try_read();
        let Ok(workspace) = ws_lock else {
            ui.label("Workspace locked...");
            return;
        };

        // Find selected model item
        match selected {
            SelectedItem::Epic(epic_id) => {
                let Some(epic) = workspace.epics.iter().find(|e| e.id == epic_id) else {
                    return;
                };
                let mut epic = epic.clone();

                ui.horizontal(|ui| {
                    ui.label("ID:");
                    ui.label(&epic.id);
                });

                let mut title_changed = false;
                ui.horizontal(|ui| {
                    ui.label("Title:");
                    title_changed = ui.text_edit_singleline(&mut epic.title).changed();
                });

                ui.horizontal(|ui| {
                    if ui.button("Generate Description Template").clicked() {
                        epic.description = generate_template(
                            "Epic",
                            &self.tool,
                            &self.desc_type,
                            self.include_out_of_scope,
                            self.include_compliance,
                        );
                        title_changed = true;
                    }
                });

                ui.label("Description:");
                let desc_changed = ui.text_edit_multiline(&mut epic.description).changed();

                // Render Tag Managers
                let tag_changed = self.render_tag_managers(
                    ui,
                    ctx,
                    &workspace.products,
                    &mut epic.products,
                    &mut epic.capabilities,
                    &workspace.labels,
                    &mut epic.labels,
                );

                if title_changed || desc_changed || tag_changed {
                    let _ = ctx.command_bus.try_dispatch(Command::UpdateEpic { epic });
                }

                ui.add_space(10.0);
                if ui.button("Create Feature under Epic").clicked() {
                    let new_feature = Feature {
                        id: format!("feat-{}", uuid::Uuid::new_v4()),
                        title: "New Feature".to_string(),
                        description: "".to_string(),
                        team: None,
                        stories: vec![],
                        metadata: None,
                        labels: vec![],
                        products: vec![],
                        capabilities: vec![],
                        parent_epic_id: Some(id.clone()),
                        gitlab_id: None,
                        gitlab_iid: None,
                        last_synced_at: None,
                        is_conflicted: false,
                    };
                    let _ = ctx.command_bus.try_dispatch(Command::CreateFeature {
                        parent_epic_id: id,
                        feature: new_feature,
                    });
                }
            }
            SelectedItem::Feature(feat_id) => {
                let mut found_feature: Option<Feature> = None;
                for e in &workspace.epics {
                    for f in &e.features {
                        if f.id == feat_id {
                            found_feature = Some(f.clone());
                            break;
                        }
                    }
                }
                let Some(mut feature) = found_feature else {
                    return;
                };

                ui.horizontal(|ui| {
                    ui.label("ID:");
                    ui.label(&feature.id);
                });

                let mut title_changed = false;
                ui.horizontal(|ui| {
                    ui.label("Title:");
                    title_changed = ui.text_edit_singleline(&mut feature.title).changed();
                });

                ui.horizontal(|ui| {
                    if ui.button("Generate Description Template").clicked() {
                        feature.description = generate_template(
                            "Feature",
                            &self.tool,
                            &self.desc_type,
                            self.include_out_of_scope,
                            self.include_compliance,
                        );
                        title_changed = true;
                    }
                });

                ui.label("Description:");
                let desc_changed = ui.text_edit_multiline(&mut feature.description).changed();

                let tag_changed = self.render_tag_managers(
                    ui,
                    ctx,
                    &workspace.products,
                    &mut feature.products,
                    &mut feature.capabilities,
                    &workspace.labels,
                    &mut feature.labels,
                );

                if title_changed || desc_changed || tag_changed {
                    let _ = ctx
                        .command_bus
                        .try_dispatch(Command::UpdateFeature { feature });
                }

                ui.add_space(10.0);
                if ui.button("Create Story under Feature").clicked() {
                    let new_story = Story {
                        id: format!("story-{}", uuid::Uuid::new_v4()),
                        title: "New Story".to_string(),
                        description: "".to_string(),
                        team: None,
                        metadata: None,
                        labels: vec![],
                        interface_boundary: None,
                        products: vec![],
                        capabilities: vec![],
                        weight: 1.0,
                        status: "Backlog".to_string(),
                        assignee_id: None,
                        iteration_id: None,
                        parent_feature_id: Some(id.clone()),
                        gitlab_id: None,
                        gitlab_iid: None,
                        last_synced_at: None,
                        is_conflicted: false,
                    };
                    let _ = ctx.command_bus.try_dispatch(Command::CreateStory {
                        parent_feature_id: id,
                        story: new_story,
                    });
                }
            }
            SelectedItem::Story(story_id) => {
                let mut found_story: Option<Story> = None;
                for e in &workspace.epics {
                    for f in &e.features {
                        for s in &f.stories {
                            if s.id == story_id {
                                found_story = Some(s.clone());
                                break;
                            }
                        }
                    }
                }
                let Some(mut story) = found_story else {
                    return;
                };

                ui.horizontal(|ui| {
                    ui.label("ID:");
                    ui.label(&story.id);
                });

                let mut is_changed = false;
                ui.horizontal(|ui| {
                    ui.label("Title:");
                    if ui.text_edit_singleline(&mut story.title).changed() {
                        is_changed = true;
                    }
                });

                // Assignee Combobox
                ui.horizontal(|ui| {
                    ui.label("Assignee:");
                    let current_assignee_name = story
                        .assignee_id
                        .and_then(|aid| workspace.members.iter().find(|m| m.id == aid))
                        .map(|m| m.name.clone())
                        .unwrap_or_else(|| "Unassigned".to_string());

                    egui::ComboBox::from_id_salt("story_assignee")
                        .selected_text(&current_assignee_name)
                        .show_ui(ui, |ui| {
                            if ui
                                .selectable_label(story.assignee_id.is_none(), "Unassigned")
                                .clicked()
                            {
                                story.assignee_id = None;
                                is_changed = true;
                            }
                            for member in &workspace.members {
                                let is_sel = story.assignee_id == Some(member.id);
                                if ui.selectable_label(is_sel, &member.name).clicked() {
                                    story.assignee_id = Some(member.id);
                                    is_changed = true;
                                }
                            }
                        });
                });

                // Iteration Combobox
                ui.horizontal(|ui| {
                    ui.label("Iteration:");
                    let current_iter_title = story
                        .iteration_id
                        .and_then(|iid| workspace.iterations.iter().find(|it| it.id == iid))
                        .map(|it| it.title.clone())
                        .unwrap_or_else(|| "Unassigned".to_string());

                    egui::ComboBox::from_id_salt("story_iteration")
                        .selected_text(&current_iter_title)
                        .show_ui(ui, |ui| {
                            if ui
                                .selectable_label(story.iteration_id.is_none(), "Unassigned")
                                .clicked()
                            {
                                story.iteration_id = None;
                                is_changed = true;
                            }
                            for iter in &workspace.iterations {
                                let is_sel = story.iteration_id == Some(iter.id);
                                if ui.selectable_label(is_sel, &iter.title).clicked() {
                                    story.iteration_id = Some(iter.id);
                                    is_changed = true;
                                }
                            }
                        });
                });

                ui.horizontal(|ui| {
                    ui.label("Weight:");
                    if ui.add(egui::DragValue::new(&mut story.weight)).changed() {
                        is_changed = true;
                    }
                });

                ui.horizontal(|ui| {
                    ui.label("Status:");
                    egui::ComboBox::from_id_salt("story_status")
                        .selected_text(&story.status)
                        .show_ui(ui, |ui| {
                            for status_opt in &[
                                "Backlog",
                                "In Progress",
                                "In Review",
                                "Done",
                                "Closed",
                            ] {
                                if ui
                                    .selectable_value(
                                        &mut story.status,
                                        status_opt.to_string(),
                                        *status_opt,
                                    )
                                    .changed()
                                {
                                    is_changed = true;
                                }
                            }
                        });
                });

                ui.horizontal(|ui| {
                    if ui.button("Generate Description Template").clicked() {
                        story.description = generate_template(
                            "Story",
                            &self.tool,
                            &self.desc_type,
                            self.include_out_of_scope,
                            self.include_compliance,
                        );
                        is_changed = true;
                    }
                });

                ui.label("Description:");
                if ui.text_edit_multiline(&mut story.description).changed() {
                    is_changed = true;
                }

                let tag_changed = self.render_tag_managers(
                    ui,
                    ctx,
                    &workspace.products,
                    &mut story.products,
                    &mut story.capabilities,
                    &workspace.labels,
                    &mut story.labels,
                );

                if is_changed || tag_changed {
                    let _ = ctx.command_bus.try_dispatch(Command::UpdateStory { story });
                }
            }
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn render_tag_managers(

        &mut self,
        ui: &mut egui::Ui,
        ctx: &AppContext,
        workspace_products: &[dapper_domain::Product],
        item_products: &mut Vec<String>,
        item_capabilities: &mut Vec<String>,
        workspace_labels: &std::collections::HashMap<String, Label>,
        item_labels: &mut Vec<String>,
    ) -> bool {
        let mut changed = false;

        ui.add_space(10.0);
        ui.separator();

        // 1. Products Dual-Listbox / Manager
        ui.group(|ui| {
            ui.label(egui::RichText::new("Products Tag Manager").strong());
            ui.columns(2, |cols| {
                cols[0].vertical(|ui| {
                    ui.label("Available Products");
                    egui::ScrollArea::vertical()
                        .id_salt("products_available_scroll_area")
                        .max_height(100.0)
                        .show(ui, |ui| {
                            for p in workspace_products {
                                let is_sel = self.selected_avail_product.as_deref() == Some(&p.name);
                                if ui.selectable_label(is_sel, &p.name).clicked() {
                                    self.selected_avail_product = Some(p.name.clone());
                                }
                            }
                        });

                    ui.horizontal(|ui| {
                        ui.text_edit_singleline(&mut self.new_product_name);
                        if ui.button("Add").clicked() && !self.new_product_name.is_empty() {
                            let _ = ctx.command_bus.try_dispatch(Command::AddProduct {
                                product_name: self.new_product_name.clone(),
                            });
                            self.new_product_name.clear();
                        }
                        if ui.button("Delete").clicked() {
                            if let Some(p_name) = &self.selected_avail_product {
                                let _ = ctx.command_bus.try_dispatch(Command::DeleteProduct {
                                    product_name: p_name.clone(),
                                });
                                self.selected_avail_product = None;
                            }
                        }
                    });
                });

                cols[1].vertical(|ui| {
                    ui.label("Assigned Products");
                    ui.horizontal(|ui| {
                        if ui.button(">>").clicked() {
                            if let Some(p_name) = &self.selected_avail_product {
                                if !item_products.contains(p_name) {
                                    item_products.push(p_name.clone());
                                    changed = true;
                                }
                            }
                        }
                        if ui.button("Remove").clicked() {
                            if let Some(p_name) = &self.selected_assigned_product {
                                item_products.retain(|p| p != p_name);
                                self.selected_assigned_product = None;
                                changed = true;
                            }
                        }
                    });

                    egui::ScrollArea::vertical()
                        .id_salt("products_assigned_scroll_area")
                        .max_height(100.0)
                        .show(ui, |ui| {
                            for p_name in item_products.iter() {
                                let is_sel = self.selected_assigned_product.as_deref() == Some(p_name);
                                if ui.selectable_label(is_sel, p_name).clicked() {
                                    self.selected_assigned_product = Some(p_name.clone());
                                }
                            }
                        });
                });
            });
        });

        ui.add_space(5.0);

        // 2. Capabilities Dual-Listbox / Manager
        ui.group(|ui| {
            ui.label(egui::RichText::new("Capabilities Tag Manager").strong());
            ui.columns(2, |cols| {
                cols[0].vertical(|ui| {
                    ui.label("Available Capabilities");
                    egui::ScrollArea::vertical()
                        .id_salt("capabilities_available_scroll_area")
                        .max_height(100.0)
                        .show(ui, |ui| {
                            let master_caps = vec![
                                "Core Infrastructure",
                                "Data Analytics",
                                "User Auth",
                                "Reporting",
                            ];
                            for cap in master_caps {
                                let is_sel = self.selected_avail_capability.as_deref() == Some(cap);
                                if ui.selectable_label(is_sel, cap).clicked() {
                                    self.selected_avail_capability = Some(cap.to_string());
                                }
                            }
                        });
                });

                cols[1].vertical(|ui| {
                    ui.label("Assigned Capabilities");
                    ui.horizontal(|ui| {
                        if ui.button(">>").clicked() {
                            if let Some(cap) = &self.selected_avail_capability {
                                if !item_capabilities.contains(cap) {
                                    item_capabilities.push(cap.clone());
                                    changed = true;
                                }
                            }
                        }
                        if ui.button("Remove").clicked() {
                            if let Some(cap) = &self.selected_assigned_capability {
                                item_capabilities.retain(|c| c != cap);
                                self.selected_assigned_capability = None;
                                changed = true;
                            }
                        }
                    });

                    egui::ScrollArea::vertical()
                        .id_salt("capabilities_assigned_scroll_area")
                        .max_height(100.0)
                        .show(ui, |ui| {
                            for cap in item_capabilities.iter() {
                                let is_sel = self.selected_assigned_capability.as_deref() == Some(cap);
                                if ui.selectable_label(is_sel, cap).clicked() {
                                    self.selected_assigned_capability = Some(cap.clone());
                                }
                            }
                        });
                });
            });
        });

        ui.add_space(5.0);

        // 3. GitLab Labels Dual-Listbox / Manager
        ui.group(|ui| {
            ui.label(egui::RichText::new("GitLab Labels").strong());
            ui.columns(2, |cols| {
                cols[0].vertical(|ui| {
                    ui.label("Available Labels");
                    egui::ScrollArea::vertical()
                        .id_salt("labels_available_scroll_area")
                        .max_height(100.0)
                        .show(ui, |ui| {
                            for (lbl_name, lbl) in workspace_labels {
                                let scope = lbl.scope_name.as_deref().unwrap_or("group");
                                let display = format!("({}) {}", scope, lbl_name);
                                let is_sel = self.selected_avail_label.as_deref() == Some(lbl_name);
                                if ui.selectable_label(is_sel, &display).clicked() {
                                    self.selected_avail_label = Some(lbl_name.clone());
                                }
                            }
                        });

                    ui.horizontal(|ui| {
                        ui.text_edit_singleline(&mut self.new_label_name);
                        if ui.button("Create Local Label").clicked()
                            && !self.new_label_name.is_empty()
                        {
                            let new_lbl = Label {
                                id: None,
                                name: self.new_label_name.clone(),
                                color: Some("#666666".to_string()),
                                description: Some("Locally created label".to_string()),
                                scope: Some("group".to_string()),
                                scope_name: Some("group".to_string()),
                            };
                            let _ = ctx.command_bus.try_dispatch(Command::AddLocalLabel {
                                label: new_lbl,
                            });
                            self.new_label_name.clear();
                        }
                    });
                });

                cols[1].vertical(|ui| {
                    ui.label("Assigned Labels");
                    ui.horizontal(|ui| {
                        if ui.button(">>").clicked() {
                            if let Some(lbl_name) = &self.selected_avail_label {
                                if !item_labels.contains(lbl_name) {
                                    item_labels.push(lbl_name.clone());
                                    changed = true;
                                }
                            }
                        }
                        if ui.button("Remove").clicked() {
                            if let Some(lbl_name) = &self.selected_assigned_label {
                                item_labels.retain(|l| l != lbl_name);
                                self.selected_assigned_label = None;
                                changed = true;
                            }
                        }
                    });

                    egui::ScrollArea::vertical()
                        .id_salt("labels_assigned_scroll_area")
                        .max_height(100.0)
                        .show(ui, |ui| {
                            for lbl_name in item_labels.iter() {
                                let scope = workspace_labels
                                    .get(lbl_name)
                                    .and_then(|l| l.scope_name.as_deref())
                                    .unwrap_or("group");
                                let display = format!("({}) {}", scope, lbl_name);

                                let is_sel = self.selected_assigned_label.as_deref() == Some(lbl_name);
                                if ui.selectable_label(is_sel, &display).clicked() {
                                    self.selected_assigned_label = Some(lbl_name.clone());
                                }
                            }
                        });
                });
            });
        });


        changed
    }
}
