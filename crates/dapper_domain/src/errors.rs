use thiserror::Error;

#[derive(Error, Debug, PartialEq, Eq)]
pub enum DomainError {
    #[error("Entity with ID '{0}' not found")]
    EntityNotFound(String),

    #[error("Invalid capacity calculation: {0}")]
    InvalidCapacityInput(String),

    #[error("Permission denied for role '{role}' on action '{action}'")]
    PermissionDenied { role: String, action: String },

    #[error("Serialization error: {0}")]
    SerializationError(String),
}
