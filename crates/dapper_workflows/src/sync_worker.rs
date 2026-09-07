use crate::dry_push::{DryPushEngine, DryPushSummary};
use crate::errors::WorkflowError;
use dapper_core::{AppContext, Event};
use dapper_gitlab::GitLabClientTrait;
use std::sync::Arc;
use tracing::instrument;

pub struct SyncWorker {
    app_context: AppContext,
    gitlab_client: Arc<dyn GitLabClientTrait>,
}

impl SyncWorker {
    pub fn new(app_context: AppContext, gitlab_client: Arc<dyn GitLabClientTrait>) -> Self {
        Self {
            app_context,
            gitlab_client,
        }
    }

    #[instrument(skip(self))]
    pub async fn execute_pull(&self, group_id: i64) -> Result<(), WorkflowError> {
        self.app_context
            .event_dispatcher
            .dispatch(Event::SyncStarted {
                mode: "Pull".to_string(),
            })?;

        let members = self.gitlab_client.fetch_members(group_id).await?;
        let labels = self.gitlab_client.fetch_labels(group_id).await?;
        let iterations = self.gitlab_client.fetch_iterations(group_id).await?;

        {
            let mut workspace = self.app_context.workspace.write().await;
            workspace.members = members;
            workspace.iterations = iterations;
            for label in labels {
                workspace.labels.insert(label.name.clone(), label);
            }
        }

        self.app_context
            .event_dispatcher
            .dispatch(Event::SyncCompleted {
                mode: "Pull".to_string(),
            })?;

        Ok(())
    }

    #[instrument(skip(self))]
    pub async fn execute_dry_push(&self) -> Result<DryPushSummary, WorkflowError> {
        let workspace = self.app_context.workspace.read().await;
        let summary = DryPushEngine::simulate_push(&workspace);

        let count = summary.creations_list.len()
            + summary.updates_list.len()
            + summary.deletions_list.len();

        self.app_context
            .event_dispatcher
            .dispatch(Event::DryPushCompleted {
                summary: format!(
                    "Dry push completed: {} creations, {} updates, {} conflicts, {} deletions",
                    summary.creations_list.len(),
                    summary.updates_list.len(),
                    summary.conflicts_list.len(),
                    summary.deletions_list.len()
                ),
                items_count: count,
            })?;

        Ok(summary)
    }

    #[instrument(skip(self))]
    pub async fn execute_push(&self) -> Result<(), WorkflowError> {
        self.app_context
            .event_dispatcher
            .dispatch(Event::SyncStarted {
                mode: "Push".to_string(),
            })?;

        {
            let mut workspace = self.app_context.workspace.write().await;
            // Perform actual push logic...
            // Post-push requirement: re-snapshot shadow hierarchy baseline
            workspace.save_shadow_hierarchy();
        }

        self.app_context
            .event_dispatcher
            .dispatch(Event::SyncCompleted {
                mode: "Push".to_string(),
            })?;

        Ok(())
    }
}
