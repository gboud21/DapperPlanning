use dapper_domain::{Epic, Feature, Story};
use std::path::PathBuf;

#[derive(Debug, Clone, PartialEq)]
pub enum Command {
    // Workspace File Commands
    NewWorkspace,
    LoadWorkspace {
        path: PathBuf,
    },
    SaveWorkspace {
        path: PathBuf,
    },
    SaveWorkspaceAs {
        path: PathBuf,
    },
    ImportWorkspace {
        path: PathBuf,
        format: String,
    },
    ExportWorkspace {
        path: PathBuf,
        format: String,
    },

    // Backlog Domain Mutations & Edit Operations
    CreateEpic {
        epic: Epic,
    },
    CreateFeature {
        parent_epic_id: String,
        feature: Feature,
    },
    CreateStory {
        parent_feature_id: String,
        story: Story,
    },
    UpdateStory {
        story: Story,
    },
    DeleteStory {
        story_id: String,
    },
    CloneStory {
        story_id: String,
    },
    SplitStory {
        story_id: String,
        split_weight: f64,
    },
    ReparentStory {
        story_id: String,
        new_parent_feature_id: String,
    },

    // GitLab Synchronization & Integrations
    TriggerGitLabPull,
    TriggerGitLabPush,
    TriggerDryPush,
    ResolveConflict {
        item_id: String,
        resolved_data: serde_json::Value,
    },
}
