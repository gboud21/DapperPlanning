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
    workspace._epics = [Epic(id="e1", title="Epic", description="", gitlab_id=1, features=[
        Feature(id="f1", title="Feat", description="", team=Team(name="A"), gitlab_id=2, stories=[story])
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


def test_pull_conflict_detection_when_both_diverged(sync_setup):
    context, workspace, client, dispatcher = sync_setup
    from src.core.events import ModelConflictDetectedEvent
    
    client.fetch_group_epics.return_value = []
    client.fetch_project_issues.return_value = []
    
    team = Team(name="Team A")
    story = Story(id="s1", title="Base Title", description="Base Desc", team=team, gitlab_id=101, weight=1.0)
    workspace._epics = [Epic(id="e1", title="Epic", description="", gitlab_id=1, features=[
        Feature(id="f1", title="Feat", description="", team=team, gitlab_id=2, stories=[story])
    ])]
    workspace.save_shadow_hierarchy(workspace._epics)
    workspace.active_product_name = "Prod"
    workspace.products = [Product(name="Prod", gitlab_project_id=1, gitlab_group_id=1)]
    
    # 1. Local Mutation
    story.title = "Local Title"
    
    # 2. Remote Mutation
    remote_story = Story(id="gl-s-101", title="Remote Title", description="Base Desc", team=team, gitlab_id=101, weight=1.0)
    
    with patch('src.features.integrations.sync_worker.GitLabTransformer') as MockTransformer:
        transformer = MockTransformer.return_value
        transformer.transform_pull_data.return_value = {
            'root_epics': [Epic(id="gl-1", title="Epic", description="", gitlab_id=1, features=[
                Feature(id="gl-f-1", title="Feat", description="", team=team, gitlab_id=2, stories=[remote_story])
            ])],
            'orphaned_features': [],
            'orphaned_stories': []
        }
        
        worker = SyncWorker(context, sync_type='pull')
        worker._execute_pull()
        
        # Verify conflict flagged
        assert story.is_conflicted is True
        # Verify event dispatched
        assert any(isinstance(call.args[0], ModelConflictDetectedEvent) for call in dispatcher.dispatch.call_args_list)


def test_pull_auto_acceptance_when_only_remote_changed(sync_setup):
    context, workspace, client, dispatcher = sync_setup
    
    client.fetch_group_epics.return_value = []
    client.fetch_project_issues.return_value = []
    
    team = Team(name="Team A")
    story = Story(id="s1", title="Base Title", description="Base Desc", team=team, gitlab_id=101, weight=1.0)
    workspace._epics = [Epic(id="e1", title="Epic", description="", gitlab_id=1, features=[
        Feature(id="f1", title="Feat", description="", team=team, gitlab_id=2, stories=[story])
    ])]
    workspace.save_shadow_hierarchy(workspace._epics)
    workspace.active_product_name = "Prod"
    workspace.products = [Product(name="Prod", gitlab_project_id=1, gitlab_group_id=1)]
    
    # Local item NOT modified
    # Remote item modified
    remote_story = Story(id="gl-s-101", title="Remote Updated Title", description="Remote Updated Desc", team=team, gitlab_id=101, weight=5.0)
    
    with patch('src.features.integrations.sync_worker.GitLabTransformer') as MockTransformer:
        transformer = MockTransformer.return_value
        transformer.transform_pull_data.return_value = {
            'root_epics': [Epic(id="gl-1", title="Epic", description="", gitlab_id=1, features=[
                Feature(id="gl-f-1", title="Feat", description="", team=team, gitlab_id=2, stories=[remote_story])
            ])],
            'orphaned_features': [],
            'orphaned_stories': []
        }
        
        worker = SyncWorker(context, sync_type='pull')
        worker._execute_pull()
        
        # Verify conflict is False and remote data accepted
        assert story.is_conflicted is False
        assert story.title == "Remote Updated Title"
        assert story.description == "Remote Updated Desc"
        assert story.weight == 5.0


def test_structural_diff_conflict_detection(sync_setup):
    context, workspace, client, dispatcher = sync_setup
    
    client.fetch_group_epics.return_value = []
    client.fetch_project_issues.return_value = []
    
    team = Team(name="Team A")
    feature = Feature(id="f1", title="Feat", description="", team=team, gitlab_id=2, parent_epic_id="e1")
    epic1 = Epic(id="e1", title="Epic 1", description="", gitlab_id=1, features=[feature])
    epic2 = Epic(id="e2", title="Epic 2", description="", gitlab_id=3, features=[])
    workspace._epics = [epic1, epic2]
    workspace.save_shadow_hierarchy(workspace._epics)
    workspace.active_product_name = "Prod"
    workspace.products = [Product(name="Prod", gitlab_project_id=1, gitlab_group_id=1)]
    
    # Local change in structural linkage (parent_epic_id)
    feature.parent_epic_id = "e2"
    
    # Remote change in structural linkage (parent_epic_id)
    remote_feature = Feature(id="gl-f-2", title="Feat", description="", team=team, gitlab_id=2, parent_epic_id="e3")
    
    with patch('src.features.integrations.sync_worker.GitLabTransformer') as MockTransformer:
        transformer = MockTransformer.return_value
        transformer.transform_pull_data.return_value = {
            'root_epics': [
                Epic(id="gl-1", title="Epic 1", description="", gitlab_id=1, features=[]),
                Epic(id="gl-3", title="Epic 3", description="", gitlab_id=3, features=[remote_feature])
            ],
            'orphaned_features': [],
            'orphaned_stories': []
        }
        
        worker = SyncWorker(context, sync_type='pull')
        worker._execute_pull()
        
        # Verify structural conflict flagged
        assert feature.is_conflicted is True


def test_auto_save_upon_conflict_resolution(sync_setup):
    context, workspace, client, dispatcher = sync_setup
    from src.core.events import UISaveWorkspaceRequestedEvent
    from src.features.integrations.conflict_resolution_modal import ConflictResolutionModal
    
    story = Story(id="s1", title="Local", description="", team=Team(name="A"), is_conflicted=True)
    remote_story = Story(id="s1", title="Remote", description="", team=Team(name="A"))
    workspace._epics = [Epic(id="e1", title="Epic", description="", features=[
        Feature(id="f1", title="Feat", description="", team=Team(name="A"), stories=[story])
    ])]
    workspace.save_shadow_hierarchy(workspace._epics)
    
    with patch('tkinter.StringVar'):
        with patch('tkinter.Toplevel.__init__', return_value=None):
            with patch('tkinter.Toplevel.title'):
                with patch('tkinter.Toplevel.geometry'):
                    with patch('tkinter.Toplevel.transient'):
                        with patch('tkinter.Toplevel.grab_set'):
                            with patch('tkinter.Toplevel.update_idletasks'):
                                with patch('tkinter.Toplevel.winfo_width', return_value=800):
                                    with patch('tkinter.Toplevel.winfo_height', return_value=600):
                                        with patch('tkinter.Toplevel.winfo_rootx', return_value=100):
                                            with patch('tkinter.Toplevel.winfo_rooty', return_value=100):
                                                with patch('src.features.integrations.conflict_resolution_modal.ConflictResolutionModal._setup_ui'):
                                                    modal = ConflictResolutionModal(MagicMock(), dispatcher, story, remote_story, workspace)
                                                    modal.dispatcher = dispatcher
                                                    modal.local_item = story
                                                    modal.remote_item = remote_story
                                                    modal.workspace = workspace
                                                    modal.chosen_title = MagicMock()
                                                    modal.chosen_title.get.return_value = 'local'
                                                    modal.chosen_description = MagicMock()
                                                    modal.chosen_description.get.return_value = 'local'
                                                    modal.chosen_weight = MagicMock()
                                                    modal.chosen_weight.get.return_value = 'local'
                                                    modal.chosen_status = MagicMock()
                                                    modal.chosen_status.get.return_value = 'local'
                                                    modal.chosen_assignee = MagicMock()
                                                    modal.chosen_assignee.get.return_value = 'local'
                                                    modal.chosen_iteration = MagicMock()
                                                    modal.chosen_iteration.get.return_value = 'local'
                                                    modal.chosen_labels = MagicMock()
                                                    modal.chosen_labels.get.return_value = 'local'
                                                    modal.chosen_parent_epic = MagicMock()
                                                    modal.chosen_parent_epic.get.return_value = 'local'
                                                    modal.chosen_parent_feature = MagicMock()
                                                    modal.chosen_parent_feature.get.return_value = 'local'
                                                    modal.destroy = MagicMock()
                                                    
                                                    with patch('tkinter.messagebox.askokcancel', return_value=True):
                                                        with patch('tkinter.messagebox.showinfo'):
                                                            with patch.object(workspace, 'save_shadow_hierarchy', wraps=workspace.save_shadow_hierarchy) as mock_save:
                                                                modal._on_ok_clicked()
                                                                
                                                                assert story.is_conflicted is False
                                                                assert mock_save.called
                                                                assert any(isinstance(call.args[0], UISaveWorkspaceRequestedEvent) for call in dispatcher.dispatch.call_args_list)



