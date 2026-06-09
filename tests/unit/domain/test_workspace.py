import pytest
from unittest.mock import MagicMock
from src.domain.workspace import Workspace
from src.domain.entities import Epic

@pytest.fixture
def empty_workspace():
    # Workspace requires a dispatcher
    dispatcher = MagicMock()
    return Workspace(dispatcher)

def test_add_and_get_epic(empty_workspace):
    """Verifies epics can be added and retrieved by ID."""
    epic = Epic(id="e1", title="Test Epic", description="Test Description")
    empty_workspace.add_epic(epic)
    
    # Workspace uses _find_item_by_id for retrieval
    retrieved = empty_workspace._find_item_by_id("e1")
    assert retrieved is not None
    assert retrieved.title == "Test Epic"

def test_get_all_epics(empty_workspace):
    """Verifies retrieval of all root items."""
    empty_workspace.add_epic(Epic(id="1", title="E1", description="D1"))
    empty_workspace.add_epic(Epic(id="2", title="E2", description="D2"))
    
    epics = empty_workspace.get_epics()
    assert len(epics) == 2

def test_clear_workspace(empty_workspace):
    """Verifies the workspace can be safely emptied."""
    empty_workspace.add_epic(Epic(id="1", title="E1", description="D1"))
    empty_workspace.clear()
    assert len(empty_workspace.get_epics()) == 0
