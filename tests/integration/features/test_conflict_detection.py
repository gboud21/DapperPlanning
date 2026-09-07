import pytest
from unittest.mock import MagicMock, patch
from dataclasses import asdict
from src.domain.entities import Story, Team, Epic, Feature, Product
from src.domain.workspace import Workspace
from src.features.integrations.sync_worker import SyncWorker
from src.core.app_context import AppContext

@pytest.fixture
def sync_setup():
    context = AppContext()
    dispatcher = MagicMock()
    workspace = Workspace(dispatcher)
    client = MagicMock()
    
    # Setup default sync labels on client mock
    client.epic_sync_label = "Epic"
    client.feature_sync_label = "Feature"
    
    context.register('event_dispatcher', dispatcher)
    context.register('workspace', workspace)
    context.register('gitlab_client', client)
    context.register('settings_manager', MagicMock())
    context.register('integrations_controller', MagicMock())
    
    return context, workspace, client, dispatcher

def test_conflict_detection_logic(sync_setup):
    context, workspace, client, dispatcher = sync_setup
    
    # 1. Setup Baseline (Shadow)
    team = Team(name="Team A")
    story = Story(id="s1", title="Base Title", description="Base Desc", team=team, gitlab_id=101, weight=1.0)
    workspace._epics = [Epic(id="e1", title="Epic", description="", features=[
        Feature(id="f1", title="Feat", description="", team=team, stories=[story])
    ])]
    workspace.save_shadow_hierarchy(workspace._epics)
    
    # 2. Local Mutation
    story.title = "Local Title"
    
    # 3. Mock Remote Mutation (via client fetch)
    remote_story = Story(id="gl-s-101", title="Remote Title", description="Base Desc", team=team, gitlab_id=101, weight=1.0)
    
    # Mock return from transformer (already simplified for test)
    with patch('src.features.integrations.sync_worker.GitLabTransformer') as MockTransformer:
        transformer = MockTransformer.return_value
        transformer.transform_pull_data.return_value = {
            'root_epics': [Epic(id="gl-1", title="Epic", description="", gitlab_id=1, features=[
                Feature(id="gl-f-1", title="Feat", description="", team=team, gitlab_id=2, stories=[remote_story])
            ])],
            'orphaned_features': [],
            'orphaned_stories': []
        }
        
        worker = SyncWorker(context, sync_type='push')
        workspace.active_product_name = "Prod"
        # Product MUST be a real object or have the required attributes
        workspace.products = [Product(name="Prod", gitlab_project_id=1, gitlab_group_id=1)]
        
        worker._execute_push()
        
        # Verify conflict flagged
        assert story.is_conflicted is True

def test_no_conflict_if_only_local_changed(sync_setup):
    context, workspace, client, dispatcher = sync_setup
    
    story = Story(id="s1", title="Base Title", description="Base Desc", team=Team(name="A"), gitlab_id=101)
    workspace._epics = [Epic(id="e1", title="Epic", description="", features=[
        Feature(id="f1", title="Feat", description="", team=Team(name="A"), stories=[story])
    ])]
    workspace.save_shadow_hierarchy(workspace._epics)
    
    # Local Change
    story.title = "Local Title"
    
    # Remote same as shadow
    remote_story = Story(id="gl-s-101", title="Base Title", description="Base Desc", team=Team(name="A"), gitlab_id=101)
    
    with patch('src.features.integrations.sync_worker.GitLabTransformer') as MockTransformer:
        transformer = MockTransformer.return_value
        transformer.transform_pull_data.return_value = {
            'root_epics': [Epic(id="gl-1", title="Epic", description="", gitlab_id=1, features=[
                Feature(id="gl-f-1", title="Feat", description="", team=Team(name="A"), gitlab_id=2, stories=[remote_story])
            ])],
            'orphaned_features': [],
            'orphaned_stories': []
        }
        # Mock actual push call to avoid errors
        worker = SyncWorker(context, sync_type='push')
        worker._perform_actual_push = MagicMock()
        workspace.active_product_name = "Prod"
        workspace.products = [Product(name="Prod", gitlab_project_id=1, gitlab_group_id=1)]
        
        worker._execute_push()
        
        assert story.is_conflicted is False
        worker._perform_actual_push.assert_called()


def test_subsequent_push_no_false_conflict(sync_setup):
    """Verifies shadow_hierarchy is updated after push, preventing false merge conflicts on subsequent pushes."""
    context, workspace, client, dispatcher = sync_setup
    
    settings_manager = context.resolve('settings_manager')
    settings_manager.get.side_effect = lambda key, default=None: default
    
    # 1. Setup Initial Workspace & Baseline Shadow
    team = Team(name="Team A")
    story = Story(id="s1", title="Base Title", description="Base Desc", team=team, gitlab_id=101, gitlab_iid=10, weight=1.0)
    feature = Feature(id="f1", title="Feat", description="", team=team, gitlab_id=2, gitlab_iid=20, stories=[story])
    epic = Epic(id="e1", title="Epic", description="", gitlab_id=1, gitlab_iid=30, features=[feature])
    workspace._epics = [epic]
    workspace.save_shadow_hierarchy(workspace._epics)
    workspace.active_product_name = "Prod"
    workspace.products = [Product(name="Prod", gitlab_project_id=1, gitlab_group_id=1)]
    
    assert workspace.shadow_hierarchy["s1"]["title"] == "Base Title"
    
    # 2. First Push with local modification
    story.title = "Pushed Title 1"
    
    remote_story_1 = Story(id="gl-s-101", title="Base Title", description="Base Desc", team=team, gitlab_id=101, gitlab_iid=10, weight=1.0)
    remote_epic_1 = Epic(id="gl-1", title="Epic", description="", gitlab_id=1, gitlab_iid=30, features=[
        Feature(id="gl-f-1", title="Feat", description="", team=team, gitlab_id=2, gitlab_iid=20, stories=[remote_story_1])
    ])
    
    with patch('src.features.integrations.sync_worker.GitLabTransformer') as MockTransformer:
        transformer = MockTransformer.return_value
        transformer.transform_pull_data.return_value = {
            'root_epics': [remote_epic_1],
            'orphaned_features': [],
            'orphaned_stories': []
        }
        
        worker = SyncWorker(context, sync_type='push')
        worker._execute_push()
        
        # Verify 1st push succeeded without conflict
        assert story.is_conflicted is False
        
        # Verify post-push shadow hierarchy is updated to match post-push workspace item
        assert workspace.shadow_hierarchy["s1"]["title"] == "Pushed Title 1"
        
        # 3. Second Push (Remote now has Pushed Title 1 from 1st push)
        remote_story_2 = Story(id="gl-s-101", title="Pushed Title 1", description="Base Desc", team=team, gitlab_id=101, gitlab_iid=10, weight=1.0)
        remote_epic_2 = Epic(id="gl-1", title="Epic", description="", gitlab_id=1, gitlab_iid=30, features=[
            Feature(id="gl-f-1", title="Feat", description="", team=team, gitlab_id=2, gitlab_iid=20, stories=[remote_story_2])
        ])
        transformer.transform_pull_data.return_value = {
            'root_epics': [remote_epic_2],
            'orphaned_features': [],
            'orphaned_stories': []
        }
        
        story.title = "Pushed Title 2"
        
        worker._execute_push()
        
        # Verify 2nd push has NO false merge conflict flag
        assert story.is_conflicted is False

