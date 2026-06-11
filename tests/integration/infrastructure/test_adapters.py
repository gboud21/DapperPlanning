import pytest
import json
from src.domain.entities import Epic, Feature, Story, Team
from src.infrastructure.storage.adapters import JSONAdapter
from src.infrastructure.storage.transformers import HierarchyBuilder

def test_epic_full_serialization_cycle(tmp_path):
    """Verifies an Epic and its nested children survive serialization and deserialization without data loss."""
    test_file = tmp_path / "serialization_test.json"
    team = Team(name="Integration Team")
    
    # Create hierarchy
    original_epic = Epic(id="e1", title="Root Epic", description="Root Desc", gitlab_iid=100)
    feature = Feature(id="f1", title="Child Feature", description="Feat Desc", team=team)
    story = Story(id="s1", title="Grandchild Story", description="Story Desc", team=team)
    
    feature.stories.append(story)
    original_epic.features.append(feature)
    
    # 1. Test Export (Object -> File)
    adapter = JSONAdapter()
    adapter.export_data(str(test_file), [original_epic])
    
    # Verify file content manually to ensure asdict worked
    with open(test_file, 'r') as f:
        saved_data = json.load(f)
    
    assert saved_data["epics"][0]["id"] == "e1"
    assert len(saved_data["epics"][0]["features"]) == 1
    assert saved_data["epics"][0]["features"][0]["id"] == "f1"
    
    # 2. Test Import (File -> Object)
    # import_data returns (root_epics, active_product, products, members, deleted)
    restored_epics, _, _, _, _ = adapter.import_data(str(test_file))
    restored_epic = restored_epics[0]
    
    assert restored_epic.id == "e1"
    assert restored_epic.title == "Root Epic"
    assert len(restored_epic.features) == 1
    assert restored_epic.features[0].id == "f1"
    assert len(restored_epic.features[0].stories) == 1
    assert restored_epic.features[0].stories[0].id == "s1"
    assert restored_epic.features[0].stories[0].title == "Grandchild Story"
    assert restored_epic.features[0].team.name == "Integration Team"
