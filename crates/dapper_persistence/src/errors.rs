use thiserror::Error;

#[derive(Error, Debug)]
pub enum PersistenceError {
    #[error("File I/O error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("JSON serialization/deserialization error: {0}")]
    JsonError(#[from] serde_json::Error),

    #[error("Workspace path '{0}' does not exist")]
    FileNotFound(String),
}
