import pytest
from src.infrastructure.storage.transformers import GitLabTransformer
from src.domain.entities import Epic, Feature, Story

def test_transform_pull_data_hierarchy_construction():
    """
    Tests GitLabTransformer converting raw group epic and project issue JSON responses
    into domain model hierarchies (Epic -> Feature -> Story).
    """
    raw_epics = [
        {
            "id": 100,
            "iid": 10,
            "title": "Root Epic 1",
            "description": "Epic Desc",
            "labels": ["Epic", "Scope::Group"],
            "parent_id": None
        },
        {
            "id": 200,
            "iid": 20,
            "title": "Sub Feature 1",
            "description": "Feature Desc",
            "labels": ["Feature"],
            "parent_id": 100
        }
    ]

    raw_issues = [
        {
            "id": 300,
            "iid": 30,
            "title": "Issue Story 1",
            "description": "Story Desc",
            "labels": ["status::in_progress"],
            "weight": 8,
            "assignees": [{"id": 42, "username": "alice"}],
            "iteration": {"id": 500},
            "epic_iid": 20
        }
    ]

    transformer = GitLabTransformer()
    result = transformer.transform_pull_data(
        exact_epic_label="Epic",
        exact_feature_label="Feature",
        raw_epics=raw_epics,
        raw_issues=raw_issues
    )

    root_epics = result['root_epics']
    assert len(root_epics) == 1
    epic = root_epics[0]
    assert isinstance(epic, Epic)
    assert epic.gitlab_id == 100
    assert epic.title == "Root Epic 1"

    assert len(epic.features) == 1
    feat = epic.features[0]
    assert isinstance(feat, Feature)
    assert feat.gitlab_id == 200
    assert feat.title == "Sub Feature 1"

    assert len(feat.stories) == 1
    story = feat.stories[0]
    assert isinstance(story, Story)
    assert story.gitlab_id == 300
    assert story.title == "Issue Story 1"
    assert story.weight == 8.0
    assert story.assignee_id == 42
    assert story.iteration_id == 500

def test_transform_pull_data_legacy_status_resolution():
    """
    Tests legacy status label mappings when legacy_enabled=True.
    """
    raw_epics = [
        {
            "id": 100,
            "iid": 10,
            "title": "Root Epic",
            "labels": ["Epic"],
            "parent_id": None
        },
        {
            "id": 200,
            "iid": 20,
            "title": "Feature 1",
            "labels": ["Feature"],
            "parent_id": 100
        }
    ]

    raw_issues = [
        {
            "id": 301,
            "iid": 31,
            "title": "In Progress Story",
            "labels": ["workflow::wip"],
            "weight": 3,
            "epic_iid": 20
        },
        {
            "id": 302,
            "iid": 32,
            "title": "Done Story",
            "labels": ["workflow::completed"],
            "weight": 5,
            "epic_iid": 20
        }
    ]

    status_mappings = {
        "Backlog": "workflow::backlog",
        "In Progress": "workflow::wip",
        "Done": "workflow::completed"
    }

    transformer = GitLabTransformer()
    result = transformer.transform_pull_data(
        exact_epic_label="Epic",
        exact_feature_label="Feature",
        raw_epics=raw_epics,
        raw_issues=raw_issues,
        legacy_enabled=True,
        mappings=status_mappings
    )

    stories = result['root_epics'][0].features[0].stories
    assert len(stories) == 2

    s1 = next(s for s in stories if s.gitlab_id == 301)
    s2 = next(s for s in stories if s.gitlab_id == 302)

    assert s1.status == "In Progress"
    assert s2.status == "Done"

def test_transform_pull_data_orphan_triage_logic():
    """
    Tests orphan feature and orphan story triage logic.
    """
    raw_epics = [
        {
            "id": 100,
            "iid": 10,
            "title": "Root Epic 1",
            "labels": ["Epic"],
            "parent_id": None
        },
        {
            "id": 250,
            "iid": 25,
            "title": "Orphan Feature",
            "labels": ["Feature"],
            "parent_id": 9999  # Missing parent epic ID
        }
    ]

    raw_issues = [
        {
            "id": 350,
            "iid": 35,
            "title": "Direct Epic Story",
            "labels": [],
            "epic_iid": 10  # Points directly to Root Epic (no feature iid)
        },
        {
            "id": 360,
            "iid": 36,
            "title": "Completely Orphaned Story",
            "labels": [],
            "epic_iid": 999  # Points to non-existent epic/feature iid
        }
    ]

    transformer = GitLabTransformer()
    result = transformer.transform_pull_data(
        exact_epic_label="Epic",
        exact_feature_label="Feature",
        raw_epics=raw_epics,
        raw_issues=raw_issues
    )

    # 1. Orphaned features
    orphaned_features = result['orphaned_features']
    assert len(orphaned_features) == 1
    assert orphaned_features[0].gitlab_id == 250

    # 2. Direct Epic Story creates a "General Stories" feature under Root Epic
    root_epic = result['root_epics'][0]
    assert len(root_epic.features) == 1
    gen_feature = root_epic.features[0]
    assert gen_feature.title == "General Stories"
    assert len(gen_feature.stories) == 1
    assert gen_feature.stories[0].gitlab_id == 350

    # 3. Completely orphaned story
    orphaned_stories = result['orphaned_stories']
    assert len(orphaned_stories) == 1
    assert orphaned_stories[0].gitlab_id == 360
