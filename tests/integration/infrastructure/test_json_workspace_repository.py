import pytest
from unittest.mock import MagicMock
from src.domain.workspace import Workspace
from src.domain.entities import Epic
from src.infrastructure.storage.json_workspace_repository import JsonWorkspaceRepository

def test_repository_save_and_load_persistence(tmp_path):
    """Verifies the repository successfully writes to and reads from the filesystem."""
    # Create a temporary file path for the test
    test_file = tmp_path / "test_workspace_data.json"
    dispatcher = MagicMock()
    
    # Setup initial workspace and save
    repo = JsonWorkspaceRepository(file_path=str(test_file), dispatcher=dispatcher)
    workspace = Workspace(dispatcher)
    workspace.add_epic(Epic(id="e99", title="Disk Persistence Epic", description="Saved to Disk"))
    repo.save(workspace)
    
    # Verify the file was actually created on disk
    assert test_file.exists()
    assert test_file.stat().st_size > 0
    
    # Spin up a fresh repository to simulate an app restart
    new_repo = JsonWorkspaceRepository(file_path=str(test_file), dispatcher=dispatcher)
    loaded_workspace = new_repo.load()
    
    # Verify the data was perfectly reconstructed into memory
    epics = loaded_workspace.get_epics()
    assert len(epics) == 1
    assert epics[0].id == "e99"
    assert epics[0].title == "Disk Persistence Epic"
    assert epics[0].description == "Saved to Disk"
