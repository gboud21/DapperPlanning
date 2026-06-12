import pytest
from unittest.mock import MagicMock
from src.domain.workspace import Workspace
from src.domain.entities import Epic, Feature, Story, Team

@pytest.fixture
def populated_workspace(empty_workspace):
    epic = Epic(id="e1", title="Epic 1", description="D1")
    feature = Feature(id="f1", title="Feature 1", description="D2", team=Team(name="Team A"))
    story = Story(id="s1", title="Login Page", description="D3", team=Team(name="Team A"), weight=3.0, gitlab_id=123, last_synced_at="2023-01-01")
    
    feature.stories.append(story)
    epic.features.append(feature)
    empty_workspace.add_epic(epic)
    return empty_workspace

def test_split_story_weight_distribution(populated_workspace):
    """Verifies that passing original weight 3 and new weight 2 correctly updates the original story and assigns weight 2 to the clone."""
    populated_workspace.split_story("s1", orig_new_weight=1.0, clone_new_weight=2.0, split_desc="Too big")
    
    epic = populated_workspace.get_epics()[0]
    feature = epic.features[0]
    assert len(feature.stories) == 2
    
    orig = feature.stories[0]
    clone = feature.stories[1]
    
    assert orig.weight == 1.0
    assert clone.weight == 2.0

def test_split_story_regex_renaming(populated_workspace):
    """Verifies that splitting 'Login Page' results in 'Login Page (Part 1 of 2)' and 'Login Page (Part 2 of 2)'."""
    populated_workspace.split_story("s1", orig_new_weight=1.5, clone_new_weight=1.5, split_desc="Split")
    
    feature = populated_workspace.get_epics()[0].features[0]
    assert feature.stories[0].title == "Login Page (Part 1 of 2)"
    assert feature.stories[1].title == "Login Page (Part 2 of 2)"

def test_split_story_clears_sync_flags(populated_workspace):
    """Asserts that the clone's gitlab_id and last_synced_at are strictly None."""
    populated_workspace.split_story("s1", orig_new_weight=1.0, clone_new_weight=2.0, split_desc="Split")
    
    feature = populated_workspace.get_epics()[0].features[0]
    clone = feature.stories[1]
    
    assert clone.gitlab_id is None
    assert clone.gitlab_iid is None
    assert clone.last_synced_at is None
    
    # Original story should also be marked as dirty
    assert feature.stories[0].last_synced_at is None

def test_move_story_updates_lists_and_flags(populated_workspace):
    """Instantiate an Epic with two Features, and attach a Story to Feature A. Call move_story to move it to Feature B. Assert that Feature A's story list is empty, Feature B's story list has len() == 1, story.parent_feature_id is updated, and story.last_synced_at is None."""
    epic = populated_workspace.get_epics()[0]
    feature_b = Feature(id="f2", title="Feature 2", description="D4", team=Team(name="Team A"))
    epic.features.append(feature_b)
    
    story = populated_workspace._find_item_by_id("s1")
    story.last_synced_at = "2023-01-01"
    
    populated_workspace.move_story("s1", "f2")
    
    feature_a = populated_workspace._find_item_by_id("f1")
    assert len(feature_a.stories) == 0
    assert len(feature_b.stories) == 1
    assert feature_b.stories[0].id == "s1"
    assert feature_b.stories[0].last_synced_at is None

def test_apply_label_recursively_adds_to_children(populated_workspace):
    """Instantiate an Epic containing a Feature containing a Story. Call apply_label_recursively on the Epic with add=True. Assert that the Epic, Feature, and Story all have the label in their labels list."""
    populated_workspace.apply_label_recursively("e1", "Epic", "Urgent", add=True)
    
    epic = populated_workspace._find_item_by_id("e1")
    feature = populated_workspace._find_item_by_id("f1")
    story = populated_workspace._find_item_by_id("s1")
    
    assert "Urgent" in epic.labels
    assert "Urgent" in feature.labels
    assert "Urgent" in story.labels
    assert story.last_synced_at is None

def test_remove_label_recursively(populated_workspace):
    """Ensure it safely removes the label without throwing errors."""
    # First add it
    populated_workspace.apply_label_recursively("e1", "Epic", "Urgent", add=True)
    # Then remove it
    populated_workspace.apply_label_recursively("e1", "Epic", "Urgent", add=False)
    
    epic = populated_workspace._find_item_by_id("e1")
    feature = populated_workspace._find_item_by_id("f1")
    story = populated_workspace._find_item_by_id("s1")
    
    assert "Urgent" not in epic.labels
    assert "Urgent" not in feature.labels
    assert "Urgent" not in story.labels

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
