#![deny(unsafe_code)]

pub mod errors;
pub mod json_repository;
pub mod repository;

pub use errors::PersistenceError;
pub use json_repository::JsonWorkspaceRepository;
pub use repository::WorkspaceRepository;
