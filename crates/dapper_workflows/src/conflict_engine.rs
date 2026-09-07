use dapper_domain::Story;
use serde_json::Value;

#[derive(Debug, Clone, PartialEq)]
pub struct ItemDiff {
    pub item_id: String,
    pub has_local_changed: bool,
    pub has_remote_changed: bool,
    pub is_conflicted: bool,
    pub field_diffs: Vec<String>,
}

pub struct ConflictEngine;

impl ConflictEngine {
    pub fn evaluate_story_diff(
        local: &Story,
        remote: &Story,
        shadow: Option<&Value>,
    ) -> ItemDiff {
        let local_val = serde_json::to_value(local).unwrap_or_default();
        let remote_val = serde_json::to_value(remote).unwrap_or_default();

        let has_local_changed = match shadow {
            Some(sh) => local_val != *sh,
            None => true,
        };

        let has_remote_changed = match shadow {
            Some(sh) => remote_val != *sh,
            None => true,
        };

        let is_conflicted = has_local_changed && has_remote_changed && (local_val != remote_val);

        let mut field_diffs = Vec::new();
        if local.title != remote.title {
            field_diffs.push("title".to_string());
        }
        if local.description != remote.description {
            field_diffs.push("description".to_string());
        }
        if (local.weight - remote.weight).abs() > 1e-4 {
            field_diffs.push("weight".to_string());
        }
        if local.status != remote.status {
            field_diffs.push("status".to_string());
        }
        if local.assignee_id != remote.assignee_id {
            field_diffs.push("assignee_id".to_string());
        }
        if local.iteration_id != remote.iteration_id {
            field_diffs.push("iteration_id".to_string());
        }
        if local.labels != remote.labels {
            field_diffs.push("labels".to_string());
        }
        if local.parent_feature_id != remote.parent_feature_id {
            field_diffs.push("parent_feature_id".to_string());
        }

        ItemDiff {
            item_id: local.id.clone(),
            has_local_changed,
            has_remote_changed,
            is_conflicted,
            field_diffs,
        }
    }
}
