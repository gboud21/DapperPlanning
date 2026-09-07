#![deny(unsafe_code)]

pub mod errors;
pub mod json_repository;
pub mod repository;
pub mod settings_manager;

pub use errors::PersistenceError;
pub use json_repository::JsonWorkspaceRepository;
pub use repository::WorkspaceRepository;
pub use settings_manager::{IntegrationSettings, SettingsManager};
