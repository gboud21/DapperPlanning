import pytest
from unittest.mock import MagicMock
from src.domain.workspace import Workspace
from src.domain.entities import Epic, Feature, Story, Team

@pytest.fixture
def workspace_with_hierarchy():
    dispatcher = MagicMock()
    ws = Workspace(dispatcher)
    team = Team(name="Test Team")
    
    e1 = Epic(id="e1", title="Epic 1", description="D1")
    e2 = Epic(id="e2", title="Epic 2", description="D2")
    
    f1 = Feature(id="f1", title="Feature 1", description="FD1", team=team)
    s1 = Story(id="s1", title="Story 1", description="SD1", team=team)
    
    f1.stories.append(s1)
    e1.features.append(f1)
    
    ws.add_epic(e1)
    ws.add_epic(e2)
    return ws, e1, e2, f1, s1

def test_move_feature(workspace_with_hierarchy):
    ws, e1, e2, f1, s1 = workspace_with_hierarchy
    
    # Pre-condition
    assert f1 in e1.features
    assert f1 not in e2.features
    
    # Move
    ws.move_feature("f1", "e2")
    
    # Post-condition
    assert f1 not in e1.features
    assert f1 in e2.features
    assert f1.last_synced_at is None
    # Verify dispatcher was called
    ws.dispatcher.dispatch.assert_called()

def test_move_story(workspace_with_hierarchy):
    ws, e1, e2, f1, s1 = workspace_with_hierarchy
    
    f2 = Feature(id="f2", title="Feature 2", description="FD2", team=Team(name="Team 2"))
    e2.features.append(f2)
    
    # Pre-condition
    assert s1 in f1.stories
    assert s1 not in f2.stories
    
    # Move
    ws.move_story("s1", "f2")
    
    # Post-condition
    assert s1 not in f1.stories
    assert s1 in f2.stories
    assert s1.last_synced_at is None
    # Verify dispatcher was called
    ws.dispatcher.dispatch.assert_called()

def test_move_feature_to_non_existent_epic(workspace_with_hierarchy):
    ws, e1, e2, f1, s1 = workspace_with_hierarchy
    ws.move_feature("f1", "non-existent")
    assert f1 in e1.features # Should stay where it is

def test_split_story(workspace_with_hierarchy):
    from datetime import datetime
    ws, e1, e2, f1, s1 = workspace_with_hierarchy
    s1.weight = 10.0
    s1.title = "Original Story"
    today_str = datetime.now().strftime("%m/%d/%Y")
    
    ws.split_story("s1", 6.0, 4.0, "Testing split")
    
    assert len(f1.stories) == 2
    assert f1.stories[0].id == "s1"
    assert f1.stories[0].weight == 6.0
    assert f1.stories[0].title == "Original Story (Part 1 of 2)"
    assert f"[{today_str}] **Split into:** Original Story (Part 2 of 2)" in f1.stories[0].description
    assert f"**Reason:** Testing split" in f1.stories[0].description
    
    assert f1.stories[1].weight == 4.0
    assert f1.stories[1].title == "Original Story (Part 2 of 2)"
    assert f1.stories[1].gitlab_id is None
    assert f"[{today_str}] **Split from:** Original Story (Part 1 of 2)" in f1.stories[1].description
    assert f"**Reason:** Testing split" in f1.stories[1].description
    
    # Test second split
    ws.split_story("s1", 3.0, 3.0, "Split again")
    assert len(f1.stories) == 3
    assert f1.stories[0].title == "Original Story (Part 1 of 3)"
    assert f1.stories[1].title == "Original Story (Part 2 of 3)"
    assert f1.stories[2].title == "Original Story (Part 3 of 3)"

def test_split_story_with_gitlab_iid(workspace_with_hierarchy):
    from datetime import datetime
    ws, e1, e2, f1, s1 = workspace_with_hierarchy
    s1.weight = 10.0
    s1.gitlab_iid = 123
    today_str = datetime.now().strftime("%m/%d/%Y")
    
    ws.split_story("s1", 5.0, 5.0, "Ref split")
    
    # Check the clone's description for the IID reference
    clone = f1.stories[1]
    assert f"**Split from:** {f1.stories[0].title} (#123)" in clone.description
