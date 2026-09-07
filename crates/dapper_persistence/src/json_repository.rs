use crate::errors::PersistenceError;
use crate::repository::WorkspaceRepository;
use dapper_domain::Workspace;
use std::fs::File;
use std::io::{BufReader, BufWriter};
use std::path::Path;

#[derive(Debug, Default, Clone)]
pub struct JsonWorkspaceRepository;

impl JsonWorkspaceRepository {
    pub fn new() -> Self {
        Self
    }
}

impl WorkspaceRepository for JsonWorkspaceRepository {
    fn load_from_file(&self, path: &Path) -> Result<Workspace, PersistenceError> {
        if !path.exists() {
            return Err(PersistenceError::FileNotFound(
                path.to_string_lossy().to_string(),
            ));
        }

        let file = File::open(path)?;
        let reader = BufReader::new(file);
        let workspace: Workspace = serde_json::from_reader(reader)?;
        Ok(workspace)
    }

    fn save_to_file(&self, workspace: &Workspace, path: &Path) -> Result<(), PersistenceError> {
        let file = File::create(path)?;
        let writer = BufWriter::new(file);
        serde_json::to_writer_pretty(writer, workspace)?;
        Ok(())
    }
}
