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
