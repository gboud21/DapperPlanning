import pytest
from unittest.mock import MagicMock
from src.features.integrations.sync_worker import SyncWorker
from src.core.app_context import AppContext
from src.domain.workspace import Workspace
from src.domain.entities import Epic, Product
from src.infrastructure.api.gitlab_client import GitLabClient

def test_sync_worker_pull_merges_data(mocker):
    """Verifies the SyncWorker correctly extracts data from the mocked client and populates the Workspace."""
    # 1. Setup AppContext and mocks
    context = AppContext()
    
    dispatcher = MagicMock()
    workspace = MagicMock(spec=Workspace)
    mock_client = MagicMock(spec=GitLabClient)
    
    # Configure Workspace mock
    workspace.active_product_name = "DapperPlanning"
    product = Product(name="DapperPlanning")
    product.gitlab_project_id = "888"
    product.gitlab_group_id = "999"
    workspace.products = [product]
    
    context.register('event_dispatcher', dispatcher)
    context.register('workspace', workspace)
    context.register('gitlab_client', mock_client)
    
    # 2. Configure GitLabClient mock to return raw dicts as expected by GitLabTransformer
    mock_client.base_url = "https://fake.gitlab.com"
    mock_client.group_id = "999"
    mock_client.project_id = "888"
    mock_client.headers = {"PRIVATE-TOKEN": "fake_token"}
    
    mock_client.fetch_group_epics.return_value = [
        {"id": 101, "iid": 1, "title": "Pulled Epic", "description": "Remote Description", "labels": [], "parent_id": None}
    ]
    mock_client.fetch_project_issues.return_value = []
    
    # 3. Initialize worker
    worker = SyncWorker(context, sync_type="pull")
    
    # 4. Execute the pull directly to avoid thread management in test
    worker._execute_pull(dry_run=False)
    
    # 5. Verify the workspace.merge_remote_epics was called with transformed domain objects
    args, kwargs = workspace.merge_remote_epics.call_args
    active_product_name, epics = args
    
    assert active_product_name == "DapperPlanning"
    assert len(epics) == 1
    assert epics[0].title == "Pulled Epic"
    assert epics[0].gitlab_id == 101

def test_sync_worker_pull_handles_orphans_with_triage(mocker):
    """Verifies that orphaned items are moved to a [Triage] bucket."""
    context = AppContext()
    dispatcher = MagicMock()
    workspace = Workspace(dispatcher) # Use real workspace to test find-by-title logic
    
    product = Product(name="DapperPlanning")
    product.gitlab_project_id = "888"
    product.gitlab_group_id = "999"
    workspace.products = [product]
    workspace.active_product_name = "DapperPlanning"
    
    mock_client = MagicMock(spec=GitLabClient)
    mock_client.base_url = "https://fake.gitlab.com"
    mock_client.group_id = "999"
    mock_client.project_id = "888"
    mock_client.headers = {"PRIVATE-TOKEN": "fake_token"}

    # Mock raw data with orphans
    # 1. A Feature with an unknown parent_id
    # 2. A Story with no epic_iid
    mock_client.fetch_group_epics.return_value = [
        {"id": 202, "iid": 2, "title": "Orphaned Feature", "description": "", "labels": ["Feature"], "parent_id": 9999}
    ]
    mock_client.fetch_project_issues.return_value = [
        {"id": 303, "iid": 3, "title": "Orphaned Story", "description": "", "weight": 5, "epic_iid": None}
    ]

    context.register('event_dispatcher', dispatcher)
    context.register('workspace', workspace)
    context.register('gitlab_client', mock_client)

    worker = SyncWorker(context, sync_type="pull")
    worker._execute_pull(dry_run=False)

    # Verify Triage Epic exists in workspace
    epics = workspace.get_epics()
    triage_epic = next((e for e in epics if e.title == "[Triage] Unassigned Items"), None)
    assert triage_epic is not None
    
    # Verify Orphaned Feature is inside
    assert any(f.title == "Orphaned Feature" for f in triage_epic.features)
    
    # Verify Orphaned Story is inside Triage Feature
    triage_feat = next((f for f in triage_epic.features if f.title == "[Triage] Unparented Stories"), None)
    assert triage_feat is not None
    assert any(s.title == "Orphaned Story" for s in triage_feat.stories)

def test_sync_worker_member_sync(mocker):
    """Verifies that the SyncWorker correctly fetches and merges GitLab members."""
    context = AppContext()
    dispatcher = MagicMock()
    workspace = Workspace(dispatcher)
    
    product = Product(name="DapperPlanning")
    product.gitlab_project_id = 888
    product.gitlab_group_id = 999
    workspace.products = [product]
    workspace.active_product_name = "DapperPlanning"
    
    mock_client = MagicMock(spec=GitLabClient)
    
    # Mock raw member data
    mock_client.fetch_group_members.return_value = [
        {"id": 1, "name": "Group User", "username": "guser"}
    ]
    mock_client.fetch_project_members.return_value = [
        {"id": 2, "name": "Project User", "username": "puser"},
        {"id": 1, "name": "Group User", "username": "guser"} # Overlap
    ]

    context.register('event_dispatcher', dispatcher)
    context.register('workspace', workspace)
    context.register('gitlab_client', mock_client)

    worker = SyncWorker(context, sync_type="members")
    worker._execute_member_sync()

    # Verify members in workspace
    members = workspace.get_members()
    assert len(members) == 2
    
    m1 = workspace.members[1]
    assert m1.name == "Group User"
    assert 999 in m1.group_ids
    assert 888 in m1.project_ids # Should have both if fetched from both
    
    m2 = workspace.members[2]
    assert m2.name == "Project User"
    assert 888 in m2.project_ids
    assert 999 not in m2.group_ids
