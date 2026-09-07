use crate::entities::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct Workspace {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub active_product_name: Option<String>,
    #[serde(default)]
    pub products: Vec<Product>,
    #[serde(default)]
    pub members: Vec<Member>,
    #[serde(default)]
    pub labels: HashMap<String, Label>,
    #[serde(default)]
    pub iterations: Vec<Iteration>,
    #[serde(default)]
    pub hidden_iteration_ids: Vec<i64>,
    #[serde(default)]
    pub shadow_hierarchy: HashMap<String, serde_json::Value>,
    #[serde(default)]
    pub product_teams: Vec<ProductTeam>,
    #[serde(default)]
    pub member_capacities: Vec<MemberCapacity>,
    #[serde(default)]
    pub epics: Vec<Epic>,
    #[serde(default)]
    pub deleted_remote_items: Vec<serde_json::Value>,
}

impl Workspace {
    pub fn new() -> Self {
        Self::default()
    }

    /// Re-snapshots the current epic/feature/story state into shadow_hierarchy.
    pub fn save_shadow_hierarchy(&mut self) {
        self.shadow_hierarchy.clear();
        for epic in &self.epics {
            if let Ok(val) = serde_json::to_value(epic) {
                self.shadow_hierarchy.insert(epic.id.clone(), val);
            }
            for feature in &epic.features {
                if let Ok(val) = serde_json::to_value(feature) {
                    self.shadow_hierarchy.insert(feature.id.clone(), val);
                }
                for story in &feature.stories {
                    if let Ok(val) = serde_json::to_value(story) {
                        self.shadow_hierarchy.insert(story.id.clone(), val);
                    }
                }
            }
        }
    }
}
