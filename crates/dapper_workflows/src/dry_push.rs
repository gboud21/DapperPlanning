use dapper_domain::Workspace;
use tracing::info;

#[derive(Debug, Clone, PartialEq, Default)]
pub struct DryPushSummary {
    pub creations_list: Vec<String>,
    pub updates_list: Vec<String>,
    pub conflicts_list: Vec<String>,
    pub deletions_list: Vec<String>,
}

pub struct DryPushEngine;

impl DryPushEngine {
    pub fn simulate_push(workspace: &Workspace) -> DryPushSummary {
        let mut summary = DryPushSummary::default();

        for epic in &workspace.epics {
            for feature in &epic.features {
                for story in &feature.stories {
                    let key = story.id.clone();
                    let shadow_entry = workspace.shadow_hierarchy.get(&key);

                    if story.is_conflicted {
                        summary.conflicts_list.push(format!("Story: {}", story.title));
                    } else if shadow_entry.is_none() || story.gitlab_id.is_none() {
                        summary.creations_list.push(format!("Story: {}", story.title));
                    } else if let Some(sh) = shadow_entry {
                        let current_val = serde_json::to_value(story).unwrap_or_default();
                        if current_val != *sh {
                            summary.updates_list.push(format!("Story: {}", story.title));
                        }
                    }
                }
            }
        }

        for deleted in &workspace.deleted_remote_items {
            if let Some(id) = deleted.get("id") {
                summary
                    .deletions_list
                    .push(format!("Deleted Remote Item ID: {}", id));
            }
        }

        info!("--- DRY PUSH SIMULATION SUMMARY ---");
        info!("Creations ({}): {:?}", summary.creations_list.len(), summary.creations_list);
        info!("Updates ({}): {:?}", summary.updates_list.len(), summary.updates_list);
        info!("Conflicts ({}): {:?}", summary.conflicts_list.len(), summary.conflicts_list);
        info!("Deletions ({}): {:?}", summary.deletions_list.len(), summary.deletions_list);

        summary
    }
}
