import pytest
from unittest.mock import MagicMock
from src.features.integrations.sync_worker import SyncWorker
from src.core.app_context import AppContext
from src.domain.workspace import Workspace
from src.domain.entities import Epic, Product, Label, Feature, Story, Team
from src.infrastructure.api.gitlab_client import GitLabClient

@pytest.fixture
def sync_setup(mocker):
    context = AppContext()
    dispatcher = MagicMock()
    workspace = MagicMock(spec=Workspace)
    mock_client = MagicMock(spec=GitLabClient)
    mock_client.epic_sync_label = "Epic"
    mock_client.feature_sync_label = "Feature"
    mock_settings = MagicMock()
    mock_integrations = MagicMock()
    
    context.register('event_dispatcher', dispatcher)
    context.register('workspace', workspace)
    context.register('gitlab_client', mock_client)
    context.register('settings_manager', mock_settings)
    context.register('integrations_controller', mock_integrations)
    
    return context, workspace, mock_client, dispatcher, mock_settings

def test_sync_worker_pull_merges_data(sync_setup):
    """Verifies the SyncWorker correctly extracts data from the mocked client and populates the Workspace."""
    context, workspace, mock_client, dispatcher, _ = sync_setup
    
    # Configure Workspace mock
    workspace.active_product_name = "DapperPlanning"
    product = Product(name="DapperPlanning")
    product.gitlab_project_id = "888"
    product.gitlab_group_id = "999"
    workspace.products = [product]
    
    # Configure GitLabClient mock to return raw dicts as expected by GitLabTransformer
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

def test_sync_worker_pull_handles_orphans_with_triage(sync_setup, mocker):
    """Verifies that orphaned items are moved to a [Triage] bucket."""
    context, _, mock_client, dispatcher, _ = sync_setup
    workspace = Workspace(dispatcher) # Use real workspace to test find-by-title logic
    context.register('workspace', workspace) # Override the mock
    
    product = Product(name="DapperPlanning")
    product.gitlab_project_id = "888"
    product.gitlab_group_id = "999"
    workspace.products = [product]
    workspace.active_product_name = "DapperPlanning"
    
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

def test_sync_worker_member_sync(sync_setup):
    """Verifies that the SyncWorker correctly fetches and merges GitLab members."""
    context, _, mock_client, dispatcher, _ = sync_setup
    workspace = Workspace(dispatcher)
    context.register('workspace', workspace)
    
    product = Product(name="DapperPlanning")
    product.gitlab_project_id = 888
    product.gitlab_group_id = 999
    workspace.products = [product]
    workspace.active_product_name = "DapperPlanning"
    
    # Mock raw member data
    mock_client.fetch_group_members.return_value = [
        {"id": 1, "name": "Group User", "username": "guser"}
    ]
    mock_client.fetch_project_members.return_value = [
        {"id": 2, "name": "Project User", "username": "puser"},
        {"id": 1, "name": "Group User", "username": "guser"} # Overlap
    ]

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

def test_pull_does_not_duplicate_triage_buckets(sync_setup):
    """Mock a GitLab pull payload containing orphaned issues, and seed the local Workspace with an existing Epic titled '[Triage] Unassigned Items'."""
    context, _, mock_client, dispatcher, _ = sync_setup
    workspace = Workspace(dispatcher)
    context.register('workspace', workspace)
    
    triage_title = "[Triage] Unassigned Items"
    existing_triage = Epic(id="existing-triage", title=triage_title, description="Existing")
    workspace.add_epic(existing_triage)
    
    product = Product(name="DapperPlanning")
    product.gitlab_project_id = "888"
    product.gitlab_group_id = "999"
    workspace.products = [product]
    workspace.active_product_name = "DapperPlanning"
    
    mock_client.base_url = "https://fake.gitlab.com"
    mock_client.group_id = "999"
    mock_client.project_id = "888"
    mock_client.headers = {"PRIVATE-TOKEN": "fake_token"}
    
    # Mock pull with orphans
    mock_client.fetch_group_epics.return_value = []
    mock_client.fetch_project_issues.return_value = [
        {"id": 505, "iid": 5, "title": "New Orphaned Story", "description": "", "weight": 1, "epic_iid": None}
    ]
    
    worker = SyncWorker(context, sync_type="pull")
    worker._execute_pull(dry_run=False)
    
    epics = workspace.get_epics()
    assert len(epics) == 1
    assert epics[0].title == triage_title
    
    triage_feat = epics[0].features[0]
    assert any(s.title == "New Orphaned Story" for s in triage_feat.stories)

def test_worker_pushes_new_labels_before_items(sync_setup, mocker):
    """Mock gitlab_client.create_group_label. Seed the workspace with a new Label entity that has no remote ID."""
    context, _, mock_client, dispatcher, _ = sync_setup
    workspace = Workspace(dispatcher)
    context.register('workspace', workspace)
    
    product = Product(name="DapperPlanning")
    product.gitlab_project_id = 888
    product.gitlab_group_id = 999
    workspace.products = [product]
    workspace.active_product_name = "DapperPlanning"
    
    new_label = Label(id=None, name="Critical", color="#ff0000", description="", scope="group", scope_name="999")
    workspace.labels["Critical"] = new_label
    
    epic = Epic(id="e1", title="Important Epic", description="", labels=["Critical"])
    workspace.add_epic(epic)
    
    mock_client.create_group_label.return_value = {"id": 777, "name": "Critical"}
    mock_client.create_group_epic.return_value = {"id": 1001, "iid": 10}
    
    manager = MagicMock()
    manager.attach_mock(mock_client.create_group_label, 'create_label')
    manager.attach_mock(mock_client.create_group_epic, 'create_epic')
    
    worker = SyncWorker(context, sync_type="push")
    worker._execute_push()
    
    label_call_index = -1
    epic_call_index = -1
    
    for i, call in enumerate(manager.mock_calls):
        if 'create_label' in str(call):
            label_call_index = i
        if 'create_epic' in str(call):
            epic_call_index = i
            
    assert label_call_index != -1
    assert epic_call_index != -1
    assert label_call_index < epic_call_index
    assert new_label.id == 777

def test_sync_worker_dry_push(sync_setup, tmp_path, mocker):
    """Verifies that dry-push simulation correctly identifies creations, updates, conflicts, and deletions, without mutating the workspace models."""
    context, workspace, mock_client, dispatcher, mock_settings = sync_setup
    
    # 1. Configure Workspace
    workspace.active_product_name = "DapperPlanning"
    product = Product(name="DapperPlanning")
    product.gitlab_project_id = "888"
    product.gitlab_group_id = "999"
    workspace.products = [product]
    
    # Set workspace current filepath so report is written to tmp_path
    workspace.current_filepath = str(tmp_path / "workspace.json")
    
    # 2. Setup mock client response for fetch
    mock_client.base_url = "https://fake.gitlab.com"
    mock_client.group_id = "999"
    mock_client.project_id = "888"
    mock_client.headers = {"PRIVATE-TOKEN": "fake_token"}
    mock_client.epic_sync_label = "Epic"
    mock_client.feature_sync_label = "Feature"
    
    # Create domain items
    # - Local Creation (no gitlab_id)
    new_epic = Epic(id="local-epic-1", title="New Local Epic", description="Desc")
    new_epic.gitlab_id = None
    
    # - Local Update (has gitlab_id, has local changes, no remote changes)
    update_epic = Epic(id="local-epic-2", title="Updated Epic", description="Local Desc")
    update_epic.gitlab_id = 200
    
    # - Local Conflict (has gitlab_id, has local and remote changes)
    conflict_epic = Epic(id="local-epic-3", title="Conflict Epic Local", description="Local Desc")
    conflict_epic.gitlab_id = 300
    conflict_epic.is_conflicted = False # starts false
    
    # - Deleted item (tracked in deleted_remote_items)
    workspace.deleted_remote_items = [
        {'type': 'story', 'id': 400, 'iid': 4, 'project_id': 888, 'group_id': 999}
    ]
    
    # Setup shadow hierarchy (ancestors)
    workspace.shadow_hierarchy = {
        "local-epic-2": {
            "id": "local-epic-2",
            "title": "Updated Epic Original",
            "description": "Original Desc",
            "labels": [],
            "products": [],
            "capabilities": [],
            "gitlab_id": 200,
            "gitlab_iid": 2,
            "last_synced_at": None,
            "is_conflicted": False
        },
        "local-epic-3": {
            "id": "local-epic-3",
            "title": "Conflict Epic Original",
            "description": "Original Desc",
            "labels": [],
            "products": [],
            "capabilities": [],
            "gitlab_id": 300,
            "gitlab_iid": 3,
            "last_synced_at": None,
            "is_conflicted": False
        }
    }
    
    # Setup workspace all_items_iterable
    workspace.get_epics.return_value = [new_epic, update_epic, conflict_epic]
    workspace.all_items_iterable.return_value = [new_epic, update_epic, conflict_epic]
    
    # Setup remote data returning from GitLab API
    # remote epic 2: same as shadow (no remote changes)
    remote_epic_2 = {"id": 200, "iid": 2, "title": "Updated Epic Original", "description": "Original Desc", "labels": [], "parent_id": None}
    # remote epic 3: different from shadow (remote changes)
    remote_epic_3 = {"id": 300, "iid": 3, "title": "Conflict Epic Remote", "description": "Remote Desc", "labels": [], "parent_id": None}
    
    mock_client.fetch_group_epics.return_value = [remote_epic_2, remote_epic_3]
    mock_client.fetch_project_issues.return_value = []
    
    # We also mock integrations_controller.remote_data_cache
    mock_controller = context.resolve('integrations_controller')
    mock_controller.remote_data_cache = {}
    
    # Mock settings
    mock_settings.get.side_effect = lambda key, default=None: {
        'legacy_status_enabled': False,
        'status_label_mappings': {}
    }.get(key, default)
    
    # Mock logger to check info logs
    mock_logger_info = mocker.patch('src.features.integrations.sync_worker.logger.info')
    
    # 3. Instantiate and run dry-push
    worker = SyncWorker(context, sync_type="dry-push")
    worker._execute_dry_push()
    
    # 4. Verify results
    # - Model conflict flag should NOT be mutated
    assert conflict_epic.is_conflicted is False
    
    # - Report should exist and contain the counts
    report_file = tmp_path / "gitlab_dry_push_report.md"
    assert report_file.exists()
    content = report_file.read_text()
    
    assert "Creations:** 1" in content
    assert "Updates:** 1" in content
    assert "Conflicts:** 1" in content
    assert "Deletions:** 1" in content
    assert "New Local Epic" in content
    assert "Updated Epic" in content
    assert "Conflict Epic Local" in content
    
    # Verify logger.info was called with object details
    logged_messages = [call.args[0] for call in mock_logger_info.call_args_list if call.args]
    assert any("New Local Epic" in msg for msg in logged_messages)
    assert any("Updated Epic" in msg for msg in logged_messages)
    assert any("Conflict Epic Local" in msg for msg in logged_messages)
    
    # - ModelDryPushCompletedEvent should be dispatched
    from src.core.events import ModelDryPushCompletedEvent
    
    # Verify event dispatch
    dispatcher.dispatch.assert_any_call(mocker.ANY)
    # Find the specific ModelDryPushCompletedEvent call
    completed_event = None
    for call in dispatcher.dispatch.mock_calls:
        args = call[1]
        if args and isinstance(args[0], ModelDryPushCompletedEvent):
            completed_event = args[0]
            break
            
    assert completed_event is not None
    assert completed_event.creations == 1
    assert completed_event.updates == 1
    assert completed_event.conflicts == 1
    assert completed_event.deletions == 1
    assert completed_event.report_path == str(report_file)
    assert completed_event.creations_list == [new_epic]
    assert completed_event.updates_list == [update_epic]
    assert completed_event.conflicts_list == [conflict_epic]
    assert completed_event.deletions_list == [{'type': 'story', 'id': 400, 'iid': 4, 'project_id': 888, 'group_id': 999}]


