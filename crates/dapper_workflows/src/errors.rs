use thiserror::Error;

#[derive(Error, Debug)]
pub enum WorkflowError {
    #[error("Sync operation failed: {0}")]
    SyncError(String),

    #[error("GitLab integration error: {0}")]
    GitLabError(#[from] dapper_gitlab::GitLabError),

    #[error("Core error: {0}")]
    CoreError(#[from] dapper_core::CoreError),
}
