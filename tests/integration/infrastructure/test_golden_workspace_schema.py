import os
import json
import pytest
from unittest.mock import MagicMock
from src.domain.workspace import Workspace
from src.domain.entities import (
    Epic, Feature, Story, Product, Team, Member, Label, Iteration, ProductTeam, TeamMemberCapacity, GitLabMetadata
)
from src.infrastructure.storage.json_workspace_repository import JsonWorkspaceRepository

def test_golden_workspace_schema_round_trip():
    """
    Instantiates a fully populated Workspace object with all data structures,
    exports it to tests/fixtures/golden_workspace.json, and tests round-trip loading
    using JsonWorkspaceRepository to verify data structure serialization.
    """
    dispatcher = MagicMock()
    workspace = Workspace(dispatcher)

    # 1. Setup Active Product & Products
    workspace.active_product_name = "Golden Product"
    product = Product(name="Golden Product", gitlab_project_id=101, gitlab_group_id=201)
    workspace.products = [product]

    # 2. Setup Members
    member1 = Member(id=42, name="Alice Doe", username="alice_d", group_ids=[201], project_ids=[101])
    member2 = Member(id=43, name="Bob Smith", username="bob_s", group_ids=[201], project_ids=[101])
    workspace.members = {member1.id: member1, member2.id: member2}

    # 3. Setup Labels
    label1 = Label(id=1, name="golden", color="#ff0000", description="Golden Tag", scope="group", scope_name="group1")
    workspace.labels = {"golden": label1}

    # 4. Setup Iterations & Hidden Iterations
    iteration1 = Iteration(id=301, iid=1, title="Sprint 1", start_date="2026-09-01T00:00:00", end_date="2026-09-14T00:00:00", state="opened")
    workspace.iterations = [iteration1]
    workspace.hidden_iteration_ids = [302]

    # 5. Setup Teams & Capacities
    pteam = ProductTeam(id="pt-1", name="Backend Team", product_id="prod-1", member_ids=[42, 43])
    workspace.product_teams = [pteam]

    capacity = TeamMemberCapacity(
        team_id="pt-1",
        member_id=42,
        iteration_id=301,
        pto=1,
        allocation_pct=90,
        velocity_factor=85
    )
    workspace.member_capacities = {"pt-1_42_301": capacity}

    # 6. Setup Epics, Features, Stories (Hierarchy with capabilities and boundaries)
    team_obj = Team(name="Backend Team", domain="Engineering")
    story = Story(
        id="story-gold-1",
        title="Golden Story",
        description="Golden Story Description",
        team=team_obj,
        metadata=GitLabMetadata(assignee="alice_d", milestone="v1.0", weight=5, labels=["story-label"]),
        labels=["story-label"],
        interface_boundary="REST API",
        products=["Golden Product"],
        capabilities=["Sync Engine"],
        weight=5.0,
        status="In Progress",
        assignee_id=42,
        iteration_id=301,
        parent_feature_id="feat-gold-1",
        gitlab_id=3001,
        gitlab_iid=301,
        last_synced_at="2026-09-07T12:00:00",
        is_conflicted=False
    )

    feature = Feature(
        id="feat-gold-1",
        title="Golden Feature",
        description="Golden Feature Description",
        team=team_obj,
        stories=[story],
        metadata=GitLabMetadata(labels=["feature-label"]),
        labels=["feature-label"],
        products=["Golden Product"],
        capabilities=["Sync Engine"],
        parent_epic_id="epic-gold-1",
        gitlab_id=2001,
        gitlab_iid=201,
        last_synced_at="2026-09-07T12:00:00",
        is_conflicted=False
    )

    epic = Epic(
        id="epic-gold-1",
        title="Golden Epic",
        description="Golden Epic Description",
        features=[feature],
        metadata=GitLabMetadata(labels=["golden", "epic-label"]),
        labels=["golden", "epic-label"],
        products=["Golden Product"],
        capabilities=["Core Engine", "Sync Engine"],
        gitlab_id=1001,
        gitlab_iid=101,
        last_synced_at="2026-09-07T12:00:00",
        is_conflicted=False
    )

    workspace.add_epic(epic)

    # 7. Setup deleted_remote_items & shadow_hierarchy
    workspace.deleted_remote_items = [{"type": "story", "id": 9999, "iid": 99, "project_id": 101, "group_id": 201}]
    workspace.shadow_hierarchy = {"epic-gold-1": {"id": "epic-gold-1", "title": "Golden Epic"}}

    # Target path for fixture export
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)
    golden_file_path = os.path.join(fixtures_dir, "golden_workspace.json")

    # Export using JsonWorkspaceRepository
    repo = JsonWorkspaceRepository(file_path=golden_file_path, dispatcher=dispatcher)
    repo.save(workspace)

    assert os.path.exists(golden_file_path)
    assert os.path.getsize(golden_file_path) > 0

    # Load back using fresh repository instance
    loaded_repo = JsonWorkspaceRepository(file_path=golden_file_path, dispatcher=dispatcher)
    loaded = loaded_repo.load()

    # Verification assertions
    assert loaded.active_product_name == "Golden Product"
    assert len(loaded.products) == 1
    assert loaded.products[0].name == "Golden Product"
    assert loaded.products[0].gitlab_project_id == 101
    assert loaded.products[0].gitlab_group_id == 201

    assert len(loaded.members) == 2
    assert loaded.members[42].name == "Alice Doe"
    assert loaded.members[42].username == "alice_d"

    assert len(loaded.labels) == 1
    assert loaded.labels["golden"].color == "#ff0000"

    assert len(loaded.iterations) == 1
    assert loaded.iterations[0].title == "Sprint 1"
    assert loaded.hidden_iteration_ids == [302]

    assert len(loaded.product_teams) == 1
    assert loaded.product_teams[0].name == "Backend Team"

    assert len(loaded.member_capacities) == 1
    cap_loaded = loaded.member_capacities["pt-1_42_301"]
    assert cap_loaded.pto == 1
    assert cap_loaded.allocation_pct == 90
    assert cap_loaded.velocity_factor == 85

    assert loaded.deleted_remote_items == [{"type": "story", "id": 9999, "iid": 99, "project_id": 101, "group_id": 201}]
    assert loaded.shadow_hierarchy == {"epic-gold-1": {"id": "epic-gold-1", "title": "Golden Epic"}}

    # Verify root epics & children
    loaded_epics = loaded.get_epics()
    assert len(loaded_epics) == 1
    l_epic = loaded_epics[0]
    assert l_epic.id == "epic-gold-1"
    assert l_epic.title == "Golden Epic"
    assert l_epic.capabilities == ["Core Engine", "Sync Engine"]

    assert len(l_epic.features) == 1
    l_feat = l_epic.features[0]
    assert l_feat.id == "feat-gold-1"
    assert l_feat.title == "Golden Feature"
    assert l_feat.team.name == "Backend Team"
    assert l_feat.parent_epic_id == "epic-gold-1"

    assert len(l_feat.stories) == 1
    l_story = l_feat.stories[0]
    assert l_story.id == "story-gold-1"
    assert l_story.title == "Golden Story"
    assert l_story.team.name == "Backend Team"
    assert l_story.weight == 5.0
    assert l_story.status == "In Progress"
    assert l_story.assignee_id == 42
    assert l_story.iteration_id == 301
    assert l_story.parent_feature_id == "feat-gold-1"
    assert l_story.interface_boundary == "REST API"
