use crate::errors::PersistenceError;
use dapper_domain::Workspace;
use std::path::Path;

pub trait WorkspaceRepository: Send + Sync {
    fn load_from_file(&self, path: &Path) -> Result<Workspace, PersistenceError>;
    fn save_to_file(&self, workspace: &Workspace, path: &Path) -> Result<(), PersistenceError>;
}
