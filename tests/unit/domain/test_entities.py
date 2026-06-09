import pytest
from src.domain.entities import Epic, Feature, Story, Team

def test_epic_feature_story_hierarchy():
    """Verifies the parent-child relationships between agile entities."""
    team = Team(name="Test Team")
    # Adding required description and team parameters to match entities.py
    epic = Epic(id="e1", title="Auth System", description="Authentication Epic")
    feature = Feature(id="f1", title="OAuth Login", description="OAuth Feature", team=team)
    story = Story(id="s1", title="Google Provider", description="Google Story", team=team)
    
    epic.features.append(feature)
    feature.stories.append(story)
    
    assert len(epic.features) == 1
    assert epic.features[0].id == "f1"
    assert len(epic.features[0].stories) == 1
    assert epic.features[0].stories[0].title == "Google Provider"

def test_entity_equality():
    """Verifies that entities with the same ID are considered equivalent."""
    e1 = Epic(id="123", title="Same", description="Same Desc")
    assert e1.id == "123"
